# Rough demo scenario: autonomous XAUUSD / M1

Updated from the owner's message on 2026-09-03.

The owner's instructions define project requirements. The canonical specification
describes the economic problem; website claims are reference information. FeneFX
is excluded as a funding candidate, and its rules are not adopted for this project.

## Starting market

The owner selected XAUUSD on M1 (one-minute candles). Start the investigation there.
An alternative instrument or timeframe needs evidence before replacing this choice.
The owner has no existing strategy. The project will research and test about 5–7
candidates, with layers tested as measurable additions. See the
[strategy research plan](STRATEGY_RESEARCH_PLAN.md). The intended system makes and
places trades automatically; its entry, exit and sizing rules still need research
and testing. Supplying a strategy is not a prerequisite placed on the owner.

Evidence for changing the choice should compare realistic trading costs, results
on data not used to tune the strategy, stability across tested periods, loss-limit
breaches and progress toward the economic objective. A better-looking single test
or a general opinion about timeframes is insufficient. No alternative has yet been
shown to be better.

## Rough account rules

The owner recalled these figures from another firm's website and asked to use
them roughly. They are an approximate test model, not FIBO's or FeneFX's terms.

| Event | Recalled condition | Recalled consequence |
| --- | --- | --- |
| Success level 1 | 4% TP1 | Bonus: TBD |
| Success level 2 | 4% TP2 | Bonus: TBD |
| Failure condition 1 | Daily drawdown reaches 4% | Prop account is taken away |
| Failure condition 2 | Total drawdown reaches 12% | Prop account is taken away |

TP1 and TP2 are treated as account-level targets. They do not specify an individual
trade's take-profit price, stop, position size or acceptable risk.

## Provisional simulation defaults

These calculation choices were proposed in this conversation to make the rough
model testable. They are adjustable assumptions, not additional owner requirements,
provider terms or implemented controls.

| Item | Working definition |
| --- | --- |
| Starting amount | USD 3,000 of virtual capital |
| Stages | Two separate stages, each starting at USD 3,000 in the simulation |
| Pass a stage | Closed-trade balance reaches at least USD 3,120, with no open positions or pending orders and no prior failure |
| Daily loss | Fail when equity reaches or falls below 96% of the day's opening balance; first-day floor USD 2,880 |
| Total loss | Fail when equity reaches or falls below USD 2,640; fixed within each stage |
| Day boundary | 00:00 UTC for repeatable tests |
| Open trades and costs | Equity includes open profit/loss; commissions, swaps and modeled execution costs count |
| Failure | End the simulated attempt; a simultaneous profit target does not override failure |
| Rewards | Record stage completion; assign no cash bonus or payout value |

A simulated stage reset does not change the broker demo account. The first day's
loss allowance is USD 120; later daily allowances depend on the opening balance.
The total loss allowance is USD 360 per stage. A future provider's precise account,
automation and payout terms must be checked when considering that provider.

Checking only minute closes cannot prove that equity stayed within these limits
between closes. M1 is the strategy timeframe; finer observations or conservative
bounds are needed for loss-limit evidence. Report gaps in that evidence explicitly.

The actual FIBO demo is the data/connection test account. No evidence establishes
that it enforces this rough model. The current Python code supports read-only
connection/account probes, historical-data normalization and quote recording; it
does not enforce this model or place orders.

## Next useful work

1. Use the completed [data readiness report](DATA_READINESS_REPORT.md) as the
   evidence and limits for historical testing.
2. Research 5–7 candidate strategies and define reproducible buy/sell, exit and
   sizing rules under the strategy research plan.
3. Compare them after costs under this rough account model; test layers separately.

No success bonus is counted as received cash. Personal spending/loss authorization,
cash-flow targets and real-account decisions remain separate unresolved inputs.
