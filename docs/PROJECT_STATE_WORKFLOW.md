# Py-Mynyra briefing workflow

For each task using this repository:

1. When the optional local MCP server is installed and registered, call
   `get_project_state()` on entry. Otherwise use
   `mynyra-project-state --project-root .` or inspect the owning records.
2. If a source is `stale` or `missing`, or the inventory says `review_needed`, inspect the affected public record before relying on its claims.
3. Do the authorized work in the owning record. The briefing is a reviewed summary, not the authority and not an authorization grant.
4. At closeout, update the owning public record and `docs/PROJECT_STATE.toml` together. Refresh a recorded SHA-256 only after reading and reviewing the changed content.

Detection runs on every resolver call and covers registered local public files. It
does not detect conversation-only decisions, private `.local` records, remote
changes, or unregistered files outside the public inventory roots. The active
briefing, reader, and optional adapter are repository-owned:
`docs/PROJECT_STATE.toml`, `mynyra.project_state`, and
`mynyra.mcp_server`. See `PROJECT_STATE_MCP_PILOT.md` for operational limits.
