# Praxis Step 4 — expanded exploratory comparison

The approved batch is specified in [the frozen protocol](PRAXIS_STEP4_PROTOCOL.md)
and `experiments/praxis_step4_v1.toml`. P01–P10 are ten additional specifications,
not ten independent economic effects. Unchanged SMA and no-trade are baselines.
January–March is exploratory. April remains sealed; evaluation is unavailable.

## Reproduction

Use Python 3.11.14 and the matching private inputs named in the registry. The
committed `experiments/praxis_step4_source.json` binds numerical source and the
exact 1,344-case inventory. Source/protocol/configuration changes invalidate it.
Do not regenerate that manifest to legitimize already observed results.

From a clean checkout of the frozen implementation, choose new private names:

```sh
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py baseline \
  --output .local/praxis_step4_baseline_repeat
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py run \
  --baseline .local/praxis_step4_baseline_repeat \
  --output .local/praxis_step4_screen_repeat
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py run \
  --baseline .local/praxis_step4_baseline_repeat \
  --output .local/praxis_step4_replay_repeat
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py verify \
  --screen .local/praxis_step4_screen_repeat \
  --replay .local/praxis_step4_replay_repeat \
  --output .local/praxis_step4_verified_repeat
PYTHONPATH=src .venv/bin/python scripts/praxis-step4.py evaluate \
  --output .local/praxis_step4_evaluation_skipped_repeat.json
```

The baseline command must reconcile all 672 original numerical artifacts before
expanded execution. The run command checks that evidence against the same freeze.
Each pass is limited to two hours and requires at least 2 GiB free; a timeout or
exception retains incomplete evidence. An index is published only after all cases
complete. A modeled account loss is an outcome, not a runner exception.

Verify performs independent ledger accounting, exact replay comparison, fixed
bootstrap diagnostics, SMA attribution, and SQLite backup/isolated restore. Its
aggregate report contains no candle prices, trade timestamps or ledgers. Full
private recovery includes numerical-source artifacts. SQLite remains a catalog;
only the frozen CSV enters simulation. Original catalogs and evidence are retained.

Evaluation has no price-loading path: it writes only the explicit skip. Commit
the empty advancement record and report without opening April. A future data or
strategy change requires a new registered experiment, not an edited old result.

Synthetic checks require no private market inputs:

```sh
PYTHONPATH=src .venv/bin/python -m twisted.trial tests/test_*.py
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q src tests scripts
git diff --check
```

Use fresh names after interruption. Retain the failed directory, commit and
explain any code defect before rerunning. Returning to the prior unmerged branch
restores the original file workflow; no broker or system service was modified.
