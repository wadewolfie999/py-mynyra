# XAUUSD M1 historical comparison — 2026-09-06

## Decision

**No historical survivor. Keep April sealed.** All five registered candidates failed the March selection rules; no layers, replacement candidates or parameter tuning were tried. The empty finalist set was committed in `10095a4` before recording the evaluation skip. This rejects these exact rules under this model, not every possible XAUUSD strategy.

The screen completed **672 registered cases**: five candidates plus no-trade, 27 cost/price-side scenarios, two measurement views, development and selection, plus 24 fixed-start account diagnostics. The independent accounting audit passed for every case. The full replay and final gate are recorded in [VERIFICATION.md](VERIFICATION.md).

## What was fixed before results

- Protocol and numerical settings: preregistration commit `d3c664a`; simulator committed as `8445601` before historical execution.
- Development: 2026-01-20 03:59 UTC through February; selection: March. Evaluation was reserved from 2026-04-01 through the May 1 tail. Intervals use the exact boundaries in the [TOML](../experiments/xauusd_m1_v1.toml).
- Only the 69,846-row prefix ending 2026-03-31 23:59 UTC entered strategy calculations. Whole-corpus structural validation passed for 81 series and 3,552,511 rows.
- One specification per candidate; zero tuned variants and zero layers. Three continuation mechanisms and two distinct reversal mechanisms; sources and their limitations are in the [protocol](XAUUSD_COMPARISON_PROTOCOL.md).
- One-ounce signal economics is unconstrained. Account feasibility independently runs the same decisions with $3,000 virtual capital, 0.25% modeled per-trade risk, whole-ounce rounding, a 1:25 margin model, and the rough two-stage account limits.

## March comparison

Reference scenario: midpoint assumption, $0.58 spread per ounce, $0.15 adverse slippage per execution, plus 0.003% commission per execution. Dollar amounts below are simulated net results after these costs.

| Candidate | One-ounce trades | One-ounce net USD | Account trades | Account net USD | Account modeled drawdown USD | Size/risk skips |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sma_cross | 245 | -61.48 | 97 | 50.81 | 192.39 | 201 |
| channel_break | 468 | -449.49 | 168 | -113.92 | 198.62 | 1092 |
| hour_momentum | 228 | -328.00 | 94 | -67.25 | 151.23 | 167 |
| band_reentry | 899 | -1,157.55 | 245 | -325.35 | 358.71 | 784 |
| rsi_reentry | 370 | -544.60 | 96 | -124.19 | 146.84 | 326 |
| no_trade | 0 | 0.00 | 0 | 0.00 | 0.00 | 0 |

All five signal runs had 22 active days and exceeded the registered 50-trade minimum. Nevertheless, every 1% lower block-bootstrap expectancy estimate was negative. Each candidate also had a losing March half. The bootstrap is a descriptive, dependence-sensitive screen, not a formal proof of significance.

| Candidate | Lower expectancy estimate, USD/trade | Main rejection |
| --- | ---: | --- |
| sma_cross | -2.41 | Signal loses at p95 costs despite positive account result |
| channel_break | -2.52 | Both signal and account lose under every gate scenario |
| hour_momentum | -2.97 | Both signal and account lose under every gate scenario |
| band_reentry | -1.85 | Both signal and account lose under every gate scenario |
| rsi_reentry | -2.49 | Both signal and account lose under every gate scenario |

SMA illustrates why the two measurements matter: its account run earned $50.81 while its one-ounce signal lost $61.48. Minimum-size/risk constraints skipped 201 flat signals and changed the executed sequence. That is not evidence that the unchanged base signal passed its predeclared gate. Any future claim about a volatility filter induced by sizing needs a separate registered experiment.

At the reference scenario there were no March account failures, gap-held exposures or unresolved intrabar-floor events, and no stage completions. None of those absences establishes profitability. No-trade preserved $3,000 with zero trades, costs, drawdown, failures or stage completions.

## Cost sensitivity and attribution

One-ounce March net USD under the midpoint assumption; commission is included throughout. Slippage is per side.

| Candidate | Median spread / $0.05 slip | p95 / $0.05 slip | p95 / $0.15 slip | $0.80 spread / $0.15 slip |
| --- | ---: | ---: | ---: | ---: |
| sma_cross | 12.02 | -12.48 | -61.48 | -115.38 |
| channel_break | -309.09 | -355.89 | -449.49 | -552.45 |
| hour_momentum | -259.60 | -282.40 | -328.00 | -378.16 |
| band_reentry | -887.85 | -977.75 | -1,157.55 | -1,355.33 |
| rsi_reentry | -433.60 | -470.60 | -544.60 | -626.00 |
| no_trade | 0.00 | 0.00 | 0.00 | 0.00 |

SMA’s $12.02 median-cost signal result becomes negative with the measured p95 spread even at the same $0.05 slippage. The other four signal rules lose in all 27 scenarios, including zero assumed slippage. Bid/mid/ask reference assumptions do not rescue their selection decisions. These are scenario bounds, not reconstructed historical quotes.

