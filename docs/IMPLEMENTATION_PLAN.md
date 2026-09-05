# Python implementation plan

Status: updated 2026-09-04. Implemented scope is the connection probe, bounded
XAUUSD/M1 capture, Faraz archive audit and UTC normalization, fixed-interval FIBO
quote recorder, and reproducible quote summary. The
[data readiness gate](DATA_READINESS_REPORT.md) now passes for conservative
historical screening. Remaining increments depend on new evidence and the owner's
unresolved economic decisions.

The owner wants autonomous Python trading, starting with **XAUUSD / M1** and
evidence before changing that choice. Use the 4%/4% targets and 4% daily/12% total
loss limits as a [rough simulation model](DEMO_SCENARIO.md). FeneFX is excluded as
a funding candidate; its website does not define project requirements.

The owner has no existing strategy. Researching and testing about 5–7 candidates
is part of this project, with deep internet research authorized when strategy
selection is the focus. The [strategy research plan](STRATEGY_RESEARCH_PLAN.md)
sets the comparison approach. No strategy, order support or loss-rule engine is
implemented yet.

## First increment: establish identifiable, read-only demo access

Use one local Python 3.11 process and Spotware's published Protobuf SDK. The first
vertical slice consists of:

1. Connect to `demo.ctraderapi.com:5035` with certificate/hostname verification.
2. Authenticate the existing application's client ID and secret.
3. Obtain a view-only `accounts` token through cTrader's sandbox consent flow.
4. Retrieve the token's authorized account list; match the explicitly supplied
   broker login to one demo `ctidTraderAccountId`.
5. Authenticate that account; read trader information, deposit currency and
   available symbols. Convert monetary values using the returned precision.
6. Emit filtered, timestamped evidence and stop the connection.

Steps 1–6 have passed against the real demo service. A view-only token became
available in the user's browser, and the account check completed at 15:39:36 UTC:
correct selected account, USD 3,000.00 and 60 symbols. Simulated protocol tests
cover rejection and failure paths. The CLI separates the three levels of proof.

V2BOX is currently a working system VPN route for this machine: the cTrader
destination uses `utun4`. A retry through the suggested local port 1081 was refused.
Use the verified OS tunnel in this mode; verify the listener/protocol first if a
future local-proxy mode requires an HTTP CONNECT or SOCKS transport adapter.

Current modules:

| Module | Ownership |
| --- | --- |
| `config.py` | Credential input and safe validation messages |
| `network.py` | Fixed demo endpoint and credential-free TLS check |
| `ctrader.py` | SDK, transport, authentication order, account identity and protocol conversion |
| `market.py` | Exact price-bar conversion, owner-only capture persistence and quote validation/statistics |
| `datasets.py` | Safe ZIP audit, Tehran-to-UTC normalization and full output validation |
| `cli.py` | Operator commands, bounded lifecycle, filtered output and exit codes |

The current probe has a 45-second overall deadline, 10-second request deadlines,
10-second heartbeats and sequential requests. A failed run closes its service;
the operator can rerun it. It sends far below the documented limits of 50
non-historical or 5 historical requests per second per connection.

The request allowlist contains only application/account authentication and reads.
Live accounts, absent/ambiguous account identity, unconfirmed demo metadata,
unconfirmed/broader token scope and mismatched response identities fail the run.
Raw messages and remote error descriptions are not printed because they can echo
tokens. The account balance output is not an equity or profit calculation.

## Adapter decision and limitations

Chosen baseline: the official `ctrader-open-api==0.9.2` SDK, which PyPI lists as
the current non-yanked release. The later 0.9.3 release is yanked. The official
Python SDK uses Twisted and does not provide a WebSocket client.

Alternative: a small `asyncio` JSON/WebSocket adapter with a current WebSocket
library. It would avoid the SDK's older dependency pins, but would make this
project own message typing, correlation, pacing, heartbeats and lifecycle behavior.
For this finite proof, retain the vendor messages/client and isolate its details.
Reconsider the adapter before unattended operation if the pinned dependencies or
maintenance burden obstruct the next useful experiment.

Direct inspection of installed SDK 0.9.2 found three integration seams requiring
small local corrections:

- Its client constructs `ssl:host:port` without a hostname-verification parameter.
  The adapter replaces that endpoint with Twisted `SSL4ClientEndpoint` and
  `optionsForClientTLS` for the fixed demo hostname, with `service-identity` installed.
  This uses one private SDK/Twisted attribute and therefore depends on the pinned
  versions. Review this seam whenever upgrading them.
