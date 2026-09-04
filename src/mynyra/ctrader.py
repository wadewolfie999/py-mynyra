"""The only boundary that knows cTrader messages and the pinned SDK's internals."""

from collections import deque
from datetime import datetime, timezone
from decimal import Decimal

from ctrader_open_api import Client, Protobuf, TcpProtocol
from ctrader_open_api.messages import OpenApiMessages_pb2 as messages
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoErrorRes
from ctrader_open_api.messages import OpenApiModelMessages_pb2 as models
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import SCOPE_VIEW
from twisted.application.internet import ClientService
from twisted.internet import defer, task
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet.ssl import optionsForClientTLS

from mynyra.config import Credentials, ProbeError
from mynyra.market import RELATIVE_PRICE_SCALE, decimal_text, decode_trendbars, price_text
from mynyra.network import DEMO_HOST, DEMO_PORT

READ_REQUESTS = {
    messages.ProtoOAApplicationAuthReq: messages.ProtoOAApplicationAuthRes,
    messages.ProtoOAGetAccountListByAccessTokenReq: messages.ProtoOAGetAccountListByAccessTokenRes,
    messages.ProtoOAAccountAuthReq: messages.ProtoOAAccountAuthRes,
    messages.ProtoOATraderReq: messages.ProtoOATraderRes,
    messages.ProtoOAAssetListReq: messages.ProtoOAAssetListRes,
    messages.ProtoOASymbolsListReq: messages.ProtoOASymbolsListRes,
    messages.ProtoOASymbolByIdReq: messages.ProtoOASymbolByIdRes,
    messages.ProtoOAGetTrendbarsReq: messages.ProtoOAGetTrendbarsRes,
    messages.ProtoOASubscribeSpotsReq: messages.ProtoOASubscribeSpotsRes,
    messages.ProtoOAUnsubscribeSpotsReq: messages.ProtoOAUnsubscribeSpotsRes,
    messages.ProtoOAGetDynamicLeverageByIDReq: messages.ProtoOAGetDynamicLeverageByIDRes,
    messages.ProtoOAExpectedMarginReq: messages.ProtoOAExpectedMarginRes,
}


class DemoProtocol(TcpProtocol):
    def __init__(self):
        super().__init__()
        # SDK 0.9.2 otherwise shares the outbound queue between connections.
        self._send_queue = deque()


def make_demo_client(reactor) -> Client:
    client = Client(DEMO_HOST, DEMO_PORT, DemoProtocol)
    # SDK 0.9.2 builds an ssl: endpoint without the hostname-verification option.
    # Confine this pinned-version adaptation to one place; never send secrets
    # through its default endpoint. Twisted buffers writes until TLS completes.
    client._endpoint = SSL4ClientEndpoint(
        reactor, DEMO_HOST, DEMO_PORT, optionsForClientTLS(DEMO_HOST), timeout=10
    )
    return client


@defer.inlineCallbacks
def exchange(client, request):
    expected = READ_REQUESTS.get(type(request))
    if expected is None:
        raise ProbeError("This probe only permits its fixed authentication and read requests.")
    envelope = yield client.send(request, responseTimeoutInSeconds=10)
    try:
        response = Protobuf.extract(envelope)
    except Exception:
        raise ProbeError("cTrader returned an unreadable protocol response.") from None
    if isinstance(response, (messages.ProtoOAErrorRes, ProtoErrorRes)):
        # Remote error descriptions and account-list replies can contain tokens.
        raise ProbeError(f"cTrader rejected {type(request).__name__}; check credentials and authorization.")
    if not isinstance(response, expected) or not response.IsInitialized():
        raise ProbeError(f"Unexpected or incomplete response to {type(request).__name__}.")
    return response


def select_demo_account(response, login: int):
    if not response.HasField("permissionScope") or response.permissionScope != SCOPE_VIEW:
        raise ProbeError("The account probe requires a token explicitly reported as view-only.")
    matches = [account for account in response.ctidTraderAccount if account.traderLogin == login]
    if len(matches) != 1:
        raise ProbeError("The requested login did not resolve to exactly one authorized account.")
    account = matches[0]
    if not account.HasField("isLive") or account.isLive:
        raise ProbeError("The selected account is live or its demo status is unconfirmed.")
    if account.ctidTraderAccountId <= 0:
        raise ProbeError("cTrader returned an invalid internal account identifier.")
    return account


