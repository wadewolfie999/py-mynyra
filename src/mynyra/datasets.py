"""Safe inspection and UTC normalization of Faraz chart-export archives."""

import csv
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from zipfile import BadZipFile, ZipFile

from mynyra.config import ProbeError


MAX_ARCHIVE_MEMBERS = 2_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2_000_000_000
MAX_MEMBER_BYTES = 250_000_000
FARAZ_TIMEZONE = "Asia/Tehran"
NORMALIZED_COLUMNS = (
    "timestamp_utc", "open", "high", "low", "close", "volume"
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_members(infos) -> None:
    if len(infos) > MAX_ARCHIVE_MEMBERS:
        raise ProbeError("The dataset archive contains too many files.")
    if sum(info.file_size for info in infos) > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
        raise ProbeError("The dataset archive expands beyond the safe inspection limit.")
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise ProbeError("The dataset archive contains duplicate file paths.")
    for info in infos:
        parts = PurePosixPath(info.filename)
        file_type = (info.external_attr >> 16) & 0o170000
        if parts.is_absolute() or ".." in parts.parts:
            raise ProbeError("The dataset archive contains an unsafe file path.")
        if info.flag_bits & 1:
            raise ProbeError("Encrypted dataset archives are unsupported.")
        if file_type == stat.S_IFLNK:
            raise ProbeError("Dataset archives containing symbolic links are unsupported.")
        if info.file_size > MAX_MEMBER_BYTES:
            raise ProbeError("A dataset file exceeds the safe inspection limit.")


def _series_identity(name: str) -> tuple[str, str] | None:
    parts = PurePosixPath(name).parts
    if len(parts) != 4 or parts[1] != "general-platforms" or not name.endswith(".csv"):
        return None
    folder, _, timeframe, filename = parts
    if not folder.startswith("FXCM_"):
        return None
    symbol = folder.removeprefix("FXCM_")
    if (
        not SAFE_NAME.fullmatch(symbol)
        or not SAFE_NAME.fullmatch(timeframe)
        or filename != f"{folder}-{timeframe}.csv"
    ):
        return None
    return symbol, timeframe


def _parse_fields(fields: list[str]) -> tuple[datetime, tuple[Decimal, ...], int]:
    if len(fields) != 7:
        raise ValueError("wrong column count")
    timestamp = datetime.strptime(f"{fields[0]} {fields[1]}", "%Y.%m.%d %H:%M")
    prices = tuple(Decimal(value) for value in fields[2:6])
    volume = int(fields[6])
    if not all(value.is_finite() for value in prices):
        raise ValueError("non-finite price")
    return timestamp, prices, volume


def _audit_series(archive: ZipFile, info, symbol: str, timeframe: str) -> dict:
    rows = 0
    malformed = 0
    invalid_ohlc = 0
    negative_volume = 0
    zero_volume = 0
    non_increasing = 0
    non_increasing_examples = []
    first = None
    last = None
    previous = None

    with archive.open(info) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        for fields in csv.reader(text):
            rows += 1
            try:
                timestamp, prices, volume = _parse_fields(fields)
            except (InvalidOperation, ValueError):
                malformed += 1
                continue
            open_price, high, low, close = prices
            if not low <= open_price <= high or not low <= close <= high:
                invalid_ohlc += 1
            if volume < 0:
                negative_volume += 1
            elif volume == 0:
                zero_volume += 1
            if first is None:
                first = timestamp
            if previous is not None and timestamp <= previous:
                non_increasing += 1
                if len(non_increasing_examples) < 3:
                    non_increasing_examples.append({
                        "previous": previous.isoformat(timespec="minutes"),
                        "current": timestamp.isoformat(timespec="minutes"),
                    })
            previous = timestamp
            last = timestamp

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "row_count": rows,
        "first_timestamp_local": first.isoformat(timespec="minutes") if first else None,
        "last_timestamp_local": last.isoformat(timespec="minutes") if last else None,
        "at_100000_row_cap": rows == 100_000,
        "malformed_rows": malformed,
        "invalid_ohlc_rows": invalid_ohlc,
        "negative_volume_rows": negative_volume,
        "zero_volume_rows": zero_volume,
        "non_increasing_timestamp_rows": non_increasing,
        "non_increasing_timestamp_examples": non_increasing_examples,
    }


def _archive_candidates(path: Path):
    try:
        archive = ZipFile(path)
    except BadZipFile:
        raise ProbeError("A supplied dataset archive is not a readable ZIP file.") from None
    try:
        infos = archive.infolist()
        _validate_members(infos)
        candidates = []
        for info in infos:
            identity = _series_identity(info.filename)
            if identity is not None:
                candidates.append((info, *identity))
        if not candidates:
            raise ProbeError(
                "The archive contains no recognized Faraz general-platform CSV files."
            )
        return archive, infos, sorted(candidates, key=lambda item: (item[1], item[2]))
    except Exception:
        archive.close()
        raise


