# Praxis Step 3 — one frozen data-to-result path

This increment translates the Step 2 PostgreSQL prototype contracts into one
authoritative SQLite migration at
[`sql/migrations/001_research_catalog.sql`](../sql/migrations/001_research_catalog.sql).
The catalog owns source, instrument, immutable artifact, explicit dataset-version,
validation finding, experiment, snapshot and run identities, including each run's
chronological partition. It does not own a
production bar table and it is never a simulator input.

## Contract

The bounded proof script imports the validated Faraz XAUUSD M1 version, freezes
the exact pre-April CSV lines, and runs the existing registered baseline only from
that frozen export. It validates the complete normalized corpus before import, and
the frozen replay stops at `2026-04-01T00:00:00+00:00`; no April price is parsed.
The script retains both the untouched file-only baseline and the original files.

The catalog checks artifact containment, owner-only regular files, SHA-256 and
byte count. SQLite foreign keys, append-only triggers, same-instrument revision
checks and snapshot-within-dataset triggers protect relationships. Repeating an
identical import is idempotent; a correction must be a new version with a distinct
normalized artifact and an explicit parent. An injected pre-commit interruption
rolls back all staged catalog facts.

The proof uses SQLite's backup interface, copies every referenced immutable
artifact to the backup, then restores the database and artifact tree to a distinct
private directory. It verifies every restored path, byte count and SHA-256.

## Completed evidence — 2026-09-07

The private v3 proof completed with the following bounded results:

| Check | Result |
| --- | --- |
| Imported version | `faraz-xauusd-m1-20260904-r1`; first import created it and an identical retry returned the existing version |
| Explicit correction behavior | Focused test created a distinct `v2` normalized artifact with `v1` as its parent; reusing `v1` with changed content was rejected |
| Interrupted import | Injected pre-commit failure rolled back source, instrument, artifact, dataset-version and quality-finding rows to zero |
| Frozen export | 69,846 exact CSV rows from 2026-01-20 03:59 through 2026-03-31 23:59 UTC; two exports matched SHA-256 `82cd15e0f5a9394d1327591c58e93a7d2977edbde470022e82c2d7685b9f9554` |
| Unchanged baseline reconciliation | All 672 result artifacts matched the committed historical screen index hash `5454250a38b492b511ba478ed23c84ccb1bdde3b3a2d9e3bc1e5ce460c3f0ff0` |
| Backup and isolated restore | 678 catalog references reconciled by path, byte count and SHA-256 in the original, backup and isolated restored trees; backup footprint was 112,145,279 bytes |

The completed private report hash is
`57fe13814db37470572f4ba91fcd666152c04589bbf293d338222a3e143fa258`.
Earlier interrupted outputs were retained rather than overwritten: one exposed a
raw-archive mapping defect, and one exposed an omitted chronological run-key
dimension. Both corrections are covered by the final migration and proof.

## Reproduction

Use a fresh output name; outputs are create-only and owner-only:

```sh
PYTHONPATH=src .venv/bin/python scripts/praxis-step3.py \
  --output .local/praxis_step3_proof_<new-name>
```

The existing file-only workflow remains the rollback path. It needs neither the
SQLite catalog nor a database query to reproduce the original baseline. A failed
or interrupted proof is retained under `.local/`; correct the cause and use a new
output directory.

## Limits

This is a local single-user integrity/recovery proof, not an access-control
boundary against the machine owner. SQLite cannot by itself seal April from an
owner who can read the filesystem; the frozen export and runner input boundary are
the demonstrated protection here. The result does not run new candidates, revise
strategy economics, acquire history, contact a broker, capture quotes or place
orders. The Faraz source's historical quote side and intraminute order remain
unknown, so the existing model limitations still apply.
