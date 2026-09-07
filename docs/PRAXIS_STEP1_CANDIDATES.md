# Praxis Step 1: ten additional candidate specifications

Status: research specification, 2026-09-07. No candidate below has been backtested.
These are proposed numerical definitions for implementation review, not the final
Step 4 preregistration. Parameters are deliberate simple starting choices, not
source-proven optima. Final data, splits, code and selection rules must be frozen
before results. January–March 2026 is exploratory; April remains sealed.

## Common contract

Use XAUUSD M1 completed candles. A candle labeled t is available at t+1 minute;
entries and close-triggered exits execute at the next contiguous minute open.
No execution at a signal candle's earlier price. Long/short definitions below are
symmetric unless a clock anchor is stated. A cross above means previous close
<= the specified level and current close > that level; reverse for cross below.
When the level is frozen for a setup, compare both closes with that frozen level.
When it is rolling, compare each close with its contemporaneous level.

Proposed common stops are 2 Wilder ATR(14), tick-rounded adversely as in v1,
fixed at entry; no profit target or trailing stop. Use v1 commission and all 27
cost/price-side scenarios until better evidence justifies a separately recorded
cost model. Signal view stays one ounce; account view retains the rough $3,000
model. Common entry hours are 06:00–19:00 UTC weekdays, flatten at 20:00 UTC.
The candidate-specific windows below further restrict this common window.

At most one position per candidate, no pyramiding, no same-open exit/reentry.
Emit a single entry event when the setup triggers; do not retry a skipped event.
New signals while occupied are ignored. Setup state still expires/consumes on
its signal event, regardless of account execution, so rules do not depend on
account balance. A missing minute cancels pending entries and active setups;
reset rolling indicators and require their entire lookback again. Use v1 gap
liquidation and uncertainty labeling for existing positions. Prior partition
candles may warm indicators but cannot seed a pending trade/setup across a split.

EMA(n) seeds with an n-close arithmetic mean and uses alpha=2/(n+1).
ATR uses v1 Wilder semantics. SMA and population standard deviation use completed
closes. At least 61 contiguous M1 bars are required, plus each rule's longer
lookbacks. Zero denominators/zero dispersion mean no signal. Rolling extrema
used as breakout levels exclude the current bar. All strategy inputs exclude
volume because its meaning is unresolved. No news, order-book or future data.

## Candidate definitions

