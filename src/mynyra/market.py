"""Pure conversion and persistence for cTrader market captures."""

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from mynyra.config import ProbeError


RELATIVE_PRICE_SCALE = Decimal("100000")
QUOTE_COLUMNS = (
    "received_at_utc",
    "source_timestamp_ms",
    "symbol",
    "bid",
    "ask",
    "spread_price",
    "spread_pips",
)


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def price_text(relative: int, digits: int) -> str:
    if not 0 <= digits <= 8:
        raise ProbeError("The symbol uses unsupported price precision.")
    value = Decimal(relative) / RELATIVE_PRICE_SCALE
    return format(value.quantize(Decimal(1).scaleb(-digits)), f".{digits}f")


def decode_trendbars(trendbars, digits: int) -> list[dict]:
    rows = []
    seen = set()
    for bar in trendbars:
        required = ("low", "deltaOpen", "deltaHigh", "deltaClose", "utcTimestampInMinutes")
        if any(not bar.HasField(field) for field in required):
            raise ProbeError("cTrader returned an incomplete M1 price bar.")
        if bar.utcTimestampInMinutes in seen:
            raise ProbeError("cTrader returned duplicate M1 bar timestamps.")
        seen.add(bar.utcTimestampInMinutes)
        low = bar.low
        rows.append({
            "timestamp_utc": datetime.fromtimestamp(
                bar.utcTimestampInMinutes * 60, timezone.utc
            ).isoformat(),
            "open": price_text(low + bar.deltaOpen, digits),
            "high": price_text(low + bar.deltaHigh, digits),
            "low": price_text(low, digits),
            "close": price_text(low + bar.deltaClose, digits),
            "tick_volume": bar.volume,
        })
    rows.sort(key=lambda row: row["timestamp_utc"])
    return rows


def write_capture(path: Path, payload: dict) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    created = False
    try:
        with path.open("x", encoding="utf-8") as stream:
            created = True
            os.chmod(path, 0o600)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        if created and path.exists():
            path.unlink()
        raise


def _short_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _quantile(ordered: list[Decimal], numerator: int, denominator: int) -> Decimal:
    position = Decimal(len(ordered) - 1) * Decimal(numerator) / Decimal(denominator)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _distribution(values: list[Decimal]) -> dict:
    ordered = sorted(values)
    return {
        "min": _short_decimal(ordered[0]),
        "p05": _short_decimal(_quantile(ordered, 5, 100)),
        "p25": _short_decimal(_quantile(ordered, 25, 100)),
        "median": _short_decimal(_quantile(ordered, 50, 100)),
        "mean": _short_decimal(sum(ordered) / len(ordered)),
        "p75": _short_decimal(_quantile(ordered, 75, 100)),
        "p95": _short_decimal(_quantile(ordered, 95, 100)),
        "p99": _short_decimal(_quantile(ordered, 99, 100)),
        "max": _short_decimal(ordered[-1]),
    }


def _timedelta_microseconds(later: datetime, earlier: datetime) -> int:
    delta = later - earlier
    return ((delta.days * 86_400 + delta.seconds) * 1_000_000) + delta.microseconds


