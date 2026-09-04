# py-mynyra
a python-based trading software

Mynyra supports a path toward repeatable, usable cash flow with survivable failures.
The economic objective and the software milestones are recorded separately in the
[worldmap](docs/WORLDMAP.md) and [implementation plan](docs/IMPLEMENTATION_PLAN.md).
This Python project starts from this repository's own source and the supplied
canonical problem specification.

The first increments provide bounded, read-only cTrader checks plus a private,
validated market-data preparation path:

| Command | What a successful result proves |
| --- | --- |
| `mynyra network-check` | A TLS connection with certificate verification to the demo endpoint |
| `mynyra app-check` | The API accepted the application's client ID and secret |
| `mynyra account-check --login <broker-login>` | View-only authorization, exact demo account identity, balance/currency and symbol-list reads |
| `mynyra market-capture --login <broker-login> --output <new-file>` | XAUUSD M1 bars, one bid/ask quote, account-specific costs, volume limits and minimum-volume margin |
| `mynyra quote-capture --login <broker-login> --output <new-file>` | Fixed-interval XAUUSD bid/ask samples from the view-only demo stream |
| `mynyra quote-summary --input <csv> --output <new-file>` | Spread and timing statistics after validating every recorded quote |
| `mynyra faraz-audit --archive <zip> --output <new-file>` | Safe structural audit of Faraz chart-export ZIPs without extracting them |
| `mynyra faraz-normalize --archive <zip> --output-dir <new-directory>` | Tehran-local candles converted to owner-only UTC CSVs and checked before publication |
| `mynyra faraz-validate --input-dir <directory>` | Every normalized CSV reread and matched to its manifest hash and row count |

Each command prints one filtered JSON result and exits. Success for an earlier
check does not imply success for a later check. The probe has no order-placement
command or live endpoint option.

## Local setup

The initial supported/tested runtime is Python 3.11; `.python-version` records
3.11.14. Use a Python 3.11 interpreter explicitly when creating the environment.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock -e .
.venv/bin/mynyra network-check
```

`requirements.lock` records the resolved versions from the first environment.
It is a version snapshot, not a cross-platform or hash-verified lock.

Application credentials can come from `CTRADER_CLIENT_ID` and
`CTRADER_CLIENT_SECRET` environment variables. An account check also needs
`CTRADER_ACCESS_TOKEN`. `.env.example` documents these names; the CLI does not
load shell files automatically.

Alternatively, use a private JSON file under the ignored `.local/` directory:

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "access_token": "YOUR_VIEW_ONLY_ACCESS_TOKEN"
}
```

The directory should have mode 700 and the file mode 600. Enter actual values in
a local editor or secret manager rather than shell command arguments. Keep
credentials, tokens, account snapshots and personal economic figures out of Git.
The app check needs only the first two JSON fields.

```sh
.venv/bin/mynyra app-check --credentials-file .local/ctrader.json
.venv/bin/mynyra account-check --credentials-file .local/ctrader.json --login <broker-login>
```

Replace `<broker-login>` with the visible account number. The code discovers the
separate `ctidTraderAccountId` from the authorized account list; it never assumes
those identifiers are interchangeable or picks the first returned account.

## First account authorization

Use the existing application's cTrader Sandbox with **Account info** selected.
Review the consent screen and authorize only the intended demo account. The
sandbox can supply an access token for this private development check. Custom
OAuth callback handling is a later increment; the playground redirect is not a
production redirect for this software.

The code requires the API to explicitly report view-only scope and demo status.
Missing/ambiguous metadata fails the check. Tokens are not automatically refreshed;
a failed/expired token needs operator attention at this stage. An access token is
different from the application secret.

The authenticated checks default to a 45-second overall timeout and a 10-second
request timeout. Heartbeats run every 10 seconds while connected. Failure ends
the run; restart the command for another bounded attempt. Account reads do not
calculate equity, execute a strategy or prove profitability.

## Gold market capture

