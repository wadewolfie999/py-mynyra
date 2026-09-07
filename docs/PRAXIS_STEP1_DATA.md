# Praxis Step 1: historical data assessment

Reviewed 2026-09-07. **Prioritize a bounded Dukascopy XAUUSD bid/ask history sample,
with HistData as a fallback; retain FIBO history as the eventual execution-feed
comparison.** This is a source assessment, not a completed acquisition or license
clearance. No account was created, no payment made, no market history downloaded,
and no live capture or broker request performed in this step.

## What is actually available locally

The validated private Faraz manifest contains 81 series / 3,552,511 rows. XAUUSD M1
has 100,000 rows, 2026-01-20 03:59 through 2026-05-01 20:29 UTC. Only its pre-April
prefix is available for this exploration. Manifest metadata also shows M5 starting
2024-11-28 and M15 starting 2022-02-03, both 100,000 rows; H1 starts 2022-01-02.
These coarser files cannot reconstruct absent M1 events or historical bid/ask.
They also differ from M1 aggregation in places and remain separate sources.
No coarser-price results were inspected here.

Single-price FXCM-labeled candles have unknown quote side. The separate one-hour
FIBO quote capture describes September costs; it is not a period-matched spread
history. Importing the same dates from a new provider improves feed comparison,
not temporal independence. A relational database cannot repair these evidence gaps.

## Source comparison

| Source | Verified public capability | Access/cost status | Coverage and remaining proof |
| --- | --- | --- | --- |
| Dukascopy | Official export covers commodities and offers CSV from ticks through monthly; separate export documentation says bid/ask and volumes are available. | Public export described as free. Programmatic export path, applicable automated-use/redistribution terms and actual host retrieval not yet verified. | Best first sampling candidate. Exact XAUUSD first/last dates, 2020–2025 completeness, timestamp configuration and tick semantics need inspection of export metadata/sample. Do not treat a third-party coverage claim as verified. |
| HistData | XAU/USD explicitly listed; monthly/yearly ZIP organization, M1 and tick formats. M1 OHLC is bid-based; Generic ASCII ticks include ask. Fixed EST without DST. | Website advertises free downloads; separate bulk FTP/SFTP option. No bulk-service price or redistribution entitlement verified. | Useful fallback/cross-check. Exact year inventory not established: direct date-selector retrieval failed. No guarantee/certification; file gap diagnostics are advertised. Volume is removed, so do not infer volume signals. |
| OANDA v20 | M1 candles can contain bid, ask and mid components; completion flag and price-update count; API examples document bounded pagination (maximum 5,000 candles). | Requires authorized account/token; available instruments depend on account. No account or new credential is requested/created now. | Exact XAU_USD availability and earliest accessible history are unverified for this user. Separate bid/ask candle extrema do not recover intrabar quote ordering. |
| FIBO through cTrader | Official API supports historical bars and side-specific historical ticks, with a maximum one-week tick request interval and backend-dependent response limit. | Existing demo/view-only integration is present; a historical downloader would need bounded pagination and recovery, not broader trading scope. | Preferred broker-aligned comparison if adequate retention exists. Retention depth, completeness and broker permissions unverified; the existing 1,000-bar sample does not prove years of history. |
| FXCM direct | Official Pro page advertises historical bid/ask and long FX history; free minute/hour/day history for 17 currencies. | Free currency subset versus other access must be distinguished. No paid-service quote verified. | Gold exists as an FXCM spot instrument, but the free currency-history statement does not prove XAUUSD inclusion. Same-provider identity as Faraz is not enough to establish matching feed/conventions. |

