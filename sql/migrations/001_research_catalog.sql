-- Authoritative local SQLite catalog migration. Market data and run artifacts
-- remain immutable files; this database records their identity and relations.
PRAGMA foreign_keys = ON;

CREATE TABLE schema_migration (
    version INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    applied_at_utc TEXT NOT NULL
);

CREATE TABLE source (
    source_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    source_clock TEXT NOT NULL,
    terms_reference TEXT NOT NULL
);

CREATE TABLE instrument (
    instrument_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source(source_id),
    source_symbol TEXT NOT NULL,
    canonical_symbol TEXT NOT NULL,
    price_unit TEXT NOT NULL,
    volume_semantics TEXT NOT NULL,
    UNIQUE(source_id, source_symbol)
);

CREATE TABLE artifact (
    sha256 TEXT PRIMARY KEY CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    relative_path TEXT NOT NULL UNIQUE CHECK (
        relative_path <> '' AND relative_path NOT LIKE '/%' AND
        relative_path NOT LIKE '../%' AND relative_path NOT LIKE '%/../%' AND
        relative_path NOT LIKE '%/..'
    ),
    byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
    media_type TEXT NOT NULL
);

CREATE TABLE dataset_version (
    version_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES instrument(instrument_id),
    parent_version TEXT REFERENCES dataset_version(version_id),
    raw_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
    normalized_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
    transform_sha256 TEXT NOT NULL CHECK (length(transform_sha256) = 64 AND transform_sha256 NOT GLOB '*[^0-9a-f]*'),
    quote_side TEXT NOT NULL CHECK (quote_side IN ('bid', 'ask', 'mid', 'unknown')),
    interval_seconds INTEGER NOT NULL CHECK (interval_seconds > 0),
    label_convention TEXT NOT NULL CHECK (label_convention = 'open'),
    start_utc TEXT NOT NULL,
    end_exclusive_utc TEXT NOT NULL,
    row_count INTEGER NOT NULL CHECK (row_count > 0),
    CHECK (start_utc < end_exclusive_utc),
    CHECK (parent_version IS NULL OR parent_version <> version_id),
    UNIQUE(instrument_id, normalized_sha256, transform_sha256, quote_side, interval_seconds)
);

CREATE TABLE quality_finding (
    version_id TEXT NOT NULL REFERENCES dataset_version(version_id),
    finding_id TEXT NOT NULL,
    check_code TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'reject')),
    evidence_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
    PRIMARY KEY(version_id, finding_id)
);

CREATE TABLE experiment_definition (
    experiment_id TEXT PRIMARY KEY,
    specification_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
    code_sha256 TEXT NOT NULL CHECK (length(code_sha256) = 64 AND code_sha256 NOT GLOB '*[^0-9a-f]*'),
    config_sha256 TEXT NOT NULL REFERENCES artifact(sha256)
);

CREATE TABLE snapshot (
    snapshot_id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL REFERENCES dataset_version(version_id),
    experiment_id TEXT NOT NULL REFERENCES experiment_definition(experiment_id),
    partition_name TEXT NOT NULL,
    access_class TEXT NOT NULL CHECK (access_class IN ('exploratory', 'sealed')),
    start_utc TEXT NOT NULL,
    end_exclusive_utc TEXT NOT NULL,
    export_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
    row_count INTEGER NOT NULL CHECK (row_count > 0),
    CHECK (start_utc < end_exclusive_utc),
    UNIQUE(snapshot_id, experiment_id)
);

CREATE TABLE research_run (
    run_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    partition_name TEXT NOT NULL,
    candidate TEXT NOT NULL,
    scenario TEXT NOT NULL,
    view_name TEXT NOT NULL CHECK (view_name IN ('signal', 'account')),
    result_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
    status TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'open')),
    FOREIGN KEY(snapshot_id, experiment_id) REFERENCES snapshot(snapshot_id, experiment_id),
    UNIQUE(experiment_id, snapshot_id, partition_name, candidate, scenario, view_name)
);
CREATE INDEX research_run_lookup ON research_run(experiment_id, candidate, view_name);

CREATE TRIGGER dataset_parent_same_instrument
BEFORE INSERT ON dataset_version WHEN NEW.parent_version IS NOT NULL
BEGIN
    SELECT CASE WHEN (SELECT instrument_id FROM dataset_version WHERE version_id = NEW.parent_version) <> NEW.instrument_id
        THEN RAISE(ABORT, 'dataset revision parent has another instrument') END;
END;

CREATE TRIGGER snapshot_within_dataset
BEFORE INSERT ON snapshot
BEGIN
    SELECT CASE WHEN NEW.start_utc < (SELECT start_utc FROM dataset_version WHERE version_id = NEW.version_id)
                       OR NEW.end_exclusive_utc > (SELECT end_exclusive_utc FROM dataset_version WHERE version_id = NEW.version_id)
        THEN RAISE(ABORT, 'snapshot is outside dataset coverage') END;
END;

-- Catalog facts are append-only. Correction is a new version or artifact.
CREATE TRIGGER source_no_update BEFORE UPDATE ON source BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER source_no_delete BEFORE DELETE ON source BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER instrument_no_update BEFORE UPDATE ON instrument BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER instrument_no_delete BEFORE DELETE ON instrument BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER artifact_no_update BEFORE UPDATE ON artifact BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER artifact_no_delete BEFORE DELETE ON artifact BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER version_no_update BEFORE UPDATE ON dataset_version BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER version_no_delete BEFORE DELETE ON dataset_version BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER finding_no_update BEFORE UPDATE ON quality_finding BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER finding_no_delete BEFORE DELETE ON quality_finding BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER experiment_no_update BEFORE UPDATE ON experiment_definition BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER experiment_no_delete BEFORE DELETE ON experiment_definition BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER snapshot_no_update BEFORE UPDATE ON snapshot BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER snapshot_no_delete BEFORE DELETE ON snapshot BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER run_no_update BEFORE UPDATE ON research_run BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
CREATE TRIGGER run_no_delete BEFORE DELETE ON research_run BEGIN SELECT RAISE(ABORT, 'catalog is append-only'); END;