def _checked_paths(paths: list[Path]) -> list[Path]:
    if not paths:
        raise ProbeError("At least one Faraz dataset archive is required.")
    checked = []
    for supplied in paths:
        path = supplied.expanduser()
        if not path.is_file():
            raise ProbeError("A supplied dataset archive does not exist or is not a file.")
        checked.append(path)
    return checked


def audit_faraz_archives(paths: list[Path]) -> dict:
    archives = []
    series = []
    identities = set()
    for path in _checked_paths(paths):
        archive, infos, candidates = _archive_candidates(path)
        try:
            start = len(series)
            for info, symbol, timeframe in candidates:
                identity = (symbol, timeframe)
                if identity in identities:
                    raise ProbeError("The archives contain the same symbol and timeframe twice.")
                identities.add(identity)
                series.append(_audit_series(archive, info, symbol, timeframe))
            archives.append({
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": archive_sha256(path),
                "member_count": len(infos),
                "uncompressed_bytes": sum(info.file_size for info in infos),
                "csv_series_count": len(series) - start,
                "ignored_prn_count": sum(info.filename.endswith(".prn") for info in infos),
            })
        finally:
            archive.close()

    malformed = sum(item["malformed_rows"] for item in series)
    invalid_ohlc = sum(item["invalid_ohlc_rows"] for item in series)
    negative_volume = sum(item["negative_volume_rows"] for item in series)
    non_increasing = sum(item["non_increasing_timestamp_rows"] for item in series)
    return {
        "schema_version": 2,
        "source": "Faraz chart export",
        "format": {
            "selected_files": "general-platforms CSV",
            "columns": ["date", "time", "open", "high", "low", "close", "volume"],
            "header_present": False,
            "timestamp_timezone": FARAZ_TIMEZONE,
            "timestamp_timezone_basis": "user-confirmed export setting",
            "price_side": None,
            "volume_semantics": None,
        },
        "archive_count": len(archives),
        "archives": archives,
        "series_count": len(series),
        "row_count": sum(item["row_count"] for item in series),
        "symbols": sorted({item["symbol"] for item in series}),
        "timeframes": sorted({item["timeframe"] for item in series}),
        "quality": {
            "malformed_rows": malformed,
            "invalid_ohlc_rows": invalid_ohlc,
            "negative_volume_rows": negative_volume,
            "zero_volume_rows": sum(item["zero_volume_rows"] for item in series),
            "non_increasing_timestamp_rows": non_increasing,
            "capped_series": sum(item["at_100000_row_cap"] for item in series),
            "requires_timestamp_normalization": True,
            "structurally_usable": not (malformed or invalid_ohlc or negative_volume),
        },
        "series": series,
    }


def _utc_candidates(local: datetime, zone: ZoneInfo) -> list[tuple[datetime, int]]:
    candidates = []
    seen = set()
    for fold in (0, 1):
        aware = local.replace(tzinfo=zone, fold=fold)
        utc = aware.astimezone(timezone.utc)
        round_trip = utc.astimezone(zone)
        if round_trip.replace(tzinfo=None) != local or round_trip.fold != fold:
            continue
        if utc not in seen:
            candidates.append((utc, fold))
            seen.add(utc)
    return sorted(candidates)


def _select_utc(local: datetime, zone: ZoneInfo, previous: datetime | None):
    candidates = _utc_candidates(local, zone)
    if not candidates:
        # Tehran advanced its clock at local midnight in 2022. Faraz can still
        # label a calendar candle at that nonexistent wall time. Moving that
        # label through the gap preserves the candle and the actual UTC order.
        aware = local.replace(tzinfo=zone, fold=0)
        utc = aware.astimezone(timezone.utc)
        resolved = utc.astimezone(zone).replace(tzinfo=None)
        if resolved <= local or (previous is not None and utc <= previous):
            raise ProbeError(
                "A nonexistent local timestamp cannot be safely shifted forward."
            )
        return utc, 0, False, True
    for utc, fold in candidates:
        if previous is None or utc > previous:
            return utc, fold, len(candidates) > 1, False
    raise ProbeError(
        "A timestamp cannot be made strictly increasing after timezone normalization."
    )