| ID | Proposed entry/setup | Additional exit; maximum hold | Source and adaptation |
| --- | --- | --- | --- |
| P01 `london_range_break` | Build high/low from all 15 bars labeled 08:00–08:14 Europe/London. Between 08:15 and 10:00 local, take the first close crossing outside that frozen range, long above/short below. Require complete range; at most one signal per local date. | Close in the inclusive frozen [low,high] range; 120 minutes. | S1 supplies opening-range mechanics. 08:00 is our London activity anchor, not a centralized spot-gold opening or the LBMA fixing. |
| P02 `previous_day_break` | Prior UTC calendar date must be a weekday with >=1,200 observed M1 bars and no within-date gap >90 minutes. Freeze its high/low. First crossing above/below those levels during common hours triggers continuation; one signal per UTC date. Skip Mondays when the immediately previous UTC date is Sunday. | Long close <= prior high; short close >= prior low; 120 minutes. | S2 discusses prior extrema and level breaks. Daily boundary, completeness and trigger choices are ours. |
| P03 `failed_range_break` | At close t, a break above the preceding 60-bar high arms a short reversal; a break below the low arms a long. Freeze both extrema and wait up to five subsequent bars. A close strictly inside the frozen range triggers the reversal; otherwise expire. Ignore new setups while armed; after consumption/expiry, only a subsequent fresh rolling-range cross can arm again. | Long close >= frozen range midpoint; short <= midpoint; 60 minutes. | S2 supplies support/resistance context; the five-bar failure/reentry rule is an original falsifiable adaptation, not a published result. |
| P04 `compression_break` | Compute Bollinger width=(upper-lower)/SMA using 20 closes, 2 population SD. At t-1 its width must be <= every width in the preceding 120 valid bars (excluding t-1). At t, close crosses above the upper band or below the lower band. One event per qualifying crossing. Require 141 contiguous bars. | Close crosses middle SMA against the trade; 120 minutes. | S3 describes bandwidth compression and continuation; the trailing-minimum gate is ours. Mechanism differs from v1 band reentry but shares inputs. |
| P05 `trend_pullback` | Long: EMA60 is above its value ten bars ago, previous close <= previous EMA20, current close > current EMA20, and current EMA20 > EMA60. Short is the exact reverse. Require 71 contiguous bars. | EMA20 crosses EMA60 against direction; 120 minutes. | S2 describes moving-average support/retracement. EMA lengths and conjunction are our rule. |
| P06 `impulse_flag` | At t, absolute five-minute close change >=3*ATR at t-5 arms an impulse in its direction. Freeze impulse high/low from t-4..t. Observe exactly five subsequent consolidation bars; their full range must be <=1.5*ATR(t), and no close may retrace beyond the impulse midpoint. Freeze their high/low. In the next five bars, a close crossing their boundary in the impulse direction triggers. Expire otherwise; ignore new impulses while active. | Close through opposite consolidation boundary; 60 minutes. | S4 supplies impulse/consolidation/continuation mechanics. Thresholds and finite-state definition are ours. |
| P07 `impulse_exhaustion` | Same initial five-minute >=3*ATR(t-5) impulse detector as P06. Freeze midpoint and extremes. Within the next five bars, a close crossing the impulse midpoint against its direction triggers reversal. Cancel first if a close extends beyond the impulse extreme in its original direction; expire after five bars. Only one active setup. | After entry, close beyond original impulse extreme against position; 30 minutes. | S5 supplies reversal/confirmation context only; this impulse failure rule is our hypothesis and deliberately competes with P06. |
| P08 `m15_trend_m1_break` | Construct UTC-aligned M15 bars from exactly 15 M1 bars; use only closed, complete M15 bars. Long when latest M15 EMA20>EMA60 and M1 close newly crosses preceding 10-M1-bar high; short for reverse M15 trend and low break. Require 60 consecutive complete M15 bars; reset M15 indicators on a missing constituent bar. | M15 EMA20/60 direction ceases to support position; 120 minutes. | S6 motivates separating context and entry horizons; M15/M1, indicators and lengths are ours. |
| P09 `regression_reentry` | At each close t, fit OLS with intercept to the preceding 60 closes (x=0..59, excluding t); extrapolate x=60. Let z=(close_t-forecast)/population RMS fitted residual. Long when z crosses from <-2 to [-2,0); short from >2 to (0,2]. Require both current/prior z valid. | Long z>=0, short z<=0; 60 minutes. | S7 establishes regression-line forecasting mechanics, not this residual-reversion strategy. No centered window or future regression refit. |
| P10 `gold_clock_momentum` | At 10:30 and 15:00 Europe/London, calculate the last 30 completed minutes' close change, using closes labeled anchor-31 and anchor-1. Require all 31 bars. Enter in that direction at the anchor open; zero change means no entry. One event per anchor/date. | Time exit only; 30 minutes. | S8 establishes scheduled gold benchmark auctions. Directional persistence around the schedule is our unproven hypothesis. Do not use the eventual auction price, result or duration. |

All finite-state setups freeze their stated reference levels when armed. A setup
cannot trigger on its arming bar. Expiry is inclusive of the stated last bar;
trigger/cancel decisions use that bar's close, with cancellation priority if both
conditions could be true. Consume the setup on a trigger. Unspecified indicators
continue updating while occupied; no old signal is queued for later execution.
Session/end-of-day/gap cancellation takes precedence over an entry.

For P01/P10 convert clocks with IANA Europe/London, retaining timezone database
version; do not use a fixed UTC offset across DST. Skip a local date with missing
required anchor/range data. P10's auction clock is a schedule feature, not proof
that an auction actually occurred that day; this limitation must remain visible
unless an independently acquired historical business-day calendar is frozen.

## Evidence quality and sources

Reviewed 2026-09-07. Sources below support mechanics or institutional schedules.
None establishes net profitability of these exact XAUUSD M1 rules, cost assumptions,
or account constraints. Most are educational explanations, not controlled empirical
studies. Do not describe this batch as ten literature-proven strategies.

