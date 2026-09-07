# Praxis Step 2 — catalog and storage benchmark

This operation follows [Praxis](PRAXIS.md) and the
[agreed sequence](RESEARCH_EXPANSION_SEQUENCE.md). The Step 1 research exists in
PR #8, which was still open when this branch was created from current main.
Step 2 does not execute the new candidates or expose April prices.

## Knowledge ownership and proposed model

[Executable PostgreSQL schema](../sql/research-catalog.sql) defines the catalog:

| Relation | Knowledge owned |
| --- | --- |
| source | Provider identity, declared clock, terms evidence reference |
| instrument | Source-specific symbol, canonical mapping, price units, volume semantics |
| artifact | SHA-256 identity, private relative path, bytes, media type |
| dataset_version | Instrument, raw/normalized/transform hashes, side, interval, coverage, parent revision |
| quality_finding | Version-specific check outcome and evidence artifact |
| experiment_definition | Registered specification, code and configuration identity |
| snapshot | Version, experiment, chronological partition, access class and frozen export |
| research_run | Exact experiment/snapshot/candidate/scenario/view identity and result artifact |

Use UTC instants and preserve the source's original clock metadata. Unknown quote
side stays unknown; no assumption turns Faraz prices into bid/ask. Corrected inputs
create a new dataset version and new snapshot. Files own original and normalized
content, simulation inputs and ledgers; the catalog owns references and relationships.
Derived metrics must retain result-artifact identity and a versioned derivation.

The schema is a prototype, not a deployed ingestion API. Step 3 must implement and
prove append-only privileges, artifact path containment/hash checks, snapshot bounds
within parent coverage, revision lineage consistency, atomic import publication and
idempotency. A SHA hash alone does not prove semantic correctness. Import staging
must remain invisible until all validation and manifest checks pass.

Sealed data must live outside the exploratory export/credential boundary. A table
column named `sealed`, or a conventional WHERE filter, does not enforce access.
The benchmark imports only the pre-April prefix. Production research must have
neither SQL privileges nor filesystem access to reserved prices; owners/admins can
bypass ordinary database permissions and need a separate operational seal procedure.
No production roles or access enforcement are claimed complete here.

## Comparison contract

[scripts/benchmark-data.py](../scripts/benchmark-data.py) validates the existing
81-series corpus and frozen 672-case screen, then benchmarks only pre-April XAUUSD
M1 price rows and existing run status summaries. No new strategy result is computed.
The source reader stops at April before converting price fields.

The optional price-table experiment uses integer Unix seconds and integer prices
scaled by 1,000,000. Conversion rejects lost precision and signed-64-bit overflow;
this is an explicit bounded workload format, not a universal tick schema. Volume
is excluded from this price-read workload, not reinterpreted. Future instruments
need an explicit precision contract before import.

Workloads: one durable ingestion into fresh CSV files / SQLite / PostgreSQL;
five reads of 2026-03-02 UTC [00:00, next midnight); five grouped result-status
queries by candidate and view; full ordered price round-trip equality; file and
indexed relation storage. Timings include Python CSV parsing, SQLite connection
reuse, or one fresh `psql` process/connection per PostgreSQL query. Thus this is an
operator-workflow comparison, not a pure database-engine microbenchmark. No cold
cache clearing is attempted. Report all repetitions; single-ingest timing is noisy.
PostgreSQL ANALYZE occurs before reads and outside ingestion timing. PostgreSQL
startup, schema creation and original input validation are outside timed ingestion.

The CSV baseline is a canonical pre-April export plus a compact run-summary file.
It does not rescan all original ledgers for every query. PostgreSQL and SQLite
receive the same already-validated in-memory rows. Each database ingestion includes
indexes and commit; file ingestion includes fsync. This workload is too small to
predict multi-year or tick-scale throughput or concurrent writers.

## Resource and lifecycle contract

The user installed PostgreSQL 16 after a read-only package dry run. The installer
also created an online default cluster; the benchmark does not connect to it.
It creates a separate owner-only cluster beneath ignored `.local/`, uses peer
Unix-socket authentication, disables TCP listening, sets shared buffers to 32 MiB
and limits connections to five. Each command has a 120-second timeout, startup and
shutdown have 30-second limits, and preflight requires at least 2 GiB free.
The stopped cluster and private logs remain as create-only evidence. No system
service configuration, Docker permissions or credentials are changed by the script.

Reproduce from the repository root with a fresh, short output-directory name:

