"""Read the curated, public-safe project briefing index.

The index is a reviewed projection over named records.  It deliberately checks
source identity but does not interpret source bodies or turn a recorded decision
into a present authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tomllib
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INDEX_PATH = Path("docs/PROJECT_STATE.toml")
MAX_SNAPSHOT_ATTEMPTS = 2
# These are application policy, not permissions granted by the editable index.
PUBLIC_ROOTS = frozenset({"docs", "experiments"})
PUBLIC_SUFFIXES = frozenset({".md", ".toml", ".json"})
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
MAX_INVENTORY_ENTRIES = 512
MAX_SOURCES = 128
MAX_CLAIMS = 512


class ProjectStateError(ValueError):
    """The configured public briefing index cannot be read safely."""


def _safe_relative_path(value: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ProjectStateError("Invalid public record path.")
    path = Path(value)
    if (path.is_absolute() or value != path.as_posix()
            or any(part.startswith(".") for part in path.parts)
            or path.parts[0] not in PUBLIC_ROOTS
            or len(path.parts) != 2 or path.suffix not in PUBLIC_SUFFIXES):
        raise ProjectStateError("Only direct public Markdown, TOML, or JSON records in docs/ or experiments/ are allowed.")
    return path


class _SnapshotChanged(Exception):
    """A bounded retry may yield a stable observation."""


@dataclass(frozen=True)
class _ObservedFile:
    data: bytes
    identity: tuple[int, ...]


def _metadata(details: os.stat_result) -> tuple[int, ...]:
    return (details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns,
            details.st_ctime_ns, details.st_mode, details.st_nlink)


@contextmanager
def _directory(path: str | Path, *, parent: int | None = None):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _read_file(root: int, value: str, budget: list[int]) -> _ObservedFile | None:
    """Open each component relative to pinned descriptors; never follow links.

    Missing is an observation too. Reopening in the second collection detects
    replacements/appearances without consulting the filesystem during assembly.
    """
    path = _safe_relative_path(value)
    try:
        with _directory(path.parts[0], parent=root) as directory:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                 dir_fd=directory)
    except FileNotFoundError:
        return None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ProjectStateError("Public records must be regular files with a single hard link.")
        if before.st_size > MAX_FILE_BYTES:
            raise ProjectStateError("Public record exceeds the per-file byte limit.")
        data = bytearray()
        while True:
            chunk = os.read(descriptor, min(65536, MAX_FILE_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            budget[0] += len(chunk)
            if len(data) > MAX_FILE_BYTES or budget[0] > MAX_SNAPSHOT_BYTES:
                raise ProjectStateError("Public briefing exceeds its byte limits.")
        if _metadata(before) != _metadata(os.fstat(descriptor)):
            raise _SnapshotChanged
        return _ObservedFile(bytes(data), _metadata(before))
    finally:
        os.close(descriptor)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalise_sources(index: dict[str, Any]) -> list[dict[str, Any]]:
    sources = index.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_SOURCES:
        raise ProjectStateError("Index source count is missing or exceeds its limit.")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ProjectStateError("Each source must be a table.")
        source_id = source.get("id")
        location = source.get("location")
        reviewed_sha256 = source.get("reviewed_sha256")
        if not isinstance(source_id, str) or not source_id or source_id in seen:
            raise ProjectStateError("Every source requires a unique non-empty id.")
        if not isinstance(location, str) or not location:
            raise ProjectStateError(f"Source {source_id} requires a location.")
        if reviewed_sha256 is not None and not _valid_hash(reviewed_sha256):
            raise ProjectStateError(f"Source {source_id} has an invalid reviewed_sha256.")
        path = source.get("path")
        if path is not None and not isinstance(path, str):
            raise ProjectStateError(f"Source {source_id} path must be a string.")
        if path is not None:
            _safe_relative_path(path)
            publication = source.get("publication_status")
            if not isinstance(publication, str) or publication not in {
                "published", "published_shared_baseline", "published_campaign_record",
                "published_campaign_freeze", "published_campaign_protocol",
                "reviewed_public_working_record",
            }:
                raise ProjectStateError("File sources require an explicit public publication status.")
        runtime_status = source.get("runtime_status")
        if path is None and (not isinstance(runtime_status, str) or runtime_status not in {"not_checked", "unavailable"}):
            raise ProjectStateError(
                f"Non-file source {source_id} must declare runtime_status as not_checked or unavailable."
            )
        seen.add(source_id)
        result.append(dict(source))
    return sorted(result, key=lambda item: item["id"])


def _normalise_claims(index: dict[str, Any], source_ids: set[str]) -> list[dict[str, Any]]:
    claims = index.get("claims")
    if not isinstance(claims, list) or not 1 <= len(claims) <= MAX_CLAIMS:
        raise ProjectStateError("Index claim count is missing or exceeds its limit.")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise ProjectStateError("Each claim must be a table.")
        claim_id = claim.get("id")
        section = claim.get("briefing_section")
        statement = claim.get("statement")
        sources = claim.get("sources")
        if not isinstance(claim_id, str) or not claim_id or claim_id in seen:
            raise ProjectStateError("Every claim requires a unique non-empty id.")
        if not isinstance(section, str) or not section:
            raise ProjectStateError(f"Claim {claim_id} requires a briefing_section.")
        if not isinstance(statement, str) or not statement:
            raise ProjectStateError(f"Claim {claim_id} requires a statement.")
        if not isinstance(sources, list) or not sources or not all(isinstance(item, str) for item in sources):
            raise ProjectStateError(f"Claim {claim_id} requires one or more source ids.")
        unknown_sources = sorted(set(sources) - source_ids)
        if unknown_sources:
            raise ProjectStateError(f"Claim {claim_id} names unknown source ids: {', '.join(unknown_sources)}.")
        layer = claim.get("layer", "shared_baseline")
        if not isinstance(layer, str) or layer not in {"shared_baseline", "working_observation", "current_assignment"}:
            raise ProjectStateError(f"Claim {claim_id} has an unsupported layer.")
        seen.add(claim_id)
        result.append(dict(claim))
    return sorted(result, key=lambda item: item["id"])


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _inventory_paths(root: int, index: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    inventory = index.get("inventory", {})
    if not isinstance(inventory, dict):
        raise ProjectStateError("[inventory] must be a table.")
    roots = inventory.get("roots", [])
    ignored = inventory.get("ignored", [])
    if not isinstance(roots, list) or not all(isinstance(item, str) for item in roots):
        raise ProjectStateError("inventory.roots must be a list of relative paths.")
    if len(roots) != len(set(roots)) or not set(roots) <= PUBLIC_ROOTS:
        raise ProjectStateError("Inventory roots must be distinct application-approved public directories.")
    if not isinstance(ignored, list) or not all(isinstance(item, str) for item in ignored):
        raise ProjectStateError("inventory.ignored must be a list of relative paths.")
    expected: dict[str, str] = {}
    records = inventory.get("records", [])
    if not isinstance(records, list) or len(records) > MAX_INVENTORY_ENTRIES:
        raise ProjectStateError("Inventory records are invalid or exceed their limit.")
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str) or not isinstance(record.get("sha256"), str):
            raise ProjectStateError("Each inventory record needs path and sha256 strings.")
        path = _safe_relative_path(record["path"])
        if not _valid_hash(record["sha256"]):
            raise ProjectStateError(f"Inventory hash is invalid for {path}.")
        if path.parts[0] not in roots:
            raise ProjectStateError("Inventory record is outside the configured public inventory roots.")
        key = path.as_posix()
        if key in expected:
            raise ProjectStateError(f"Inventory path is duplicated: {key}.")
        expected[key] = record["sha256"]

    ignored_set = {_safe_relative_path(item).as_posix() for item in ignored}
    actual: list[str] = []
    count = 0
    for root_value in sorted(roots):
        try:
            with _directory(root_value, parent=root) as directory:
                with os.scandir(directory) as entries:
                    for candidate in entries:
                        count += 1
                        if count > MAX_INVENTORY_ENTRIES:
                            raise ProjectStateError("Public inventory exceeds its entry limit.")
                        # No recursion: private/hidden subtrees and links are not inspected.
                        if candidate.name.startswith(".") or Path(candidate.name).suffix not in PUBLIC_SUFFIXES:
                            continue
                        relative = f"{root_value}/{candidate.name}"
                        if relative in ignored_set:
                            continue
                        try:
                            details = candidate.stat(follow_symlinks=False)
                        except FileNotFoundError:
                            raise _SnapshotChanged from None
                        if stat.S_ISREG(details.st_mode):
                            actual.append(relative)
        except FileNotFoundError:
            continue
    return expected, sorted(actual)


def _source_result(source: dict[str, Any], contents: dict[str, bytes]) -> dict[str, Any]:
    result = {
        "id": source["id"],
        "location": source["location"],
        "section": source.get("section"),
        "publication_status": source.get("publication_status", "published"),
        "reviewed_sha256": source.get("reviewed_sha256"),
    }
    path = source.get("path")
    if path is None:
        result["status"] = source["runtime_status"]
        result["path"] = None
        return result
    result["path"] = path
    if path not in contents:
        result["status"] = "missing"
        return result
    digest = _sha256(contents[path])
    result["observed_sha256"] = digest
    result["status"] = "current" if digest == source.get("reviewed_sha256") else "stale"
    return result


def _claim_result(claim: dict[str, Any], statuses: dict[str, str]) -> dict[str, Any]:
    source_statuses = {source_id: statuses[source_id] for source_id in sorted(claim["sources"])}
    unresolved = {"stale", "missing", "not_checked", "unavailable"}
    result = {
        "id": claim["id"],
        "layer": claim.get("layer", "shared_baseline"),
        "statement": claim["statement"],
        "source_ids": sorted(claim["sources"]),
        "source_statuses": source_statuses,
        "status": "current" if not unresolved.intersection(source_statuses.values()) else "stale_or_unresolved",
    }
    for key in ("topic", "position", "recorded_at", "label"):
        if key in claim:
            result[key] = claim[key]
    return result


def _assemble(
    index: dict[str, Any],
    contents: dict[str, bytes],
    expected_inventory: dict[str, str],
    actual_inventory: list[str],
) -> dict[str, Any]:
    sources = _normalise_sources(index)
    source_by_id = {source["id"]: source for source in sources}
    claims = _normalise_claims(index, set(source_by_id))
    source_results = [_source_result(source, contents) for source in sources]
    statuses = {source["id"]: source["status"] for source in source_results}
    claim_results = [_claim_result(claim, statuses) for claim in claims]

    sections: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim, result in zip(claims, claim_results):
        sections[claim["briefing_section"]].append(result)
    briefing = {key: sorted(value, key=lambda item: item["id"]) for key, value in sorted(sections.items())}

    conflicts: list[dict[str, Any]] = []
    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claim_results:
        if isinstance(claim.get("topic"), str) and isinstance(claim.get("position"), str):
            by_topic[claim["topic"]].append(claim)
    for topic, candidates in sorted(by_topic.items()):
        positions = {candidate["position"] for candidate in candidates}
        if len(positions) > 1:
            conflicts.append(
                {
                    "topic": topic,
                    "claim_ids": sorted(candidate["id"] for candidate in candidates),
                    "status": "unresolved",
                    "reason": "Conflicting layers are retained; the reader does not apply a newest-wins rule.",
                }
            )

    actual_set = set(actual_inventory)
    expected_set = set(expected_inventory)
    new_records = sorted(actual_set - expected_set)
    missing_records = sorted(expected_set - actual_set)
    revised_records: list[str] = []
    for path in sorted(actual_set & expected_set):
        if _sha256(contents[path]) != expected_inventory[path]:
            revised_records.append(path)
    inventory_status = "current" if not (new_records or missing_records or revised_records) else "review_needed"

    coverage = index.get("coverage", {})
    if not isinstance(coverage, dict):
        raise ProjectStateError("[coverage] must be a table.")
    return {
        "schema_version": index.get("schema_version"),
        "project_id": index.get("project_id"),
        "snapshot": {"status": "consistent", "basis": "bounded_double_collection"},
        "briefing": briefing,
        "sources": source_results,
        "source_consistency": {
            "status": (
                "current_for_verifiable_sources"
                if all(item["status"] == "current" for item in source_results if item["path"] is not None)
                else "review_needed"
            ),
            "sources": {item["id"]: item["status"] for item in source_results},
            "unverified_source_ids": sorted(
                item["id"] for item in source_results if item["status"] in {"not_checked", "unavailable"}
            ),
        },
        "coverage": {
            "status": coverage.get("status", "partial"),
            "reviewed_at": coverage.get("reviewed_at"),
            "reviewed_shared_baseline": coverage.get("reviewed_shared_baseline"),
            "remote_freshness": "not_checked",
            "local_git_freshness": "not_checked",
            "baseline_identity": "indexed_reference_only",
            "uninspected_contexts": sorted(coverage.get("uninspected_contexts", [])),
            "inventory": {
                "status": inventory_status,
                "scope": "direct_approved_public_records",
                "new_public_records": new_records,
                "missing_reviewed_records": missing_records,
                "revised_public_records": revised_records,
            },
        },
        "conflicts": conflicts,
        "limitations": index.get("limitations", []),
    }


def _snapshot(root: int) -> tuple[dict[str, Any], dict[str, bytes], dict[str, str], list[str]] | None:
    budget = [0]
    index_path = INDEX_PATH.as_posix()
    index_file = _read_file(root, index_path, budget)
    if index_file is None:
        raise ProjectStateError("Configured public briefing index is missing.")
    try:
        index = tomllib.loads(index_file.data.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        if _read_file(root, index_path, budget) != index_file:
            return None
        # Parser diagnostics can echo index content; keep the operator error bounded.
        raise ProjectStateError("Unable to parse the public briefing index as UTF-8 TOML.") from None
    if index.get("schema_version") != 1:
        raise ProjectStateError("Unsupported project-state index schema_version.")
    coverage = index.get("coverage", {})
    if not isinstance(coverage, dict):
        raise ProjectStateError("Index coverage must be a table.")
    for values in (index.get("limitations", []), coverage.get("uninspected_contexts", [])):
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ProjectStateError("Index limitations and uninspected contexts must be lists of strings.")
    sources = _normalise_sources(index)
    _normalise_claims(index, {source["id"] for source in sources})
    expected_inventory, actual_inventory = _inventory_paths(root, index)
    paths = set(expected_inventory) | {source["path"] for source in sources if source.get("path") is not None}
    before = {path: _read_file(root, path, budget) for path in sorted(paths)}
    # Double collection includes missing sources and reviewed inventory records.
    # It detects observed changes, not an atomic filesystem transaction.
    for path, observed in before.items():
        if _read_file(root, path, budget) != observed:
            return None
    if _read_file(root, index_path, budget) != index_file:
        return None
    current_expected, current_actual = _inventory_paths(root, index)
    if current_expected != expected_inventory or current_actual != actual_inventory:
        return None
    # Files disappearing between enumeration and first read invalidate that pass.
    if any(before[path] is None for path in set(actual_inventory) & paths):
        return None
    contents = {path: observed.data for path, observed in before.items() if observed is not None}
    return index, contents, expected_inventory, actual_inventory


def read_project_state(project_root: Path) -> dict[str, Any]:
    """Return a deterministic public briefing from the configured project root.

    ``project_root`` is supplied by administrative startup configuration.  The
    reader only opens direct approved public records through no-follow directory
    descriptors. Public record and index contents still require editorial review.
    A consistent snapshot means two bounded collections agreed, not a transaction
    across working files, a Git commit, or a defense against a hostile root owner.
    """

    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise ProjectStateError("This reader requires POSIX no-follow descriptor-relative reads.")
    try:
        root = Path(project_root).resolve(strict=True)
        with _directory(root) as descriptor:
            for attempt in range(1, MAX_SNAPSHOT_ATTEMPTS + 1):
                try:
                    result = _snapshot(descriptor)
                except _SnapshotChanged:
                    continue
                if result is not None:
                    index, contents, expected_inventory, actual_inventory = result
                    assembled = _assemble(index, contents, expected_inventory, actual_inventory)
                    assembled["snapshot"]["attempt"] = attempt
                    return assembled
    except OSError:
        raise ProjectStateError("Public briefing filesystem access failed or a path was unsafe.") from None
    return {
        "schema_version": 1,
        "project_id": None,
        "snapshot": {
            "status": "inconsistent",
            "attempts": MAX_SNAPSHOT_ATTEMPTS,
            "reason": "Index or configured sources changed while the briefing was read.",
        },
        "briefing": {},
        "sources": [],
        "source_consistency": {"status": "unknown", "sources": {}},
        "coverage": {"status": "unknown"},
        "conflicts": [],
        "limitations": ["No briefing claims were returned from an inconsistent snapshot."],
    }


def main(argv: list[str] | None = None) -> int:
    """Print the same diagnostic JSON used by the adapter."""

    parser = argparse.ArgumentParser(description="Read the public Mynyra project briefing index.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Administrative project-root setting.")
    arguments = parser.parse_args(argv)
    try:
        result = read_project_state(arguments.project_root)
    except ProjectStateError as error:
        print(f"project-state: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
