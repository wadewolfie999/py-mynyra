"""The only boundary that knows cTrader messages and the pinned SDK's internals."""

from collections import deque
from decimal import Decimal

from ctrader_open_api import Client, Protobuf, TcpProtocol
from ctrader_open_api.messages import OpenApiMessages_pb2 as messages
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoErrorRes
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import SCOPE_VIEW
from twisted.application.internet import ClientService
from twisted.internet import defer, task
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet.ssl import optionsForClientTLS

from mynyra.config import Credentials, ProbeError
from mynyra.network import DEMO_HOST, DEMO_PORT

READ_REQUESTS = {
    messages.ProtoOAApplicationAuthReq: messages.ProtoOAApplicationAuthRes,
    messages.ProtoOAGetAccountListByAccessTokenReq: messages.ProtoOAGetAccountListByAccessTokenRes,
    messages.ProtoOAAccountAuthReq: messages.ProtoOAAccountAuthRes,
    messages.ProtoOATraderReq: messages.ProtoOATraderRes,
    messages.ProtoOAAssetListReq: messages.ProtoOAAssetListRes,
    messages.ProtoOASymbolsListReq: messages.ProtoOASymbolsListRes,
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