The market command defaults to 1,000 XAUUSD one-minute bars and one current
bid/ask quote. It also reads the selected demo account's symbol costs, trading
schedule, size limits and the expected margin for the smallest trade. The command
requires view-only access and has no order request in its allowlist.

```sh
.venv/bin/mynyra market-capture \
  --credentials-file .local/ctrader.json \
  --login <broker-login> \
  --output .local/data/xauusd_m1_capture.json
```

The output must be a new file; the command never replaces an existing capture.
It creates the file with owner-only permissions. Keep captures under `.local/`,
which Git ignores. See the [first market report](docs/MARKET_DATA.md) for the
observed data, costs, limits and remaining proof gaps.

For a longer spread sample, record changed bid/ask quotes once per second:

```sh
.venv/bin/mynyra quote-capture \
  --credentials-file .local/ctrader.json \
  --login <broker-login> \
  --duration-seconds 3600 \
  --sample-interval-ms 1000 \
  --output .local/data/quotes/xauusd_quotes.csv
```

The CSV records the cTrader source timestamp, local receipt time, bid, ask and
spread. The command remains view-only and bounded; an existing file is never
replaced. Validate and summarize a completed run with:

```sh
.venv/bin/mynyra quote-summary \
  --input .local/data/quotes/xauusd_quotes.csv \
  --symbol XAUUSD \
  --output .local/data/quotes/xauusd_quotes_summary.json
```

## Faraz historical datasets

The supplied Faraz ZIPs can be audited directly without extraction:

```sh
.venv/bin/mynyra faraz-audit \
  --archive <first-zip> \
  --archive <second-zip> \
  --output .local/data/faraz/audit.json
```

See the [Faraz data audit and strategy role](docs/FARAZ_DATA_AUDIT.md). The data
is normalized from the owner-confirmed `Asia/Tehran` export setting with:

```sh
.venv/bin/mynyra faraz-normalize \
  --archive <first-zip> \
  --archive <second-zip> \
  --output-dir .local/data/faraz/normalized_utc
.venv/bin/mynyra faraz-validate \
  --input-dir .local/data/faraz/normalized_utc
```

The output directory must be new. The command preserves both sides of Tehran's
2022 repeated hour, handles the skipped spring hour explicitly, writes a hash
manifest and rereads every output before reporting success. See the
[data readiness report](docs/DATA_READINESS_REPORT.md) for the verified scope and
limits. Historical candles do not replace FIBO bid/ask costs or forward evidence.

## VPN routing on the initial Mac

V2BOX was observed connected as a macOS system VPN. The cTrader demo destination
resolved onto interface `utun4`, and the real account check succeeded on that route.
The user's suggested `127.0.0.1:1081` proxy refused connections at the time of the
retry; no listener was found. System HTTP/HTTPS/SOCKS proxy switches were disabled.

Keep the VPN connected for this environment. The current Python transport uses
the operating system's route, including its VPN tunnel. Do not hard-code port
1081 as an HTTP or SOCKS proxy without verifying an actual listener and protocol.
If V2BOX changes to a local-proxy mode, its TCP tunneling needs explicit transport
support; setting an HTTPS proxy variable alone does not configure the SDK's raw
TLS connection. Interface names and routes can change, so these are observations
from this session rather than permanent configuration assumptions.

## Verification

```sh
.venv/bin/python -m twisted.trial tests.test_probe tests.test_market tests.test_datasets
.venv/bin/python -m pip check
git diff --check
```

See [verification evidence](docs/VERIFICATION.md) for completed checks and gaps.
Authentication/transport details stay in the cTrader adapter. Its small
compatibility corrections for the pinned official SDK are explained in the plan.

Implementation references: [cTrader Open API](https://help.ctrader.com/open-api/),
[Python SDK](https://help.ctrader.com/open-api/python-SDK/python-sdk-index/), and
[account authentication](https://help.ctrader.com/open-api/account-authentication/).
