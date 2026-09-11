# Praxis Step 4 — expanded exploratory comparison

**No advancement finalist. April remains sealed.** This completed screen compares
ten additional fixed XAUUSD M1 hypotheses, unchanged SMA, and no-trade. January–March
2026 was already observed. Results are exploratory rejection/diagnostic evidence,
not independent validation, executable profitability, or a cash-receipt claim.

The exact protocol is [PRAXIS_STEP4_PROTOCOL.md](PRAXIS_STEP4_PROTOCOL.md); the
numerical registry is `experiments/praxis_step4_v1.toml`. Candidate mechanics and
source limitations remain in [PRAXIS_STEP1_CANDIDATES.md](PRAXIS_STEP1_CANDIDATES.md).

## Temporal freeze and completed proof

- Tested numerical source, protocol, registry and inventory were committed and published as `1bdcfbaddc8be5b0f8e6c7945218885ae4cb9268` before the complete retained batch. Initial freeze `aae610b` preceded the interrupted first attempt; see the correction record below.
- Python 3.11.14; **111 tests passed**, dependencies, compilation, full 81-series/3,552,511-row Faraz validation and whitespace checks passed before the freeze.
- All **672 original numerical artifacts** replayed byte-for-byte before expanded execution. All **224 unchanged SMA/no-trade cases** within Step 4 also match their original numerical bodies.
- All **1344 registered cases** completed and their full second replay matched the complete index and every result hash. Independent accounting reconciled **176,567 scenario trade records**, not independent observations.
- The frozen recovery command verified **2,060 references** in each catalog tree. A subsequent [complete registry-input recovery check](PRAXIS_STEP4_RECOVERY.md) verified **2,066 references and all nine registered inputs** in fresh original/backup/restore trees. Immutable files remain simulator inputs.
- The simulator consumed only 69,846 frozen rows through March 31 23:59 UTC. No April/May evaluation, new acquisition, broker operation, order, shadow campaign or spending occurred.
- No parameter search, SMA filter or economic rule correction was performed. The first attempt was interrupted for an experiment-identity envelope defect before performance inspection; 523 partial case artifacts remain preserved. The corrected source was recommitted before the complete fresh batch and replay; see [correction record](PRAXIS_STEP4_CORRECTIONS.md).

## Reference comparison

Reference costs: mid-price assumption, 0.58 spread, 0.15 slippage per execution,
and 0.003% commission per execution. Dollar values are simulated net P&L.
Both partitions are exploratory, despite retaining v1 development/selection labels.

| Candidate | Jan–Feb signal | Jan–Feb account | March signal | March account | March signal trades | Active days | Account failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P01 london_range_break | -92.67 | -40.26 | -114.10 | -31.12 | 22 | 22 | 0 |
| P02 previous_day_break | -37.94 | 11.35 | -80.10 | 0.00 | 10 | 10 | 0 |
| P03 failed_range_break | 72.05 | -286.63 | -597.43 | -207.17 | 331 | 22 | 0 |
| P04 compression_break | -239.86 | -168.84 | 38.03 | -22.77 | 54 | 21 | 0 |
| P05 trend_pullback | -954.59 | -360.99 | -98.86 | -28.11 | 290 | 22 | 0 |
| P06 impulse_flag | -76.15 | -13.36 | 58.16 | 2.20 | 18 | 11 | 0 |
| P07 impulse_exhaustion | 9.44 | -30.15 | -237.81 | -61.17 | 110 | 21 | 0 |
| P08 m15_trend_m1_break | 32.14 | -75.73 | 83.91 | -17.46 | 123 | 22 | 0 |
| P09 regression_reentry | -633.18 | -361.06 | -793.93 | -222.46 | 746 | 22 | 0 |
| P10 gold_clock_momentum | 162.34 | -27.31 | -222.15 | -35.14 | 44 | 22 | 0 |
| sma_cross | 34.75 | -83.52 | -61.48 | 50.81 | 245 | 22 | 0 |
| no_trade | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |

All ten candidates failed at least one economic gate, independently of the
60-day evidence requirement. P04 and P08 had positive reference signal net but
negative account net. P06 earned +$58.16 signal / +$2.20 account at the reference
costs, but its account lost under the required median/base and p95/base scenarios.
Account net is not monotonic in cost because sizing and skipped events change the
trade sequence. Every registered five-day bootstrap lower bound was negative.

## Every diagnostic decision

A rejected rule fails economics or modeled safety. Inconclusive means the evidence
fails precision/stability gates without that rejection. The registered 60-active-day
requirement cannot fit in March; it was not weakened. Bootstrap tails are descriptive
under dependence and previous adaptive research, not formal familywise guarantees.