def check_account_id(response, account_id: int):
    if response.ctidTraderAccountId != account_id:
        raise ProbeError("Response account identifier does not match the selected demo account.")


def select_symbol(response, name: str):
    matches = [symbol for symbol in response.symbol if symbol.symbolName.casefold() == name.casefold()]
    if len(matches) != 1:
        raise ProbeError(f"The requested symbol {name!r} did not resolve to exactly one active symbol.")
    symbol = matches[0]
    if symbol.symbolId <= 0:
        raise ProbeError("cTrader returned an invalid symbol identifier.")
    if symbol.HasField("enabled") and not symbol.enabled:
        raise ProbeError(f"The requested symbol {name!r} is disabled for this account.")
    return symbol


def enum_name(message, field: str, enum) -> str | None:
    return enum.Name(getattr(message, field)) if message.HasField(field) else None


def volume_text(raw: int) -> str:
    return decimal_text(Decimal(raw).scaleb(-2))


def describe_symbol(symbol, trader, dynamic_leverage=None) -> dict:
    if (
        symbol.symbolId <= 0
        or not symbol.HasField("digits")
        or not 0 <= symbol.digits <= 8
    ):
        raise ProbeError("cTrader returned unsupported symbol metadata.")
    if not symbol.HasField("pipPosition") or not 0 <= symbol.pipPosition <= 8:
        raise ProbeError("cTrader returned unsupported pip precision.")
    commission_type = enum_name(symbol, "commissionType", models.ProtoOACommissionType)
    commission_rate = None
    if symbol.HasField("preciseTradingCommissionRate"):
        scale = -5 if commission_type == "PERCENTAGE_OF_VALUE" else -8
        commission_rate = decimal_text(
            Decimal(symbol.preciseTradingCommissionRate).scaleb(scale)
        )
    quote = {
        "commission_rate": commission_rate,
        "commission_type": commission_type,
        "minimum_commission": (
            decimal_text(Decimal(symbol.preciseMinCommission).scaleb(-8))
            if symbol.HasField("preciseMinCommission") else None
        ),
        "minimum_commission_asset": (
            symbol.minCommissionAsset if symbol.HasField("minCommissionAsset") else None
        ),
        "minimum_commission_type": enum_name(
            symbol, "minCommissionType", models.ProtoOAMinCommissionType
        ),
        "swap_calculation": enum_name(
            symbol, "swapCalculationType", models.ProtoOASwapCalculationType
        ),
        "swap_long": str(symbol.swapLong) if symbol.HasField("swapLong") else None,
        "swap_short": str(symbol.swapShort) if symbol.HasField("swapShort") else None,
        "triple_swap_day": enum_name(symbol, "swapRollover3Days", models.ProtoOADayOfWeek),
        "swap_period_hours": symbol.swapPeriod if symbol.HasField("swapPeriod") else None,
        "swap_time_minutes_from_utc_midnight": (
            symbol.swapTime if symbol.HasField("swapTime") else None
        ),
        "pnl_conversion_fee_percent": (
            decimal_text(Decimal(symbol.pnlConversionFeeRate).scaleb(-2))
            if symbol.HasField("pnlConversionFeeRate") else None
        ),
    }
    limits = {
        "minimum_volume_units": volume_text(symbol.minVolume) if symbol.HasField("minVolume") else None,
        "maximum_volume_units": volume_text(symbol.maxVolume) if symbol.HasField("maxVolume") else None,
        "volume_step_units": volume_text(symbol.stepVolume) if symbol.HasField("stepVolume") else None,
        "lot_size_units": volume_text(symbol.lotSize) if symbol.HasField("lotSize") else None,
        "maximum_exposure_raw": symbol.maxExposure if symbol.HasField("maxExposure") else None,
        "short_selling_enabled": (
            symbol.enableShortSelling if symbol.HasField("enableShortSelling") else None
        ),
        "trading_mode": enum_name(symbol, "tradingMode", models.ProtoOATradingMode),
        "minimum_stop_loss_distance_raw": symbol.slDistance if symbol.HasField("slDistance") else None,
        "minimum_take_profit_distance_raw": symbol.tpDistance if symbol.HasField("tpDistance") else None,
        "distance_unit": enum_name(symbol, "distanceSetIn", models.ProtoOASymbolDistanceType),
        "schedule_time_zone": symbol.scheduleTimeZone if symbol.HasField("scheduleTimeZone") else None,
        "trading_intervals": [
            {"start_second": interval.startSecond, "end_second": interval.endSecond}
            for interval in symbol.schedule
        ],
    }
    account = {
        "leverage": (
            decimal_text(Decimal(trader.leverageInCents).scaleb(-2))
            if trader.HasField("leverageInCents") else None
        ),
        "swap_free": trader.swapFree if trader.HasField("swapFree") else None,
        "account_type": enum_name(trader, "accountType", models.ProtoOAAccountType),
        "limited_risk": trader.isLimitedRisk if trader.HasField("isLimitedRisk") else None,
    }
    if dynamic_leverage is not None:
        limits["dynamic_leverage_tiers"] = [
            {"up_to_usd_notional": volume_text(tier.volume), "leverage_raw": tier.leverage}
            for tier in dynamic_leverage.tiers
        ]
    return {"costs": quote, "limits": limits, "account": account}


