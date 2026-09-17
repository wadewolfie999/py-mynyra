"""Synthetic public-fixture tests for the project-state reader."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mynyra import project_state


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def manifest(*, sources: str, claims: str, inventory: str = "", coverage: str = "") -> str:
    return f'''schema_version = 1
project_id = "synthetic-mynyra"
limitations = ["Synthetic fixture; no private records are read."]

[coverage]
status = "partial"
reviewed_at = "2026-09-15T00:00:00Z"
reviewed_shared_baseline = "baseline"
remote_freshness = "not_checked"
uninspected_contexts = ["uninspected conversation", "other machine"]
{coverage}

[inventory]
roots = ["docs"]
ignored = ["docs/PROJECT_STATE.toml"]
{inventory}
{sources}
{claims}
'''


class ProjectStateTests(unittest.TestCase):
    def make_root(self, *, source_text: str = "Purpose record\n") -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        docs = root / "docs"
        docs.mkdir()
        (docs / "purpose.md").write_text(source_text, encoding="utf-8")
        source = f'''[[sources]]
id = "purpose"
path = "docs/purpose.md"
location = "docs/purpose.md"
section = "Purpose"
publication_status = "published"
reviewed_sha256 = "{digest(source_text)}"
'''
        claims = '''[[claims]]
id = "project-direction"
briefing_section = "project_direction"
layer = "shared_baseline"
topic = "direction"
position = "project direction"
statement = "The project direction is independent from the current implementation assignment."
sources = ["purpose"]

[[claims]]
id = "assignment"
briefing_section = "current_assignment"
layer = "current_assignment"
statement = "The current assignment is a read-only briefing implementation, not a project-direction change."
sources = ["purpose"]
'''
        inventory = f'''[[inventory.records]]
path = "docs/purpose.md"
sha256 = "{digest(source_text)}"
'''
        (docs / "PROJECT_STATE.toml").write_text(
            manifest(sources=source, claims=claims, inventory=inventory), encoding="utf-8"
        )
        return root

    def test_current_state_is_deterministic_and_separates_assignment(self) -> None:
        root = self.make_root()
        first = project_state.read_project_state(root)
        second = project_state.read_project_state(root)
        self.assertEqual(first, second)
        self.assertEqual("consistent", first["snapshot"]["status"])
        self.assertEqual("current", first["sources"][0]["status"])
        self.assertEqual(["assignment"], [item["id"] for item in first["briefing"]["current_assignment"]])
        self.assertEqual(["project-direction"], [item["id"] for item in first["briefing"]["project_direction"]])

    def test_committed_repository_index_is_consistent_and_current(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]

        result = project_state.read_project_state(repository_root)

        self.assertEqual("consistent", result["snapshot"]["status"])
        self.assertEqual("current", result["coverage"]["inventory"]["status"])
        file_sources = [source for source in result["sources"] if source.get("path")]
        self.assertTrue(file_sources)
        self.assertTrue(all(source["status"] == "current" for source in file_sources))

    def test_reviewed_public_working_record_is_a_current_file_source(self) -> None:
        root = self.make_root()
        index = root / "docs/PROJECT_STATE.toml"
        index.write_text(
            index.read_text().replace(
                'publication_status = "published"',
                'publication_status = "reviewed_public_working_record"',
            ),
            encoding="utf-8",
        )

        result = project_state.read_project_state(root)

        self.assertEqual("current", result["sources"][0]["status"])
        self.assertEqual(
            "reviewed_public_working_record",
            result["sources"][0]["publication_status"],
        )

    def test_changed_source_marks_only_its_claim_stale_without_returning_source_body(self) -> None:
        root = self.make_root()
        (root / "docs/purpose.md").write_text("Changed public source\n", encoding="utf-8")
        result = project_state.read_project_state(root)
        self.assertEqual("stale", result["sources"][0]["status"])
        self.assertEqual("stale_or_unresolved", result["briefing"]["project_direction"][0]["status"])
        self.assertNotIn("Changed public source", json.dumps(result))

    def test_inventory_reports_new_and_revised_public_metadata(self) -> None:
        root = self.make_root()
        (root / "docs/purpose.md").write_text("Revised\n", encoding="utf-8")
        (root / "docs/new-record.md").write_text("New\n", encoding="utf-8")
        inventory = project_state.read_project_state(root)["coverage"]["inventory"]
        self.assertEqual("review_needed", inventory["status"])
        self.assertEqual(["docs/new-record.md"], inventory["new_public_records"])
        self.assertEqual(["docs/purpose.md"], inventory["revised_public_records"])

    def test_uninspected_context_and_external_working_source_remain_explicit(self) -> None:
        root = self.make_root()
        source = '''[[sources]]
id = "working-overlay"
location = "Unpublished working overlay"
section = "State"
publication_status = "unpublished_working"
runtime_status = "not_checked"
reviewed_sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
'''
        claims = '''[[claims]]
id = "working"
briefing_section = "unfinished_work"
layer = "working_observation"
statement = "A selected unpublished working observation requires reconciliation."
sources = ["working-overlay"]
'''
        (root / "docs/PROJECT_STATE.toml").write_text(manifest(sources=source, claims=claims), encoding="utf-8")
        result = project_state.read_project_state(root)
        self.assertEqual("not_checked", result["sources"][0]["status"])
        self.assertEqual("stale_or_unresolved", result["briefing"]["unfinished_work"][0]["status"])
        self.assertEqual(["other machine", "uninspected conversation"], result["coverage"]["uninspected_contexts"])

    def test_conflicting_layers_are_preserved_without_newest_wins(self) -> None:
        root = self.make_root()
        purpose_hash = digest("Purpose record\n")
        source = f'''[[sources]]
id = "baseline"
path = "docs/purpose.md"
location = "docs/purpose.md"
section = "State"
publication_status = "published"
reviewed_sha256 = "{purpose_hash}"

[[sources]]
id = "overlay"
location = "Unpublished overlay"
section = "State"
publication_status = "unpublished_working"
runtime_status = "not_checked"
'''
        claims = '''[[claims]]
id = "baseline-position"
briefing_section = "unfinished_work"
layer = "shared_baseline"
topic = "next-work"
position = "deferred"
statement = "Baseline defers the work."
sources = ["baseline"]

[[claims]]
id = "overlay-position"
briefing_section = "unfinished_work"
layer = "working_observation"
topic = "next-work"
position = "recorded-running"
statement = "Overlay records working state."
sources = ["overlay"]
'''
        (root / "docs/PROJECT_STATE.toml").write_text(manifest(sources=source, claims=claims), encoding="utf-8")
        result = project_state.read_project_state(root)
        self.assertEqual("unresolved", result["conflicts"][0]["status"])
        self.assertEqual(["baseline-position", "overlay-position"], result["conflicts"][0]["claim_ids"])

    def test_snapshot_retries_once_then_returns_no_claims_when_a_source_changes_mid_read(self) -> None:
        root = self.make_root()
        original = project_state._read_file
        changed = False

        def mutate_after_read(descriptor, path, budget):
            nonlocal changed
            data = original(descriptor, path, budget)
            if path == "docs/purpose.md":
                (root / path).write_text("mutated while reading\n", encoding="utf-8")
                changed = True
            return data

        with patch.object(project_state, "_read_file", side_effect=mutate_after_read):
            result = project_state.read_project_state(root)
        self.assertTrue(changed)
        self.assertEqual("inconsistent", result["snapshot"]["status"])
        self.assertEqual({}, result["briefing"])

    def test_traversal_and_symlink_sources_are_rejected(self) -> None:
        root = self.make_root()
        index = (root / "docs/PROJECT_STATE.toml")
        index.write_text(index.read_text(encoding="utf-8").replace("docs/purpose.md", "../outside.md", 1), encoding="utf-8")
        with self.assertRaises(project_state.ProjectStateError):
            project_state.read_project_state(root)

        root = self.make_root()
        target = root / "docs/target.md"
        target.write_text("Target\n", encoding="utf-8")
        (root / "docs/purpose.md").unlink()
        os.symlink(target, root / "docs/purpose.md")
        with self.assertRaises(project_state.ProjectStateError):
            project_state.read_project_state(root)

    def test_reader_uses_only_public_configured_paths_without_writes_or_network_imports(self) -> None:
        root = self.make_root()
        private = root / ".local"
        private.mkdir()
        private_file = private / "must-not-be-read.txt"
        private_file.write_text("private", encoding="utf-8")
        public_paths = {root / "docs/PROJECT_STATE.toml", root / "docs/purpose.md"}
        before = {path: path.stat().st_mtime_ns for path in public_paths | {private_file}}
        original = project_state._read_file
        observed: list[Path] = []

        def record_read(descriptor, path, budget):
            observed.append((root / path).resolve())
            return original(descriptor, path, budget)

        with patch.object(project_state, "_read_file", side_effect=record_read):
            expected = project_state.read_project_state(root)
        self.assertEqual({path.resolve() for path in public_paths}, set(observed))
        self.assertEqual(before, {path: path.stat().st_mtime_ns for path in before})

        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        completed = subprocess.run(
            [sys.executable, "-m", "mynyra.project_state", "--project-root", str(root)],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(expected, json.loads(completed.stdout))
        module_source = Path(project_state.__file__).read_text(encoding="utf-8")
        for forbidden in ("mynyra.ctrader", "mynyra.market", "socket", "urllib"):
            self.assertNotIn(forbidden, module_source)

    def test_misconfigured_private_source_and_inventory_are_rejected_before_read(self):
        for path in (".local/secret.md", "docs/.local/secret.md", "docs/private/secret.md",
                     "src/secret.md", "docs/.credentials.json", "docs/key.pem", "docs/../secret.md"):
            with self.subTest(path=path):
                root = self.make_root()
                index = root / "docs/PROJECT_STATE.toml"
                index.write_text(index.read_text().replace("docs/purpose.md", path), encoding="utf-8")
                original = project_state._read_file
                observed = []

                def record(descriptor, value, budget):
                    observed.append(value)
                    return original(descriptor, value, budget)

                with patch.object(project_state, "_read_file", side_effect=record):
                    with self.assertRaises(project_state.ProjectStateError):
                        project_state.read_project_state(root)
                self.assertEqual(["docs/PROJECT_STATE.toml"], observed)
        root = self.make_root()
        index = root / "docs/PROJECT_STATE.toml"
        index.write_text(index.read_text().replace('roots = ["docs"]', 'roots = [".local"]'))
        with self.assertRaises(project_state.ProjectStateError):
            project_state.read_project_state(root)

    def test_parent_symlink_and_hard_link_are_rejected(self):
        root = self.make_root()
        (root / "docs").rename(root / "original")
        (root / "docs").symlink_to(root / "original", target_is_directory=True)
        with self.assertRaises(project_state.ProjectStateError):
            project_state.read_project_state(root)
        root = self.make_root()
        os.link(root / "docs/purpose.md", root / "linked.md")
        with self.assertRaises(project_state.ProjectStateError):
            project_state.read_project_state(root)

    def test_symlink_swap_between_enumeration_and_open_does_not_read_target(self):
        root = self.make_root()
        original = project_state._read_file
        private = root / ".local"
        private.mkdir()
        (private / "secret.md").write_text("MUST NOT READ")

        def swap(descriptor, path, budget):
            if path == "docs/purpose.md":
                (root / path).unlink()
                (root / path).symlink_to(private / "secret.md")
            return original(descriptor, path, budget)

        with patch.object(project_state, "_read_file", side_effect=swap):
            with self.assertRaises(project_state.ProjectStateError):
                project_state.read_project_state(root)

    def test_parent_directory_swap_before_source_open_is_rejected(self):
        root = self.make_root()
        original = project_state._read_file
        private = root / ".local"
        private.mkdir()
        (private / "purpose.md").write_text("MUST NOT READ")

        def swap(descriptor, path, budget):
            if path == "docs/purpose.md":
                (root / "docs").rename(root / "saved-docs")
                (root / "docs").symlink_to(private, target_is_directory=True)
            return original(descriptor, path, budget)

        with patch.object(project_state, "_read_file", side_effect=swap):
            with self.assertRaises(project_state.ProjectStateError):
                project_state.read_project_state(root)

    def test_missing_source_is_recorded_without_post_snapshot_stat(self):
        root = self.make_root()
        (root / "docs/purpose.md").unlink()
        original = project_state._assemble

        def create_before_assembly(*args):
            (root / "docs/purpose.md").write_text("New after snapshot")
            return original(*args)

        with patch.object(project_state, "_assemble", side_effect=create_before_assembly):
            result = project_state.read_project_state(root)
        self.assertEqual("missing", result["sources"][0]["status"])
        self.assertEqual(["docs/purpose.md"], result["coverage"]["inventory"]["missing_reviewed_records"])

    def test_source_removed_after_snapshot_uses_collected_bytes(self):
        root = self.make_root()
        original = project_state._assemble

        def remove_before_assembly(*args):
            (root / "docs/purpose.md").unlink()
            return original(*args)

        with patch.object(project_state, "_assemble", side_effect=remove_before_assembly):
            result = project_state.read_project_state(root)
        self.assertEqual("current", result["sources"][0]["status"])

    def test_appearing_missing_source_retries_and_returns_new_coherent_observation(self):
        root = self.make_root()
        target = root / "docs/purpose.md"
        target.unlink()
        original = project_state._read_file
        changed = False

        def appear(descriptor, path, budget):
            nonlocal changed
            observed = original(descriptor, path, budget)
            if path == "docs/purpose.md" and not changed:
                target.write_text("Purpose record\n")
                changed = True
            return observed

        with patch.object(project_state, "_read_file", side_effect=appear):
            result = project_state.read_project_state(root)
        self.assertEqual(2, result["snapshot"]["attempt"])
        self.assertEqual("current", result["sources"][0]["status"])

    def test_removed_or_replaced_source_during_collection_retries(self):
        for replacement in (None, "replacement"):
            with self.subTest(replacement=replacement):
                root = self.make_root()
                original = project_state._read_file
                changed = False

                def change(descriptor, path, budget):
                    nonlocal changed
                    observed = original(descriptor, path, budget)
                    if path == "docs/purpose.md" and not changed:
                        (root / path).unlink()
                        if replacement is not None:
                            (root / path).write_text(replacement)
                        changed = True
                    return observed

                with patch.object(project_state, "_read_file", side_effect=change):
                    result = project_state.read_project_state(root)
                self.assertEqual(2, result["snapshot"]["attempt"])
                self.assertEqual("missing" if replacement is None else "stale", result["sources"][0]["status"])

    def test_inventory_does_not_descend_or_read_new_record_bodies(self):
        root = self.make_root()
        (root / "docs/.local").mkdir()
        (root / "docs/.local/secret.md").write_text("secret")
        (root / "docs/new.md").write_text("unreviewed")
        (root / "docs/link.md").symlink_to(root / "docs/.local/secret.md")
        original = project_state._read_file
        paths = []

        def observe(descriptor, path, budget):
            paths.append(path)
            return original(descriptor, path, budget)

        with patch.object(project_state, "_read_file", side_effect=observe):
            result = project_state.read_project_state(root)
        self.assertEqual(["docs/new.md"], result["coverage"]["inventory"]["new_public_records"])
        self.assertEqual({"docs/PROJECT_STATE.toml", "docs/purpose.md"}, set(paths))

    def test_limits_on_bytes_entries_sources_and_claims_fail_closed(self):
        for constant, maximum in (("MAX_FILE_BYTES", 1), ("MAX_SNAPSHOT_BYTES", 1),
                                  ("MAX_INVENTORY_ENTRIES", 1), ("MAX_SOURCES", 0), ("MAX_CLAIMS", 1)):
            with self.subTest(constant=constant):
                root = self.make_root()
                with patch.object(project_state, constant, maximum):
                    with self.assertRaises(project_state.ProjectStateError):
                        project_state.read_project_state(root)

    def test_fifo_and_missing_root_fail_safely(self):
        root = self.make_root()
        (root / "docs/purpose.md").unlink()
        os.mkfifo(root / "docs/purpose.md")
        with self.assertRaises(project_state.ProjectStateError):
            project_state.read_project_state(root)
        with self.assertRaises(project_state.ProjectStateError):
            project_state.read_project_state(root / "missing")

    def test_git_freshness_cannot_be_asserted_by_index(self):
        root = self.make_root()
        index = root / "docs/PROJECT_STATE.toml"
        index.write_text(index.read_text().replace('remote_freshness = "not_checked"', 'remote_freshness = "current"'))
        coverage = project_state.read_project_state(root)["coverage"]
        self.assertEqual("not_checked", coverage["remote_freshness"])
        self.assertEqual("not_checked", coverage["local_git_freshness"])
        self.assertEqual("indexed_reference_only", coverage["baseline_identity"])

    def test_in_place_change_during_descriptor_read_is_retried(self):
        root = self.make_root()
        original = os.read
        changed = False

        def mutate(descriptor, size):
            nonlocal changed
            data = original(descriptor, size)
            if data == b"Purpose record\n" and not changed:
                (root / "docs/purpose.md").write_text("Updated record\n")
                changed = True
            return data

        with patch.object(os, "read", side_effect=mutate):
            result = project_state.read_project_state(root)
        self.assertTrue(changed)
        self.assertEqual(2, result["snapshot"]["attempt"])
        self.assertEqual("stale", result["sources"][0]["status"])

    def test_invalid_publication_and_invalid_index_fail_without_content_echo(self):
        root = self.make_root()
        index = root / "docs/PROJECT_STATE.toml"
        index.write_text(index.read_text().replace('publication_status = "published"',
                                                  'publication_status = "private"'))
        with self.assertRaises(project_state.ProjectStateError):
            project_state.read_project_state(root)
        index.write_text('secret-value = "DO-NOT-ECHO\n')
        with self.assertRaises(project_state.ProjectStateError) as caught:
            project_state.read_project_state(root)
        self.assertNotIn("DO-NOT-ECHO", str(caught.exception))

    def test_runtime_audit_rejects_write_or_connection_attempts(self):
        root = self.make_root()
        script = '''import os, sys
from pathlib import Path
from mynyra.project_state import read_project_state
def audit(event, args):
    if event == "open":
        flags = args[2]
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError("Unexpected write-capable open")
    if event in {"socket.connect", "socket.bind", "subprocess.Popen", "os.system",
                 "os.rename", "os.remove", "os.mkdir", "os.link", "os.symlink", "os.chmod"}:
        raise AssertionError("Unexpected side effect: " + event)
sys.addaudithook(audit)
assert read_project_state(Path(sys.argv[1]))["snapshot"]["status"] == "consistent"
print("audited fixture read passed")
'''
        completed = subprocess.run([sys.executable, "-c", script, str(root)], check=True,
                                   capture_output=True, text=True,
                                   env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src")))
        self.assertIn("audited fixture read passed", completed.stdout)

    def test_malformed_coverage_and_limitations_are_safe_errors(self):
        for old, new in (('["uninspected conversation", "other machine"]', '"not a list"'),
                         ('["Synthetic fixture; no private records are read."]', '3'),
                         ('publication_status = "published"', 'publication_status = []'),
                         ('layer = "shared_baseline"', 'layer = []')):
            with self.subTest(new=new):
                root = self.make_root()
                index = root / "docs/PROJECT_STATE.toml"
                index.write_text(index.read_text().replace(old, new))
                with self.assertRaises(project_state.ProjectStateError):
                    project_state.read_project_state(root)


if __name__ == "__main__":
    unittest.main()
