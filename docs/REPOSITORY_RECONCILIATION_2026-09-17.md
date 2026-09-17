# Repository reconciliation — 2026-09-17

**Status:** review candidate on
`codex/reconcile-authoritative-project-state`.<br>
**GitHub integration base:** `origin/main`
`8d5081131af3b88cb45f554a2d730d7108ca8ddb`.<br>
**Purpose:** make the reviewed GitHub repository the durable project state after
the associated pull request is merged.

## Audit and dispositions

| Candidate | Disposition | Reason |
| --- | --- | --- |
| Fetched GitHub `origin/main` | Integration base | Latest shared repository revision observed before this reconciliation. |
| Execution-roadmap worktree | Adopt public records and navigation | Contains the active roadmap, P1/P2 working records, briefing index, and workflow. |
| Project-state worktree | Adopt reader and tests only | Its implementation is needed; its local index explicitly described itself as superseded. |
| Local `py-myn-mcp` prototype | Adopt adapter, tests, and path-free dependency pins | Provides the reviewed one-tool local stdio transport for the public resolver. |
| Bigi validation branch | Preserve the unique verification section | Its reported demo-only workstation validation is historical evidence not otherwise present on main. |
| Strategy-research branch | Do not merge | Its relevant patch is already present on main under rewritten history. |
| Older ChatGPT clone | Exclude and retain in place | It is based on the September 3 repository state and contains superseded planning edits. |
| Codex retained snapshots | Exclude | They contain generated environment metadata and one transient non-project lockfile. |

No credential, token, raw archive, normalized dataset, quote log, account
snapshot, private run output, sealed data, or personal financial value was read,
copied, or committed during this reconciliation.

## Repository changes

The reconciliation imports the active public briefing records, the safe
project-state resolver, its tests, the one-tool adapter, the optional MCP
dependency lock, and the historical pilot record. It also corrects documentation
that previously depended on temporary worktree paths or described a merged
repository adoption as pending.

The implementation retains the existing hard boundary: cTrader remains demo-only
and view-only, the MCP adapter is read-only and public-record-only, and no order,
provider, payout, account, network, or private-data capability is introduced.

## Verification and authority

The integration must pass the documented core regression gate, resolver/index
checks, optional MCP stdio tests, dependency checks, compilation, whitespace
checks, and review before it is published. The branch is a candidate state only.
GitHub `main` becomes the authoritative shared project state after the reviewed
pull request is merged; no branch, local record, or successful test grants
additional operational authority.

The ASUS environment is treated as clean based on the owner confirmation made for
this reconciliation. The sanctioned node inventory was unavailable on the Mac, so
this document does not claim an independent ASUS inspection.

## Post-merge cutover and preservation

After merge and canonical-checkout verification, the existing local
`py-mynyra-project-state` registration may be repointed to the repository-owned
`py-myn-mcp` command with only `get_project_state` enabled. Verify a fresh
stdio discovery and call before retiring any source location.

Do not delete the former sources. Move the two linked source worktrees and the
standalone adapter prototype into the owner-home archive directory
`Archives/py-mynyra-reconciliation-2026-09-17/`, preserving their branches,
files, and a small rollback manifest. The old ChatGPT clone, other active task
worktrees, remote branches, and private data remain outside this archive
operation.
