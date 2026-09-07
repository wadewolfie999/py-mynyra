# Locked research expansion sequence

Operating discipline: [Praxis](PRAXIS.md).

Agreed with the owner on 2026-09-07. This document owns the order and completion
criteria for the next research expansion. It is a work plan, not a numerical
preregistration or evidence of completed experiments.

## 1. Research candidates, diagnose SMA, assess longer history

Research and define at least ten additional XAUUSD M1 strategies, alongside the
separate SMA sizing investigation. Initial hypotheses: session opening-range
breakout, previous-day range breakout, failed-breakout reversal, volatility-
compression breakout, trend pullback, impulse continuation, impulse exhaustion,
higher-timeframe trend with M1 entry, regression-residual mean reversion, and
session-conditioned momentum. Sources must support method semantics; do not
mistake indicator documentation for evidence of XAUUSD M1 profitability. Record
related mechanisms and do not count parameter variants as independent strategies.

Compare SMA executed/skipped decisions and subsequent paths to explain the
account/signal difference. Treat discovered filters as exploratory hypotheses.
Assess longer independent history, provider/quote-side semantics, coverage,
quality, access terms, costs and storage needs. No purchase is authorized.

Completion: a source-backed candidate specification set, SMA diagnostic report,
and data-source assessment identifying available history and remaining gaps.
January–March is already observed and must be labeled exploratory in new work.

## 2. Define the data model and benchmark PostgreSQL

Preferred direction: PostgreSQL owns the catalog of sources, dataset versions,
quality findings, experiment definitions, runs and artifact references. Retain
immutable original files and frozen experiment inputs with hashes. Define source,
symbol, timestamp, quote-side and revision identity explicitly. A corrected
history creates a new version; it must not mutate an old experiment's inputs.

Benchmark a bounded PostgreSQL prototype against the existing file workflow using
representative ingestion, time-range reads, result queries and storage footprint.
Measure before selecting production layout. SQLite remains the simpler local
alternative; DuckDB/Parquet is an optional analytical layer only if measurements
justify it. TimescaleDB is deferred. Database service installation/configuration
requires the concrete deployment decision and applicable system-change authority;
this plan does not authorize credentials, network exposure or paid services.

Completion: documented schema and ownership, measured comparison, and a justified
integration/deployment decision with resource and recovery requirements.

## 3. Prove one complete data-to-result path

Import → validate → freeze snapshot → run unchanged baseline → reconcile results
→ back up and restore. Compare the baseline against existing file-based evidence.
Prove duplicate-import handling, explicit revision behavior, timestamp/precision
preservation, interrupted-ingest recovery, snapshot reproducibility and restored
artifact references. The simulator consumes a frozen snapshot rather than mutable
live database queries. Protect reserved periods from exploratory access.

Completion: one scripted end-to-end proof, reconciled baseline results and a
successful isolated restore. Retain old evidence and a documented rollback path.

## 4. Preregister and execute the expanded batch

After steps 1–3 pass, finalize and commit exact rules, parameters, costs, sizing,
splits, selection thresholds, candidate count and evaluation procedure before
inspecting new candidate results. Use one specification per new candidate in the
initial batch; record all failures. Treat any SMA-derived filter as an additional
explicit hypothesis. Include unchanged SMA and no-trade baselines, separate signal
and account views, cost sensitivity, dependence and expanded-search considerations.

Keep April sealed throughout exploration. A new evaluation protocol and committed
finalist freeze must precede any decision to open it. Prefer longer independent
history where available. If suitable evaluation data is unavailable, report an
exploratory screen and the evidence gap; do not relabel familiar data as untouched.

Execute using scripts with bounded progress summaries and durable private outputs.
Report every candidate's outcome, reproduction evidence and limitations. No
survivor is a valid outcome. Changes go through a PR; do not merge automatically.

Completion: reproducible comparative evidence for at least ten additional
strategies, a separately identified SMA investigation, and an evidence-backed
report/PR stating exactly which evaluation claims the data supports.

## Sequence and authority

The dependency order is 1 → 2 → 3 → 4. Read-only preparation may overlap; completion
of an earlier gate must precede dependent implementation or experimental claims.
Do not substitute database expansion for the strategy comparison, or skip the
end-to-end proof to accelerate the batch. Routine decisions stay autonomous;
material missing authority or unavailable inputs must be surfaced explicitly.

Preserve private data under ignored owner-only `.local/`. No orders, trading-scope
changes, spending, live quote capture or shadow campaign are authorized by locking
this sequence. The existing five-candidate report and frozen evidence remain intact.
