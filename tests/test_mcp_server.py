"""Real stdio transport tests for the one-tool Py-Mynyra adapter."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fixture_root() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    docs = root / "docs"
    docs.mkdir()
    source = "Public source\n"
    (docs / "source.md").write_text(source, encoding="utf-8")
    (docs / "PROJECT_STATE.toml").write_text(
        f'''schema_version = 1
project_id = "adapter-fixture"
limitations = ["synthetic"]

[coverage]
status = "partial"
reviewed_at = "2026-09-15T00:00:00Z"
reviewed_shared_baseline = "fixture"
remote_freshness = "not_checked"
uninspected_contexts = ["conversations"]

[inventory]
roots = ["docs"]
ignored = ["docs/PROJECT_STATE.toml"]

[[inventory.records]]
path = "docs/source.md"
sha256 = "{_digest(source)}"

[[sources]]
id = "public"
path = "docs/source.md"
location = "docs/source.md"
section = "State"
publication_status = "published"
reviewed_sha256 = "{_digest(source)}"

[[claims]]
id = "direction"
briefing_section = "project_direction"
layer = "shared_baseline"
statement = "Fixture direction."
sources = ["public"]
''',
        encoding="utf-8",
    )
    return temporary, root


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary, self.project_root = _fixture_root()
        self.addCleanup(self.temporary.cleanup)
        self.adapter_root = Path(__file__).resolve().parents[1]

    def test_one_tool_has_no_model_arguments_and_delegates_to_reader(self) -> None:
        environment = dict(os.environ, MYNYRA_PROJECT_ROOT=str(self.project_root))
        inspection = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json; from pathlib import Path; from mynyra.mcp_server import create_server; "
                "mcp = create_server(Path(__import__('os').environ['MYNYRA_PROJECT_ROOT'])); "
                "tool = list(mcp._tool_manager._tools.values())[0]; "
                "print(json.dumps({'name': tool.name, 'schema': tool.parameters}, sort_keys=True))",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        detail = json.loads(inspection.stdout)
        self.assertEqual("get_project_state", detail["name"])
        self.assertEqual({}, detail["schema"].get("properties", {}))
        self.assertFalse(detail["schema"].get("required"))

    def test_real_stdio_round_trip_and_sdk_context_cleanup(self) -> None:
        from mynyra.project_state import read_project_state

        async def run_client() -> dict[str, object]:
            from mcp.client.session import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client

            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mynyra.mcp_server"],
                env=dict(os.environ, MYNYRA_PROJECT_ROOT=str(self.project_root)),
                cwd=str(self.adapter_root),
            )
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertEqual(["get_project_state"], [tool.name for tool in tools.tools])
                    self.assertEqual({}, tools.tools[0].input_schema.get("properties", {}))
                    self.assertFalse(tools.tools[0].input_schema.get("required"))
                    result = await session.call_tool("get_project_state", {})
                    self.assertFalse(result.is_error)
                    self.assertEqual("adapter-fixture", result.structured_content["project_id"])
                    unexpected = await session.call_tool("get_project_state", {"path": "not-allowed"})
                    self.assertTrue(unexpected.is_error)
                    return result.structured_content

        received = asyncio.run(run_client())
        self.assertEqual(read_project_state(self.project_root), received)
        self.assertEqual("consistent", received["snapshot"]["status"])

    def test_unsafe_reader_configuration_returns_bounded_unavailable_result_over_stdio(self) -> None:
        index = self.project_root / "docs/PROJECT_STATE.toml"
        index.write_text(index.read_text().replace("docs/source.md", ".local/secret.md"))

        async def run_client():
            from mcp.client.session import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client

            parameters = StdioServerParameters(
                command=sys.executable, args=["-m", "mynyra.mcp_server"],
                env=dict(os.environ, MYNYRA_PROJECT_ROOT=str(self.project_root)),
                cwd=str(self.adapter_root),
            )
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.call_tool("get_project_state", {})

        result = asyncio.run(run_client())
        self.assertEqual("unavailable", result.structured_content["snapshot"]["status"])
        self.assertEqual({}, result.structured_content["briefing"])
        self.assertNotIn("secret.md", json.dumps(result.structured_content))

    def test_adapter_has_no_policy_network_or_private_data_logic(self) -> None:
        from mynyra import mcp_server as server

        source = inspect.getsource(server)
        for forbidden in ("mynyra.ctrader", "mynyra.market", "socket", "urllib", ".local", "open(", "write_"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
