# Reproduce the offline comparison

The [preregistered protocol](XAUUSD_COMPARISON_PROTOCOL.md) and
[`xauusd_m1_v1.toml`](../experiments/xauusd_m1_v1.toml) define this experiment.
Rules were committed before historical results. Use the supported Python 3.11.14
environment and the independently validated, owner-only normalized archive under
ignored `.local/data/faraz/normalized_utc_20260904/`. The tool verifies the exact
registered XAUUSD M1 hash plus the full normalized-data manifest before any run.
It requires no credentials and has no network or order operation.

On this Codex worktree `.venv` points to the already prepared main-checkout venv;
the data is a separate private copy. `PYTHONPATH=src` explicitly selects this
worktree's source. No installation or writes into the shared venv are necessary.
Elsewhere, create a normal local venv using the repository setup instructions.
These commands work with either arrangement:

```sh
PYTHONPATH=src .venv/bin/python -m twisted.trial tests.test_probe tests.test_market tests.test_datasets tests.test_experiment
PYTHONPATH=src .venv/bin/python -m pip check
PYTHONPATH=src .venv/bin/python -m compileall -q src tests
PYTHONPATH=src .venv/bin/mynyra faraz-validate --input-dir .local/data/faraz/normalized_utc_20260904
git diff --check

PYTHONPATH=src .venv/bin/python -m mynyra.experiment screen --output .local/experiments/screen_v1
PYTHONPATH=src .venv/bin/python -m mynyra.experiment freeze --screen .local/experiments/screen_v1 --output .local/experiments/finalists_v1.json
PYTHONPATH=src .venv/bin/python -m mynyra.experiment report --screen .local/experiments/screen_v1 --output .local/experiments/aggregates_v1.json
```

Do not reuse an existing output name. A partial run remains evidence of an
interrupted/failed attempt; a complete run has `index.json`. Registration and
each result file are hashed, owner-only and create-only. Progress output contains
only run counts. Full trade ledgers and daily series stay private. The aggregate
export deliberately omits trade prices, timestamps, candle rows and ledgers; use
it for the reviewed decision report.

Before evaluating, commit a sanitized finalist-freeze record with the manifest
hash, protocol/implementation hashes, selection result and all candidate decisions.
That Git checkpoint supplies the temporal audit; filesystem checks alone cannot
prevent someone deliberately rewriting both code and evidence. The evaluation
command revalidates screen coverage, file hashes, provenance and finalist selection.

With no finalists, leave April sealed and record the explicit skip:

```sh
PYTHONPATH=src .venv/bin/python -m mynyra.experiment evaluate --screen .local/experiments/screen_v1 --freeze .local/experiments/finalists_v1.json --output .local/experiments/evaluation_skipped_v1.json
```

With finalists, use a fresh directory instead of a JSON filename:

```sh
PYTHONPATH=src .venv/bin/python -m mynyra.experiment evaluate --screen .local/experiments/screen_v1 --freeze .local/experiments/finalists_v1.json --output .local/experiments/evaluation_v1
PYTHONPATH=src .venv/bin/python -m mynyra.experiment report --screen .local/experiments/evaluation_v1 --output .local/experiments/evaluation_aggregates_v1.json
```

No variant or rescue tuning is permitted after results. A defect correction must
invalidate the affected evidence explicitly and use new artifact names. If April
has influenced the correction, it no longer supplies untouched evaluation data.
Independent reproduction uses the same commands with fresh output names. Compare
every result-file SHA-256; registration metadata and indices are deterministic too.
No system-clock timestamp is part of the numerical output.

## Scope of the model

Bar timestamps are **treated as** minute-open labels. Stop triggers are reference-
price barriers mapped to hypothetical bid/ask sides; real bid/ask trigger semantics
and execution gaps remain unverified. Costs are scenarios, not historical fills.
Modeled excursions and drawdown use an adverse-first within-bar convention; they
are not observations of intrabar order. A bar that passes a floor beyond its
modeled stop is flagged as uncertain, and an open position over missing minutes
cannot advance as proven safe. Account failure liquidations use an adverse observed
bound rather than claiming an exact unavailable threshold fill.

Daily net figures attribute a complete trade to its exit date for block-bootstrap
diagnostics; account loss checks separately include entry fees, swaps and open
liquidation equity. A stage reset is a virtual accounting event, never cash received.
The one-ounce signal portfolio is unconstrained and can continue after losses that
would end a modeled account. Account skip/failure counts explain that difference.

Recovery is local: retain the original data and previous evidence, fix/review the
small source change, rerun synthetic tests, and create a new run directory. To
discard development, leave this unmerged branch; no broker or system configuration
rollback is needed. Do not merge automatically.
