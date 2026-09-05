import json
import tempfile
from collections import deque
from pathlib import Path

from ctrader_open_api.messages import OpenApiMessages_pb2 as messages
from ctrader_open_api.messages import OpenApiModelMessages_pb2 as models
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from twisted.internet import defer, task
from twisted.trial import unittest

from mynyra.config import Credentials, ProbeError
from mynyra.ctrader import (
    describe_expected_margin,
    describe_symbol,
    read_market_capture,
    read_quote_stream,
    select_symbol,
)
from mynyra.market import (
    QuoteCsvLog,
    decode_trendbars,
    summarize_quote_csv,
    write_capture,
)


def envelope(message):
    return ProtoMessage(payloadType=message.payloadType, payload=message.SerializeToString())


class EventClient:
    def __init__(self, responses, spot_event):
        self.responses = deque(responses)
        self.spot_event = spot_event
        self.requests = []
        self.callback = None

    def setMessageReceivedCallback(self, callback):
        self.callback = callback

    def send(self, request, **kwargs):
        self.requests.append(request)
        response = self.responses.popleft()
        if isinstance(request, messages.ProtoOASubscribeSpotsReq):
            self.callback(self, envelope(self.spot_event))
        return defer.succeed(envelope(response))


def granted_accounts():
    response = messages.ProtoOAGetAccountListByAccessTokenRes(
        accessToken="test-token", permissionScope=models.SCOPE_VIEW
    )
    response.ctidTraderAccount.add(ctidTraderAccountId=200, traderLogin=123, isLive=False)
    return response