def describe_expected_margin(response, volume: int, currency: str) -> dict:
    matches = [margin for margin in response.margin if margin.volume == volume]
    if len(matches) != 1:
        raise ProbeError("Expected margin did not match the requested minimum volume.")
    margin = matches[0]
    if not response.HasField("moneyDigits") or not 0 <= response.moneyDigits <= 18:
        raise ProbeError("Expected margin precision was not supplied or is unsupported.")
    return {
        "volume_units": volume_text(volume),
        "buy_margin": decimal_text(Decimal(margin.buyMargin).scaleb(-response.moneyDigits)),
        "sell_margin": decimal_text(Decimal(margin.sellMargin).scaleb(-response.moneyDigits)),
        "currency": currency,
    }


@defer.inlineCallbacks
def authenticate_demo_account(client, credentials: Credentials, login: int):
    yield exchange(client, messages.ProtoOAApplicationAuthReq(
        clientId=credentials.client_id, clientSecret=credentials.client_secret
    ))
    accounts = yield exchange(client, messages.ProtoOAGetAccountListByAccessTokenReq(
        accessToken=credentials.access_token
    ))
    account = select_demo_account(accounts, login)
    authorized = yield exchange(client, messages.ProtoOAAccountAuthReq(
        ctidTraderAccountId=account.ctidTraderAccountId, accessToken=credentials.access_token
    ))
    check_account_id(authorized, account.ctidTraderAccountId)
    return account.ctidTraderAccountId


@defer.inlineCallbacks
def wait_for_quote(
    client, reactor, account_id: int, symbol_id: int, digits: int, pip_position: int
):
    quote = defer.Deferred()
    latest = {}

    def received(_client, envelope):
        if quote.called:
            return
        try:
            event = Protobuf.extract(envelope)
        except Exception:
            return
        if not isinstance(event, messages.ProtoOASpotEvent):
            return
        if event.ctidTraderAccountId != account_id or event.symbolId != symbol_id:
            return
        if event.HasField("bid"):
            latest["bid"] = event.bid
        if event.HasField("ask"):
            latest["ask"] = event.ask
        if event.HasField("timestamp"):
            latest["timestamp"] = event.timestamp
        if "bid" in latest and "ask" in latest:
            quote.callback(dict(latest))

    client.setMessageReceivedCallback(received)
    subscribed = False
    try:
        response = yield exchange(client, messages.ProtoOASubscribeSpotsReq(
            ctidTraderAccountId=account_id,
            symbolId=[symbol_id],
            subscribeToSpotTimestamp=True,
        ))
        check_account_id(response, account_id)
        subscribed = True
        raw = yield quote.addTimeout(8, reactor)
    finally:
        client.setMessageReceivedCallback(lambda _client, _message: None)
        if subscribed:
            response = yield exchange(client, messages.ProtoOAUnsubscribeSpotsReq(
                ctidTraderAccountId=account_id, symbolId=[symbol_id]
            ))
            check_account_id(response, account_id)
    bid = Decimal(raw["bid"]) / Decimal("100000")
    ask = Decimal(raw["ask"]) / Decimal("100000")
    if ask < bid:
        raise ProbeError("cTrader returned a quote with ask below bid.")
    pip_size = Decimal(1).scaleb(-pip_position)
    return {
        "bid": price_text(raw["bid"], digits),
        "ask": price_text(raw["ask"], digits),
        "spread_price": decimal_text(ask - bid),
        "spread_pips": decimal_text((ask - bid) / pip_size),
        "source_timestamp_ms": raw.get("timestamp"),
    }


