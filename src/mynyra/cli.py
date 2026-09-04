"""Small operator commands; only filtered proof is printed."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from mynyra.config import ProbeError, load_credentials
from mynyra.market import QuoteCsvLog, summarize_quote_csv, write_capture
from mynyra.network import check_network


def emit(status: str, **fields):
    print(json.dumps({
        "status": status, "observed_at": datetime.now(timezone.utc).isoformat(), **fields
    }, sort_keys=True))


def positive_login(value: str) -> int:
    if not value.isascii() or not value.isdigit() or not 0 < int(value) < 2**63:
        raise argparse.ArgumentTypeError("Use a positive numeric account login.")
    return int(value)


def bounded_integer(minimum: int, maximum: int):
    def parse(value: str) -> int:
        if not value.isascii() or not value.isdigit() or not minimum <= int(value) <= maximum:
            raise argparse.ArgumentTypeError(f"Use an integer from {minimum} to {maximum}.")
        return int(value)
    return parse


def symbol_name(value: str) -> str:
    if not 1 <= len(value) <= 32 or not all(character.isalnum() or character in "._-" for character in value):
        raise argparse.ArgumentTypeError("Use a broker symbol name containing letters, numbers, dot, dash or underscore.")
    return value


def main():
    parser = argparse.ArgumentParser(
        description="Read-only cTrader checks and private market-data preparation."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("network-check", help="Verify the demo endpoint's TLS connection; no credentials.")
    audit = commands.add_parser("faraz-audit", help="Inspect Faraz chart-export ZIP files without extracting them.")
    audit.add_argument("--archive", type=Path, action="append", required=True)
    audit.add_argument("--output", type=Path, required=True, help="New JSON file; an existing file is never replaced.")
    normalize = commands.add_parser(
        "faraz-normalize", help="Convert confirmed Tehran-time Faraz CSVs to checked UTC CSVs."
    )
    normalize.add_argument("--archive", type=Path, action="append", required=True)
    normalize.add_argument(
        "--output-dir", type=Path, required=True,
        help="New private directory; an existing path is never replaced.",
    )
    validate = commands.add_parser(
        "faraz-validate", help="Recheck every normalized CSV against its manifest."
    )
    validate.add_argument("--input-dir", type=Path, required=True)
    quotes = commands.add_parser("quote-capture", help="Record fixed-interval bid/ask samples from one demo symbol.")
    quotes.add_argument("--credentials-file", type=Path, help="Private JSON file, or use CTRADER_* environment variables.")
    quotes.add_argument("--login", type=positive_login, required=True, help="Visible broker login, not the internal API account ID.")
    quotes.add_argument("--symbol", type=symbol_name, default="XAUUSD")
    quotes.add_argument("--duration-seconds", type=bounded_integer(10, 86_400), default=3_600)
    quotes.add_argument("--sample-interval-ms", type=bounded_integer(250, 60_000), default=1_000)
    quotes.add_argument("--output", type=Path, required=True, help="New CSV file; an existing file is never replaced.")
    quote_summary = commands.add_parser(
        "quote-summary", help="Validate and summarize a recorded bid/ask CSV."
    )
    quote_summary.add_argument("--input", type=Path, required=True)
    quote_summary.add_argument("--symbol", type=symbol_name)
    quote_summary.add_argument(
        "--output", type=Path, required=True,
        help="New JSON file; an existing file is never replaced.",
    )
    for command in ("app-check", "account-check", "market-capture"):
        sub = commands.add_parser(command)
        sub.add_argument("--credentials-file", type=Path, help="Private JSON file, or use CTRADER_* environment variables.")
        sub.add_argument("--timeout", type=int, choices=range(10, 121), default=45, metavar="10..120")
        if command in ("account-check", "market-capture"):
            sub.add_argument("--login", type=positive_login, required=True, help="Visible broker login, not the internal API account ID.")
        if command == "market-capture":
            sub.add_argument("--symbol", type=symbol_name, default="XAUUSD")
            sub.add_argument("--bars", type=bounded_integer(10, 5000), default=1000)
            sub.add_argument("--lookback-hours", type=bounded_integer(1, 168), default=72)
            sub.add_argument("--output", type=Path, required=True, help="New JSON file; an existing file is never replaced.")
    args = parser.parse_args()
    if args.command == "network-check":
        try:
            emit("passed", **check_network())
        except Exception as error:
            emit("failed", proof="demo_tls", error_type=type(error).__name__)
            raise SystemExit(1) from None
        return
    if args.command == "faraz-audit":
        from mynyra.datasets import audit_faraz_archives

        try:
            result = audit_faraz_archives(args.archive)
            write_capture(args.output, result)
            emit(
                "passed",
                proof="faraz_dataset_audit",
                archive_count=result["archive_count"],
                series_count=result["series_count"],
                row_count=result["row_count"],
                symbols=result["symbols"],
                timeframes=result["timeframes"],
                quality=result["quality"],
                output=str(args.output),
            )
        except ProbeError as error:
            emit("failed", error=str(error))
            raise SystemExit(1) from None
        except Exception as error:
            emit("failed", proof="faraz_dataset_audit", error_type=type(error).__name__)
            raise SystemExit(1) from None
        return
    if args.command == "faraz-normalize":
        from mynyra.datasets import normalize_faraz_archives

        try:
            result = normalize_faraz_archives(args.archive, args.output_dir)
            emit(
                "passed",
                proof="faraz_utc_normalization",
                series_count=result["series_count"],
                row_count=result["row_count"],
                ambiguous_local_rows=result["ambiguous_local_rows"],
                second_fold_rows=result["second_fold_rows"],
                nonexistent_local_rows_shifted_forward=(
                    result["nonexistent_local_rows_shifted_forward"]
                ),
                output=str(args.output_dir),
                validation=result["validation"],
            )
        except ProbeError as error:
            emit("failed", error=str(error))
            raise SystemExit(1) from None
        except Exception as error:
            emit("failed", proof="faraz_utc_normalization", error_type=type(error).__name__)
            raise SystemExit(1) from None
        return
    if args.command == "faraz-validate":
        from mynyra.datasets import validate_normalized_faraz

        try:
            emit("passed", **validate_normalized_faraz(args.input_dir))
        except ProbeError as error:
            emit("failed", error=str(error))
            raise SystemExit(1) from None
        except Exception as error:
            emit("failed", proof="normalized_faraz_validation", error_type=type(error).__name__)
            raise SystemExit(1) from None
        return
    if args.command == "quote-summary":
        try:
            result = summarize_quote_csv(args.input, args.symbol)
            write_capture(args.output, result)
            emit(
                "passed",
                proof=result["proof"],
                symbol=result["symbol"],
                row_count=result["row_count"],
                received=result["received"],
                spread_price=result["spread_price"],
                output=str(args.output),
            )
        except ProbeError as error:
            emit("failed", error=str(error))
            raise SystemExit(1) from None
        except Exception as error:
            emit("failed", proof="quote_capture_summary", error_type=type(error).__name__)
            raise SystemExit(1) from None
        return
    try:
        credentials = load_credentials(
            args.credentials_file,
            account=args.command in ("account-check", "market-capture", "quote-capture"),
        )
    except ProbeError as error:
        emit("failed", error=str(error))
        raise SystemExit(1) from None

    from twisted.internet import task
    from twisted.python.failure import Failure
    from mynyra.ctrader import start_market_capture, start_probe, start_quote_capture

    quote_log = None
    if args.command == "quote-capture":
        try:
            quote_log = QuoteCsvLog(args.output)
        except Exception as error:
            emit("failed", proof="quote_capture_write", error_type=type(error).__name__)
            raise SystemExit(1) from None

    def run(reactor):
        if args.command == "quote-capture":
            operation = start_quote_capture(
                reactor,
                credentials,
                args.login,
                args.symbol,
                args.duration_seconds,
                args.sample_interval_ms,
                quote_log.append,
            )
        elif args.command == "market-capture":
            operation = start_market_capture(
                reactor,
                credentials,
                args.login,
                args.symbol,
                args.bars,
                args.lookback_hours,
                args.timeout,
            )
        else:
            operation = start_probe(reactor, credentials, getattr(args, "login", None), args.timeout)

        def failed(failure):
            if quote_log is not None:
                quote_log.close()
            fields = {"error_type": failure.type.__name__}
            if failure.check(ProbeError):
                fields["error"] = str(failure.value)
            emit("failed", **fields)
            return Failure(SystemExit(1))

        def passed(result):
            if quote_log is not None:
                quote_log.close()
                emit("passed", **result, output=str(args.output), rows=quote_log.rows)
                return None
            if args.command != "market-capture":
                emit("passed", **result)
                return None
            try:
                write_capture(args.output, result)
            except Exception as error:
                emit("failed", proof="market_capture_write", error_type=type(error).__name__)
                return Failure(SystemExit(1))
            emit(
                "passed",
                proof="demo_market_capture",
                symbol=result["symbol"]["name"],
                period=result["period"],
                bar_count=result["bar_count"],
                first_bar_utc=result["first_bar_utc"],
                last_bar_utc=result["last_bar_utc"],
                live_quote=result["live_quote"],
                costs=result["costs"],
                limits=result["limits"],
                account=result["account"],
                output=str(args.output),
            )
            return None

        operation.addCallbacks(passed, failed)
        return operation

    task.react(run)


if __name__ == "__main__":
    main()
