import json
import tempfile
from collections import deque
from pathlib import Path
from unittest.mock import Mock, patch

from ctrader_open_api.messages import OpenApiMessages_pb2 as messages
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import SCOPE_TRADE, SCOPE_VIEW
from twisted.internet import defer, task
from twisted.trial import unittest

from mynyra.config import Credentials, ProbeError, load_credentials
from mynyra.ctrader import DemoProtocol, exchange, read_demo, select_demo_account, start_probe


def envelope(message):
    return ProtoMessage(payloadType=message.payloadType, payload=message.SerializeToString())


def granted_accounts():
    response = messages.ProtoOAGetAccountListByAccessTokenRes(
        accessToken="test-access-token", permissionScope=SCOPE_VIEW
    )
    # A live account appears first: account choice must follow explicit login.
    response.ctidTraderAccount.add(ctidTraderAccountId=100, traderLogin=999, isLive=True)
    response.ctidTraderAccount.add(ctidTraderAccountId=200, traderLogin=123, isLive=False)
    return response


class FakeClient:
    def __init__(self, responses):
        self.responses = deque(responses)
        self.requests = []

    def send(self, request, **kwargs):
        self.requests.append(request)
        return defer.succeed(envelope(self.responses.popleft()))


class ProbeTests(unittest.TestCase):
    def test_application_auth_stops_before_account_access(self):
        client = FakeClient([messages.ProtoOAApplicationAuthRes()])
        result = self.successResultOf(read_demo(client, Credentials("id", "secret"), None))
        self.assertTrue(result["application_authenticated"])
        self.assertFalse(result["account_authenticated"])
        self.assertEqual(len(client.requests), 1)

    def test_demo_read_resolves_login_and_exact_money_precision(self):
        trader = messages.ProtoOATraderRes(ctidTraderAccountId=200)
        trader.trader.ctidTraderAccountId = 200
        trader.trader.traderLogin = 123
        trader.trader.balance = 300001
        trader.trader.moneyDigits = 2
        trader.trader.depositAssetId = 4
        assets = messages.ProtoOAAssetListRes(ctidTraderAccountId=200)
        assets.asset.add(assetId=4, name="USD")
        symbols = messages.ProtoOASymbolsListRes(ctidTraderAccountId=200)
        symbols.symbol.add(symbolId=42, symbolName="EXAMPLE")
        client = FakeClient([
            messages.ProtoOAApplicationAuthRes(), granted_accounts(),
            messages.ProtoOAAccountAuthRes(ctidTraderAccountId=200), trader, assets, symbols,
        ])
        result = self.successResultOf(read_demo(client, Credentials("id", "secret", "token"), 123))
        self.assertEqual(result["balance"], "3000.01")
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["ctid_trader_account_id"], 200)
        self.assertEqual(result["account_login"], 123)
        self.assertEqual(result["symbol_count"], 1)
        self.assertNotIn("token", json.dumps(result))
        self.assertEqual(client.requests[2].ctidTraderAccountId, 200)

    def test_live_account_is_rejected(self):
        self.assertRaises(ProbeError, select_demo_account, granted_accounts(), 999)

    def test_missing_and_ambiguous_logins_are_rejected(self):
        response = granted_accounts()
        self.assertRaises(ProbeError, select_demo_account, response, 456)
        response.ctidTraderAccount.add(ctidTraderAccountId=201, traderLogin=123, isLive=False)
        self.assertRaises(ProbeError, select_demo_account, response, 123)

    def test_unknown_demo_status_and_broader_permissions_are_rejected(self):
        response = granted_accounts()
        response.ctidTraderAccount[1].ClearField("isLive")
        self.assertRaises(ProbeError, select_demo_account, response, 123)
        response = granted_accounts()
        response.permissionScope = SCOPE_TRADE
        self.assertRaises(ProbeError, select_demo_account, response, 123)
        response.ClearField("permissionScope")
        self.assertRaises(ProbeError, select_demo_account, response, 123)

    def test_mismatched_account_auth_stops_following_reads(self):
        client = FakeClient([
            messages.ProtoOAApplicationAuthRes(), granted_accounts(),
            messages.ProtoOAAccountAuthRes(ctidTraderAccountId=100),
        ])
        self.failureResultOf(read_demo(client, Credentials("id", "secret", "token"), 123), ProbeError)
        self.assertEqual(len(client.requests), 3)

    def test_order_request_never_reaches_transport(self):
        client = FakeClient([])
        self.failureResultOf(exchange(client, messages.ProtoOANewOrderReq()), ProbeError)
        self.assertEqual(client.requests, [])

    def test_remote_error_cannot_echo_a_secret(self):
        client = FakeClient([messages.ProtoOAErrorRes(errorCode="ERROR", description="private-token-value")])
        failure = self.failureResultOf(exchange(client, messages.ProtoOAApplicationAuthReq()), ProbeError)
        self.assertNotIn("private-token-value", str(failure.value))

    def test_unexpected_response_is_not_counted_as_success(self):
        client = FakeClient([messages.ProtoOAVersionRes(version="test")])
        self.failureResultOf(exchange(client, messages.ProtoOAApplicationAuthReq()), ProbeError)

    def test_timeout_stops_an_unconnected_service(self):
        clock = task.Clock()
        client = Mock()
        client.whenConnected.return_value = defer.Deferred()
        with patch("mynyra.ctrader.make_demo_client", return_value=client), patch(
            "mynyra.ctrader.ClientService.stopService", return_value=defer.succeed(None)
        ) as stop:
            operation = start_probe(clock, Credentials("id", "secret"), None, 10)
            clock.advance(10)
            self.failureResultOf(operation, defer.TimeoutError)
            stop.assert_called_once_with(client)

    def test_disconnect_fails_instead_of_reporting_success(self):
        clock = task.Clock()
        client = Mock()
        client.whenConnected.return_value = defer.Deferred()
        with patch("mynyra.ctrader.make_demo_client", return_value=client), patch(
            "mynyra.ctrader.ClientService.stopService", return_value=defer.succeed(None)
        ) as stop:
            operation = start_probe(clock, Credentials("id", "secret"), None, 10)
            client.setDisconnectedCallback.call_args.args[0](client, "disconnected")
            self.failureResultOf(operation, defer.CancelledError)
            stop.assert_called_once_with(client)

    def test_outbound_queue_is_not_shared_between_connections(self):
        first, second = DemoProtocol(), DemoProtocol()
        first._send_queue.append("pending")
        self.assertEqual(len(second._send_queue), 0)


class CredentialTests(unittest.TestCase):
    def test_repr_and_invalid_config_do_not_disclose_credentials(self):
        self.assertNotIn("private-secret", repr(Credentials("id", "private-secret", "private-token")))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "credentials.json"
            path.write_text('{"client_secret":"private-secret", malformed')
            path.chmod(0o600)
            error = self.assertRaises(ProbeError, load_credentials, path, account=True)
            self.assertNotIn("private-secret", str(error))

    def test_readable_by_others_is_rejected_and_owner_only_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "credentials.json"
            path.write_text(json.dumps({"client_id": "id", "client_secret": "secret"}))
            path.chmod(0o644)
            self.assertRaises(ProbeError, load_credentials, path, account=False)
            path.chmod(0o600)
            credentials = load_credentials(path, account=False)
            self.assertEqual(credentials.client_id, "id")
            self.assertRaises(ProbeError, load_credentials, path, account=True)
