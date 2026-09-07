# Verification evidence — updated 2026-09-07

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

## ASUS parity verification — 2026-09-05

The [ASUS environment report](ASUS_ENVIRONMENT.md) records the full platform,
installation, private-state, authorization, network, rollback and parity evidence.
On Ubuntu 24.04.4/amd64, the project-local Python 3.11.14 environment passed the
same 31 tests, `pip check`, project/test compilation, the full 81-series and
3,552,511-row Faraz validation, and a create-only re-summary of all 3,285 one-hour
XAUUSD quotes. The capture SHA-256, median spread and p95 spread matched the prior
evidence exactly.

The ASUS cTrader TLS check passed with TLS 1.3 through the v2rayN `singbox_tun`
system route. The transferred token passed the bounded application and single-demo-
account read sequence with `accounts` scope and 60 symbols. No token was created or
refreshed, no trading scope was selected, and no order path was called or changed.

## Offline comparison verification — 2026-09-06

This section supersedes the earlier absence of a historical simulator. It does
not refresh the historical network, credential or broker-account observations.

| Check | Observed result | Scope |
| --- | --- | --- |
| Preregistration | Commit `d3c664a` precedes implementation and all strategy results | Fixed candidate rules, costs, sizing, partitions, trial budget and selection policy |
| Supported runtime and imports | Python 3.11.14; `PYTHONPATH=src` selects this worktree | Shared venv reused without modifying its installation |
| Full test gate | 71 tests passed | Existing 31 safety/data tests plus 40 causal, execution, account, selection and seal tests |
| Dependencies / compilation | `pip check` and compilation of src/tests/scripts passed | No dependency changes; supported local environment |
| Full Faraz validation | 81 series, 3,552,511 rows passed; hashes, OHLCV and UTC order valid | Structural validation only; no sealed strategy results inspected |
| Registered screen | All 672 cases completed | Five candidates plus no-trade, all 27 cost/side scenarios, both views, development/March and four fixed-start account cohorts |
| Independent accounting audit | All 672 cases passed | 189,339 scenario trade records reconciled; repeated scenarios are not independent observations |
| Independent full replay | Every result SHA-256 and the complete index matched | Deterministic numerical output, provenance and case coverage reproduced |
| Finalists | Empty manifest; sanitized freeze committed as `10095a4` | All candidates rejected under the preregistered March gates; no reselection |
| April seal | Evaluation returned `not_opened`, reason `no_finalists` | Both strategy runs loaded only 69,846 bars through 2026-03-31 23:59 UTC |
| Private evidence | All generated evidence files checked owner-only; `.local/` and `.venv` untracked | Raw data, ledgers and run outputs excluded from Git |
| Review preparation | Diff whitespace checks passed | Report/source ready for an unmerged PR; no automatic merge |

The full screen index and independent replay index both have SHA-256
`5454250a38b492b511ba478ed23c84ccb1bdde3b3a2d9e3bc1e5ce460c3f0ff0`.
The finalist manifest SHA-256 is
`f13616e61ec6360be7bca2adcb8d0e9629701b5bc63f3c926eb3a92854fc3ffb`.
Private command output and the completed gate are retained in
`.local/experiments/verification_v1.json`; independent replay/accounting evidence
is in `.local/experiments/audit_replay_v1.json`. See the
[report](XAUUSD_COMPARISON_REPORT.md) and
[reproduction commands](COMPARISON_WORKFLOW.md).

No credentialed checks, orders, trading-scope changes, quote/shadow campaigns or
spending occurred in this increment. No protocol correction or numerical source
change was made after historical results. April was not consumed for a forced
winner. Untested parameter neighborhoods, limited market regimes, unknown quote
paths, later-period cost evidence and actual fills remain material limitations.

## Bigi workstation cTrader validation — 2026-09-07

This validation ran on branch `codex/bigi-ctrader-connection-validation`, created
directly from then-current `origin/main` commit
`373f6068db872fe7a389a0ac540528e5197a3e38`. The workstation was macOS
26.6.1/arm64 with Homebrew Python 3.11.16. This establishes Python 3.11
compatibility on this Mac; it is not an exact Python 3.11.14 ASUS parity claim.

| Check | Observed result | Scope |
| --- | --- | --- |
| Locked installation | `requirements.lock` and the editable package installed; `pip check` passed | The locked dependencies are internally consistent in this Python 3.11.16 environment |
| Compilation | `src`, `tests` and `scripts` compiled successfully | Checked Python sources were syntactically importable; this is not runtime or provider evidence |
| Full offline gate | All 83 tests passed | Probe, market, dataset, experiment, SMA diagnostic, benchmark, catalog and Praxis Step 3 behavior passed locally |
| Demo TLS | PASS, 2026-09-07 17:42:45 UTC, TLS 1.3 | Certificate-verified connection to the fixed `demo.ctraderapi.com:5035` endpoint |
| Application authentication | PASS, 2026-09-07 17:42:46 UTC | The demo API accepted the private application credentials |
| Demo account read | PASS, 2026-09-07 17:45:36 UTC; USD; 60 symbols; `accounts` scope | Exact account mapping, API-confirmed non-live status, view-only account authentication, currency and symbol-list reads |
| Private-state boundary | Credential and complete account-result files were regular, owner-only, ignored and untracked | Credential values, account identifiers, balances and raw provider payloads remain outside Git |

The first account attempt failed closed before account selection because the API
did not explicitly report view-only scope. After Vahid separately authorized and
replaced the access token, the repeated TLS, application and account checks passed.
No token refresh or rewrite was performed by the validation command itself.

These results prove bounded read-only access to one API-confirmed demo account.
They do not prove profitability, order readiness, token recovery, reconnect
behavior, unattended operation, live-account safety or authority to trade. No
order, market/quote capture, historical experiment, trading-scope change,
deployment or release occurred during this validation.