@defer.inlineCallbacks
def read_quote_stream(
    client,
    reactor,
    credentials: Credentials,
    login: int,
    symbol_name: str,
    duration_seconds: int,
    sample_interval_ms: int,
    on_quote,
):
    """Sample the newest complete quote at a fixed interval for one bounded run."""
    account_id = yield authenticate_demo_account(client, credentials, login)
    symbols = yield exchange(client, messages.ProtoOASymbolsListReq(
        ctidTraderAccountId=account_id, includeArchivedSymbols=False
    ))
    check_account_id(symbols, account_id)
    light = select_symbol(symbols, symbol_name)
    full_response = yield exchange(client, messages.ProtoOASymbolByIdReq(
        ctidTraderAccountId=account_id, symbolId=[light.symbolId]
    ))
    check_account_id(full_response, account_id)
    full = [symbol for symbol in full_response.symbol if symbol.symbolId == light.symbolId]
    if len(full) != 1:
        raise ProbeError("The quote symbol did not resolve to exactly one full symbol record.")
    symbol = full[0]
    if (
        not symbol.HasField("digits")
        or not 0 <= symbol.digits <= 8
        or not symbol.HasField("pipPosition")
        or not 0 <= symbol.pipPosition <= 8
    ):
        raise ProbeError("cTrader returned unsupported quote precision.")

    latest = {}
    revision = 0
    sampled_revision = 0
    event_count = 0
    sample_count = 0
    done = defer.Deferred()

    def received(_client, envelope):
        nonlocal revision, event_count
        try:
            event = Protobuf.extract(envelope)
        except Exception:
            return
        if not isinstance(event, messages.ProtoOASpotEvent):
            return
        if event.ctidTraderAccountId != account_id or event.symbolId != light.symbolId:
            return
        changed = False
        if event.HasField("bid"):
            latest["bid"] = event.bid
            changed = True
        if event.HasField("ask"):
            latest["ask"] = event.ask
            changed = True
        if changed:
            if event.HasField("timestamp"):
                latest["timestamp"] = event.timestamp
            else:
                latest.pop("timestamp", None)
            revision += 1
            event_count += 1

    def sample():
        nonlocal sampled_revision, sample_count
        if (
            revision == sampled_revision
            or "bid" not in latest
            or "ask" not in latest
            or "timestamp" not in latest
        ):
            return
        bid = Decimal(latest["bid"]) / RELATIVE_PRICE_SCALE
        ask = Decimal(latest["ask"]) / RELATIVE_PRICE_SCALE
        if ask < bid:
            raise ProbeError("cTrader returned a quote with ask below bid.")
        pip_size = Decimal(1).scaleb(-symbol.pipPosition)
        on_quote({
            "received_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_timestamp_ms": latest.get("timestamp"),
            "symbol": light.symbolName,
            "bid": price_text(latest["bid"], symbol.digits),
            "ask": price_text(latest["ask"], symbol.digits),
            "spread_price": decimal_text(ask - bid),
            "spread_pips": decimal_text((ask - bid) / pip_size),
        })
        sampled_revision = revision
        sample_count += 1

    client.setMessageReceivedCallback(received)
    sampling = task.LoopingCall(sample)
    sampling.clock = reactor
    stop_call = None
    subscribed = False
    try:
        response = yield exchange(client, messages.ProtoOASubscribeSpotsReq(
            ctidTraderAccountId=account_id,
            symbolId=[light.symbolId],
            subscribeToSpotTimestamp=True,
        ))
        check_account_id(response, account_id)
        subscribed = True
        sampling_done = sampling.start(sample_interval_ms / 1000, now=True)

        def sampling_failed(failure):
            if not done.called:
                done.errback(failure)
            return None

        sampling_done.addErrback(sampling_failed)
        stop_call = reactor.callLater(
            duration_seconds, lambda: None if done.called else done.callback(None)
        )
        yield done
    finally:
        if stop_call is not None and stop_call.active():
            stop_call.cancel()
        if sampling.running:
            sampling.stop()
        client.setMessageReceivedCallback(lambda _client, _message: None)
        if subscribed:
            response = yield exchange(client, messages.ProtoOAUnsubscribeSpotsReq(
                ctidTraderAccountId=account_id, symbolId=[light.symbolId]
            ))
            check_account_id(response, account_id)
    if sample_count == 0:
        raise ProbeError("No complete quote arrived during the capture window.")
    return {
        "proof": "demo_quote_capture",
        "symbol": light.symbolName,
        "duration_seconds": duration_seconds,
        "sample_interval_ms": sample_interval_ms,
        "spot_event_count": event_count,
        "sample_count": sample_count,
    }


