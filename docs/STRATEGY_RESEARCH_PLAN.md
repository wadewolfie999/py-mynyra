# Finding and testing strategies

Updated 2026-09-03 from the owner's instructions.

The owner has no existing strategy and wants about 5–7 strategies or layers of a
complex strategy tested. Researching candidates, defining their rules and comparing
them is part of this project. Deep internet research is authorized when strategy
selection becomes the active focus.

The intended system trades autonomously. Start with XAUUSD on M1; changing the
instrument or timeframe requires comparative evidence. Use the
[rough account model](DEMO_SCENARIO.md) for initial experiments. FeneFX is not a
funding candidate and its website does not define project requirements.

## First approach

Start with 5–7 simple, distinct strategies. Then test useful additions to stronger
candidates one at a time, measuring what each addition changes. Different parameter
settings of the same rule are variants, not distinct strategies.

A combined strategy is an alternative, but would require tests with each layer
removed to identify its contribution. Defer that complexity until a simpler
starting point has evidence worth improving.

The exact candidates have not been selected. This planning update does not claim
completed strategy research, a profitability comparison or trading results.

## Order of work

1. **Complete.** Verify FIBO's XAUUSD symbol, historical M1 availability, quote
   timestamps, contract units and trading costs. Normalize and validate the Faraz
   history, then summarize a longer FIBO bid/ask capture. The
   [data readiness report](DATA_READINESS_REPORT.md) records the passing scope and
   the constraints that later tests must obey.
2. Research candidate ideas and their limitations. Prefer original studies,
   reproducible methods and first-party data or platform documentation. Record
   source dates, markets, timeframes, costs and test methods. Evidence from another
   market or timeframe supplies a hypothesis, not proof for M1 gold.
3. Select 5–7 candidates with different decision rules that available data can
   support. Write exact rules and the comparison plan before inspecting results.
4. Run a common historical test with realistic costs and the same account model.
   Separate development, selection and final evaluation periods in time.
5. Test a small number of justified layers using development/selection data.
   Compare each addition with its unchanged base strategy.
6. Freeze selected rules and assess them on the reserved final period. Move to
   a FIBO shadow run first. Shadow mode consumes live bid/ask, records signals and
   simulated fills, and sends no orders. Consider bounded demo execution only if
   that forward evidence justifies it.

Data preparation is complete for conservative historical screening. Personal
spending decisions and provider selection do not need to be resolved to research
or simulate candidates.

## Required rules and comparison controls

Each candidate must specify its idea, sources, possible failure reasons, required
data, entry, exit, stop, maximum holding time, trading hours and sizing. Record when
each input becomes available, a small parameter range, and handling of data gaps,
wide spreads, overlapping signals and existing positions. Version configurations.

Use the same periods, starting capital, account limits and a shared simulation
sizing policy. Test sizing changes separately. Charge spread, commission, slippage
and relevant overnight costs; label estimates and test plausible cost increases.
Simulation settings do not authorize spending or changes to view-only access.

Only use information available at the decision time. A completed-candle signal
cannot receive a fill from earlier in that candle. Use finer observations or
conservative bounds for within-minute stops and loss limits. If a stop and target
both lie inside a candle, do not assume the profitable event happened first.

Record every strategy, parameter variant and layer tried, including failures.
Include a no-trade comparison. Reserve the final evaluation period before selection
and keep it unused for tuning. If its results lead to changes, those changes need
new independent evaluation data. Compare multiple periods and starting dates,
disclosing dependence and limited sample size.

## Decision report

Compare net results after costs, trade counts, drawdown, simulated account failures,
stage completions, elapsed time and sensitivity to costs and parameters. State
whether the data support each conclusion. Observed pass rates are not promises.

Stage completions are simulated outcomes, not cash payouts. Keep the canonical aim
visible: a recoverable path toward repeatable usable cash after costs. A high
backtest score alone does not meet that aim.

The result may be useful candidates or none. Do not force a winner. A combined
strategy must show improvement over its components after costs and on independent
evaluation data.

Next deliverables: a source-backed shortlist, exact test rules, and chronological
development/selection/evaluation boundaries fixed before results are inspected.
The owner need not invent or supply a strategy to proceed.
