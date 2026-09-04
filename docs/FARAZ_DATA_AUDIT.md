# Faraz historical-data audit and UTC normalization — 2026-09-04

## Decision

The two downloads are ready as a **historical strategy playground** after full
UTC normalization and validation. They are not execution evidence for the FIBO
account. Use them to reject weak ideas and polish a fixed shortlist. Survivors
then run in shadow mode against live FIBO bid/ask quotes, with signals and
simulated fills recorded but no orders sent.

Testing every possible strategy is neither finite nor statistically safe. The
project will compare the previously agreed 5–7 distinct candidates and a limited,
recorded set of variants. This keeps repeated experimentation from manufacturing
an apparent winner.

## Preserved inputs

The original ZIP files were copied byte-for-byte into the Git-ignored
`.local/data/faraz/raw/` directory with owner-only permissions. The originals in
Downloads were not changed.

| Archive | Size | SHA-256 | Contents |
| --- | ---: | --- | --- |
| `ef13d28e638b477c85097302a36447cb.zip` | 67,596,490 bytes | `7b170e9101aac25edf5a3c20ab40a8f5b39ad50ccbd82dab68b98e676d002367` | Eight FXCM-labelled markets |
| `af65b7baff054baeb9d645f4c9f2a172.zip` | 9,164,099 bytes | `f185a02923901863d194b0abf427f4dc00c0ec9bcb387f6b71c008e1d5e4a0bb` | FXCM-labelled XAUUSD |

The audit reads the CSV files directly from each ZIP and does not extract archive
paths. The Advanced GET PRN copies are ignored: they are capped at 20,000 rows and
their format does not preserve an ordinary intraday timestamp. The general CSVs
are larger and contain separate date and time fields.

## Inventory and checks

- 9 markets: XAUUSD, EURUSD, GBPUSD, USDJPY, EURJPY, GBPAUD, GBPCAD,
  BTCUSD and ETHUSD;
- 9 timeframes for each market: M1, M5, M15, M30, H1, H4, D1, W1 and MN1;
- 81 series and 3,552,511 OHLCV rows;
- no malformed rows, impossible OHLC rows or negative volume values;
- three zero-volume M1 rows, one each in EURUSD, GBPUSD and USDJPY;
- all 27 M1, M5 and M15 series hit Faraz's 100,000-row export cap.

The source README says capped exports keep the newest rows. The requested start
date therefore does not prove the first candle in a file. Actual XAUUSD coverage is:

| Timeframe | Rows | First timestamp in file | Last timestamp in file |
| --- | ---: | --- | --- |
| M1 | 100,000 | 2026-01-20 07:29 | 2026-05-01 23:59 |
| M5 | 100,000 | 2024-11-28 17:00 | 2026-05-01 23:55 |
| M15 | 100,000 | 2022-02-03 05:15 | 2026-05-01 23:45 |
| M30 | 51,181 | 2022-01-03 02:30 | 2026-05-01 23:30 |
| H1 | 25,598 | 2022-01-03 02:30 | 2026-05-01 23:30 |
| H4 | 6,692 | 2022-01-03 02:30 | 2026-05-01 21:30 |
| D1 | 1,120 | 2022-01-03 00:00 | 2026-05-01 00:00 |
| W1 | 226 | 2022-01-03 00:00 | 2026-04-27 00:00 |
| MN1 | 53 | 2022-01-03 00:00 | 2026-05-01 00:00 |

## Timestamp normalization and price limitations

The owner confirmed that Faraz exported the CSV times in `Asia/Tehran`. Every
market has one repeated/backward clock point in M15, M30 and H1 at
`2022-09-21 23:xx`, for 27 visible non-increasing transitions in total. This is
Iran's final daylight-saving rollback. The normalizer processes rows in source
order and keeps both occurrences: 126 candle labels fall inside the ambiguous
hour, of which 63 use the second UTC offset. It also moves nine daily labels
forward through the skipped hour at the March 2022 clock change. No row is sorted
away or deduplicated.

The normalized output contains all 81 series and all 3,552,511 rows. A separate
validation pass confirmed owner-only files, matching hashes and row counts, valid
market values and strictly increasing UTC timestamps for every series.

The files contain one OHLC price and one volume value per candle. They do not say
whether price is bid, ask, midpoint or another indicative value, and they do not
define the volume field. The filename identifies FXCM as the feed, while the target
execution account is FIBO. Broker feed, session and candle differences therefore
remain real.

A consistency check aggregated overlapping M1 candles into M5 and M15. Almost all
XAUUSD bars agreed within one cent, but a small number differed; one M5 bar differed
from the M1 aggregation by USD 5.28. Native higher-timeframe files must not be
silently treated as exact resamples of M1.

## Strategy-selection workflow

1. **Define before testing.** Write exact rules for 5–7 candidates, their small
   parameter ranges and rejection criteria before viewing performance.
2. **Historical playground.** Use XAUUSD M1 for target-timeframe work. Use longer
   XAUUSD M5/M15 data to expose different regimes. Use other Forex markets as
   portability checks after rules are fixed.
3. **Out-of-domain stress.** BTCUSD and ETHUSD are 24/7 markets with materially
   different behavior. Use them to reveal fragile assumptions, not to select the
   XAUUSD winner.
4. **Realistic costs.** Apply FIBO commission, swap and a distribution of recorded
   FIBO spreads. Faraz candles alone cannot supply those costs or within-candle
   execution order.
5. **Sealed evaluation.** Keep chronological final periods unused during tuning.
   Preserve XAUUSD data after 2026-05-01 as a later evaluation set rather than
   downloading and inspecting it during strategy development.
6. **FIBO shadow run.** Feed live bid/ask samples to surviving strategies. Record
   signals, hypothetical entry/exit side, spread, latency and simulated PnL. Do
   not retune from the shadow period and do not submit orders.
7. **Demo execution later.** Only a strategy that survives the sealed history and
   shadow period becomes eligible for a separately bounded demo-order experiment.

Cross-market evidence is valuable, but trading cannot be completely independent
of the traded market. Sessions, spread, volatility, jumps and contract economics
change the result. Other markets are robustness tests rather than substitutes for
proof on XAUUSD at FIBO.

## Implemented tools and evidence

`mynyra faraz-audit` safely rechecks both ZIPs and writes a private JSON manifest.
The current manifest is `.local/data/faraz/faraz_audit_20260904_v3.json`.

`mynyra faraz-normalize` writes the UTC data and a per-file hash manifest to the
ignored `.local/data/faraz/normalized_utc_20260904/` directory. The result contains
82 owner-only files and occupies 219,829,474 bytes. `mynyra faraz-validate` rereads
that result independently.

`mynyra quote-capture` subscribes to the view-only FIBO demo quote stream and
samples the latest changed bid/ask at a fixed interval. The completed one-hour
capture and its limits are summarized in the
[data readiness report](DATA_READINESS_REPORT.md).

## Sources

- The `README.txt` inside each supplied ZIP is the source for its export caps and
  actual truncated coverage.
- [FXCM's official sample-data repository](https://github.com/fxcm/MarketData)
  describes its own historical candles as indicative data and documents UTC for
  the direct FXCM samples. Faraz is a separate export, and the owner confirmed its
  timezone independently.
- [cTrader symbol-data documentation](https://help.ctrader.com/open-api/symbol-data/)
  defines historical bars and live spot subscriptions used by the FIBO recorder.
- [Faraz's market guide](https://faraz.io/blog/learn/show-days-of-the-week-in-the-chart/)
  distinguishes five-day Forex trading from 24/7 crypto trading, which is why the
  crypto series serve as a different-market stress test.
