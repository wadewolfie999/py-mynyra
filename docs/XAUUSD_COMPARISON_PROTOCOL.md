# XAUUSD M1 comparison: preregistered Plan A

Status: registered before implementation or strategy results, 2026-09-05 UTC.
Authority: historical research, implementation, tests, private experiments and an
unmerged PR. No orders, scope changes, spending, quote campaigns or shadow runs.

`experiments/xauusd_m1_v1.toml` owns all numerical settings. This document owns
their semantics, sources and decision policy. Freeze both in Git before running
any historical strategy. Record their hashes, implementation hash, input hash,
Python version and run arguments in create-only private artifacts. Corrections
must retain previous runs and identify whether any results had been inspected.

## Research and candidate register

Sources accessed 2026-09-05. None demonstrates profitability of these exact XAUUSD
M1 rules. This is a source-backed hypothesis screen, not a literature replication.

| Candidate | Mechanism and source | Evidence and limits | Failure hypothesis |
| --- | --- | --- | --- |
| `sma_cross` | Smoothed trend transitions; [Brock, Lakonishok and LeBaron, 1992](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1992.tb04681.x) | Publisher abstract: moving averages and range breaks on Dow Jones 1897–1986, bootstrap comparison with null models. Full cost treatment not verified; M1 settings below are our adaptation. | Whipsaws, lag and turnover consume the effect. |
| `channel_break` | Crossing recent extrema; same original study | Different entry/exit information from smoothed-trend crossings, but economically related. No assumption of independent returns. | Breakouts fail, especially after costs. |
| `hour_momentum` | Persistence of own past return; [Moskowitz, Ooi and Pedersen, 2012](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum) | Authors' summary: 58 futures/forwards, over 25 years, long lookbacks and holding periods. It supplies a persistence hypothesis, not support for compressing months into minutes; cost details not established by this summary. | M1 return persistence is absent or smaller than costs. |
| `band_reentry` | Reversion after standardized price displacement; [John Bollinger's rules](https://www.bollingerbands.com/bollinger-band-rules) | Undated first-party method guidance, no controlled M1 gold cost study. Bands describe relative extremes; touches alone do not justify reversal. Our additional re-entry event is an explicit unproven adaptation. | Persistent trends and changing volatility defeat reversion. |
| `rsi_reentry` | Reversal after directional gain/loss imbalance relaxes; [Spotware RSI documentation](https://help.ctrader.com/indicators/built-in/oscillators/relative-strength-index/) | Undated platform method description, attributed to Wilder (1978); describes extreme-zone re-entry and neutral exit. No profitability sample, costs or statistical validation. | Momentum remains extreme, or mean exit is too small after costs. |

The last two rules use different information: price displacement versus the ratio
of directional increments. Three continuation rules remain related; do not call
five strategies five independent bets. Record trade overlap and daily-result
correlations descriptively. One numerical specification each; no parameter search,
sizing variants, layers, ensemble or other market/timeframe in this experiment.
Opening-range breakout is deferred: a spot-gold opening anchor requires a separate
justification. Volume/VWAP rules are excluded because volume semantics are unknown.
News, order-book and learned predictors are excluded for missing causal inputs or
an unjustified search budget. Rejections are research decisions, not tested losses.

## Exact causal rules

Bars are minute-open-labeled UTC; a bar at t becomes available at t+1 minute.
Indicators use only completed raw single-price candles, independent of cost side.
SMA is the arithmetic mean including the current close. Bands use population
standard deviation of the same closes. ATR is Wilder-smoothed true range, seeded
with the arithmetic mean of the first configured number of ranges (first range
is high-low). RSI uses Wilder-smoothed positive and negative close increments,
seeded with their first configured number of increments. RSI is 50 if both means
are zero, 100 if only losses are zero, and 0 if only gains are zero.

Every gap greater than one minute resets indicator history and pending entries.
Require the configured contiguous warm-up even for shorter indicators. Prior
partition bars can warm indicators but cannot create a pending entry or position.

* SMA: long when fast-minus-slow changes from <=0 to >0; short from >=0 to <0.
  Exit long when fast<=slow, short when fast>=slow.
* Channel: long when current close is strictly above the preceding entry-window
  highs, short strictly below its lows (exclude current bar). Exit long below
  preceding exit-window lows, short above its highs. Entry may recur after a
  completed exit, but never while a position exists.
* Hour momentum: on bars whose close time is a UTC hour, long if current close is
  above the close a lookback earlier, short if below; equal means no signal.
  No indicator exit; use the registered holding limit and protective stop.
* Bands: long when previous close was strictly below its own lower band and the
  current close is inside both current bands; short mirrors from above. If the
  current close already reaches/passes the middle band in the intended exit
  direction, skip entry. Exit long at close>=current mean, short at close<=mean.
* RSI: long when previous RSI<lower and current RSI>=lower but <neutral; short
  when previous RSI>upper and current RSI<=upper but >neutral. Exit long at
  RSI>=neutral, short at RSI<=neutral.

Entries execute at next consecutive bar open in the configured entry window.
An exit decision at close executes next open, even across a gap. No same-open
reversal; a new completed bar is required. One position per candidate/run, no
pyramiding. Entry bars may hit their stop. Native holding limits are fixed by
hypothesis (trend: longer; reversal: shorter), not optimized. Stop distance is
signal ATR times the registered multiple, rounded UP to a tick; the raw-reference
stop is next-open reference price minus/plus this distance for long/short. No
profit-target or trailing-stop path exists. Zero ATR cancels entry.

## Execution, uncertainty and accounting

The full Cartesian spread/slippage/price-side grid is a sensitivity experiment,
not a parameter search. Every candidate and no-trade use the same grid. The spread
median/p95 come from the one-hour [FIBO evidence](DATA_READINESS_REPORT.md); the
larger spread and all slippage figures are assumptions. Commission is charged on
each execution's actual modeled notional, not a constant dollar fee.

Convert a raw reference r to midpoint r (mid), r+s/2 (bid) or r-s/2 (ask).
Buys pay midpoint+s/2+slippage, rounded up to a tick; sells receive
midpoint-s/2-slippage, rounded down. Stops trigger on raw-reference OHLC and use
the same executable conversion. This is an explicit reference-bar stop model;
unknown historical quote paths remain an external-validity gap. No spread is
subtracted a second time. Keep raw-reference gross P&L, execution drag,
commissions, swaps and net P&L separately reconciled. All monetary/indicator
arithmetic uses Decimal at the registered precision; outputs retain decimal text.

Process a bar as: UTC day rollover; elapsed swap charges; existing-position open
equity check; gap/stop/queued/time/session exits; eligible pending entry; adverse
intrabar move (stop before favorable movement); close equity; next-close decisions.
An opening gap fills at its open, never at an unavailable stop price. Intrabar
stops fill at the stop plus modeled slippage. Test account limits on liquidation
equity including estimated exit commission. Failure overrides success. If bar
extremes cross a loss floor beyond an earlier modeled stop, record unresolved
intrabar-floor evidence rather than claiming a proven safe path. No favorable
intrabar ordering may improve the result.

Schedule flat at the configured UTC hour, before documented rollover. If missing
bars delay that exit, close at first available open, count a gap-held event and
apply each crossed daily swap boundary (Wednesday triple, otherwise single).
Any position held over a gap has unobserved loss-limit exposure: flag it and make
that account path ineligible for advancement, even if modeled P&L is positive.
No synthetic bars or hindsight exit at the last pre-gap close. Unexpected missing
session data cannot be silently omitted. New flat-position signals wait for warm-up.
At the known partition end, liquidate at the last available close with costs;
record this terminal valuation convention separately. No trade crosses a partition.

Signal economics always trades one ounce without capital constraints or stage
termination. It is a diagnostic portfolio, not a feasible account claim. Account
feasibility runs the same rules with the registered capital, integer-ounce limits
and sizing. Choose the largest whole-oz quantity that fits the risk fraction of
current flat equity using modeled stop loss including both commissions, and the
margin ceiling q*entry_price/leverage. Cap at symbol maximum; skip below minimum.
Count risk/minimum-size and margin skips, overlap and canceled signals. No risk
increase to force stage success; the sizing default is a research assumption.

Apply [DEMO_SCENARIO.md](DEMO_SCENARIO.md): daily floor is a fraction of that day's
opening balance, total floor is fixed within each stage, and stage target requires
flat closed balance with no pending order. First target resets virtual balance and
daily baseline, starts the next stage at the next available bar, and cancels pending
signals; second target ends the attempt. Failure ends the attempt without restart.
Report sum of net trade P&L across stages separately from reset balance. No-trade
has unchanged capital, zero drawdown/trades/targets/failures and undefined expectancy.
No received-cash, withdrawable-profit or real-provider inference is made.

## Splits, trial budget and decision

All intervals in TOML are start-inclusive/end-exclusive. Development ends at
selection_start; selection ends at evaluation_start; evaluation includes the
available May 1 tail. No price charts, indicators or results from evaluation may
be inspected before the finalist manifest is frozen. Structural validation and
whole-file hashing do not constitute strategy evaluation. The loader stops at
the boundary before converting sealed OHLC values. This is an auditable workflow
guard, not a security boundary against a user who can edit the code.

Run all five bases and no-trade in both views and all 27 cost scenarios for each
development and selection interval (648 runs total). No data-driven changes after
either set of results. Code defects may be corrected with a documented invalidation
and a fresh create-only rerun, never by overwriting evidence or tuning policy.
Run four additional registered selection-start cohorts, account view only, at
p95 spread/adverse slippage/mid reference: 24 diagnostic runs. Same capital and
flat reset; these overlapping cohorts are not independent samples. Daily results
and fixed March halves disclose concentration; do not pick a favorable start date.

An eligible finalist must meet ALL of these rules in March:

1. Strictly positive signal AND account net P&L under mid-reference median/base
   slippage, p95/base slippage, and p95/adverse slippage.
2. Under p95/adverse slippage, positive signal AND account P&L for bid and ask
   reference assumptions too; zero modeled failures, gap-held events and unresolved
   intrabar-floor events in all five gate scenarios.
3. The mid-reference p95/adverse signal run meets minimum trade and active-day
   counts. Its lower bootstrap quantile of per-trade expectancy is strictly
   positive. Bootstrap contiguous two-observed-weekday blocks, circularly, with
   daily (net, trade-count) pairs, including zero-trade observed weekdays. Truncate
   to original day count and divide sampled total P&L by sampled trade count;
   a zero-trade resample has expectancy zero. Use the frozen seed and replicate
   count. The 1% tail accounts heuristically for five candidates; it is NOT a
   formal multiplicity-corrected proof under dependence or a claim of stationarity.
4. Both fixed March halves have strictly positive p95/adverse signal net P&L.
   All four account start cohorts have zero failures/uncertain exposures. Cohort
   profitability is descriptive, not an additional selection target.

If positive economic results have insufficient trades/days or a nonpositive
bootstrap lower bound, label evidence inconclusive, not proven useless. Negative
net results reject that exact rule under that model. Record every failed gate.
Rank eligible candidates by account net P&L at mid-reference p95/adverse costs,
then lower modeled equity drawdown, then lower ounce turnover, then candidate ID.
Keep at most the configured number. Stress results are disclosed, not optimized.
Break-even cost is the mean raw gross move per ounce less commission and swap
drag on the actual trade sequence, a conditional budget, not an executable quote.

Freeze a create-only finalist manifest containing result/configuration/code hashes,
all eligibility decisions and the ranked IDs. Commit a sanitized freeze record
before evaluation. Evaluate only frozen finalists plus no-trade using the same
grid and gates applicable to a single interval (no March halves/cohorts). No
reselections. If no finalist exists, record an empty freeze and leave April sealed.
This is a complete negative screening outcome, not a reason to run April anyway.

Layers are deferred to a new experiment and new independent evaluation data.
Actual fills, provider eligibility, shadow observation and cash receipt are outside
this authorization. Even an April survivor is only a historical survivor.

## Verification contract and architecture

Prefer a small pure-Python chronological simulator to a vendor backtesting
framework: event order, costs and failure semantics are the central uncertainty.
Alternative framework adoption adds translation/validation work without removing
that uncertainty. Strategy rules own causal decisions; simulation owns fills,
account lifecycle and metrics; experiment orchestration owns hashes, partitions,
selection and private create-only persistence. Reuse existing dataset validation
and capture persistence instead of duplicating those responsibilities.

Prove hand-calculated long/short trades, commission reconciliation, causal prefix
invariance, indicator seeds, minimum-size/margin skips, gaps, stops on entry bars,
failure-before-target, stage/day reset, unknown intrabar exposure, terminal costs,
no-trade, malformed inputs, hash mismatch, seal enforcement and replay identity.
Use synthetic fixtures for simulator correctness. Run the existing Python 3.11
gate plus new tests, full Faraz validation, dependency check, compilation and diff
checks. Raw candles, ledgers and run artifacts stay owner-only under `.local/`;
the PR contains source, protocol, tests and a sanitized aggregate decision report.