- Its protocol's outbound queue is defined at class level. The local protocol
  subclass gives each connection a separate queue.
- Its `stopService` checks `isConnected`, which can leave a pending connection
  service running. Cleanup calls Twisted's base stop directly, including on timeout.

The adapter schedules the documented heartbeat cadence explicitly. Do not patch
installed package files or weaken certificate checks to obtain a passing result.
The dependency snapshot is suitable for reproducing this development probe; it is
not a completed dependency security review or approval for a deployed trading service.

## Next increments, chosen by information gained

| Order | Small deliverable | Exit evidence and why it matters |
| --- | --- | --- |
| 1 — complete | View-only demo consent and account read | Exact account, currency, balance and symbol list confirmed against the API |
| 2 — data gate complete | Verify XAUUSD metadata and M1 availability; normalize supplied history; record and summarize FIBO bid/ask | 3.55 million rows normalized and independently validated; 1,000 FIBO bars and 3,285 one-hour quote samples captured; limits are explicit |
| 3 | Compare 5–7 simple strategies under common costs and rough account rules, then test useful layers | Reproducible rules, all trials recorded, independent evaluation and explicit failure evidence; no forced winner |
| 4 | Bounded demo execution and recovery, only after its exposure limits are set | Size/price rounding, server acknowledgement, fills/rejections, partial execution, restart reconciliation and STOP behavior |
| 5 | Decide whether a paid/live/prop attempt is justified | Current strategy evidence, firm eligibility, payout route, spending cap and survivable failure state |
| 6 | Measure cash realization and repeatability | Receipts reconciled against attempts, fees, operating costs and obligations; sufficient remaining reserve |

Before step 2 runs unattended, add a registered callback and token lifecycle only
if repeated operation needs them: keep code exchange off browser/history logs,
use view-only scope, track expiry and store replacement access/refresh tokens
atomically with owner-only permissions. Refresh invalidates old token values;
avoid concurrent refreshers and recover explicitly from failed persistence.

Use a bounded reconnect policy with reauthentication and subscription restoration
when continuous data capture is required. Record UTC event times and detected gaps.
Do not hide a broken data stream behind retries. Before order support, distinguish
an unanswered submission from a rejected order; reconcile before any resubmission.
This behavior is not implemented by the current finite read probe.

Start evidence capture with local JSONL/CSV files; introduce SQLite if durable
queries/reconciliation need it. Keep strategy decisions independent of SDK types.
Add risk/execution boundaries when the chosen strategy and target rules are known.
A dashboard, distributed services, deployment automation or general strategy engine
has no current completion requirement. Manual rule verification and cash accounting
can serve the first experiments.

The account percentages do not define per-trade risk, position size, strategy,
personal spending authorization or payment amounts. Research and experiments will
define candidate trading rules and simulation sizing; personal spending decisions
remain the owner's. M1 remains the starting timeframe, with evidence required for
a change.

## Questions that change the next step

1. Which chronological development, selection and sealed evaluation boundaries
   give the 100,000-row XAUUSD M1 sample a fair comparison without leakage?
2. What is the first cash-received target, the operating cost/runway baseline, and
   the maximum total cash loss/spend authorized? What debt/attempt/STOP limits apply?
3. Which 5–7 distinct rules merit testing, and what evidence would justify keeping
   or rejecting them? Resolve this through the research and comparison work.
4. For an eventual funding account, which provider permits the intended automation,
   accepts the owner and offers suitable rules and a usable payout route? What
   counts as cash under operational control? FeneFX is not a current candidate.

The read-only connection and historical-data gates are complete. Candidate
research can now begin without a chosen funding provider or an owner-supplied
strategy. Historical screening must follow the readiness report's constraints;
real-provider accuracy and economic exposure require their own evidence and inputs.

## Sources

- [cTrader endpoints](https://help.ctrader.com/open-api/proxies-endpoints/): demo/ live separation, port and protocol selection.
- [Connection guide](https://help.ctrader.com/open-api/connection/): SSL, heartbeat cadence, connection count and Python transport support.
- [Account authentication](https://help.ctrader.com/open-api/account-authentication/): application/account flow, view-only scope, sandbox tokens and refresh behavior.
- [Python SDK](https://help.ctrader.com/open-api/python-SDK/python-sdk-index/): official package and Twisted runtime.
- [Message definitions](https://help.ctrader.com/open-api/messages/): authentication, account list, trader, assets and symbol requests.
- [PyPI package](https://pypi.org/project/ctrader-open-api/): published releases and dependency metadata; installed files were inspected directly.
