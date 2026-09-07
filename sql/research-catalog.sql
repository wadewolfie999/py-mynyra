-- PostgreSQL prototype, applied only to a new isolated benchmark database.
-- Immutable artifacts remain files. These tables own catalog identity, not prices.
CREATE TABLE source (
 source_id TEXT PRIMARY KEY,
 provider TEXT NOT NULL, source_clock TEXT NOT NULL,
 terms_reference TEXT NOT NULL
);
CREATE TABLE instrument (
 instrument_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source,
 source_symbol TEXT NOT NULL, canonical_symbol TEXT NOT NULL,
 price_unit TEXT NOT NULL, volume_semantics TEXT NOT NULL,
 UNIQUE(source_id, source_symbol)
);
CREATE TABLE artifact (
 sha256 TEXT PRIMARY KEY CHECK (sha256 ~ '^[0-9a-f]{64}$'),
 relative_path TEXT NOT NULL UNIQUE CHECK
  (relative_path !~ '(^/|(^|/)\.\.(/|$))'),
 byte_count BIGINT NOT NULL CHECK (byte_count >= 0),
 media_type TEXT NOT NULL
);
CREATE TABLE dataset_version (
 version_id TEXT PRIMARY KEY,
 instrument_id TEXT NOT NULL REFERENCES instrument,
 parent_version TEXT REFERENCES dataset_version,
 raw_sha256 TEXT NOT NULL REFERENCES artifact,
 normalized_sha256 TEXT NOT NULL REFERENCES artifact,
 transform_sha256 TEXT NOT NULL CHECK (transform_sha256 ~ '^[0-9a-f]{64}$'),
 quote_side TEXT NOT NULL CHECK (quote_side IN ('bid','ask','mid','unknown')),
 interval_seconds INTEGER NOT NULL CHECK (interval_seconds > 0),
 label_convention TEXT NOT NULL CHECK (label_convention = 'open'),
 start_utc TIMESTAMPTZ NOT NULL, end_exclusive_utc TIMESTAMPTZ NOT NULL,
 row_count BIGINT NOT NULL CHECK (row_count > 0),
 CHECK (start_utc < end_exclusive_utc),
 CHECK (parent_version IS NULL OR parent_version <> version_id),
 UNIQUE(instrument_id, normalized_sha256, transform_sha256, quote_side, interval_seconds)
);
CREATE TABLE quality_finding (
 version_id TEXT NOT NULL REFERENCES dataset_version,
 finding_id TEXT NOT NULL, check_code TEXT NOT NULL,
 severity TEXT NOT NULL CHECK (severity IN ('info','warning','reject')),
 evidence_sha256 TEXT NOT NULL REFERENCES artifact,
 PRIMARY KEY(version_id, finding_id)
);
CREATE TABLE experiment_definition (
 experiment_id TEXT PRIMARY KEY,
 specification_sha256 TEXT NOT NULL REFERENCES artifact,
 code_sha256 TEXT NOT NULL CHECK (code_sha256 ~ '^[0-9a-f]{64}$'),
 config_sha256 TEXT NOT NULL REFERENCES artifact
);
CREATE TABLE snapshot (
 snapshot_id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES dataset_version,
 experiment_id TEXT NOT NULL REFERENCES experiment_definition,
 partition_name TEXT NOT NULL,
 access_class TEXT NOT NULL CHECK (access_class IN ('exploratory','sealed')),
 start_utc TIMESTAMPTZ NOT NULL, end_exclusive_utc TIMESTAMPTZ NOT NULL,
 export_sha256 TEXT NOT NULL REFERENCES artifact,
 CHECK (start_utc < end_exclusive_utc),
 UNIQUE(snapshot_id, experiment_id)
);
CREATE TABLE research_run (
 run_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiment_definition,
 snapshot_id TEXT NOT NULL, candidate TEXT NOT NULL, scenario TEXT NOT NULL,
 view_name TEXT NOT NULL CHECK (view_name IN ('signal','account')),
 result_sha256 TEXT NOT NULL REFERENCES artifact,
 status TEXT NOT NULL CHECK (status IN ('completed','failed','open')),
 FOREIGN KEY(snapshot_id, experiment_id) REFERENCES snapshot(snapshot_id, experiment_id),
 UNIQUE(experiment_id, snapshot_id, candidate, scenario, view_name)
);
CREATE INDEX research_run_lookup ON research_run(experiment_id, candidate, view_name);
-- No application grants: this prototype is not a production security boundary.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
