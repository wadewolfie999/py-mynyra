# Initialization evidence — 2026-09-03

Source: `wadewolfie999/py-mynyra`, branch `main`, initial commit `6fa3b54`.
The newly cloned worktree was clean. Existing source was a README, license and
Python ignore file. Initialization changes remain local and uncommitted.

| Check | Observed result | Scope of proof |
| --- | --- | --- |
| Explicit environment | Python 3.11.14; official SDK 0.9.2; dependency consistency check passed | This local environment installs/imports the selected dependencies |
| Demo TLS check | PASS, 2026-09-03 14:43:39 UTC, TLS 1.3 | Verified secure connection to `demo.ctraderapi.com:5035` |
| Real application authentication | PASS, 2026-09-03 14:45:05 UTC | The demo API accepted the existing app credentials through the verified endpoint |
| Account-information consent | View-only token became available in the user's browser | Existing authorized token captured privately; API confirmed `accounts` scope |
| Real demo account read | PASS, 2026-09-03 15:39:36 UTC; USD 3,000.00; 60 symbols | Exact login/internal-ID mapping, demo status, view-only scope, account authentication, balance/currency and symbol-list reads |
| V2BOX routing | Connected system VPN; cTrader destination uses `utun4` | Account check succeeded using the active operating-system tunnel |
| Suggested local proxy | `127.0.0.1:1081` refused the connection; no listener found | No working explicit local proxy was demonstrated on that port |
| GitHub URL retry | HTTP 200 | Repository URL reachable in the current network state; no 404 reproduced |
| Automated behavior tests | 14 focused tests pass | Simulated protocol flow, account selection, money precision, request limits, secret handling and bounded failure cleanup |
| Credential storage | Ignored `.local/` directory; file mode 600; directory mode 700 | Actual app credentials kept out of versioned project content |

Commands:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
.venv/bin/mynyra network-check
.venv/bin/mynyra app-check --credentials-file .local/ctrader.json
.venv/bin/mynyra account-check --credentials-file .local/ctrader.json --login <broker-login>
git diff --check
```

Focused tests cover application-only stopping, a complete simulated demo account
read, exact login-to-internal-ID matching with a live account listed first,
Decimal balance conversion, missing/ambiguous/live account rejection, missing
environment/scope rejection, broader permission rejection, mismatched account
responses, prohibited order requests, remote errors containing secrets, unexpected
message types, overall timeout, disconnect, separate protocol queues, malformed
credential input and credential file permissions.

Remaining proof gaps:

- One finite account read succeeded. No price subscription, heartbeat soak, restart/reconnect, token refresh, order,
  fill, strategy, realistic prop-rule simulation or cash realization has been verified.
- The finite CLI uses a pinned SDK with a small private endpoint adaptation. A
  dependency upgrade must recheck that seam; no deployment security review is claimed.
- Account-field validation is deliberately strict. Required metadata was present
  for the selected account; compatibility with other accounts/brokers is untested.
- No financial return, payout eligibility or economic self-sufficiency is established.

The first connection milestone is complete. Next justified action: obtain the
owner's first strategy/instrument and target rulebook, then capture the smallest
useful data sample for that experiment. Economic thresholds and authorized exposure
remain open inputs in the implementation plan.
