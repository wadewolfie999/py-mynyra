# ASUS Python and cTrader environment — 2026-09-05

## Result and boundary

ASUS is ready for the repository's current Python 3.11, demo-only, view-only
workflow. Python 3.11.14 is installed below ignored project state, `.venv` was
created from it, the dependency snapshot is installed, the full local gate passes,
and the transferred cTrader token completes a bounded demo account read. No order
was sent, no order path or broader permission was enabled, and no strategy work
was performed.

This is a description of the observed ASUS state, not a claim that the network,
token, market data, or external service will remain unchanged.

## Platform diagnosis

| Item | Observed state |
| --- | --- |
| Operating system | Ubuntu 24.04.4 LTS (Noble), amd64 |
| Kernel | `6.8.0-139-generic` |
| Ubuntu Python | `/usr/bin/python3` resolves to Python 3.12.3 |
| Required Python | Python 3.11.14 from `.python-version` |
| Package availability | The configured Noble base, updates, backports, security, and universe sources offer Python 3.12, not Python 3.11.14 |
| Existing version tools | No pyenv, mise, asdf, uv, Conda, or Pixi installation was found |
| Build tools | GCC 13.3.0, GNU Make 4.3, `pkg-config`, `curl`, `apt-get`, and `dpkg-deb` were available |

The Microsoft and Codex application repositories present on the machine are
unrelated to Python selection and were not used. No PPA or other Python package
source was added.

## Installation decision

The selected design is a controlled CPython source build at
`.local/runtime/python-3.11.14`, encapsulated by
[`scripts/install-python311.sh`](../scripts/install-python311.sh). The script:

- refuses platforms other than Ubuntu 24.04/amd64;
- downloads the official Python 3.11.14 source archive and verifies its pinned
  SHA-256 before extraction;
- downloads required development packages from configured, signed Ubuntu
  repositories and extracts them into a temporary sysroot without `sudo` or a
  persistent dpkg change;
- uses `make altinstall` with a project-local prefix; and
- verifies the exact interpreter and the SSL, hashing, compression, SQLite,
  readline, ctypes, UUID, and zlib modules before reporting success.

The downloaded source was also verified manually during this installation with a
valid Python release signature. The primary key fingerprint was
`A035 C8C1 9219 BA82 1ECE A86B 64E6 28F8 D684 696D`, the signing subkey fingerprint
was `CFDC A245 B104 3CF2 A5F9 7865 FFE8 7404 168B D847`, and the source SHA-256 is
`8d3ed8ec5c88c1c95f5e558612a725450d2452813ddad5e58fdb1a53b1209b78`.

The build intentionally omits the optional `_dbm`, `_gdbm`, `_tkinter`, and `nis`
modules; Mynyra does not import or require them. The installed interpreter reports
OpenSSL 3.0.13 and SQLite 3.45.1. Its relevant Ubuntu runtime packages are:

| Package | Version |
| --- | --- |
| `libbz2-1.0` | `1.0.8-5.1ubuntu0.1` |
| `libffi8` | `3.4.6-1build1` |
| `liblzma5` | `5.6.1+really5.4.5-1ubuntu0.3` |
| `libncursesw6` | `6.4+20240113-1ubuntu2.2` |
| `libreadline8t64` | `8.2-4build1` |
| `libsqlite3-0` | `3.45.1-1ubuntu2.7` |
| `libssl3t64` | `3.0.13-0ubuntu3.15` |
| `libuuid1` | `2.39.3-9ubuntu6.6` |
| `zlib1g` | `1:1.3.dfsg-3.1ubuntu2.2` |

### Alternative considered

pyenv would also isolate Python 3.11 from Ubuntu Python and makes managing many
interpreter versions convenient. For this repository's single exact interpreter,
it adds another updater, shim layer, user-wide directory, and shell integration
without removing the need to supply native build headers. The controlled build was
chosen because its interface is one repository script, its source hash and prefix
are explicit, and its entire persistent footprint is below ignored project state.

Installing from source into `/usr/local` was also rejected because it requires root
access and creates machine-wide coupling. Ubuntu's `/usr/bin/python3` remains
Python 3.12.3 and was not replaced, removed, or repointed.

## Reproduce, update, and remove

From the repository root:

```sh
bash scripts/install-python311.sh
.local/runtime/python-3.11.14/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock -e .
```

The installer is idempotent for a valid existing interpreter and refuses an
unexpected partial prefix. `MYNYRA_BUILD_JOBS` may be set to an integer from 1
through 64; the default is 4. `requirements.lock` is the authoritative list of the
24 third-party package versions. The environment additionally contains
`pip==24.0`, `setuptools==79.0.1`, and editable `py-mynyra==0.1.0`.

For a deliberate Python patch update, review the new Python release and key,
change the version and SHA in the installer and `.python-version`, build into a new
versioned prefix, recreate `.venv`, and run the complete gate before removing the
old prefix. Do not update the ignored runtime in place.

Removal is limited to the two project-local generated paths:

```sh
rm -rf -- /home/wade/libs/py-mynyra/.venv
rm -rf -- /home/wade/libs/py-mynyra/.local/runtime/python-3.11.14
```

Those commands do not affect `/usr/bin/python3`, apt packages, shell startup files,
or other repositories. Re-run the three reproduction commands to recover.

## Private-state audit

Before token work, `.local/` was inspected internally. Excluding the new runtime,
it contains 96 regular files in 15 directories, no symlinks, and no file whose mode
is broader than `0600`. The top directory is `0700`. The credential JSON is a
regular `0600` file containing non-empty client ID, client secret, access token,
and refresh token strings. Values were not displayed, hashed for display, copied,
or committed. One empty quote log transferred with mode `0644` was corrected to
`0600`; its content was not changed.

