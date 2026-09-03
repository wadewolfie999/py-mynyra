"""Small operator commands; only filtered proof is printed."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from mynyra.config import ProbeError, load_credentials
from mynyra.network import check_network


def emit(status: str, **fields):
    print(json.dumps({
        "status": status, "observed_at": datetime.now(timezone.utc).isoformat(), **fields
    }, sort_keys=True))


def positive_login(value: str) -> int:
    if not value.isascii() or not value.isdigit() or not 0 < int(value) < 2**63:
        raise argparse.ArgumentTypeError("Use a positive numeric account login.")
    return int(value)


def main():
    parser = argparse.ArgumentParser(description="Read-only cTrader demo connection checks.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("network-check", help="Verify the demo endpoint's TLS connection; no credentials.")
    for command in ("app-check", "account-check"):
        sub = commands.add_parser(command)
        sub.add_argument("--credentials-file", type=Path, help="Private JSON file, or use CTRADER_* environment variables.")
        sub.add_argument("--timeout", type=int, choices=range(10, 121), default=45, metavar="10..120")
        if command == "account-check":
            sub.add_argument("--login", type=positive_login, required=True, help="Visible broker login, not the internal API account ID.")
    args = parser.parse_args()
    if args.command == "network-check":
        try:
            emit("passed", **check_network())
        except Exception as error:
            emit("failed", proof="demo_tls", error_type=type(error).__name__)
            raise SystemExit(1) from None
        return
    try:
        credentials = load_credentials(args.credentials_file, account=args.command == "account-check")
    except ProbeError as error:
        emit("failed", error=str(error))
        raise SystemExit(1) from None

    from twisted.internet import task
    from twisted.python.failure import Failure
    from mynyra.ctrader import start_probe

    def run(reactor):
        operation = start_probe(reactor, credentials, getattr(args, "login", None), args.timeout)

        def failed(failure):
            fields = {"error_type": failure.type.__name__}
            if failure.check(ProbeError):
                fields["error"] = str(failure.value)
            emit("failed", **fields)
            return Failure(SystemExit(1))

        operation.addCallbacks(lambda result: emit("passed", **result), failed)
        return operation

    task.react(run)
