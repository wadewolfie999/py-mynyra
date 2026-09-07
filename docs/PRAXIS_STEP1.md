# Praxis Step 1 — research specification and evidence

Completed 2026-09-07 within [the locked sequence](RESEARCH_EXPANSION_SEQUENCE.md).
Step 1 is research and diagnosis; the ten new strategies have not been executed.
April remains sealed, and January–March is explicitly exploratory for future work.

## Deliverables and conclusions

1. [Ten additional candidate specifications](PRAXIS_STEP1_CANDIDATES.md): causal
   entries/exits, time windows, lookbacks, setup lifecycle, source quality,
   overlaps and a proposed future evaluation design. These are proposed exact
   rules for review, not a final Step 4 registration or profitability claims.
2. [SMA diagnostic](PRAXIS_STEP1_SMA.md): four full replays match the original
   frozen results; 692 actual account entry attempts are explained. March's
   $112.29 account/signal improvement comes entirely from sequence changes,
   while development deteriorates. Keep this as an exploratory lead, not an
   established volatility filter.
3. [Data-source assessment](PRAXIS_STEP1_DATA.md): prioritize a bounded Dukascopy
   sample, with HistData fallback and FIBO as the broker-aligned comparison.
   Exact long-history coverage, download reliability and applicable rights still
   need acquisition evidence. No new data is claimed available.

The next authorized sequence stage is the data model and PostgreSQL benchmark
plan/prototype. Its schema and workload must follow these research needs. Service
installation and network configuration require a concrete deployment decision;
no database was installed here. Expanded strategy execution waits until the
end-to-end data/replay/restore proof and final preregistration.

## Verification

The diagnostic loads only the registered pre-April prefix after full normalized
corpus validation. It checks all 672 frozen case hashes, unchanged production
provenance and exact development/March signal/account replay equality. All 692
counterfactuals use the original causal entry and bounded holding horizon;
aggregate counterfactual P&L is not a realizable portfolio.

Completed gate: **75 tests passed**, dependency check passed, compilation passed,
and whitespace checks passed. The private record is
`.local/experiments/praxis_step1_verification_v1.json`. Report links, output
permissions, diagnostic source hash and pre-April cutoff were also checked.

Run the full gate and focused diagnostic tests using Python 3.11:

```sh
PYTHONPATH=src .venv/bin/python -m twisted.trial \
  tests.test_probe tests.test_market tests.test_datasets tests.test_experiment \
  tests.test_sma_diagnostic
PYTHONPATH=src .venv/bin/python -m pip check
PYTHONPATH=src .venv/bin/python -m compileall -q src tests scripts
git diff --check
```

The diagnostic command and evidence hash are in its report. No production source,
frozen protocol/configuration, credentials, broker scope or original evidence
was changed. Private artifacts remain ignored and owner-only. Changes are offered
in an unmerged PR; no database operation, order, spending or live campaign follows
from this report.
