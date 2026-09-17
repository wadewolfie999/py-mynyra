# Project-state MCP pilot

**Status:** reconciled repository candidate; effective after the associated review
is merged.<br>
**Prepared:** 2026-09-17 UTC<br>
**Scope:** one local, read-only, public-record briefing tool.

## Purpose

The pilot reduces repeated reconstruction of selected public Mynyra state. It is a
bounded coordination aid, not a project controller, approval system, data service,
or trading component. It does not establish a profitable strategy, provider
eligibility, payout feasibility, time savings, or authority for any action.

The pilot was first exercised as three separate local working directories. This
record brings its reviewed public implementation and evidence into the repository
without treating the earlier local arrangement as a deployment.

## Implemented interface

The optional local stdio adapter exposes exactly one tool:

```text
get_project_state()
```

The tool accepts no model-provided fields. Its project root is administrative
startup configuration through `MYNYRA_PROJECT_ROOT`; callers cannot supply a
path, revision, command, URL, SQL query, broker request, or evidence identifier.

The adapter delegates to `mynyra.project_state`, which:

- reads only direct, public `.md`, `.toml`, and `.json` records in approved
  `docs/` and `experiments/` roots;
- rejects private, hidden, nested, linked, special, oversized, or unreviewed
  records before their bytes can be read;
- checks source hashes and a non-recursive public inventory;
- performs two bounded descriptor-relative collections to report a consistent or
  explicitly unavailable snapshot; and
- never checks Git remotes, contacts a network service, or reads `.local`.

If the public index is unsafe or unavailable, the adapter returns a bounded,
generic unavailable result. It does not expose the rejected path or raw reader
error.

## Historical pilot evidence

The pre-consolidation pilot recorded a real local SDK stdio round trip against a
synthetic public fixture: tool discovery returned exactly the zero-input tool,
the result matched the direct resolver output, unexpected arguments were rejected,
and an unsafe index returned the bounded unavailable shape.

The resolver's synthetic suite covered private-path rejection, symlink and
hard-link rejection, FIFO and traversal rejection, source replacement races,
bounded input limits, inventory drift, stale hashes, and no-write/no-network
execution. Earlier local pilot reports recorded isolated context-recovery trials
and one bounded provider-screen handoff. Those observations remain historical and
do not prove durable host registration, shared-client operation, or measured
workflow savings.

## Installation and operation

The regular Mynyra package does not install MCP dependencies. For the optional
local adapter, install the repository's path-free optional lock under Python 3.11
and configure a client-owned stdio process with:

```text
command: <canonical-checkout>/.venv/bin/py-myn-mcp
MYNYRA_PROJECT_ROOT: <canonical-checkout>
enabled_tools: get_project_state
```

The process has no HTTP listener, background scheduler, database, credentials, or
broker/provider capability. Ending the client session ends the process.

## Maintenance and limits

Update the owning public record and `docs/PROJECT_STATE.toml` together. Refresh
a source or inventory hash only after reviewing the affected public content. A
matching hash proves reviewed byte identity, not semantic correctness, complete
coverage, live GitHub freshness, current private evidence, or a present
authorization grant.

The broader project design still lists campaign handoff, evidence reference,
authorization checks, resources, and proposal writes as possible future work.
They are not implemented by this pilot. No additional MCP tool, service, hosting,
or automation follows automatically from this record.