| Candidate | Classification | Five-day lower USD/trade | Ten-day sensitivity | Failed gates |
| --- | --- | ---: | ---: | --- |
| P01 | rejected | -7.09 | -6.74 | nonpositive:mid/0.48/0.05:signal; nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:signal; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:signal; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:signal; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:signal; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower; nonpositive_march_half |
| P02 | rejected | -11.89 | -10.67 | nonpositive:mid/0.48/0.05:signal; nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:signal; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:signal; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:signal; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:signal; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower; nonpositive_march_half |
| P03 | rejected | -2.72 | -2.65 | nonpositive:mid/0.48/0.05:signal; nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:signal; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:signal; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:signal; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:signal; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower; nonpositive_march_half |
| P04 | rejected | -2.03 | -1.32 | nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower |
| P05 | rejected | -3.33 | -2.71 | nonpositive:mid/0.48/0.05:signal; nonpositive:mid/0.58/0.05:signal; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:signal; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:signal; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:signal; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower; nonpositive_march_half |
| P06 | rejected | -3.94 | -2.30 | nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:account; insufficient_trades_or_days; nonpositive_bootstrap_lower |
| P07 | rejected | -5.73 | -5.55 | nonpositive:mid/0.48/0.05:signal; nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:signal; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:signal; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:signal; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:signal; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower; nonpositive_march_half |
| P08 | rejected | -2.46 | -2.40 | nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower; nonpositive_march_half |
| P09 | rejected | -1.64 | -1.36 | nonpositive:mid/0.48/0.05:signal; nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:signal; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:signal; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:signal; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:signal; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower; nonpositive_march_half |
| P10 | rejected | -9.49 | -8.49 | nonpositive:mid/0.48/0.05:signal; nonpositive:mid/0.48/0.05:account; nonpositive:mid/0.58/0.05:signal; nonpositive:mid/0.58/0.05:account; nonpositive:mid/0.58/0.15:signal; nonpositive:mid/0.58/0.15:account; nonpositive:bid/0.58/0.15:signal; nonpositive:bid/0.58/0.15:account; nonpositive:ask/0.58/0.15:signal; nonpositive:ask/0.58/0.15:account; insufficient_trades_or_days; nonpositive_bootstrap_lower; nonpositive_march_half |

Research priorities: **none passed the registered gates**. Advancement manifest: **empty**. Evaluation: `not_opened`, reason `independent_data_unavailable`.

## Costs, account uncertainty, and dependence

March one-ounce signal net across fixed midpoint scenarios; all bid/mid/ask
scenarios and both views are retained privately, including every modeled failure.

| Candidate | Median/base | p95/base | p95/adverse | Worse/adverse | Min across 27 | Max across 27 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P01 | -107.50 | -109.70 | -114.10 | -118.94 | -118.94 | -105.30 |
| P02 | -77.10 | -78.10 | -80.10 | -82.30 | -82.30 | -76.10 |
| P03 | -498.13 | -531.23 | -597.43 | -670.25 | -670.26 | -465.03 |
| P04 | 54.23 | 48.83 | 38.03 | 26.15 | 26.15 | 59.63 |
| P05 | -11.86 | -40.86 | -98.86 | -162.66 | -162.66 | 17.15 |
| P06 | 63.56 | 61.76 | 58.16 | 54.20 | 54.20 | 65.36 |
| P07 | -204.81 | -215.81 | -237.81 | -262.01 | -262.01 | -193.81 |
| P08 | 120.81 | 108.51 | 83.91 | 56.85 | 56.85 | 133.11 |
| P09 | -570.13 | -644.73 | -793.93 | -958.05 | -958.07 | -495.52 |
| P10 | -208.95 | -213.35 | -222.15 | -231.83 | -231.84 | -204.55 |
| sma_cross | 12.02 | -12.48 | -61.48 | -115.38 | -115.39 | 36.52 |
| no_trade | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Counts below span all registered account cases (cost repetitions and overlapping
cohorts are dependent). Safety events were not hidden by a profitable reference case.

| Candidate | Failed account cases | Gap-held cases | Unresolved-floor cases | Cases with stage completion |
| --- | ---: | ---: | ---: | ---: |
| P01 | 0 | 0 | 0 | 0 |
| P02 | 0 | 0 | 0 | 0 |
| P03 | 0 | 0 | 0 | 0 |
| P04 | 0 | 0 | 0 | 0 |
| P05 | 27 | 0 | 18 | 1 |
| P06 | 0 | 0 | 0 | 0 |
| P07 | 0 | 0 | 0 | 0 |
| P08 | 0 | 27 | 0 | 0 |
| P09 | 27 | 0 | 21 | 0 |
| P10 | 0 | 0 | 0 | 0 |
| sma_cross | 0 | 0 | 0 | 23 |
| no_trade | 0 | 0 | 0 | 0 |