def _write_normalized_series(
    archive: ZipFile,
    info,
    symbol: str,
    timeframe: str,
    root: Path,
    zone: ZoneInfo,
) -> dict:
    symbol_dir = root / symbol
    symbol_dir.mkdir(mode=0o700, exist_ok=True)
    path = symbol_dir / f"{timeframe}.csv"
    rows = 0
    zero_volume = 0
    ambiguous_rows = 0
    fold1_rows = 0
    shifted_gap_rows = 0
    first_local = None
    last_local = None
    first_utc = None
    previous_utc = None
    with archive.open(info) as raw, path.open("x", encoding="utf-8", newline="") as output:
        os.chmod(path, 0o600)
        source = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        writer = csv.writer(output)
        writer.writerow(NORMALIZED_COLUMNS)
        for line_number, fields in enumerate(source, start=1):
            try:
                local, prices, volume = _parse_fields(fields)
            except (InvalidOperation, ValueError) as error:
                raise ProbeError(
                    f"{symbol} {timeframe} has a malformed row at line {line_number}."
                ) from error
            open_price, high, low, close = prices
            if not low <= open_price <= high or not low <= close <= high:
                raise ProbeError(
                    f"{symbol} {timeframe} has invalid OHLC values at line {line_number}."
                )
            if volume < 0:
                raise ProbeError(
                    f"{symbol} {timeframe} has negative volume at line {line_number}."
                )
            utc, fold, ambiguous, shifted_gap = _select_utc(local, zone, previous_utc)
            writer.writerow((
                utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
                fields[2], fields[3], fields[4], fields[5], fields[6],
            ))
            rows += 1
            zero_volume += volume == 0
            ambiguous_rows += ambiguous
            fold1_rows += fold == 1
            shifted_gap_rows += shifted_gap
            first_local = first_local or local
            first_utc = first_utc or utc
            last_local = local
            previous_utc = utc
        output.flush()
        os.fsync(output.fileno())
    if not rows:
        raise ProbeError(f"{symbol} {timeframe} contains no data rows.")
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "path": f"{symbol}/{timeframe}.csv",
        "row_count": rows,
        "first_timestamp_local": first_local.isoformat(timespec="minutes"),
        "last_timestamp_local": last_local.isoformat(timespec="minutes"),
        "first_timestamp_utc": first_utc.isoformat(timespec="seconds"),
        "last_timestamp_utc": previous_utc.isoformat(timespec="seconds"),
        "ambiguous_local_rows": ambiguous_rows,
        "second_fold_rows": fold1_rows,
        "nonexistent_local_rows_shifted_forward": shifted_gap_rows,
        "zero_volume_rows": zero_volume,
        "sha256": archive_sha256(path),
    }


def _load_manifest(root: Path) -> dict:
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProbeError("The normalized dataset manifest is missing or invalid.") from error
    if not isinstance(manifest, dict) or not isinstance(manifest.get("series"), list):
        raise ProbeError("The normalized dataset manifest has an invalid shape.")
    return manifest


def validate_normalized_faraz(directory: Path) -> dict:
    root = directory.expanduser()
    if not root.is_dir() or root.is_symlink():
        raise ProbeError("The normalized Faraz dataset directory does not exist.")
    manifest = _load_manifest(root)
    if (
        manifest.get("schema_version") != 1
        or manifest.get("source_timezone") != FARAZ_TIMEZONE
        or manifest.get("columns") != list(NORMALIZED_COLUMNS)
    ):
        raise ProbeError("The normalized dataset manifest metadata is invalid.")
    if (root / "manifest.json").stat().st_mode & 0o077:
        raise ProbeError("The normalized dataset manifest is not owner-only.")
    total_rows = 0
    identities = set()
    expected_files = set()
    for expected in manifest["series"]:
        try:
            symbol = expected["symbol"]
            timeframe = expected["timeframe"]
            relative = expected["path"]
            expected_rows = expected["row_count"]
            expected_hash = expected["sha256"]
        except (KeyError, TypeError):
            raise ProbeError("A normalized series manifest entry is incomplete.") from None
        if not SAFE_NAME.fullmatch(symbol) or not SAFE_NAME.fullmatch(timeframe):
            raise ProbeError("A normalized series has an unsafe name.")
        if (symbol, timeframe) in identities:
            raise ProbeError("The normalized manifest contains a duplicate series.")
        identities.add((symbol, timeframe))
        if relative != f"{symbol}/{timeframe}.csv":
            raise ProbeError("A normalized series path does not match its identity.")
        expected_files.add(relative)
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ProbeError("A normalized series file is missing or unsafe.")
        if archive_sha256(path) != expected_hash:
            raise ProbeError("A normalized series file does not match its recorded hash.")
        if path.stat().st_mode & 0o077:
            raise ProbeError("A normalized series file is not owner-only.")
        count = 0
        previous = None
        first = None
        last = None
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != NORMALIZED_COLUMNS:
                raise ProbeError("A normalized series has the wrong CSV header.")
            for row in reader:
                try:
                    timestamp = datetime.fromisoformat(row["timestamp_utc"].replace("Z", "+00:00"))
                    prices = tuple(Decimal(row[key]) for key in ("open", "high", "low", "close"))
                    volume = int(row["volume"])
                except (InvalidOperation, TypeError, ValueError) as error:
                    raise ProbeError("A normalized series contains a malformed row.") from error
                if timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
                    raise ProbeError("A normalized timestamp is not UTC.")
                if previous is not None and timestamp <= previous:
                    raise ProbeError("A normalized series is not strictly increasing.")
                open_price, high, low, close = prices
                if (
                    not all(value.is_finite() for value in prices)
                    or not low <= open_price <= high
                    or not low <= close <= high
                    or volume < 0
                ):
                    raise ProbeError("A normalized series contains invalid market values.")
                count += 1
                first = first or timestamp
                last = timestamp
                previous = timestamp
        if count != expected_rows:
            raise ProbeError("A normalized series row count does not match its manifest.")
        if first is None or last is None:
            raise ProbeError("A normalized series is empty.")
        if first.isoformat(timespec="seconds") != expected["first_timestamp_utc"]:
            raise ProbeError("A normalized series start time does not match its manifest.")
        if last.isoformat(timespec="seconds") != expected["last_timestamp_utc"]:
            raise ProbeError("A normalized series end time does not match its manifest.")
        total_rows += count
    if total_rows != manifest.get("row_count"):
        raise ProbeError("The normalized total row count does not match its manifest.")
    if len(identities) != manifest.get("series_count"):
        raise ProbeError("The normalized series count does not match its manifest.")
    actual_files = {
        path.relative_to(root).as_posix() for path in root.glob("*/*.csv")
    }
    if actual_files != expected_files:
        raise ProbeError("The normalized directory contains an unexpected series set.")
    return {
        "proof": "normalized_faraz_validation",
        "series_count": len(identities),
        "row_count": total_rows,
        "utc_strictly_increasing": True,
        "hashes_match": True,
        "market_values_valid": True,
    }


