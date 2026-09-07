#!/usr/bin/env python3
"""Bounded Praxis Step 3 proof: immutable files, SQLite catalog, replay, recovery."""

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from zipfile import ZipFile

from mynyra.catalog import Catalog, CatalogError, copy_private, restore_backup
from mynyra.datasets import archive_sha256, read_normalized_minutes, validate_normalized_faraz
from mynyra.experiment import DEFAULT_CONFIG, run_cases, screen_cases, settings
from mynyra.market import write_capture

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".local"
CUTOFF = datetime(2026, 4, 1, tzinfo=timezone.utc)
EXPERIMENT = "xauusd_m1_v1"


def private_target(path: Path) -> Path:
    path = path.absolute()
    root = PRIVATE.resolve()
    if path.is_symlink() or not path.is_relative_to(root) or path == root or path.exists():
        raise CatalogError("Output must be a new non-symlink directory below project .local/.")
    return path


def copy_versioned(source: Path, target: Path) -> None:
    """Make an owner-only immutable evidence copy of a versioned definition."""
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with source.open("rb") as reader, target.open("xb") as writer:
        os.chmod(target, 0o600)
        shutil.copyfileobj(reader, writer, length=1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())


def snapshot(source: Path, target: Path) -> dict:
    """Copy exact pre-April CSV lines. No price is parsed/reformatted for export."""
    first = last = None
    rows = 0
    with source.open("r", encoding="utf-8", newline="") as reader, target.open("x", encoding="utf-8", newline="") as writer:
        os.chmod(target, 0o600)
        header = reader.readline()
        if not header:
            raise CatalogError("Normalized source has no CSV header.")
        writer.write(header)
        expected = ("timestamp_utc", "open", "high", "low", "close", "volume")
        if tuple(next(csv.reader([header]))) != expected:
            raise CatalogError("Normalized source has an unexpected CSV header.")
        for line in reader:
            fields = next(csv.reader([line]))
            if len(fields) != len(expected):
                raise CatalogError("Normalized source has a malformed CSV row.")
            stamp = datetime.fromisoformat(fields[0].replace("Z", "+00:00"))
            if stamp.tzinfo != timezone.utc:
                raise CatalogError("Normalized source contains a non-UTC timestamp.")
            if stamp >= CUTOFF:
                break
            writer.write(line)
            first = first or stamp
            last = stamp
            rows += 1
        writer.flush()
        os.fsync(writer.fileno())
    if not rows or first is None or last is None:
        raise CatalogError("The pre-April snapshot is empty.")
    return {
        "source_sha256": archive_sha256(source), "export_sha256": archive_sha256(target),
        "row_count": rows, "start_utc": first.isoformat(),
        "end_exclusive_utc": CUTOFF.isoformat(), "last_utc": last.isoformat(),
        "exact_csv_lines": True,
    }


def raw_archive_for_xauusd_m1(manifest: dict) -> Path:
    """Bind the version to the actual original archive containing its series."""
    candidates = []
    for record in manifest.get("archives", ()):
        path = PRIVATE / "data/faraz/raw" / record["filename"]
        if not path.is_file() or path.is_symlink():
            raise CatalogError("A manifest-referenced raw Faraz archive is unavailable.")
        with ZipFile(path) as archive:
            names = [item.filename for item in archive.infolist()]
        if any("XAUUSD" in name and "/1minute/" in name for name in names):
            candidates.append(path)
    if len(candidates) != 1:
        raise CatalogError("Could not uniquely identify the raw XAUUSD M1 archive.")
    return candidates[0]


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise CatalogError("Baseline evidence must be an owner-only regular file.")
    return json.loads(path.read_text(encoding="utf-8"))


def copy_baseline(source: Path, target: Path) -> tuple[dict, dict]:
    index = read_json(source / "index.json")
    registration = read_json(source / "registration.json")
    if len(index.get("runs", ())) != len(registration.get("cases", ())):
        raise CatalogError("Baseline index and registration coverage differ.")
    target.mkdir(mode=0o700)
    copy_private(source / "index.json", target / "index.json")
    copy_private(source / "registration.json", target / "registration.json")
    for entry in index["runs"]:
        name = entry.get("file", "")
        if Path(name).name != name or not name.startswith("run_"):
            raise CatalogError("Baseline index contains an unsafe result name.")
        path = source / name
        if archive_sha256(path) != entry.get("sha256"):
            raise CatalogError("Baseline result does not match its recorded hash.")
        copy_private(path, target / name)
    return index, registration


