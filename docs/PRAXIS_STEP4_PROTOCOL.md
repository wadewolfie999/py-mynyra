# Praxis Step 4 preregistration — exploratory screen

Approved scope: P01–P10, unchanged SMA and no-trade; no new filter, parameter
search, data acquisition, broker contact, spending or April evaluation. This
protocol and `experiments/praxis_step4_v1.toml` must be committed with tested
numerical code before the first new historical result. The TOML owns numerical
settings and hashes; `PRAXIS_STEP1_CANDIDATES.md` owns candidate semantics and
source limitations. It is pinned by hash. Sources support hypotheses, not profits.

## Exact rules and implementation interpretation

Use every P01–P10 definition and common contract in the pinned Step 1 document.
All calculations are Decimal(28). Entry windows apply to next-open fill time,
start-inclusive/end-exclusive; close decisions cannot fill earlier. P01 uses
London-local 08:00–08:14 labeled bars and fills before 10:00. P10 uses the close
labeled anchor-1 versus anchor-31, fills at its anchor, and has no indicator exit.
London comes from the pinned system TZif and tzdata 2026c, not a fixed UTC offset.
The schedule is not a verified historical auction/business-day calendar.

Rolling crossings compare each close with its contemporaneous excluding-current
level; frozen crossings compare both closes with the same frozen level. P03
requires a valid prior rolling-range level as well as the current one. P04 tests
the preceding width against 120 still-earlier valid widths, then the current
band cross. P09 uses population RMS fitted residuals; zero RMS produces no z.
P05 exits when its EMA direction ceases to support the trade (the adverse cross
for a trade entered under that trend). No threshold is chosen from results.

P06/P07 cannot trigger on their arming bar. The last expiry bar is eligible;
cancellation has priority. P06 observes all five consolidation bars and cancels at the fifth if any
invalidated it; rearming can occur only on a later bar. Setups are independent of portfolio
occupancy and are consumed even when execution is skipped. Frozen exits for
P01/P02/P03/P06/P07 are attached to each entry/position, never read from a newer
setup. Gaps cancel setups and the P01 range, reset rolling indicators, and require
full warm-up. P02's validated previous-calendar-day range is daily source context
and survives rolling-indicator resets; it still requires the exact completeness
rule. Prior partition bars may supply indicator/day context, but cannot arm a
setup, seed the opening range, or queue a trade across the split. The first
partition bar can generate a fresh close signal. SMA retains its original v1
semantics, including its original warm-up and execution windows.

Reuse v1 reference-price fills, adverse rounding, commission, swaps, gap handling,
conservative stop/floor uncertainty, sizing, stage resets, and terminal valuation.
No targets, trailing stops, pyramiding, volume, news or synthetic missing candles.
Signal/account and raw gross/net/stages/cash remain separate claims.

## Data, partitions and fixed inventory

Use only the hashed 69,846-row Step 3 frozen export, ending March 31 23:59 UTC.
The runner verifies its exact hash/count/bounds; whole-file source hashes and
structural validation are allowed but source/April prices never enter signals.
TOML binds raw, normalized, manifest, quote, snapshot, v1 config, candidate-spec
and timezone hashes. A committed source manifest binds all numerical source,
scripts, migration, dependency and protocol/configuration files. A run records
that manifest's hash and its introducing Git commit; dirty tracked code is refused.

January 20 03:59–March 1 and March 1–April 1 are both **exploratory**, UTC half-open.
Run 12 entries × 27 scenarios × 2 views × 2 periods = 1,296 cases. Four fixed
March 2/9/16/23 account cohorts at mid/0.58/0.15 add 48: exactly 1,344 cases.
A complete second pass must match every result and index hash. No early economic
pruning. One sequential worker, 7,200 seconds per pass, >=2 GiB free before and
during execution. Resource interruption preserves partial evidence and blocks
completeness; it cannot silently reduce the registered inventory.

## Diagnostic gates and evaluation prohibition

March mandatory economic scenarios are mid/0.48/0.05, mid/0.58/0.05,
mid/0.58/0.15, bid/0.58/0.15, ask/0.58/0.15. Require strictly positive net in both
views and zero account failures, gap-held and unresolved-floor counts in those
scenarios; all four account cohorts must be safe. Reference signal requires
100 trades, 60 active days, positive net in both March halves split at March 16,
and positive 0.005 lower expectancy quantile. Sixty active days cannot fit in
March: report insufficient evidence, never relax the gate.

Circular daily (net,count) blocks include zero-trade observed weekdays. Five-day
blocks, 20,000 replicates, seed 20260911; quantile index floor((N-1)*0.005).
Zero-trade resamples contribute zero. Ten-day blocks are sensitivity only.
Ten new hypotheses determine K; SMA/no-trade are comparison baselines. This is a
descriptive expanded-search diagnostic, not formal multiplicity control or
independent validation. Economic/safety failure means rejection under this model;
otherwise failed precision/stability gates mean inconclusive. No forced winner.
Rank at most two diagnostic gate-passers by descending reference account net,
ascending drawdown, turnover, then ID. Insufficient gates cannot be bypassed to
fill the list. No priority is an advancement finalist.

Advancement manifest is empty unconditionally. Evaluation is always
`not_opened: independent_data_unavailable`, before any evaluation input read.
April (and its original May tail) remains sealed regardless of screen performance.
Longer data and any future evaluation need a separately frozen protocol.

## Verification, recovery and reporting

Before results: synthetic causal-prefix tests for every candidate; exact entry,
exit, gap, split, DST, lookback, expiry, no-retry and frozen-reference behavior;
existing safety/account tests; all 672 old numerical artifacts reproduced exactly.
After results: every registered identity/hash and ledger reconciled; full replay;
SQLite references plus isolated backup/restore. Model account `failed` is an
observed simulation outcome; an execution exception is incomplete evidence and
must never be counted as a successful case. Exceptions preserve private failure
metadata and previous results; fixes require committed invalidation and fresh names.

Private artifacts and numerical source snapshots are create-only, owner-only,
ignored under `.local/`. The catalog owns relationships; the simulator reads
immutable CSV. Do not mutate old catalogs, baselines, reports or snapshots.
Report all ten candidates, unchanged SMA and no-trade, every failed gate, cost
sensitivity, correlations/overlap/identical-entry counts, and SMA four-way
account-minus-signal attribution at fixed reference costs. Attribute sizing and
changed sequence separately. Unsupported live fills/profitability, provider rules,
payouts and cash claims remain unsupported. Commit a sanitized report and empty
advancement freeze, then open an unmerged PR.