@defer.inlineCallbacks
def read_market_capture(
    client,
    reactor,
    credentials: Credentials,
    login: int,
    symbol_name: str,
    bar_count: int,
    lookback_hours: int,
):
    account_id = yield authenticate_demo_account(client, credentials, login)
    snapshot = yield exchange(client, messages.ProtoOATraderReq(ctidTraderAccountId=account_id))
    check_account_id(snapshot, account_id)
    trader = snapshot.trader
    if trader.ctidTraderAccountId != account_id or trader.traderLogin != login:
        raise ProbeError("Trader snapshot does not match the selected account and login.")
    assets = yield exchange(client, messages.ProtoOAAssetListReq(ctidTraderAccountId=account_id))
    check_account_id(assets, account_id)
    currencies = [asset.name for asset in assets.asset if asset.assetId == trader.depositAssetId]
    if len(currencies) != 1:
        raise ProbeError("Account deposit currency could not be resolved.")
    currency = currencies[0]

    symbols = yield exchange(client, messages.ProtoOASymbolsListReq(
        ctidTraderAccountId=account_id, includeArchivedSymbols=False
    ))
    check_account_id(symbols, account_id)
    light = select_symbol(symbols, symbol_name)
    full_response = yield exchange(client, messages.ProtoOASymbolByIdReq(
        ctidTraderAccountId=account_id, symbolId=[light.symbolId]
    ))
    check_account_id(full_response, account_id)
    full = [symbol for symbol in full_response.symbol if symbol.symbolId == light.symbolId]
    if len(full) != 1:
        raise ProbeError("The requested symbol did not resolve to exactly one full symbol record.")
    symbol = full[0]

    dynamic_leverage = None
    if symbol.HasField("leverageId"):
        leverage_response = yield exchange(client, messages.ProtoOAGetDynamicLeverageByIDReq(
            ctidTraderAccountId=account_id, leverageId=symbol.leverageId
        ))
        check_account_id(leverage_response, account_id)
        if leverage_response.leverage.leverageId != symbol.leverageId:
            raise ProbeError("Dynamic leverage details do not match the requested symbol.")
        dynamic_leverage = leverage_response.leverage

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    to_timestamp = (now_ms // 60_000) * 60_000 - 1
    from_timestamp = max(0, to_timestamp - lookback_hours * 3_600_000)
    trendbars = yield exchange(client, messages.ProtoOAGetTrendbarsReq(
        ctidTraderAccountId=account_id,
        fromTimestamp=from_timestamp,
        toTimestamp=to_timestamp,
        period=models.ProtoOATrendbarPeriod.Value("M1"),
        symbolId=light.symbolId,
        count=bar_count,
    ))
    check_account_id(trendbars, account_id)
    if trendbars.period != models.ProtoOATrendbarPeriod.Value("M1"):
        raise ProbeError("cTrader returned an unexpected bar period.")
    if trendbars.HasField("symbolId") and trendbars.symbolId != light.symbolId:
        raise ProbeError("Historical prices do not match the requested symbol.")
    bars = decode_trendbars(trendbars.trendbar, symbol.digits)
    if not bars:
        raise ProbeError("cTrader returned no M1 bars for the requested window.")

    live_quote = yield wait_for_quote(
        client, reactor, account_id, light.symbolId, symbol.digits, symbol.pipPosition
    )
    description = describe_symbol(symbol, trader, dynamic_leverage)
    if symbol.HasField("minVolume"):
        margin_response = yield exchange(client, messages.ProtoOAExpectedMarginReq(
            ctidTraderAccountId=account_id,
            symbolId=light.symbolId,
            volume=[symbol.minVolume],
        ))
        check_account_id(margin_response, account_id)
        description["limits"]["minimum_volume_expected_margin"] = describe_expected_margin(
            margin_response, symbol.minVolume, currency
        )
    return {
        "schema_version": 1,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "service": "cTrader Open API",
            "environment": "demo",
            "broker": trader.brokerName if trader.HasField("brokerName") else None,
        },
        "symbol": {
            "name": light.symbolName,
            "description": light.description if light.HasField("description") else None,
            "symbol_id": light.symbolId,
            "digits": symbol.digits,
            "pip_position": symbol.pipPosition,
            "enabled": light.enabled if light.HasField("enabled") else None,
        },
        "period": "M1",
        "request": {
            "requested_bar_count": bar_count,
            "lookback_hours": lookback_hours,
            "from_timestamp_ms": from_timestamp,
            "to_timestamp_ms": to_timestamp,
            "server_has_more": (
                trendbars.hasMore
                if "hasMore" in trendbars.DESCRIPTOR.fields_by_name
                and trendbars.HasField("hasMore")
                else None
            ),
        },
        "bar_count": len(bars),
        "first_bar_utc": bars[0]["timestamp_utc"],
        "last_bar_utc": bars[-1]["timestamp_utc"],
        "bars": bars,
        "live_quote": live_quote,
        **description,
    }