def reconcile(index: dict, replay: Path) -> dict:
    mismatches = []
    for entry in index["runs"]:
        path = replay / entry["file"]
        if not path.is_file() or archive_sha256(path) != entry["sha256"]:
            mismatches.append(entry["file"])
    if mismatches:
        raise CatalogError("Frozen-file replay differs from the unchanged baseline.")
    return {"baseline_run_count": len(index["runs"]), "matching_result_hashes": len(index["runs"])}


def interrupted_import(catalog_path: Path, root: Path, source, instrument, version, validation: Path) -> dict:
    interrupted = Catalog(catalog_path, root)
    interrupted.migrate()
    try:
        interrupted.import_dataset(source, instrument, version, validation,
                                   before_commit=lambda: (_ for _ in ()).throw(RuntimeError("injected interruption")))
    except RuntimeError as error:
        if str(error) != "injected interruption":
            raise
    else:
        raise CatalogError("Injected interrupted import unexpectedly committed.")
    with interrupted.connect() as db:
        counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                  for table in ("source", "instrument", "artifact", "dataset_version", "quality_finding")}
    if any(counts.values()):
        raise CatalogError("Interrupted import left catalog rows visible.")
    return {"injected_failure": "rolled_back", "visible_rows": counts}


def copy_references(rows, source_root: Path, target_root: Path) -> int:
    for _, relative, _, _ in rows:
        copy_private(source_root / relative, target_root / relative)
    return len(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dataset", type=Path,
                        default=PRIVATE / "data/faraz/normalized_utc_20260904")
    parser.add_argument("--baseline-screen", type=Path,
                        default=PRIVATE / "praxis_step3_baseline_source/.local/experiments/screen_v1")
    args = parser.parse_args(argv)
    try:
        if sys.version_info[:2] != (3, 11):
            raise CatalogError("Use the supported Python 3.11 runtime.")
        target = private_target(args.output)
        os.umask(0o077)
        target.mkdir(mode=0o700, parents=True)
        dataset = args.dataset.absolute()
        proof = validate_normalized_faraz(dataset)
        manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
        series = [item for item in manifest["series"] if item["path"] == "XAUUSD/1minute.csv"]
        if len(series) != 1:
            raise CatalogError("Expected one normalized XAUUSD M1 series.")
        item = series[0]
        source_csv = dataset / item["path"]
        raw = raw_archive_for_xauusd_m1(manifest)
        validation = target / "import/validation.json"
        write_capture(validation, {"validation": proof, "xauusd_m1": {
            "sha256": archive_sha256(source_csv), "row_count": item["row_count"],
            "start_utc": item["first_timestamp_utc"], "end_utc": item["last_timestamp_utc"],
        }})
        definition = target / "definition"
        definition.mkdir(mode=0o700)
        protocol = definition / "protocol.md"
        config = definition / "xauusd_m1_v1.toml"
        copy_versioned(ROOT / "docs/XAUUSD_COMPARISON_PROTOCOL.md", protocol)
        copy_versioned(DEFAULT_CONFIG, config)
        frozen = target / "snapshot/xauusd_m1_preapril.csv"
        frozen.parent.mkdir(mode=0o700)
        snapshot_proof = snapshot(source_csv, frozen)
        repeat = target / "reproducibility/xauusd_m1_preapril.csv"
        repeat.parent.mkdir(mode=0o700)
        repeated = snapshot(source_csv, repeat)
        if snapshot_proof["export_sha256"] != repeated["export_sha256"] or snapshot_proof["row_count"] != repeated["row_count"]:
            raise CatalogError("Snapshot export is not reproducible.")
        write_capture(target / "snapshot/manifest.json", snapshot_proof)

        catalog = Catalog(target / "catalog/research.sqlite", PRIVATE)
        catalog.migrate()
        source = ("faraz", "Faraz chart export", "Asia/Tehran", "docs/FARAZ_DATA_AUDIT.md")
        instrument = ("faraz-xauusd", "faraz", "XAUUSD", "XAUUSD", "USD per troy ounce", "unknown")
        version = ("faraz-xauusd-m1-20260904-r1", None, raw, source_csv,
                   archive_sha256(ROOT / "src/mynyra/datasets.py"), "unknown", 60, "open",
                   item["first_timestamp_utc"], "2026-05-01T20:30:00+00:00", item["row_count"])
        recovery = interrupted_import(target / "recovery/interrupted.sqlite", PRIVATE, source, instrument, version, validation)
        first = catalog.import_dataset(source, instrument, version, validation)
        duplicate = catalog.import_dataset(source, instrument, version, validation)
        if (first, duplicate) != ("created", "existing"):
            raise CatalogError("Duplicate dataset import was not idempotent.")
        baseline, registration = copy_baseline(args.baseline_screen.absolute(), target / "baseline")
        implementation = baseline.get("provenance", {}).get("implementation_sha256")
        if not implementation:
            raise CatalogError("Baseline lacks its implementation identity.")
        catalog.register_experiment(EXPERIMENT, protocol, config, implementation)
        frozen_status = catalog.freeze_snapshot("xauusd-m1-preapril-r1", version[0], EXPERIMENT,
                                                "development-and-selection", "exploratory",
                                                snapshot_proof["start_utc"], snapshot_proof["end_exclusive_utc"],
                                                frozen, snapshot_proof["row_count"])
        if frozen_status != "created":
            raise CatalogError("New snapshot was not published.")
        cfg = settings(config)
        bars = read_normalized_minutes(frozen, CUTOFF)
        if len(bars) != snapshot_proof["row_count"]:
            raise CatalogError("Frozen snapshot row count changed before simulation.")
        replay = target / "replay"
        run_cases(bars, cfg, screen_cases(cfg), replay, baseline["provenance"],
                  {"snapshot_sha256": snapshot_proof["export_sha256"], "loaded_prefix_rows": len(bars),
                   "loaded_last_timestamp": bars[-1].time.isoformat(), "source": "frozen_csv_only"})
        reconciliation = reconcile(baseline, replay)
        for number, entry in enumerate(baseline["runs"]):
            result = replay / entry["file"]
            status = read_json(result)["status"]
            catalog.record_run(f"xauusd-m1-preapril-r1-{number:04d}", EXPERIMENT, "xauusd-m1-preapril-r1",
                               entry["period"], entry["candidate"], entry["scenario"], entry["view"], result, status)
        original_refs = catalog.verify_references()
        backup = target / "backup"
        backup.mkdir(mode=0o700)
        catalog.backup(backup / "research.sqlite")
        copied_backup = copy_references(catalog.artifact_rows(), PRIVATE, backup / "artifacts")
        backup_catalog = Catalog(backup / "research.sqlite", backup / "artifacts")
        if backup_catalog.verify_references() != copied_backup:
            raise CatalogError("Backup artifact references do not reconcile.")
        restored = target / "restore"
        restored.mkdir(mode=0o700)
        restore_backup(backup / "research.sqlite", restored / "research.sqlite")
        copied_restore = copy_references(backup_catalog.artifact_rows(), backup / "artifacts", restored / "artifacts")
        restored_catalog = Catalog(restored / "research.sqlite", restored / "artifacts")
        restored_refs = restored_catalog.verify_references()
        if restored_refs != copied_restore:
            raise CatalogError("Isolated restored artifact references do not reconcile.")
        report = {
            "status": "passed", "cutoff_exclusive": CUTOFF.isoformat(),
            "dataset_version": version[0], "dataset_import": {"first": first, "duplicate": duplicate},
            "snapshot": {**snapshot_proof, "reproducible": True}, "recovery": recovery,
            "reconciliation": reconciliation, "artifact_references": {"original": original_refs,
            "backup": copied_backup, "restored": restored_refs},
            "backup_bytes": sum(path.stat().st_size for path in backup.rglob("*") if path.is_file()),
            "baseline_registration_cases": len(registration["cases"]),
        }
        write_capture(target / "report.json", report)
        print(json.dumps({"status": "passed", "rows": snapshot_proof["row_count"],
                          "runs": reconciliation["matching_result_hashes"], "references": restored_refs}, sort_keys=True))
        return 0
    except (CatalogError, OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
