# Candidate demo scenario: XAUUSD / M1

Updated from the owner's message on 2026-09-03.

## Starting market

The owner selected XAUUSD on M1 (one-minute candles). Start the investigation there.
An alternative instrument or timeframe needs evidence before replacing this choice.
This is a market/timeframe preference; entry, exit and position-sizing rules are
still unspecified.

Evidence for changing the choice should compare realistic trading costs, results
on data not used to tune the strategy, stability across tested periods, loss-limit
breaches and progress toward the economic objective. A better-looking single test
or a general opinion about timeframes is insufficient. No alternative has yet been
shown to be better.

## Rules recalled by the owner

The owner remembers seeing the following scenario once on another broker's website,
not FIBO's. The firm and source URL are unknown. Record it as a candidate test
scenario; it is not a verified current offer or an adopted executable rulebook.

| Event | Recalled condition | Recalled consequence |
| --- | --- | --- |
| Success level 1 | 4% TP1 | Bonus: TBD |
| Success level 2 | 4% TP2 | Bonus: TBD |
| Failure condition 1 | Daily drawdown reaches 4% | Prop account is taken away |
| Failure condition 2 | Total drawdown reaches 12% | Prop account is taken away |

For scale only, 4% of USD 3,000 is USD 120, and 12% is USD 360. These calculations
do not establish the actual target or failure balances. The base used for each
percentage, reset behavior and drawdown definitions are not known.

Interpretation to confirm: TP1 and TP2 describe account-level success milestones.
Their names alone do not define an individual trade's take-profit price or stop.
The 4% daily account limit also does not specify how much to risk on one trade.

## Gaps that change the simulation

- Source: firm name, offer URL, date/version and whether the offer is still available.
- Success: are these separate phases or milestones in one account? Does balance
  reset between them? What is the reference balance for each 4% target? Are open
  profits counted or must trades be closed?
- Daily loss: starting balance, start-of-day balance/equity, intraday peak or another
  reference? Do open-position losses, fees and swaps count? Which timezone and time
  reset the day?
- Total loss: a fixed floor based on initial balance, a floor that rises with gains,
  or another calculation? Does equity or closed-trade balance trigger failure?
- Passing and payment: what is the bonus, when is it payable, can it be withdrawn,
  and what fees, splits, other rules and eligibility conditions apply?

The owner reports failure when a limit is *reached*. That wording is preserved;
exact boundary behavior still needs a real rulebook or an explicitly agreed
simulation definition.

If failure is based on floating equity at any moment, checking only minute closes
cannot prove the loss limit was respected between those closes. The data and test
method must match the final rule definition.

The actual FIBO demo is the data/connection test account. No evidence currently
establishes that it enforces the recalled provider's rules. The current Python
implementation does not enforce this candidate scenario.

## Next useful work

1. Verify the broker's XAUUSD symbol details and M1 data availability; plan a small
   read-only sample of candles, bid/ask quotes and relevant trading costs.
2. Identify the recalled offer if the owner can supply a name or link. Otherwise,
   agree on explicit hypothetical formulas before implementing a simulator.
3. Define the first strategy's buy/sell, exit and sizing rules before testing an edge.

No success bonus is counted as received cash. Personal spending/loss authorization,
cash-flow targets and real-account decisions remain separate unresolved inputs.
