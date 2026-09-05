# ASUS working context

## Operating allocation

For the current month, ASUS Ubuntu Desktop is the primary Mynyra codebase,
development and local-execution environment. GitHub is the durable shared source
of truth. The Mac is reserved for heavy simulations. This is a temporary operating
allocation, not a permanent architectural decision.

## Starting point

Start work from the branch and pull request that contain this document. Before
changing code, read the [worldmap](WORLDMAP.md), [implementation plan](IMPLEMENTATION_PLAN.md)
and [data readiness report](DATA_READINESS_REPORT.md).

The current project state is:

- cTrader integration is **demo and view-only**; no order-placement path is
  implemented or authorized.
- XAUUSD on M1 is the starting market. A change requires comparative evidence.
- Faraz historical data has been normalized from confirmed Tehran time and
  independently validated. The raw files, normalized output and manifests are
  private local data.
- A one-hour FIBO XAUUSD bid/ask capture supplies initial cost evidence. It is not
  proof of executable profitability or all-session trading costs.
- The next work is source-backed research and a controlled comparison of 5–7
  strategy candidates. Define rules and chronological data splits before examining
  results. Do not submit demo or live orders.

## Local data and credentials

Keep credentials, cTrader tokens, raw archives, normalized datasets, quote logs,
account snapshots and other private run output under `.local/`. That directory is
intentionally ignored and must never be committed. ASUS needs its own private
setup; do not copy credentials through GitHub.

## Before the next implementation task

Run the documented tests and data validation. Confirm the working tree is clean,
keep changes on a `codex/` branch, and open a pull request to `main` for reviewed
versionable changes. Do not merge automatically.