| Candidate | Raw-reference gross USD | Execution drag USD | Commission USD | Net USD | Conditional cost budget USD/oz/trade |
| --- | ---: | ---: | ---: | ---: | ---: |
| sma_cross | 226.00 | 215.60 | 71.88 | -61.48 | 0.63 |
| channel_break | 99.12 | 411.84 | 136.77 | -449.49 | -0.08 |
| hour_momentum | -60.69 | 200.64 | 66.67 | -328.00 | -0.56 |
| band_reentry | -103.00 | 791.12 | 263.43 | -1,157.55 | -0.41 |
| rsi_reentry | -110.48 | 325.60 | 108.52 | -544.60 | -0.59 |
| no_trade | 0.00 | 0.00 | 0.00 | 0.00 | — |

Swap charges were zero in these March reference runs. The conditional cost budget uses the actual fixed trade sequence after commission, before execution drag; a negative value cannot support positive spread/slippage. Account results need not decline monotonically with cost because rounding, skipped trades and stage resets change the sequence. No scenario was chosen after seeing results.

## Development and starting-date diagnostics

Reference-scenario net USD; development is diagnostic, not held-out evidence.

| Candidate | Development signal | Development account | March signal | March account |
| --- | ---: | ---: | ---: | ---: |
| sma_cross | 34.75 | -83.52 | -61.48 | 50.81 |
| channel_break | -1,309.16 | -361.12 | -449.49 | -113.92 |
| hour_momentum | -460.39 | -360.92 | -328.00 | -67.25 |
| band_reentry | -644.98 | -361.04 | -1,157.55 | -325.35 |
| rsi_reentry | 44.14 | -279.20 | -544.60 | -124.19 |
| no_trade | 0.00 | 0.00 | 0.00 | 0.00 |

Development signal profits for SMA and RSI did not persist into March at the reference costs. Channel, momentum and band account attempts failed during development in this scenario. Several development signal portfolios held over a missing-minute gap; those paths were marked uncertain, not treated as observed executable trajectories.

The following overlapping account cohorts use the same reference costs and $3,000 flat starts. They are not independent samples, and the best start was not selected.

| Candidate | Start March 2 | Start March 9 | Start March 16 | Start March 23 |
| --- | ---: | ---: | ---: | ---: |
| sma_cross | 50.81 | 24.27 | 173.28 | 131.73 |
| channel_break | -113.92 | -76.24 | -1.75 | 4.25 |
| hour_momentum | -67.25 | -95.59 | -27.68 | -23.02 |
| band_reentry | -325.35 | -277.12 | -133.76 | -32.75 |
| rsi_reentry | -124.19 | -101.49 | -25.93 | -6.00 |
| no_trade | 0.00 | 0.00 | 0.00 | 0.00 |

All cohort safety checks passed. SMA completed one simulated stage in the March 16 and March 23 cohorts; some lower-cost full-March SMA scenarios also completed one stage. Those events are virtual balance resets, not payouts, and do not override the failed selection gates.

## Dependence and model limits

At reference costs, SMA/channel daily P&L correlation was about 0.47 and SMA/momentum about 0.36. The two reversal rules correlated about -0.29 in this short March sample. Of 245 SMA trades, 192 overlapped a channel trade. Candidate counts are not counts of independent evidence; negative correlations alone do not justify combining losing components.

The corpus is only about three months of FXCM-labeled reference-price candles; its historical quote side and volume semantics are unknown. The FIBO spread evidence covers one hour in September, later than the January–May candle period. Commission, slippage, tick rounding, reference-stop triggers and margin are modeling assumptions or account observations applied counterfactually to that history. They are not period-matched fills.

Intrabar excursions/drawdown use the registered adverse-first path. Loss-floor crossings beyond a modeled stop and gaps with open positions are explicitly uncertain. There was no parameter-neighborhood search, broader-regime validation, live quote campaign, shadow run or actual fill measurement. The result supports rejection of these candidates for advancement under Plan A; it does not establish live profitability, provider eligibility, a payout path or received cash.

## Reproduction and remaining work

Use [COMPARISON_WORKFLOW.md](COMPARISON_WORKFLOW.md) and the private normalized dataset. Raw candles, daily series and ledgers remain ignored and owner-only under `.local/`; only aggregate decisions and hashes are versioned. Public reviewers can reproduce synthetic tests without private data. Reproducing these market results requires the matching private dataset.

Private artifacts:

- `.local/experiments/screen_v1/`: registration, all case results and index.
- `.local/experiments/finalists_v1.json`: complete frozen selection decisions.
- `.local/experiments/aggregates_v1.json`: sanitized aggregate export.
- `.local/experiments/audit_v1.json`: independent accounting audit.
- `.local/experiments/evaluation_skipped_v1.json`: explicit no-finalist skip.
- `.local/experiments/screen_v1_replay/`: independent replay (verification evidence in VERIFICATION.md).

Screen index SHA-256: `5454250a38b492b511ba478ed23c84ccb1bdde3b3a2d9e3bc1e5ce460c3f0ff0`. Finalist manifest SHA-256: `f13616e61ec6360be7bca2adcb8d0e9629701b5bc63f3c926eb3a92854fc3ffb`. Full protocol/input/implementation hashes are preserved in the [committed freeze](XAUUSD_FINALIST_FREEZE.md).

This authorized experiment ends with the report and an unmerged PR. Layers or revised rules would constitute a new experiment with a new independent evaluation decision. No orders, trading-scope changes, spending, live capture or shadow campaign were performed.