class MarketTests(unittest.TestCase):
    def test_quote_csv_is_owner_only_append_only_and_labeled(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quotes.csv"
            log = QuoteCsvLog(path)
            self.assertRaises(ProbeError, log.append, {"symbol": "XAUUSD"})
            log.append({
                "received_at_utc": "2026-01-01T00:00:00+00:00",
                "source_timestamp_ms": 1,
                "symbol": "XAUUSD",
                "bid": "3000.00",
                "ask": "3000.10",
                "spread_price": "0.10",
                "spread_pips": "10",
            })
            log.close()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn("source_timestamp_ms", path.read_text())
            self.assertIn("XAUUSD,3000.00,3000.10,0.10,10", path.read_text())
            self.assertRaises(FileExistsError, QuoteCsvLog, path)

    def test_quote_stream_samples_view_only_spots_without_orders(self):
        symbols = messages.ProtoOASymbolsListRes(ctidTraderAccountId=200)
        symbols.symbol.add(symbolId=42, symbolName="XAUUSD", enabled=True)
        full = messages.ProtoOASymbolByIdRes(ctidTraderAccountId=200)
        full.symbol.add(symbolId=42, digits=2, pipPosition=2)
        spot = messages.ProtoOASpotEvent(
            ctidTraderAccountId=200,
            symbolId=42,
            bid=300000000,
            ask=300010000,
            timestamp=1_800_000,
        )
        client = EventClient([
            messages.ProtoOAApplicationAuthRes(),
            granted_accounts(),
            messages.ProtoOAAccountAuthRes(ctidTraderAccountId=200),
            symbols,
            full,
            messages.ProtoOASubscribeSpotsRes(ctidTraderAccountId=200),
            messages.ProtoOAUnsubscribeSpotsRes(ctidTraderAccountId=200),
        ], spot)
        clock = task.Clock()
        samples = []
        operation = read_quote_stream(
            client,
            clock,
            Credentials("id", "secret", "token"),
            123,
            "XAUUSD",
            2,
            1000,
            samples.append,
        )
        clock.advance(2)
        result = self.successResultOf(operation)
        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(samples[0]["bid"], "3000.00")
        self.assertEqual(samples[0]["ask"], "3000.10")
        self.assertEqual(samples[0]["spread_pips"], "10")
        request_types = {type(request) for request in client.requests}
        self.assertNotIn(messages.ProtoOANewOrderReq, request_types)

    def test_quote_stream_does_not_claim_untimestamped_data(self):
        symbols = messages.ProtoOASymbolsListRes(ctidTraderAccountId=200)
        symbols.symbol.add(symbolId=42, symbolName="XAUUSD", enabled=True)
        full = messages.ProtoOASymbolByIdRes(ctidTraderAccountId=200)
        full.symbol.add(symbolId=42, digits=2, pipPosition=2)
        spot = messages.ProtoOASpotEvent(
            ctidTraderAccountId=200,
            symbolId=42,
            bid=300000000,
            ask=300010000,
        )
        client = EventClient([
            messages.ProtoOAApplicationAuthRes(),
            granted_accounts(),
            messages.ProtoOAAccountAuthRes(ctidTraderAccountId=200),
            symbols,
            full,
            messages.ProtoOASubscribeSpotsRes(ctidTraderAccountId=200),
            messages.ProtoOAUnsubscribeSpotsRes(ctidTraderAccountId=200),
        ], spot)
        clock = task.Clock()
        operation = read_quote_stream(
            client,
            clock,
            Credentials("id", "secret", "token"),
            123,
            "XAUUSD",
            2,
            1000,
            lambda _quote: None,
        )
        clock.advance(2)
        self.failureResultOf(operation, ProbeError)

    def test_quote_summary_validates_spreads_and_reports_distribution(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quotes.csv"
            log = QuoteCsvLog(path)
            log.append({
                "received_at_utc": "2026-01-01T00:00:00.100000+00:00",
                "source_timestamp_ms": 1767225600000,
                "symbol": "XAUUSD",
                "bid": "3000.00",
                "ask": "3000.10",
                "spread_price": "0.10",
                "spread_pips": "10",
            })
            log.append({
                "received_at_utc": "2026-01-01T00:00:01.100000+00:00",
                "source_timestamp_ms": 1767225601000,
                "symbol": "XAUUSD",
                "bid": "3000.10",
                "ask": "3000.30",
                "spread_price": "0.20",
                "spread_pips": "20",
            })
            log.close()
            result = summarize_quote_csv(path, "XAUUSD")
            self.assertEqual(result["row_count"], 2)
            self.assertEqual(result["spread_price"]["median"], "0.15")
            self.assertEqual(result["prices"]["implied_pip_size"], "0.01")
            self.assertEqual(result["timing"]["gaps_over_1_5_seconds"], 0)
            self.assertEqual(len(result["capture_sha256"]), 64)

    def test_quote_summary_rejects_incorrect_spread_math(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quotes.csv"
            path.write_text(
                ",".join((
                    "received_at_utc", "source_timestamp_ms", "symbol", "bid", "ask",
                    "spread_price", "spread_pips",
                ))
                + "\n2026-01-01T00:00:00+00:00,1,XAUUSD,1,2,0.5,50\n"
            )
            self.assertRaises(ProbeError, summarize_quote_csv, path, "XAUUSD")

    def test_trendbars_are_exact_and_sorted(self):
        later = models.ProtoOATrendbar(
            volume=8, low=300000000, deltaOpen=100, deltaHigh=500,
            deltaClose=200, utcTimestampInMinutes=20,
        )
        earlier = models.ProtoOATrendbar(
            volume=5, low=299000000, deltaOpen=300, deltaHigh=700,
            deltaClose=400, utcTimestampInMinutes=10,
        )
        rows = decode_trendbars([later, earlier], digits=2)
        self.assertEqual(rows[0]["timestamp_utc"], "1970-01-01T00:10:00+00:00")
        self.assertEqual(rows[0]["open"], "2990.00")
        self.assertEqual(rows[0]["high"], "2990.01")
        self.assertEqual(rows[1]["close"], "3000.00")
        self.assertEqual(rows[1]["tick_volume"], 8)

    def test_incomplete_and_duplicate_bars_fail(self):
        incomplete = models.ProtoOATrendbar(volume=1)
        self.assertRaises(ProbeError, decode_trendbars, [incomplete], 2)
        complete = models.ProtoOATrendbar(
            volume=1, low=1, deltaOpen=0, deltaHigh=0,
            deltaClose=0, utcTimestampInMinutes=1,
        )
        self.assertRaises(ProbeError, decode_trendbars, [complete, complete], 2)

    def test_disabled_symbol_is_rejected(self):
        symbols = messages.ProtoOASymbolsListRes(ctidTraderAccountId=200)
        symbols.symbol.add(symbolId=42, symbolName="XAUUSD", enabled=False)
        self.assertRaises(ProbeError, select_symbol, symbols, "XAUUSD")

    def test_symbol_costs_and_limits_are_scaled_and_labeled(self):
        symbol = models.ProtoOASymbol(
            symbolId=42,
            digits=2,
            pipPosition=1,
            minVolume=100,
            maxVolume=10_000,
            stepVolume=100,
            lotSize=10_000,
            commissionType=models.USD_PER_LOT,
            preciseTradingCommissionRate=350_000_000,
            preciseMinCommission=25_000_000,
            minCommissionAsset="USD",
            minCommissionType=models.CURRENCY,
            swapCalculationType=models.PIPS,
            swapLong=-12.5,
            swapShort=3.25,
            tradingMode=models.ENABLED,
        )
        trader = models.ProtoOATrader(
            ctidTraderAccountId=200,
            balance=300000,
            depositAssetId=1,
            leverageInCents=2500,
            accountType=models.HEDGED,
        )
        result = describe_symbol(symbol, trader)
        self.assertEqual(result["costs"]["commission_rate"], "3.50000000")
        self.assertEqual(result["costs"]["commission_type"], "USD_PER_LOT")
        self.assertEqual(result["costs"]["minimum_commission"], "0.25000000")
        self.assertEqual(result["limits"]["minimum_volume_units"], "1.00")
        self.assertEqual(result["limits"]["lot_size_units"], "100.00")
        self.assertEqual(result["account"]["leverage"], "25.00")

        leverage = models.ProtoOADynamicLeverage(leverageId=9)
        leverage.tiers.add(volume=10_000_000, leverage=40_000)
        result = describe_symbol(symbol, trader, leverage)
        self.assertEqual(result["limits"]["dynamic_leverage_tiers"], [{
            "up_to_usd_notional": "100000.00", "leverage_raw": 40_000,
        }])

        margins = messages.ProtoOAExpectedMarginRes(ctidTraderAccountId=200, moneyDigits=2)
        margins.margin.add(volume=100, buyMargin=17948, sellMargin=17948)
        self.assertEqual(describe_expected_margin(margins, 100, "USD"), {
            "volume_units": "1.00",
            "buy_margin": "179.48",
            "sell_margin": "179.48",
            "currency": "USD",
        })

    def test_read_market_capture_is_view_only_and_collects_quote(self):
        trader = messages.ProtoOATraderRes(ctidTraderAccountId=200)
        trader.trader.ctidTraderAccountId = 200
        trader.trader.traderLogin = 123
        trader.trader.balance = 300000
        trader.trader.depositAssetId = 1
        trader.trader.leverageInCents = 2500
        assets = messages.ProtoOAAssetListRes(ctidTraderAccountId=200)
        assets.asset.add(assetId=1, name="USD")
        symbols = messages.ProtoOASymbolsListRes(ctidTraderAccountId=200)
        symbols.symbol.add(symbolId=42, symbolName="XAUUSD", enabled=True)
        full = messages.ProtoOASymbolByIdRes(ctidTraderAccountId=200)
        full.symbol.add(
            symbolId=42, digits=2, pipPosition=1, minVolume=100,
            maxVolume=10_000, stepVolume=100, lotSize=10_000,
        )
        bars = messages.ProtoOAGetTrendbarsRes(
            ctidTraderAccountId=200,
            period=models.M1,
            timestamp=1,
            symbolId=42,
        )
        bars.trendbar.add(
            volume=7, low=300000000, deltaOpen=100, deltaHigh=500,
            deltaClose=200, utcTimestampInMinutes=20,
        )
        spot = messages.ProtoOASpotEvent(
            ctidTraderAccountId=200,
            symbolId=42,
            bid=300000000,
            ask=300010000,
            timestamp=1_800_000,
        )
        margins = messages.ProtoOAExpectedMarginRes(ctidTraderAccountId=200, moneyDigits=2)
        margins.margin.add(volume=100, buyMargin=12000, sellMargin=12000)
        client = EventClient([
            messages.ProtoOAApplicationAuthRes(),
            granted_accounts(),
            messages.ProtoOAAccountAuthRes(ctidTraderAccountId=200),
            trader,
            assets,
            symbols,
            full,
            bars,
            messages.ProtoOASubscribeSpotsRes(ctidTraderAccountId=200),
            messages.ProtoOAUnsubscribeSpotsRes(ctidTraderAccountId=200),
            margins,
        ], spot)
        result = self.successResultOf(read_market_capture(
            client, task.Clock(), Credentials("id", "secret", "token"),
            123, "XAUUSD", 100, 24,
        ))
        self.assertEqual(result["symbol"]["name"], "XAUUSD")
        self.assertEqual(result["bar_count"], 1)
        self.assertEqual(result["live_quote"]["bid"], "3000.00")
        self.assertEqual(result["live_quote"]["ask"], "3000.10")
        self.assertEqual(result["live_quote"]["spread_pips"], "1")
        self.assertEqual(
            result["limits"]["minimum_volume_expected_margin"]["buy_margin"], "120.00"
        )
        request_types = {type(request) for request in client.requests}
        self.assertNotIn(messages.ProtoOANewOrderReq, request_types)
        self.assertNotIn("token", json.dumps(result))

    def test_capture_refuses_to_replace_a_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "capture.json"
            write_capture(path, {"first": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertRaises(FileExistsError, write_capture, path, {"second": True})
            self.assertEqual(json.loads(path.read_text()), {"first": True})