Git's ignore rules cover `.local/`, the credential file, runtime, raw archives,
normalized datasets, quote files, and generated reports. Runtime library files
use ordinary executable/read-only installation modes but remain inaccessible to
other users through the enclosing `0700` `.local/`; all credentials and generated
private data themselves are owner-only.

The transferred evidence remains usable and unchanged:

- the Faraz manifest validates 81 series and 3,552,511 rows, with matching hashes,
  strictly increasing UTC timestamps, and valid market values;
- the one-hour XAUUSD quote CSV still hashes to
  `e40a574561e1603be828c8fd2adc43dc53a5ca0749c20a0731352fd4f3f5e077`;
- re-summarization validates all 3,285 quote rows, exact bid/ask and spread
  arithmetic, source/receive timestamps, and the USD 0.01 pip size; and
- the observed spread remains median USD 0.48 and p95 USD 0.58.

## cTrader authorization decision

The official Open API portal shows the existing application as active. Its
Playground offers two scopes and had **Account info** selected:

- `accounts` gives view-only account information and statistics; trading operations
  are impossible;
- `trading` gives account information/statistics and all permitted trading
  operations.

The official authentication response identifies the access token type as
`bearer`; the documented flow has no device-binding field or machine identity.
The access token normally lasts 2,628,000 seconds (about 30 days), while a refresh
token has no time-based expiry. Refreshing returns a new access token and refresh
token and automatically invalidates the old values. The official FAQ additionally
states that reauthorizing the cTrader ID and accounts invalidates the prior refresh
token.

The documentation does not promise independent, simultaneously refreshable token
families for the same app/account. A second authorization might leave an existing
access token usable until another lifecycle event, but that coexistence is not an
authoritative or durable isolation contract. Separate Mac and ASUS tokens therefore
do not provide proven machine isolation; file ownership and separate local storage
are the reliable isolation boundary.

For that reason, no ASUS-specific token was created and no token was refreshed.
The transferred bearer token was retained. On ASUS it is currently accepted as
`accounts` scope, resolves to exactly one confirmed demo account, and passed
application authentication, account authentication, currency resolution, and a
60-symbol read. The refresh token is present, but it was not exercised because
doing so would invalidate the known-working access/refresh pair.

The current code enforces this boundary independently of consent UI:

- `select_demo_account()` requires the API to explicitly report `SCOPE_VIEW` and
  rejects missing or broader scope;
- the production request map contains only authentication and read/subscription
  messages; an order request is rejected before transport; and
- tests cover broader-scope, live-account, ambiguous-account, remote-error,
  response-identity, and order-request rejection.

Future separately authorized demo execution would require a deliberate transition
to `trading` scope plus a reviewed execution request interface and the sizing,
risk, reconciliation, STOP, and recovery contracts. The present view-only guard is
phase-specific, not a statement that demo execution can never be implemented.

Authoritative references:

- [cTrader app and account authentication](https://help.ctrader.com/open-api/account-authentication/)
- [cTrader Open API FAQ](https://help.ctrader.com/open-api/faq/)
- [Python 3.11.14 release](https://www.python.org/downloads/release/python-31114/)
- [Python source build guidance](https://docs.python.org/3/using/unix.html#building-python)

## ASUS network and v2rayN observation

At verification time, the route to `demo.ctraderapi.com` used the `singbox_tun`
interface and routing table 2022, consistent with the active v2rayN system-tunnel
configuration. A listener was present on `127.0.0.1:10808`; outbound HTTPS probes
through that port succeeded as both SOCKS5 and HTTP CONNECT. The cTrader SDK opens
raw TLS sockets and has no explicit application-proxy configuration, so it follows
the operating system TUN route rather than directly addressing port 10808.

The certificate-verified cTrader probe succeeded over that route with TLS 1.3.
Interface names, proxy ports, and routes are observations, not configuration
constants; re-run `mynyra network-check` and inspect the destination route after a
VPN or v2rayN mode change.

## Verification performed on ASUS

| Check | Result |
| --- | --- |
| Exact interpreter and required native modules | PASS — Python 3.11.14 |
| Dependency integrity | PASS — no broken requirements |
| Compile all project/test modules | PASS |
| Focused test suite | PASS — 31 tests |
| Faraz full-data validation | PASS — 81 series, 3,552,511 rows |
| Quote capture hash and full re-summary | PASS — 3,285 rows, median 0.48, p95 0.58 |
| cTrader demo TLS | PASS — TLS 1.3 |
| cTrader application authentication | PASS |
| cTrader view-only demo account read | PASS — `accounts`, USD, 60 symbols |

Successful access proves only that this ASUS environment can perform the current
bounded read workflow. It does not prove strategy quality, profitability, order
execution, fill behavior, unattended recovery, payout eligibility, or cash receipt.

## Remaining Mac/ASUS parity gaps

- The Mac evidence used V2BOX/`utun4`; ASUS uses v2rayN/`singbox_tun`. Both passed
  the bounded read checks, but they are different routing stacks.
- The bearer token is shared private state, not a proven independent per-machine
  token lifecycle. A single refresher and atomic owner-only persistence would be
  required before unattended operation.
- The finite client still has no reconnect/token-refresh workflow and no continuous
  route monitoring.
- The one-hour FIBO quote evidence and Faraz/FIBO feed limitations are unchanged.
- No strategy, simulation, order, fill, slippage, risk engine, or recovery proof was
  added by this parity task.
