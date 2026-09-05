# Verification evidence — updated 2026-09-04

Source: `wadewolfie999/py-mynyra`. Initial repository state and connection work are
recorded in earlier Git history. This document reports the evidence available for
the current data-preparation increment.

| Check | Observed result | Scope of proof |
| --- | --- | --- |
| Explicit environment | Python 3.11.14; official SDK 0.9.2; dependency check passed | This local environment installs and imports the selected dependencies |
| Demo TLS check | PASS, 2026-09-03 14:43:39 UTC, TLS 1.3 | Certificate-verified connection to `demo.ctraderapi.com:5035` |
| Real application authentication | PASS, 2026-09-03 14:45:05 UTC | Demo API accepted the existing private app credentials |
| Real demo account read | PASS, 2026-09-03 15:39:36 UTC; USD 3,000.00; 60 symbols | Exact login mapping, demo status, view-only scope, balance/currency and symbol reads |
| V2BOX routing | Connected system VPN; cTrader destination used `utun4` | Account check succeeded on the active operating-system route |
| Suggested local proxy | `127.0.0.1:1081` refused connections at inspection time | No explicit local-proxy listener was demonstrated on that port |
| Real XAUUSD/M1 capture | PASS, 2026-09-03 17:01:36 UTC; 1,000 continuous bars plus bid/ask | M1 bars, quote subscription, costs, limits and minimum-volume margin are readable |
| Raw Faraz audit | PASS; 2 archives, 81 series, 3,552,511 rows | No malformed rows, invalid OHLC values or negative volumes; caps and clock transitions identified |
| Faraz UTC normalization | PASS, 2026-09-04 19:10:24 UTC | Every row converted from confirmed `Asia/Tehran`; repeated and skipped clock hours handled without row loss |
| Independent normalized-data validation | PASS, 2026-09-04 19:10:47 UTC | 81 file hashes and row counts match; all 3,552,511 rows have valid values and strictly increasing UTC |
| One-hour FIBO quote capture | PASS, 2026-09-04 17:58:36 UTC; 3,285 XAUUSD samples over 3,600 seconds | View-only bid/ask recording works for one hour; saved CSV is owner-only |
| Quote summary | PASS; median USD 0.48, p95 USD 0.58, maximum USD 0.65 | Every quote passed symbol, timestamp, bid/ask, spread and pip-size checks |
| Automated behavior tests | 31 focused tests pass | Protocol, safety, market conversion, quote summary, archive audit, Tehran clock conversion and output tamper detection |
| Credential/private-data storage | Ignored `.local/`; credential and generated data files owner-only | Secrets and private market data are excluded from versioned content |

Commands for the final local gate:

```sh
.venv/bin/python -m twisted.trial tests.test_probe tests.test_market tests.test_datasets
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q src tests
.venv/bin/mynyra faraz-validate \
  --input-dir .local/data/faraz/normalized_utc_20260904
.venv/bin/mynyra quote-summary \
  --input .local/data/quotes/xauusd_bidask_20260904_1h.csv \
  --symbol XAUUSD \
  --output <new-private-json>
git diff --check
```

The tests cover application-only stopping, complete simulated demo reads, exact
login matching, Decimal money conversion, live/ambiguous account rejection,
view-only scope enforcement, response identity, forbidden order requests, secret
handling, timeouts, disconnects and separate connection queues. Market tests cover
exact M1 conversion, symbol costs and limits, fixed-interval quote sampling,
owner-only non-overwriting files, quote distributions and invalid spread rejection.
Dataset tests cover unsafe ZIP paths, structural reporting, Tehran's repeated and
skipped 2022 clock hours, full normalized validation and hash-tamper rejection.

Remaining proof gaps:

- The FIBO spread capture covers one hour of one session. Market open, rollover,
  major news and other regimes remain unmeasured.
- Faraz provides single-price OHLCV rather than historical bid/ask and does not
  define price side or volume semantics. Its feed is labeled FXCM, not FIBO.
- The finite cTrader CLI does not yet reconnect, refresh tokens or prove unattended
  recovery. The pinned SDK adapter needs rechecking on any dependency upgrade.
- No strategy, fill, slippage, rough prop-rule simulation, payout eligibility or
  cash realization has been verified.

The [data readiness report](DATA_READINESS_REPORT.md) permits conservative
historical candidate screening while keeping those gaps as hard limits on later
claims.