def normalize_faraz_archives(paths: list[Path], output_dir: Path) -> dict:
    checked = _checked_paths(paths)
    target = output_dir.expanduser()
    if target.exists() or target.is_symlink():
        raise ProbeError("The normalized output directory already exists.")
    try:
        zone = ZoneInfo(FARAZ_TIMEZONE)
    except ZoneInfoNotFoundError:
        raise ProbeError("The Asia/Tehran timezone database is unavailable.") from None
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".faraz-normalize-", dir=target.parent))
    os.chmod(staging, 0o700)
    archives = []
    series = []
    identities = set()
    try:
        for path in checked:
            archive, infos, candidates = _archive_candidates(path)
            try:
                start = len(series)
                for info, symbol, timeframe in candidates:
                    identity = (symbol, timeframe)
                    if identity in identities:
                        raise ProbeError(
                            "The archives contain the same symbol and timeframe twice."
                        )
                    identities.add(identity)
                    series.append(_write_normalized_series(
                        archive, info, symbol, timeframe, staging, zone
                    ))
                archives.append({
                    "filename": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": archive_sha256(path),
                    "member_count": len(infos),
                    "csv_series_count": len(series) - start,
                    "ignored_prn_count": sum(
                        info.filename.endswith(".prn") for info in infos
                    ),
                })
            finally:
                archive.close()
        manifest = {
            "schema_version": 1,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "Faraz chart export",
            "source_timezone": FARAZ_TIMEZONE,
            "source_timezone_basis": "user-confirmed export setting",
            "normalization": (
                "Local candle labels converted in source order; both sides of the "
                "2022 Tehran daylight-saving rollback are preserved, and calendar "
                "labels inside the spring clock gap are shifted through that gap."
            ),
            "columns": list(NORMALIZED_COLUMNS),
            "archive_count": len(archives),
            "archives": archives,
            "series_count": len(series),
            "row_count": sum(item["row_count"] for item in series),
            "ambiguous_local_rows": sum(item["ambiguous_local_rows"] for item in series),
            "second_fold_rows": sum(item["second_fold_rows"] for item in series),
            "nonexistent_local_rows_shifted_forward": sum(
                item["nonexistent_local_rows_shifted_forward"] for item in series
            ),
            "symbols": sorted({item["symbol"] for item in series}),
            "timeframes": sorted({item["timeframe"] for item in series}),
            "series": series,
        }
        manifest_path = staging / "manifest.json"
        with manifest_path.open("x", encoding="utf-8") as stream:
            os.chmod(manifest_path, 0o600)
            json.dump(manifest, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        validation = validate_normalized_faraz(staging)
        os.replace(staging, target)
        return {**manifest, "output": str(target), "validation": validation}
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
