"""SQLite catalog contracts: append-only identity, rollback and isolated recovery."""

import os
from pathlib import Path
import tempfile
import unittest

from mynyra.catalog import Catalog, CatalogError, copy_private, restore_backup
from mynyra.datasets import archive_sha256


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "private"
        self.root.mkdir(mode=0o700)
        self.catalog = Catalog(self.root / "catalog.sqlite", self.root)
        self.catalog.migrate()
        self.raw = self.write("raw.zip", b"raw")
        self.normal = self.write("normal.csv", b"timestamp_utc,open,high,low,close,volume\n2026-01-01T00:00:00Z,1,1,1,1,0\n")
        self.validation = self.write("validation.json", b"{}\n")
        self.protocol = self.write("protocol.md", b"protocol\n")
        self.config = self.write("config.toml", b"id = 'test'\n")
        self.source = ("source", "provider", "UTC", "terms")
        self.instrument = ("instrument", "source", "XAU", "XAUUSD", "USD/oz", "unknown")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(data)
        os.chmod(path, 0o600)
        return path

    def version(self, name="v1", parent=None, normalized=None):
        return (name, parent, self.raw, normalized or self.normal, "a" * 64, "unknown", 60, "open",
                "2026-01-01T00:00:00+00:00", "2026-01-01T00:01:00+00:00", 1)

    def test_duplicate_import_is_idempotent_and_revision_is_explicit(self):
        self.assertEqual(self.catalog.import_dataset(self.source, self.instrument, self.version(), self.validation), "created")
        self.assertEqual(self.catalog.import_dataset(self.source, self.instrument, self.version(), self.validation), "existing")
        corrected = self.write("normal-corrected.csv", b"timestamp_utc,open,high,low,close,volume\n2026-01-01T00:00:00Z,2,2,2,2,0\n")
        self.assertEqual(
            self.catalog.import_dataset(self.source, self.instrument, self.version("v2", "v1", corrected), self.validation),
            "created",
        )
        with self.assertRaises(CatalogError):
            self.catalog.import_dataset(self.source, self.instrument, self.version("v1", None, corrected), self.validation)
        with self.catalog.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM dataset_version").fetchone()[0], 2)

    def test_interrupted_import_rolls_back_every_staged_row(self):
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            self.catalog.import_dataset(
                self.source, self.instrument, self.version(), self.validation,
                before_commit=lambda: (_ for _ in ()).throw(RuntimeError("interrupted")),
            )
        with self.catalog.connect() as db:
            for table in ("source", "instrument", "artifact", "dataset_version", "quality_finding"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)

    def test_snapshot_bounds_append_only_and_isolated_backup_restore(self):
        self.catalog.import_dataset(self.source, self.instrument, self.version(), self.validation)
        self.catalog.register_experiment("experiment", self.protocol, self.config, "b" * 64)
        export = self.write("snapshot.csv", b"timestamp_utc,open,high,low,close,volume\n2026-01-01T00:00:00Z,3,3,3,3,0\n")
        self.assertEqual(
            self.catalog.freeze_snapshot("snapshot", "v1", "experiment", "screen", "exploratory",
                                         "2026-01-01T00:00:00+00:00", "2026-01-01T00:01:00+00:00", export, 1),
            "created",
        )
        first_result = self.write("run-development.json", b'{"status":"completed"}\n')
        second_result = self.write("run-selection.json", b'{"status":"completed","period":"selection"}\n')
        self.assertEqual(self.catalog.record_run("run-development", "experiment", "snapshot", "development",
                                                 "sma", "cost", "signal", first_result, "completed"), "created")
        self.assertEqual(self.catalog.record_run("run-selection", "experiment", "snapshot", "selection",
                                                 "sma", "cost", "signal", second_result, "completed"), "created")
        with self.assertRaises(Exception):
            self.catalog.freeze_snapshot("too-wide", "v1", "experiment", "screen", "exploratory",
                                         "2025-12-31T23:59:00+00:00", "2026-01-01T00:01:00+00:00", export, 1)
        self.assertEqual(self.catalog.verify_references(), 8)
        backup = self.root / "backup"
        backup.mkdir(mode=0o700)
        self.catalog.backup(backup / "catalog.sqlite")
        for _, relative, _, _ in self.catalog.artifact_rows():
            copy_private(self.root / relative, backup / "artifacts" / relative)
        restored = self.root / "restore"
        restored.mkdir(mode=0o700)
        restore_backup(backup / "catalog.sqlite", restored / "catalog.sqlite")
        for _, relative, _, _ in self.catalog.artifact_rows():
            copy_private(backup / "artifacts" / relative, restored / "artifacts" / relative)
        self.assertEqual(Catalog(restored / "catalog.sqlite", restored / "artifacts").verify_references(), 8)
        with self.catalog.connect() as db:
            with self.assertRaises(Exception):
                db.execute("DELETE FROM snapshot WHERE snapshot_id = 'snapshot'")

    def test_artifact_outside_root_and_hash_tamper_are_rejected(self):
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_text("outside")
        os.chmod(outside, 0o600)
        with self.catalog.transaction() as db:
            with self.assertRaises(CatalogError):
                self.catalog.register_artifact(db, outside, "text/plain")
        self.catalog.import_dataset(self.source, self.instrument, self.version(), self.validation)
        self.normal.write_text("tampered")
        os.chmod(self.normal, 0o600)
        with self.assertRaises(CatalogError):
            self.catalog.verify_references()
