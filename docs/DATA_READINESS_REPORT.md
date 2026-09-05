# Data readiness report — 2026-09-04

## Decision

The data is ready for the next **historical strategy-screening** step. It is not
proof that a strategy can trade profitably at FIBO. The historical candles can
reject weak ideas; final candidates still need a forward, view-only FIBO shadow
run using live bid/ask quotes before any demo-order experiment is considered.

No strategy research or backtest was performed as part of this data phase.

## Historical data proof

The two original Faraz ZIP files remain unchanged in the ignored private data
directory. Their SHA-256 hashes are recorded in the
[Faraz audit](FARAZ_DATA_AUDIT.md). The source timezone is `Asia/Tehran`, confirmed
by the owner from the Faraz export setting.

The normalizer converted every recognized general-platform CSV to UTC, then
reopened every output and checked its hash, row count, timestamp order, OHLC
relationships and volume values.

| Check | Result |
| --- | ---: |
| Markets | 9 |
| Timeframes per market | 9 |
| CSV series | 81 |
| Data rows | 3,552,511 |
| Malformed rows | 0 |
| Invalid OHLC rows | 0 |
| Negative-volume rows | 0 |
| Zero-volume rows | 3 |
| Output files | 82, including the manifest |
| Normalized output size | 219,829,474 bytes |
| Output permissions | Owner-only files |
| Independent validation | Passed for all 81 series and all rows |

The 2022 Tehran clock changes required explicit treatment. There were 126 local
labels inside the repeated autumn hour. The first 63 kept the earlier UTC offset;
the second 63 kept the later offset, so no candle was discarded. Nine daily candle
labels fell inside the skipped spring hour and were moved forward through that
one-hour gap. Every resulting UTC series is strictly increasing.

The normalized dataset and its manifest are private under
`.local/data/faraz/normalized_utc_20260904/`; Git ignores them. The source ZIPs
remain the recoverable originals.

## FIBO quote and cost proof

The read-only recorder captured XAUUSD bid/ask samples for 3,600 seconds from
`2026-09-04 16:58:35 UTC` to `17:58:35 UTC`. The saved CSV has 3,285 quote rows.
Its hash is
`e40a574561e1603be828c8fd2adc43dc53a5ca0749c20a0731352fd4f3f5e077`.

Every row passed these checks: one symbol, increasing receive times,
non-decreasing cTrader source times, ask at or above bid, exact spread arithmetic
and a consistent USD 0.01 pip size.

| Measured XAUUSD spread | USD price | Broker pips |
| --- | ---: | ---: |
| Minimum | 0.00 | 0 |
| 5th percentile | 0.21 | 21 |
| Median | 0.48 | 48 |
| Mean | 0.452 | 45.2 |
| 95th percentile | 0.58 | 58 |
| 99th percentile | 0.61 | 61 |
| Maximum | 0.65 | 65 |

One row had equal bid and ask and is retained rather than silently removed. The
median receive gap was about one second, the 95th percentile was about two seconds,
and the largest gap was about seven seconds. The recorder writes only when it has
a changed quote, so these gaps do not by themselves prove a network outage.

The server timestamp and the Mac clock differed by roughly -243 to +950
milliseconds during the run. That value mixes clock alignment and the recorder's
sampling delay, so it must not be called execution latency.

The API also reported the account-specific commission, swap, lot size, volume
limits and minimum-volume margin recorded in [the market report](MARKET_DATA.md).
At roughly USD 4,430 per ounce, the 0.003% commission is about USD 0.133 per side
for the one-ounce minimum. A median-spread round trip is therefore roughly
USD 0.75 before slippage and overnight swap; a 95th-percentile-spread case is
roughly USD 0.85. These are cost-model inputs, not measured fills.

## Rules for using the data

1. Read the normalized UTC files, never the raw local timestamps, in tests.
2. Use XAUUSD M1 as the target dataset. Its 100,000 rows run from
   `2026-01-20 03:59 UTC` through `2026-05-01 20:29 UTC`.
3. Split time periods before comparing strategy results and keep the final period
   sealed during tuning.
4. Use other FX markets only after rules are fixed, to test whether an idea is
   fragile outside one XAUUSD sample. Treat crypto as a different-market stress
   test.
5. Build higher timeframes from M1 inside its coverage when exact alignment
   matters. Native higher-timeframe files provide older context, but some candles
   differ from M1 aggregation and must be labeled as a separate source.
6. Model entry and exit sides with the recorded FIBO spread and commission. Test
   at least median, 95th-percentile and worse-than-observed spread cases. Do not
   infer historical bid/ask or within-candle price order from Faraz OHLC bars.
7. A historical survivor must run unchanged in FIBO shadow mode. That phase records
   signals and simulated fills against live bid/ask but sends no orders.

## Remaining proof gaps

- XAUUSD M1 history is capped at 100,000 rows, about three months of this export.
  Longer XAUUSD context exists only at coarser native timeframes.
- Faraz does not identify whether its candle price is bid, ask or midpoint, and it
  does not define the volume field.
- The feed is labeled FXCM while the target demo account is FIBO. Candle and session
  differences are possible.
- The one-hour spread sample covers one part of one trading day. It does not cover
  rollover, market open, major news or multiple volatility regimes.
- There are no measured fills or slippage observations. M1 OHLC cannot prove which
  intraminute stop or target occurred first.

These gaps do not block a conservative historical shortlist. They do block any
claim of executable profitability or readiness to risk money.