March reference daily-P&L correlations range from -0.66 (P05/P07) to 0.53 (P06/P08). All 55 candidate/SMA pairs have recorded correlations (undefined for zero variance), directional trade overlap and identical-entry counts. These are mechanism-overlap diagnostics, not independent bets or permission to combine rules.

## Separate SMA investigation

The unchanged SMA baseline preserves the Step 1 comparison. Its four-way
account-minus-signal attribution separates changed trade sequence from extra sizing.
No ATR/hour filter was added.

| Period | Account minus signal | Remove signal-only | Add account-only at 1 oz | Shared-exit change | Extra ounces |
| --- | ---: | ---: | ---: | ---: | ---: |
| development | -118.27 | -84.27 | -30.33 | 0.00 | -3.68 |
| selection | 112.29 | 86.09 | 26.20 | 0.00 | 0.00 |

## Limits and reproducibility

Unknown historical price side and volume, FXCM/FIBO feed differences, one hour of
September cost observations applied counterfactually to earlier dates, modeled
slippage and reference-price stops, unresolved intraminute paths, short history,
rare candidate events, and repeated use of January–March constrain every claim.
Simulated stage resets are not payouts. Negative results reject exact rules under
this model, not every possible strategy. Favorable cells do not establish a survivor.

Evidence SHA-256:

- source manifest: `f9f2def39c818ba1f2f5f0d5c70d8289e6ac215e0f89a643bf8ec6d9f2b148e7`.
- screen index: `9f011a48e362dd22f95b9117a4935d328c5567a7c4cda3f81f2bb3949c2d57ef`.
- replay index: `9f011a48e362dd22f95b9117a4935d328c5567a7c4cda3f81f2bb3949c2d57ef`.
- audit: `ea719433f4557d92b48a49a8fd27e2b8f1f456c71b1b47a50816f1f92056e698`.
- empty advancement manifest: `14ab6385566102c878d4846b22037dfe2b581e0e16cbb905aebd865d6b2195a0`.
- aggregate report: `2da6213f929bb71cf13f6f42848adc5215ea585b0890dc303c8c78fa5fb9cab2`.
- recovery proof: `234d39b896f887e9c5410853a8ad2d44f937cf97175f29d877508e61f239da92`.

The [committed empty advancement record](PRAXIS_STEP4_FREEZE.md) owns the no-evaluation decision. Final checks verified **12,900 private files** with zero permission/symlink issues and unchanged original Step 3 proof/snapshot hashes.

## Reproduction

Use Python 3.11.14 and the matching private inputs named in the registry. The
committed `experiments/praxis_step4_source.json` binds numerical source and the
exact 1,344-case inventory. Source/protocol/configuration changes invalidate it.
Do not regenerate that manifest to legitimize already observed results.

From a clean checkout of the frozen implementation, choose new private names:

```sh
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py baseline \
  --output .local/praxis_step4_baseline_repeat
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py run \
  --baseline .local/praxis_step4_baseline_repeat \
  --output .local/praxis_step4_screen_repeat
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py run \
  --baseline .local/praxis_step4_baseline_repeat \
  --output .local/praxis_step4_replay_repeat
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py verify \
  --screen .local/praxis_step4_screen_repeat \
  --replay .local/praxis_step4_replay_repeat \
  --output .local/praxis_step4_verified_repeat
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py evaluate \
  --output .local/praxis_step4_evaluation_skipped_repeat.json
```

The baseline command must reconcile all 672 original numerical artifacts before
expanded execution. The run command checks that evidence against the same freeze.
Each pass is limited to two hours and requires at least 2 GiB free; a timeout or
exception retains incomplete evidence. An index is published only after all cases
complete. A modeled account loss is an outcome, not a runner exception.

Verify performs independent ledger accounting, exact replay comparison, fixed
bootstrap diagnostics, SMA attribution, and SQLite backup/isolated restore. Its
aggregate report contains no candle prices, trade timestamps or ledgers. Full
private recovery includes numerical-source artifacts. SQLite remains a catalog;
only the frozen CSV enters simulation. Original catalogs and evidence are retained.
Follow the [complete input-closure recipe](PRAXIS_STEP4_RECOVERY.md) to archive
all registry support inputs as well as the cataloged run artifacts.

Evaluation has no price-loading path: it writes only the explicit skip. Commit
the empty advancement record and report without opening April. A future data or
strategy change requires a new registered experiment, not an edited old result.

Synthetic checks require no private market inputs:

```sh
PYTHONPATH=src .venv/bin/python -m twisted.trial tests/test_*.py
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q src tests scripts
git diff --check
```

Use fresh names after interruption. Retain the failed directory, commit and
explain any code defect before rerunning. Returning to the prior unmerged branch
restores the original file workflow; no broker or system service was modified.
