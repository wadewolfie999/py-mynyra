"""Client-owned stdio MCP adapter with one no-argument public briefing tool."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mynyra.project_state import ProjectStateError, read_project_state


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT_ENVIRONMENT_VARIABLE = "MYNYRA_PROJECT_ROOT"


def configured_project_root() -> Path:
    """Return the administrative root configuration; never accept it from a tool call."""

    value = os.environ.get(PROJECT_ROOT_ENVIRONMENT_VARIABLE)
    if not value:
        raise RuntimeError(f"{PROJECT_ROOT_ENVIRONMENT_VARIABLE} must name the Py-Mynyra project root.")
    return Path(value)


def create_server(project_root: Path) -> MCPServer:
    """Create an adapter whose only capability delegates to Py-Mynyra."""

    server = MCPServer("py-mynyra-project-state")

    @server.tool()
    def get_project_state(ctx: Context) -> dict[str, Any]:
        """Return Py-Mynyra's reviewed public project briefing with source and coverage status."""

        raw_parameters = ctx.request_context.params or {}
        if raw_parameters.get("arguments"):
            raise ToolError("get_project_state accepts no arguments.")
        try:
            return read_project_state(project_root)
        except ProjectStateError:
            LOGGER.warning("Project-state reader rejected the administrative configuration.")
            return {
                "schema_version": 1,
                "project_id": None,
                "snapshot": {"status": "unavailable", "reason": "Configured public briefing is unavailable."},
                "briefing": {},
                "sources": [],
                "source_consistency": {"status": "unknown", "sources": {}},
                "coverage": {"status": "unknown"},
                "conflicts": [],
                "limitations": ["The configured public briefing could not be read safely."],
            }

    return server


def main() -> None:
    """Serve the client-owned local process over stdio."""

    logging.basicConfig(level=logging.INFO)
    create_server(configured_project_root()).run(transport="stdio")


if __name__ == "__main__":
    main()
