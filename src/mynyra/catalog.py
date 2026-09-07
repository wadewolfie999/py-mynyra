"""Append-only SQLite catalog for immutable local research artifacts.

The catalog owns identity and relationships.  Market prices, snapshot CSVs and
simulation results stay in files; callers must never use catalog queries as a
simulation input.
"""

from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
import shutil
import sqlite3
from typing import Callable, Iterator

from mynyra.config import ProbeError
from mynyra.datasets import archive_sha256

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "sql/migrations/001_research_catalog.sql"


class CatalogError(ProbeError):
    """A catalog invariant or private-artifact boundary was violated."""


def migration_sha256() -> str:
    return archive_sha256(MIGRATION)


def _private_regular(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise CatalogError("Catalog artifacts must be owner-only regular files.")


def _new_private_file(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise CatalogError("Catalog outputs are create-only.") from None
    os.close(descriptor)


class Catalog:
    """One SQLite catalog and the private root containing all referenced files."""

    def __init__(self, database: Path, artifact_root: Path):
        self.database = database.absolute()
        self.artifact_root = artifact_root.absolute().resolve()

    def connect(self) -> sqlite3.Connection:
        if self.database.is_symlink():
            raise CatalogError("Catalog database must not be a symbolic link.")
        db = sqlite3.connect(self.database)
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def migrate(self) -> None:
        if not MIGRATION.is_file():
            raise CatalogError("The authoritative SQLite migration is missing.")
        self.database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        creating = not self.database.exists()
        if creating:
            _new_private_file(self.database)
        _private_regular(self.database)
        checksum = migration_sha256()
        with self.connect() as db:
            exists = db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_migration'"
            ).fetchone()
            if exists:
                applied = db.execute("SELECT sha256 FROM schema_migration WHERE version = 1").fetchone()
                if applied != (checksum,):
                    raise CatalogError("Catalog migration identity differs from this source tree.")
            else:
                db.executescript(MIGRATION.read_text(encoding="utf-8"))
                db.execute(
                    "INSERT INTO schema_migration VALUES (1, ?, '1970-01-01T00:00:00+00:00')",
                    (checksum,),
                )
        os.chmod(self.database, 0o600)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
        except BaseException:
            db.rollback()
            raise
        else:
            db.commit()
        finally:
            db.close()

    def _relative(self, path: Path) -> str:
        path = path.absolute()
        _private_regular(path)
        try:
            return path.resolve().relative_to(self.artifact_root).as_posix()
        except ValueError:
            raise CatalogError("Catalog artifact is outside its private root.") from None

    def register_artifact(self, db: sqlite3.Connection, path: Path, media_type: str) -> str:
        relative = self._relative(path)
        identity = (archive_sha256(path), relative, path.stat().st_size, media_type)
        prior = db.execute(
            "SELECT sha256, relative_path, byte_count, media_type FROM artifact WHERE sha256 = ?",
            (identity[0],),
        ).fetchone()
        if prior is None:
            try:
                db.execute("INSERT INTO artifact VALUES (?, ?, ?, ?)", identity)
            except sqlite3.IntegrityError as error:
                raise CatalogError("An artifact path is already bound to different content.") from error
        elif tuple(prior) != identity:
            raise CatalogError("An artifact hash is already bound to different metadata.")
        return identity[0]

    @staticmethod
    def _ensure(db: sqlite3.Connection, table: str, key: str, values: tuple) -> None:
        existing = db.execute(f"SELECT * FROM {table} WHERE {key} = ?", (values[0],)).fetchone()
        if existing is None:
            marks = ", ".join("?" for _ in values)
            db.execute(f"INSERT INTO {table} VALUES ({marks})", values)
        elif tuple(existing) != values:
            raise CatalogError(f"Existing {table} identity differs from this import.")

    def import_dataset(
        self,
        source: tuple[str, str, str, str],
        instrument: tuple[str, str, str, str, str, str],
        version: tuple[str, str | None, Path, Path, str, str, int, str, str, str, int],
        validation_path: Path,
        before_commit: Callable[[], None] | None = None,
    ) -> str:
        """Atomically publish a validated immutable version, or leave no partial rows."""
        version_id, parent, raw, normalized, transform, side, interval, label, start, end, rows = version
        with self.transaction() as db:
            raw_hash = self.register_artifact(db, raw, "application/zip")
            normalized_hash = self.register_artifact(db, normalized, "text/csv")
            evidence_hash = self.register_artifact(db, validation_path, "application/json")
            self._ensure(db, "source", "source_id", source)
            self._ensure(db, "instrument", "instrument_id", instrument)
            record = (version_id, instrument[0], parent, raw_hash, normalized_hash, transform,
                      side, interval, label, start, end, rows)
            prior = db.execute("SELECT * FROM dataset_version WHERE version_id = ?", (version_id,)).fetchone()
            if prior is None:
                db.execute("INSERT INTO dataset_version VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", record)
                db.execute(
                    "INSERT INTO quality_finding VALUES (?, 'normalized-validation', 'normalized_faraz_validation', 'info', ?)",
                    (version_id, evidence_hash),
                )
                result = "created"
            elif tuple(prior) == record:
                result = "existing"
            else:
                raise CatalogError("Dataset version ID was reused with different content.")
            if before_commit is not None:
                before_commit()
            return result

    def register_experiment(self, experiment_id: str, specification: Path, config: Path, code_sha256: str) -> None:
        with self.transaction() as db:
            spec_hash = self.register_artifact(db, specification, "text/markdown")
            config_hash = self.register_artifact(db, config, "application/toml")
            self._ensure(db, "experiment_definition", "experiment_id", (experiment_id, spec_hash, code_sha256, config_hash))

    def freeze_snapshot(
        self, snapshot_id: str, version_id: str, experiment_id: str, partition: str,
        access_class: str, start: str, end: str, export: Path, row_count: int,
    ) -> str:
        with self.transaction() as db:
            export_hash = self.register_artifact(db, export, "text/csv")
            record = (snapshot_id, version_id, experiment_id, partition, access_class,
                      start, end, export_hash, row_count)
            prior = db.execute("SELECT * FROM snapshot WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
            if prior is None:
                db.execute("INSERT INTO snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", record)
                return "created"
            if tuple(prior) != record:
                raise CatalogError("Snapshot ID was reused with different content.")
            return "existing"

    def record_run(
        self, run_id: str, experiment_id: str, snapshot_id: str, partition: str, candidate: str,
        scenario: str, view: str, result: Path, status: str,
    ) -> str:
        with self.transaction() as db:
            result_hash = self.register_artifact(db, result, "application/json")
            record = (run_id, experiment_id, snapshot_id, partition, candidate, scenario, view, result_hash, status)
            prior = db.execute("SELECT * FROM research_run WHERE run_id = ?", (run_id,)).fetchone()
            if prior is None:
                db.execute("INSERT INTO research_run VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", record)
                return "created"
            if tuple(prior) != record:
                raise CatalogError("Research run ID was reused with different content.")
            return "existing"

    def artifact_rows(self) -> list[tuple[str, str, int, str]]:
        with self.connect() as db:
            return [tuple(row) for row in db.execute(
                "SELECT sha256, relative_path, byte_count, media_type FROM artifact ORDER BY relative_path"
            )]

    def verify_references(self) -> int:
        checked = 0
        for digest, relative, count, _ in self.artifact_rows():
            path = self.artifact_root / relative
            _private_regular(path)
            if path.resolve() != path or archive_sha256(path) != digest or path.stat().st_size != count:
                raise CatalogError("Catalog artifact hash or path reference does not reconcile.")
            checked += 1
        return checked

    def backup(self, destination: Path) -> None:
        destination = destination.absolute()
        _new_private_file(destination)
        try:
            with self.connect() as source, sqlite3.connect(destination) as target:
                source.backup(target)
            os.chmod(destination, 0o600)
            _private_regular(destination)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise


def copy_private(source: Path, destination: Path) -> None:
    """Copy one immutable private file without replacing any evidence."""
    _private_regular(source)
    _new_private_file(destination)
    try:
        with source.open("rb") as reader, destination.open("wb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        os.chmod(destination, 0o600)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def restore_backup(backup_database: Path, restored_database: Path) -> None:
    """Use SQLite's backup interface for a create-only isolated restore."""
    _private_regular(backup_database)
    _new_private_file(restored_database)
    try:
        with sqlite3.connect(backup_database) as source, sqlite3.connect(restored_database) as target:
            source.backup(target)
        os.chmod(restored_database, 0o600)
    except BaseException:
        restored_database.unlink(missing_ok=True)
        raise
