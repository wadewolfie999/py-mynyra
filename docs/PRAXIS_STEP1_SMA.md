# Praxis Step 1: SMA sizing diagnostic

2026-09-07. Exploratory analysis of already observed January–March 2026 data.
**The sizing effect is real mechanically, but its economic benefit is unstable.**
Do not promote a filtered SMA on this evidence. Keep unchanged SMA as a baseline;
a single separately registered feasibility-filter hypothesis could be tested later,
without selecting a favorable ATR threshold or hour from this report.

## What the script proved

[diagnose-sma.py](../scripts/diagnose-sma.py) reuses the unchanged v1 simulator and
rules, instruments its position-size function, and asserts full signal/account
replay equality against the frozen development and March artifacts. It validates
all 672 indexed files, registration coverage and implementation provenance first.
Full data validation passes, but strategy calculations load only the 69,846 bars
through 2026-03-31 23:59 UTC. April remains sealed.

The observer records only actual account entry attempts, including their balance,
ATR, rounded stop distance, one-ounce modeled stop loss, quantity and skip reason.
A temporary wrapper observes existing state; no production source or frozen rule
was changed. Its coupling to simulator local variable names is intentional for
this bounded diagnostic and guarded by full replay equality and synthetic tests.

For each attempt, replay an isolated one-ounce trade with its original signal,
stop, exit decisions and maximum holding time. Disable all later entry events.
These hypothetical trades can overlap each other: their summed P&L is a diagnostic
of attempted entries, NOT a feasible portfolio return or independent observations.
All actual March entries reconcile to these isolated trades after division by size.

Reference costs: mid assumption, $0.58 spread, $0.15 slippage per execution and
0.003% commission per execution. This diagnostic uses one reference scenario,
not a new cost-grid strategy comparison. Full v1 sensitivity remains in its report.

## Exact account-minus-signal attribution

Match trades by entry timestamp and direction. Removing signal-only entries,
adding account-only entries at one ounce, changing exits on matched entries, and
adding the extra ounces must reconcile exactly to the account/signal difference.

| Component, USD | Development | March |
| --- | ---: | ---: |
| Original one-ounce signal net | 34.75 | -61.48 |
| Remove signal-only trades | -84.27 | +86.09 |
| Add account-only trades at one ounce | -30.33 | +26.20 |
| Different exits for shared entries | 0.00 | 0.00 |
| Additional ounces | -3.68 | 0.00 |
| Actual account net | -83.52 | +50.81 |
| Shared entries | 174 | 80 |
| Signal-only entries | 165 | 165 |
| Account-only entries | 5 | 17 |

March therefore improves by $112.2919549 through changed entry sequence alone.
All 97 account trades are one ounce. Skipping a trade leaves the account flat,
allowing later signals that the occupied signal portfolio cannot take. The 201
account skips are not the same set as the 165 missing signal trades. It would be
incorrect to subtract all skipped counterfactual losses from signal net.

In development the same mechanism removes profitable entries and adds losing
ones. Of 179 executed trades, 178 are one ounce and one is two ounces; the extra
ounce contributes -$3.68. There is no stable benefit across the two periods.

## Which attempts were sized out?

Every skip in this diagnostic is `risk_minimum_skip`; none is a margin rejection.
At a $3,000 balance the per-trade budget is $7.50. A one-ounce trade's modeled loss
includes rounded stop distance plus both execution sides and commission. It must
fit the current balance's 0.25% budget, so the effective volatility cutoff changes
with balance and price. It is not a constant ATR threshold.

| Period / account decision | Attempts | Mean ATR | Mean stop distance | Isolated one-ounce net USD | Mean net per attempt |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development executed | 179 | 2.202 | 4.409 | -79.84 | -0.446 |
| Development skipped | 215 | 6.153 | 12.311 | +30.61 | +0.142 |
| March executed | 97 | 2.454 | 4.914 | +50.81 | +0.524 |
| March skipped | 201 | 5.221 | 10.447 | -301.20 | -1.499 |

This is a balance-dependent preference for smaller stops/lower recent volatility.
The sign of the excluded attempts reverses across periods. Costs consume a larger
fraction of a small stop, so filtering volatility downward does not automatically
improve the underlying economic opportunity.

## Stability checks without threshold selection

Buckets were specified in the diagnostic script before inspecting its output:
rounded stop distances <=4, (4,6], (6,8], >8 USD/ounce; UTC entry hours; calendar
halves by entry date. These are exploratory descriptions, not candidate selection.

| Actual entry cohort, one-ounce net USD | First half of March | Second half of March |
| --- | ---: | ---: |
| Executed attempts | -72.49 (55) | +123.30 (42) |
| Skipped attempts, isolated | -123.26 (85) | -177.94 (116) |

The account's March profit relies on the second half. Among executed attempts,
stop distances <=4 earned +$52.61 from 15 March entries but lost $27.27 from 72
development entries. The (4,6] group lost in both periods. Do not turn the small
profitable March bucket into a chosen threshold. Hourly breakdowns also contain
small groups and shifting signs; they are retained privately without selecting
an hour filter. Calendar grouping here uses entry dates; the original portfolio
bootstrap attributes trades to exit dates, so these are different diagnostics.

## Reproduce and review

```sh
PYTHONPATH=src .venv/bin/python scripts/diagnose-sma.py \
  --output .local/experiments/praxis_step1_sma_v1.json
PYTHONPATH=src .venv/bin/python -m twisted.trial tests.test_sma_diagnostic
```

Choose a fresh output filename on rerun. Existing output is rejected before data
loading. The output is owner-only and ignored; no prices/timestamps/ledgers are
published. The private file contains every event, modeled subsequent trade and
complete stop/hour/calendar aggregates. March counterfactuals stop before April.

Evidence file: `.local/experiments/praxis_step1_sma_v1.json`.
SHA-256: `a32d3485d17ee11a4e8cc9de244ca2c4798c432e22202beafe35b3e93cd5d083`.
Screen-index SHA-256 remains
`5454250a38b492b511ba478ed23c84ccb1bdde3b3a2d9e3bc1e5ce460c3f0ff0`.
Source/config hashes and diagnostic script hash are embedded in the output.

Synthetic tests cover the four-way attribution identity, duplicate trade keys,
observer equality/counts, isolated entry suppression and wrapper restoration on
failure. The diagnostic does not establish causal economic benefit, new out-of-
sample performance or provider fills. One optional future hypothesis is to apply
one-ounce affordability at a fixed reference balance to SMA entry decisions in
both views, separating it from account equity drift; it must be registered and
compared unchanged on independent data before being advanced.