def start_market_capture(
    reactor,
    credentials: Credentials,
    login: int,
    symbol_name: str,
    bar_count: int,
    lookback_hours: int,
    timeout: int,
):
    """One bounded, read-only market capture; a dropped connection fails the run."""
    client = make_demo_client(reactor)
    heartbeat = None

    @defer.inlineCallbacks
    def connect_and_read():
        nonlocal heartbeat
        client.startService()
        protocol = yield client.whenConnected(failAfterFailures=1)
        heartbeat = task.LoopingCall(protocol.heartbeat)
        heartbeat.clock = reactor
        heartbeat.start(10, now=False)
        return (yield read_market_capture(
            client, reactor, credentials, login, symbol_name, bar_count, lookback_hours
        ))

    operation = connect_and_read()
    operation.addTimeout(timeout, reactor)

    def disconnected(_client, _reason):
        if not operation.called:
            operation.cancel()

    client.setDisconnectedCallback(disconnected)

    def cleanup(outcome):
        if heartbeat is not None and heartbeat.running:
            heartbeat.stop()
        stopped = defer.maybeDeferred(ClientService.stopService, client)
        stopped.addBoth(lambda _: outcome)
        return stopped

    operation.addBoth(cleanup)
    return operation


def start_quote_capture(
    reactor,
    credentials: Credentials,
    login: int,
    symbol_name: str,
    duration_seconds: int,
    sample_interval_ms: int,
    on_quote,
):
    """One bounded, read-only quote stream with fixed-interval sampling."""
    client = make_demo_client(reactor)
    heartbeat = None

    @defer.inlineCallbacks
    def connect_and_read():
        nonlocal heartbeat
        client.startService()
        protocol = yield client.whenConnected(failAfterFailures=1)
        heartbeat = task.LoopingCall(protocol.heartbeat)
        heartbeat.clock = reactor
        heartbeat.start(10, now=False)
        return (yield read_quote_stream(
            client,
            reactor,
            credentials,
            login,
            symbol_name,
            duration_seconds,
            sample_interval_ms,
            on_quote,
        ))

    operation = connect_and_read()
    operation.addTimeout(duration_seconds + 60, reactor)

    def disconnected(_client, _reason):
        if not operation.called:
            operation.cancel()

    client.setDisconnectedCallback(disconnected)

    def cleanup(outcome):
        if heartbeat is not None and heartbeat.running:
            heartbeat.stop()
        stopped = defer.maybeDeferred(ClientService.stopService, client)
        stopped.addBoth(lambda _: outcome)
        return stopped

    operation.addBoth(cleanup)
    return operation