Sources: [Dukascopy export](https://www.dukascopy.com/swiss/english/marketwatch/historical/),
[bid/ask export description](https://www.dukascopy.com/api/data/get/historical-data-export),
[HistData FAQ](https://www.histdata.com/f-a-q/),
[HistData download formats](https://www.histdata.com/download-free-forex-data/),
[OANDA candle definitions](https://developer.oanda.com/rest-live-v20/instrument-df/),
[OANDA pricing requests](https://developer.oanda.com/rest-live-v20/pricing-ep/),
[cTrader historical data](https://help.ctrader.com/open-api/symbol-data/),
[FXCM data offering](https://www.fxcm.com/pro/market-data/fx-price-feed/),
[FXCM gold specification](https://www.fxcm.com/uk/help/commodities-xau-usd-gold/).

No source above has been certified as complete, executable at FIBO, or licensed
for redistribution. Free access does not itself imply redistribution permission.
Keep samples private; establish provider terms before building an unattended
bulk downloader. Do not substitute COMEX futures for spot XAUUSD without a new
instrument decision, contract-roll model and basis analysis.

## Concrete acquisition acceptance contract

Request metadata for XAUUSD over 2020-01-01 through 2025-12-31 first; source coverage
is a question, not an assumption. Freeze the intended exploratory/selection/holdout
boundaries before any performance inspection. For initial mechanical validation,
use a fixed January 2022 weekday sample and the March 2022 DST transition week;
these dates were selected for parsing/calendar behavior, not observed returns.
Do not download or expose 2025 holdout prices to exploratory processes. April
2026 remains excluded regardless of provider.

For each received file record provider and symbol identity, source URL/request
parameters, acquisition time, declared timezone and bar-label convention, side,
units, compression/format version, raw hash, byte count, licensing evidence and
processing version. Keep both the original and normalized representation.
Validate monotonicity, duplicate timestamps, bid<=ask for paired quotes, OHLC
bounds, fixed-point precision and observed coverage. Distinguish scheduled breaks
from unexplained missing data; never silently forward-fill missing prices.

For bid/ask ticks, preserve each side's event time and original sequence. Do not
join stale quotes without an explicit freshness limit. Bid and ask OHLC highs at
a minute can occur at different instants; their difference is not an observed
spread. Derive paired spread statistics from synchronized quote events where
available. Record tick-count versus size-volume semantics explicitly.

Normalize HistData's fixed EST by UTC+5 hours, not America/New_York DST rules.
For any source, verify its timestamp claim against a small sample and documented
session boundaries. Resample complete M1 bins causally; produce M15 only from
complete constituent minutes. Record all rejected rows and revisions. A correction
creates a new version; previous experiment snapshots remain immutable.

Acceptance evidence: checked small sample and rejection log, metadata-only
coverage inventory, reproducible normalized hash, source terms/access status,
measured bytes per row and a capped estimate for full acquisition. If the source
fails this contract, move to the fallback with an explicit rejection reason.
Actual acquisition remains subsequent work; Step 1 completes the assessment and
identifies these gaps rather than claiming unavailable data is ready.

## Capacity and implications for Step 2

Observed local footprint: normalized corpus about 210 MiB; original 672-case screen
about 90 MiB; current filesystem about 11 GiB available. These are snapshots, not
capacity reservations. Retaining multiple ledgers/replays can dominate storage.

Planning arithmetic, not a benchmark: 252 weekdays * 23 hours * 60 minutes is
347,760 M1 rows/year. Six years is about 2.09 million rows per series. At a measured-
later assumption of 200 bytes/row, paired OHLC fields would be roughly 0.42 GB
before originals, indexes, database overhead and backups. A 1 Hz tick stream at
100 bytes/record would be about 2.09 GB/year before copies; actual event rates can
be much higher. Measure a sample before approving a bulk tick acquisition.

Step 2's database must distinguish source/instrument/side/dataset version, retain
raw-artifact references and quality findings, enforce unique versioned bar keys,
and catalog experiment/code/config/split/result hashes. Use exact prices and UTC
instants with preserved source clock metadata. A research role or export boundary
must keep sealed partitions out of ordinary queries; a WHERE clause by convention
is insufficient once arbitrary SQL is available. The simulator should still read
a frozen, hashed export. PostgreSQL is the preferred catalog prototype; no service
installation or schema migration was performed in this step.