```sh
PYTHONPATH=src .venv/bin/python scripts/benchmark-data.py --output .local/b2_repeat
```

Dependencies: the existing Python 3.11 environment and PostgreSQL 16 binaries.
Missing binaries cause a preflight failure; the script never installs packages.
When interactive installation or authentication is needed, provide the owner the
exact checked command immediately and verify the result afterward, as
[Praxis requires](PRAXIS.md).

Recovery: ordinary completion/error shuts down the private cluster. After a hard
process kill, inspect its private `server.log` and use the recorded directory with
`/usr/lib/postgresql/16/bin/pg_ctl -D <absolute-private-cluster-path> -m fast -w stop`.
Do not apply that command to the system cluster. Keep the report and artifacts;
retries use a new output directory. Full backup/restore and artifact reconciliation
belong to Step 3 and remain completion requirements before expanded experiments.

## Measured outcome and integration decision

Completed 2026-09-07 on this ASUS host: PostgreSQL 16.15, SQLite 3.45.1,
69,846 bars and 672 run summaries. The range contained 1,379 bars; the result
query produced 15 groups. Full ordered price rows and both query outputs matched
exactly across all three representations.

| Workload | CSV | SQLite | PostgreSQL |
| --- | ---: | ---: | ---: |
| Durable ingestion, one run | 560 ms | 723 ms | 1,253 ms |
| Range read, median of five | 635 ms | 13.2 ms | 48.1 ms |
| Result grouping, median of five | 1.23 ms | 0.73 ms | 46.7 ms |
| Workload files / indexed relations | 3,931,252 B | 3,870,720 B | 6,463,488 B |

The stopped PostgreSQL cluster occupied 47,185,920 allocated bytes in total.
The private report retains each timing, not only medians. These measurements
support indexed range access at this scale; they do not establish a universal
SQLite/PostgreSQL speed ranking because connection handling differs. One ingest
sample and warm local reads do not establish production capacity or reliability.

**Decision: use SQLite for the first local catalog integration in Step 3; retain
immutable market files and frozen exports.** Do not duplicate the entire market
archive into a production bar table yet. SQLite provides the needed relational
constraints without another running service for the current single-user workflow.
The PostgreSQL schema is a tested design prototype; Step 3 must translate its
contracts into one authoritative SQLite migration, not maintain parallel production
schemas. This is an evidence-based choice within Step 2's explicitly allowed
SQLite alternative, not a change to the four-stage dependency order.

Reconsider PostgreSQL when concurrent writers, independently authenticated users,
or remote catalog access become real requirements. Then benchmark persistent
connections and representative concurrency before committing to deployment.
DuckDB/Parquet and TimescaleDB add no demonstrated benefit in this workload and
remain deferred. Installing PostgreSQL made the comparison possible; it does not
commit Mynyra to running a production PostgreSQL service.

For Step 3, budget originals + normalized files + immutable exports + catalog +
one separately verified backup, with a minimum 2 GiB working reserve for this
bounded proof. Measure actual backup/copy footprints before expanding history.
SQLite backup must use its consistent backup interface (or a verified quiescent
copy), followed by isolated restore and hash reconciliation of every referenced
artifact. Rollback keeps the original file-only simulation path usable. Do not
remove originals or treat the stopped benchmark cluster as a production backup.

Verification: **74 tests passed**, dependency check, compilation and whitespace
checks passed. PostgreSQL executed the catalog DDL and rejected duplicate bars,
invalid OHLC, malformed artifact hashes and orphan instrument references. Full
existing corpus validation and all 672 frozen result hash/identity checks passed.
The isolated benchmark cluster stopped cleanly. No new candidate, order, shadow
campaign or sealed-period analysis ran. Step 3's import/export/baseline/restore
proof remains outstanding; this prototype is not an integrated production catalog.

Private evidence: `.local/b2_v2/report.json`, with script hash recorded inside it.
The first attempt (`.local/b2_v1`) failed before database startup because the script
used an incorrect input filename; it was corrected to use the authoritative
registered input loader. Its output was preserved rather than overwritten.

## Sources

PostgreSQL documents [initdb authentication](https://www.postgresql.org/docs/16/app-initdb.html),
[connection/socket settings](https://www.postgresql.org/docs/16/runtime-config-connection.html)
and [relation-size accounting](https://www.postgresql.org/docs/16/functions-admin.html).
The prototype measures indexed relation bytes separately from the whole cluster,
which also includes catalog, WAL and initialization overhead.