@defer.inlineCallbacks
def read_demo(client, credentials: Credentials, login: int | None):
    yield exchange(client, messages.ProtoOAApplicationAuthReq(
        clientId=credentials.client_id, clientSecret=credentials.client_secret
    ))
    result = {
        "proof": "application_auth",
        "endpoint": f"{DEMO_HOST}:{DEMO_PORT}",
        "application_authenticated": True,
        "account_authenticated": False,
    }
    if login is None:
        return result
    accounts = yield exchange(client, messages.ProtoOAGetAccountListByAccessTokenReq(
        accessToken=credentials.access_token
    ))
    account = select_demo_account(accounts, login)
    account_id = account.ctidTraderAccountId
    authorized = yield exchange(client, messages.ProtoOAAccountAuthReq(
        ctidTraderAccountId=account_id, accessToken=credentials.access_token
    ))
    check_account_id(authorized, account_id)
    snapshot = yield exchange(client, messages.ProtoOATraderReq(ctidTraderAccountId=account_id))
    check_account_id(snapshot, account_id)
    trader = snapshot.trader
    if trader.ctidTraderAccountId != account_id or trader.traderLogin != login:
        raise ProbeError("Trader snapshot does not match the selected account and login.")
    if not trader.HasField("moneyDigits") or not 0 <= trader.moneyDigits <= 18:
        raise ProbeError("Balance precision was not supplied or is unsupported.")
    assets = yield exchange(client, messages.ProtoOAAssetListReq(ctidTraderAccountId=account_id))
    check_account_id(assets, account_id)
    currency = [asset.name for asset in assets.asset if asset.assetId == trader.depositAssetId]
    if len(currency) != 1:
        raise ProbeError("Account deposit currency could not be resolved.")
    symbols = yield exchange(client, messages.ProtoOASymbolsListReq(
        ctidTraderAccountId=account_id, includeArchivedSymbols=False
    ))
    check_account_id(symbols, account_id)
    return {
        **result,
        "proof": "demo_account_read",
        "account_authenticated": True,
        "account_login": login,
        "ctid_trader_account_id": account_id,
        "scope": "accounts",
        "balance": str(Decimal(trader.balance).scaleb(-trader.moneyDigits)),
        "currency": currency[0],
        "symbol_count": len(symbols.symbol),
    }


def start_probe(reactor, credentials: Credentials, login: int | None, timeout: int):
    """One bounded connection; a dropped connection fails this run."""
    client = make_demo_client(reactor)
    heartbeat = None

    @defer.inlineCallbacks
    def connect_and_read():
        nonlocal heartbeat
        client.startService()
        protocol = yield client.whenConnected(failAfterFailures=1)
        heartbeat = task.LoopingCall(protocol.heartbeat)
        heartbeat.clock = reactor
        heartbeat.start(10, now=False)
        return (yield read_demo(client, credentials, login))

    operation = connect_and_read()
    operation.addTimeout(timeout, reactor)

    def disconnected(_client, _reason):
        if not operation.called:
            operation.cancel()

    client.setDisconnectedCallback(disconnected)

    def cleanup(outcome):
        if heartbeat is not None and heartbeat.running:
            heartbeat.stop()
        # Bypass SDK stopService's isConnected guard: pending connections and
        # reconnection attempts must also stop after timeout or failure.
        stopped = defer.maybeDeferred(ClientService.stopService, client)
        stopped.addBoth(lambda _: outcome)
        return stopped

    operation.addBoth(cleanup)
    return operation
