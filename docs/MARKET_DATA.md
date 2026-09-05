# XAUUSD M1 data, costs and limits — updated 2026-09-04

This report uses the selected FIBO cTrader demo account itself as the primary
source. FIBO's public cTrader specification is only a cross-check. Third-party
prop-firm pages do not define any value below.

## What was collected

The read-only collector authenticated with account-information scope and requested
XAUUSD directly from cTrader's demo API. It collected:

- 1,000 unique, ordered M1 bars from `2026-09-03 00:21 UTC` through
  `2026-09-03 17:00 UTC`, with no missing minute inside that range;
- prices from USD 4,382.37 to USD 4,510.60 across those bars;
- a live quote at collection time: bid 4,485.99, ask 4,486.34;
- an observed spread of USD 0.35, or 35 broker pips because this symbol reports
  a pip size of USD 0.01.

Two earlier spot checks in the same session had spreads of USD 0.45 and USD 0.38.
The private raw capture is
`.local/data/xauusd_m1_20260903_with_margin.json` and is excluded from Git.

The fixed-interval recorder later collected 3,285 changed bid/ask samples across
one full hour. The spread was USD 0.48 at the median, USD 0.58 at the 95th
percentile and USD 0.65 at the maximum. All rows passed symbol, timestamp,
bid/ask, spread-math and pip-size checks. See the
[data readiness report](DATA_READINESS_REPORT.md) for the full distribution.

## Costs reported by this demo account

| Item | cTrader API value | Practical meaning |
| --- | --- | --- |
| Commission | USD 30 per USD 1,000,000 executed value | 0.003% each time value is executed |
| Minimum commission | USD 0 | No extra minimum reported |
| PnL conversion fee | 0% | No conversion fee reported |
| Long swap | -68 pips | Overnight long charge under the API's `PIPS` method |
| Short swap | +28 pips | Overnight short credit/value under the same method |
| Triple swap day | Wednesday | Three-day rollover setting reported by the API |
| Swap time | 20:59 UTC | API reports minute 1,259 of the UTC day |

At prices near USD 4,430 during the one-hour run, a one-unit trade has about
USD 4,430 of executed value. The reported commission therefore implies about
USD 0.133 per execution. If both entry and exit are charged, commission is about
USD 0.266 for a round trip. Adding the recorded median spread gives a rough
USD 0.75 minimum-size round-trip cost; the 95th-percentile spread gives roughly
USD 0.85. These are model inputs, not a broker guarantee or measured fills.

FIBO's public cTrader page currently lists a 0.003% fee, 100 troy ounces per
standard lot, and a typical XAU/USD spread of USD 0.15. The live API agrees on the
fee and lot size. The three observed spreads were wider than the public typical
value, which is why later tests must use recorded bid/ask data rather than a fixed
advertised spread.

## Trading limits reported by this demo account

| Item | Observed value |
| --- | --- |
| Account leverage | 1:25 |
| Smallest trade | 1 ounce = 0.01 lot |
| Size step | 1 ounce = 0.01 lot |
| Largest single size | 4,000 ounces = 40 lots |
| Expected margin for 1-ounce buy | USD 179.45 |
| Expected margin for 1-ounce sell | USD 179.44 |
| Short selling | Enabled |
| Symbol trading | Enabled |
| Minimum stop/target distance | API reported zero points |
| Account mode | Hedged |
| Swap-free | No |
| Trading schedule | Europe/Bucharest; five daily sessions, approximately Monday–Friday 01:05–23:55 local time |

The API also returned a raw maximum-exposure value and a raw dynamic-leverage tier.
Their scaling is not stated clearly enough in the current SDK messages, so this
report does not interpret them. The explicit account leverage and expected-margin
response are usable for the first simulation.

## Rough prop-account simulation limits

The owner supplied 4% first target, 4% second target, 4% daily drawdown and 12%
total drawdown as a rough model. On the USD 3,000 demo balance, those percentages
are USD 120, USD 120, USD 120 and USD 360 respectively. They are project simulation
rules. The FIBO demo API did not report or enforce them as prop-account rules.

## What this proves and what remains open

XAUUSD/M1 exists on this account, the read path works through the active VPN, and
the account-specific contract size, commission, swap settings, size limits and
minimum margin can be captured. No order was submitted.

The historical preparation now includes 100,000 normalized XAUUSD M1 candles and
longer coarser-timeframe context, plus the other eight markets described in the
[Faraz audit](FARAZ_DATA_AUDIT.md). This is enough for conservative historical
screening when the recorded FIBO spread and commission are applied.

The quote sample still covers only one hour of one trading day. It contains no
measured fills, slippage, market-open behavior or overnight rollover behavior.
Use median, 95th-percentile and worse-than-observed spread tests during historical
screening. A strategy that survives history still requires a longer unchanged
FIBO shadow run before any demo-order work.

## Sources

- [cTrader symbol data](https://help.ctrader.com/open-api/symbol-data/)
- [cTrader message reference](https://help.ctrader.com/open-api/messages/)
- [cTrader request limits](https://help.ctrader.com/open-api/)
- [FIBO cTrader specifications](https://www.fibogroup.com/products/account-types/ctrader/)