- S1: [QuantConnect opening-range example](https://www.quantconnect.com/forum/discussion/799/strategy-opening-range-breakout). Author's demonstrative algorithm; explicitly identifies unfinished profitability work. Its equity opening anchor does not transfer automatically to spot gold.
- S2: [CME support and resistance](https://www.cmegroup.com/education/courses/technical-analysis/support-and-resistance). Educational discussion of prior extrema, moving averages and level changes; no M1 gold validation.
- S3: [John Bollinger's rules](https://www.bollingerbands.com/bollinger-band-rules). First-party bandwidth/continuation guidance and caution about normality and correlated indicators; no tested parameters for this market.
- S4: [CME trend and continuation patterns](https://www.cmegroup.com/education/courses/technical-analysis/trend-and-continuation-patterns). Qualitative flags/consolidation; our numerical pattern is not a replication of a published algorithm.
- S5: [CME reversal patterns](https://www.cmegroup.com/education/courses/technical-analysis/technical-patterns-reversals). Qualitative confirmation concepts; does not establish our impulse detector or reversal threshold.
- S6: [IG matching time frames](https://www.ig.com/au/view-ig/matching-time-frames-to-build-a-trading-system--37480-170329). Practitioner educational rationale for multiple horizons; does not validate M15/M1.
- S7: [Spotware linear regression forecast](https://help.ctrader.com/ctrader-algo/references/Indicators/LinearRegressionForecast/). Indicator reference, not a strategy-performance source. Our trailing OLS formula is specified above independently of platform code.
- S8: [LBMA gold-price FAQ](https://www.lbma.org.uk/prices-and-data/lbma-gold-price/lbma-gold-price). Confirms 10:30 and 15:00 UK-time auction schedule; offers no forecast of surrounding returns.

## Overlap, failure mechanisms and required tests

P01/P02/P04/P08 remain related breakout mechanisms. P03 tests failed breakout
reversal; P05 shares trend exposure with original SMA. P06/P07 share impulse
information but ask opposite conditional questions. P09 resembles v1 band
reversion but detrends before measuring deviation. P10 adds a fixed event clock
to momentum and may still overlap P06/v1 momentum. Count ten specifications,
not ten independent economic effects; report daily P&L correlation, simultaneous
exposure and identical entry counts after the authorized batch.

Likely failures: false breaks and spread consumption (P01–P04/P08); lag and
repeated pullbacks (P05); subjective-pattern discretization or rare events
(P06/P07); changing trend slopes and nonstationary residuals (P09); schedule
coincidence, holidays and execution shocks (P10). P01/P02/P10 have limited daily
opportunities; a low trade count is inconclusive, not permission to loosen gates.

Before implementation acceptance, test next-open causality and prefix invariance
for every candidate; exact lookback exclusion; setup expiry and cancellation;
no retry after sizing rejection; Friday/Monday and DST boundaries; missing M15
constituents; zero-variance OLS; first eligible day and dataset cutoff behavior.

## Proposed Step 4 evaluation design

Freeze the definitive candidate registry, any SMA-derived filter, cost grid and
all data hashes only after Steps 2–3. No new candidate results are inspected now.
A concrete preferred data request is 2020–2025 XAUUSD M1: use 2020–2022 for
implementation/exploration, 2023–2024 for chronological selection, and retain 2025
as one-shot evaluation. This split is conditional on source coverage, integrity
and evidence that those periods have not informed this project's rule choices.
An older unseen period is still only historical evaluation, not prospective proof.
January–March 2026 stays exploratory; do not use another provider over those same
market dates as independent market evidence. April 2026 remains separately sealed.

Proposed gates: positive signal and account net in every v1 required cost/side
scenario; no modeled account failures or unresolved exposure in the selected
periods/cohorts; >=100 signal trades and >=60 active days over selection; positive
signal net in each selection calendar year. Use daily (net,count) block bootstrap
with frozen seed, 20,000 replicates and five-observed-day circular blocks. For K
registered candidates, use lower quantile 0.05/K as a conservative descriptive
screen; dependence and adaptive prior research prevent treating it as a formal
familywise guarantee. Report ten-day blocks as sensitivity, not a rescue gate.
Rank at most two eligible finalists by p95/adverse account net, then drawdown,
then turnover, then ID. Baselines are reported but not promoted as new candidates.
No extra tuning after selection; full code/data/finalist freeze precedes one
holdout run. With no finalists, do not run holdout. For evaluation require the
same economic/safety gates and >=50 trades/>=30 active days; report calendar-half
stability. Exact calendar boundaries/cohorts must be finalized with actual data.

These proposed thresholds are not guarantees. If only the current short archive
is available, label results exploratory and leave advancement unsupported.