def summarize_quote_csv(path: Path, expected_symbol: str | None = None) -> dict:
    """Validate a quote capture and return exact, reproducible distributions."""
    path = path.expanduser()
    if not path.is_file() or path.is_symlink():
        raise ProbeError("The quote capture does not exist or is unsafe.")
    row_count = 0
    symbol = None
    first_received = None
    last_received = None
    first_source_ms = None
    last_source_ms = None
    previous_received = None
    previous_source_ms = None
    bid_min = None
    bid_max = None
    ask_min = None
    ask_max = None
    spreads = []
    spread_pips = []
    zero_spread_rows = 0
    gaps_seconds = []
    latencies_ms = []
    implied_pip_size = None

    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != QUOTE_COLUMNS:
            raise ProbeError("The quote capture has the wrong CSV header.")
        for line_number, row in enumerate(reader, start=2):
            try:
                if None in row or any(row[key] is None for key in QUOTE_COLUMNS):
                    raise ValueError("wrong column count")
                received = datetime.fromisoformat(
                    row["received_at_utc"].replace("Z", "+00:00")
                )
                source_ms = int(row["source_timestamp_ms"])
                bid = Decimal(row["bid"])
                ask = Decimal(row["ask"])
                spread = Decimal(row["spread_price"])
                pips = Decimal(row["spread_pips"])
            except (InvalidOperation, TypeError, ValueError) as error:
                raise ProbeError(
                    f"The quote capture has a malformed row at line {line_number}."
                ) from error
            if received.utcoffset() != timezone.utc.utcoffset(received):
                raise ProbeError("A quote receive timestamp is not UTC.")
            if (
                source_ms <= 0
                or not all(value.is_finite() for value in (bid, ask, spread, pips))
                or ask < bid
                or spread < 0
                or pips < 0
                or spread != ask - bid
            ):
                raise ProbeError(f"The quote capture has invalid values at line {line_number}.")
            if pips == 0:
                if spread != 0:
                    raise ProbeError("The quote capture has inconsistent spread units.")
            else:
                row_pip_size = spread / pips
                if implied_pip_size is None:
                    implied_pip_size = row_pip_size
                elif row_pip_size != implied_pip_size:
                    raise ProbeError("The quote capture has inconsistent pip sizes.")
            row_symbol = row["symbol"]
            if not row_symbol or (symbol is not None and row_symbol != symbol):
                raise ProbeError("The quote capture contains inconsistent symbols.")
            symbol = symbol or row_symbol
            if expected_symbol is not None and row_symbol != expected_symbol:
                raise ProbeError("The quote capture is for an unexpected symbol.")
            if previous_received is not None:
                if received <= previous_received:
                    raise ProbeError("Quote receive timestamps are not strictly increasing.")
                if source_ms < previous_source_ms:
                    raise ProbeError("Quote source timestamps move backward.")
                gaps_seconds.append(
                    Decimal(_timedelta_microseconds(received, previous_received))
                    / Decimal(1_000_000)
                )
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            received_ms = Decimal(_timedelta_microseconds(received, epoch)) / Decimal(1_000)
            latencies_ms.append(received_ms - source_ms)
            spreads.append(spread)
            spread_pips.append(pips)
            zero_spread_rows += spread == 0
            bid_min = bid if bid_min is None else min(bid_min, bid)
            bid_max = bid if bid_max is None else max(bid_max, bid)
            ask_min = ask if ask_min is None else min(ask_min, ask)
            ask_max = ask if ask_max is None else max(ask_max, ask)
            first_received = first_received or received
            first_source_ms = first_source_ms or source_ms
            last_received = received
            last_source_ms = source_ms
            previous_received = received
            previous_source_ms = source_ms
            row_count += 1
    if not row_count:
        raise ProbeError("The quote capture contains no quote rows.")
    received_duration = Decimal(
        _timedelta_microseconds(last_received, first_received)
    ) / Decimal(1_000_000)
    return {
        "schema_version": 1,
        "proof": "quote_capture_summary",
        "capture_filename": path.name,
        "capture_sha256": _file_sha256(path),
        "symbol": symbol,
        "row_count": row_count,
        "received": {
            "first_utc": first_received.isoformat(),
            "last_utc": last_received.isoformat(),
            "duration_seconds": _short_decimal(received_duration),
        },
        "source": {
            "first_timestamp_ms": first_source_ms,
            "last_timestamp_ms": last_source_ms,
            "duration_seconds": _short_decimal(
                Decimal(last_source_ms - first_source_ms) / Decimal(1_000)
            ),
        },
        "prices": {
            "bid_min": _short_decimal(bid_min),
            "bid_max": _short_decimal(bid_max),
            "ask_min": _short_decimal(ask_min),
            "ask_max": _short_decimal(ask_max),
            "implied_pip_size": (
                _short_decimal(implied_pip_size) if implied_pip_size is not None else None
            ),
        },
        "spread_price": _distribution(spreads),
        "spread_pips": _distribution(spread_pips),
        "zero_spread_rows": zero_spread_rows,
        "timing": {
            "source_to_receive_clock_offset_ms": _distribution(latencies_ms),
            "receive_gap_seconds": _distribution(gaps_seconds) if gaps_seconds else None,
            "gaps_over_1_5_seconds": sum(gap > Decimal("1.5") for gap in gaps_seconds),
            "gaps_over_2_seconds": sum(gap > Decimal("2") for gap in gaps_seconds),
            "gaps_over_5_seconds": sum(gap > Decimal("5") for gap in gaps_seconds),
        },
        "validation": {
            "status": "passed",
            "single_symbol": True,
            "receive_timestamps_strictly_increasing": True,
            "source_timestamps_non_decreasing": True,
            "bid_ask_valid": True,
            "spread_math_valid": True,
            "pip_size_consistent": True,
        },
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class QuoteCsvLog:
    """Append-only, owner-readable quote samples; a partial run remains useful."""

    def __init__(self, path: Path):
        self.path = path.expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = None
        created = False
        try:
            self._stream = self.path.open("x", encoding="utf-8", newline="")
            created = True
            os.chmod(self.path, 0o600)
            self._writer = csv.DictWriter(self._stream, fieldnames=QUOTE_COLUMNS)
            self._writer.writeheader()
            self._stream.flush()
        except Exception:
            if self._stream is not None:
                self._stream.close()
            if created and self.path.exists():
                self.path.unlink()
            raise
        self.rows = 0
        self.closed = False

    def append(self, quote: dict) -> None:
        if self.closed:
            raise ProbeError("The quote log is already closed.")
        if any(key not in quote or quote[key] is None for key in QUOTE_COLUMNS):
            raise ProbeError("The quote sample is incomplete.")
        self._writer.writerow({key: quote[key] for key in QUOTE_COLUMNS})
        self._stream.flush()
        self.rows += 1

    def close(self) -> None:
        if self.closed:
            return
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._stream.close()
        self.closed = True
