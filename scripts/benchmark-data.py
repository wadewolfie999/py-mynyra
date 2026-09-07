#!/usr/bin/env python3
"""Bounded file/SQLite/PostgreSQL comparison; no installs or existing DB access."""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import statistics
import subprocess
import time

from mynyra.experiment import DEFAULT_CONFIG, inputs, load_runs, provenance, screen_cases, settings

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = datetime(2026, 4, 1, tzinfo=timezone.utc)
SCALE = 1_000_000
DDL = """
CREATE TABLE bar_workload (
 stamp BIGINT PRIMARY KEY, o BIGINT NOT NULL, h BIGINT NOT NULL,
 l BIGINT NOT NULL, c BIGINT NOT NULL,
 CHECK(l > 0 AND l <= o AND o <= h AND l <= c AND c <= h));
CREATE TABLE run_workload (
 run_id INTEGER PRIMARY KEY, candidate TEXT NOT NULL,
 view_name TEXT NOT NULL, status TEXT NOT NULL);
CREATE INDEX run_lookup ON run_workload(candidate, view_name, status);
"""
RANGE = "SELECT * FROM bar_workload WHERE stamp >= 1772409600 AND stamp < 1772496000 ORDER BY stamp"
RESULTS = "SELECT candidate, view_name, status, count(*) FROM run_workload GROUP BY candidate, view_name, status ORDER BY candidate, view_name, status"


def fixed(value):
    scaled = value * SCALE
    if not scaled.is_finite() or scaled != scaled.to_integral_value() or abs(scaled) >= 2**63:
        raise ValueError("Price outside exact fixed-point contract")
    return int(scaled)


def measured(call, repeats=5):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        result = call()
        times.append(time.perf_counter() - start)
    return result, {"seconds": times, "median_seconds": statistics.median(times)}


def write_csv(path, rows):
    with path.open('x', newline='') as stream:
        csv.writer(stream).writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.reader(stream))


def file_results(path):
    groups = {}
    for _, candidate, view, status in read_csv(path):
        key = (candidate, view, status)
        groups[key] = groups.get(key, 0) + 1
    return [list(k) + [str(v)] for k, v in sorted(groups.items())]


def stringify(rows):
    return [[str(v) for v in row] for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--pg-bin', type=Path, default=Path('/usr/lib/postgresql/16/bin'))
    args = parser.parse_args()
    # Create-only private evidence, including server logs and retained stopped cluster.
    private = (ROOT / '.local').resolve()
    target = args.output.absolute()
    if target.is_symlink() or not target.resolve().is_relative_to(private) or target.exists():
        parser.error('output must be a new directory below repository .local')
    for name in ('initdb', 'pg_ctl', 'psql'):
        if not (args.pg_bin / name).is_file():
            parser.error('PostgreSQL binaries missing; install before running')
    if shutil.disk_usage(private).free < 2 * 1024**3:
        parser.error('at least 2 GiB free required')
    os.umask(0o077)
    target.mkdir(mode=0o700, parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
    env['LC_ALL'] = 'C'
    pg = target / 'cluster'
    sock = target / 'socket'
    sock.mkdir(mode=0o700)
    if len(str(sock)) > 85:
        parser.error('output path too long for PostgreSQL Unix socket')
    log = (target / 'commands.log').open('x')

    def command(name, *argv, sql=None):
        result = subprocess.run([str(args.pg_bin / name), *argv], input=sql,
                                text=True, stdout=subprocess.PIPE, stderr=log,
                                env=env, timeout=120)
        if result.returncode:
            raise RuntimeError('PostgreSQL command failed; inspect private commands.log')
        return result.stdout

    def query(sql):
        return command('psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-h', str(sock),
                       '-p', '55432', '-d', 'postgres', sql=sql)

    started = False
    try:
        dataset = ROOT / '.local/data/faraz/normalized_utc_20260904'
        candles, proof = inputs(dataset / 'XAUUSD/1minute.csv', settings(DEFAULT_CONFIG), CUTOFF)
        bars = [(int(c.time.timestamp()), *(fixed(p) for p in (c.open,c.high,c.low,c.close))) for c in candles]
        _, original = load_runs(ROOT / '.local/experiments/screen_v1',
                                provenance(DEFAULT_CONFIG), screen_cases(settings(DEFAULT_CONFIG)))
        runs = [(i, r['candidate'], r['view'], r['status']) for i, r in enumerate(original.values())]
        report = {'schema_version': 1, 'rows': len(bars), 'runs': len(runs),
                  'cutoff_exclusive': CUTOFF.isoformat(), 'scale': SCALE,
                  'validation': proof, 'sqlite_version': sqlite3.sqlite_version,
                  'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        _, report['file_ingest'] = measured(lambda: (write_csv(target/'bars.csv', bars), write_csv(target/'runs.csv', runs)), 1)
        file_range, report['file_range'] = measured(lambda: [r for r in read_csv(target/'bars.csv') if 1772409600 <= int(r[0]) < 1772496000])
        file_groups, report['file_results'] = measured(lambda: file_results(target/'runs.csv'))
        with sqlite3.connect(target/'benchmark.sqlite') as db:
            db.execute('PRAGMA synchronous=FULL')
            def ingest():
                db.executescript(DDL)
                db.executemany('INSERT INTO bar_workload VALUES (?,?,?,?,?)', bars)
                db.executemany('INSERT INTO run_workload VALUES (?,?,?,?)', runs)
                db.commit()
            _, report['sqlite_ingest'] = measured(ingest, 1)
            sql_range, report['sqlite_range'] = measured(lambda: stringify(db.execute(RANGE).fetchall()))
            sql_groups, report['sqlite_results'] = measured(lambda: stringify(db.execute(RESULTS).fetchall()))
            assert sql_range == file_range and sql_groups == file_groups
            assert stringify(db.execute('SELECT * FROM bar_workload ORDER BY stamp').fetchall()) == stringify(bars)
        command('initdb', '-D', str(pg), '--auth-local=peer', '--auth-host=reject', '--no-locale', '--encoding=UTF8')
        command('pg_ctl', '-D', str(pg), '-l', str(target/'server.log'), '-w', '-t', '30',
                '-o', f"-c listen_addresses='' -c unix_socket_directories='{sock}' -c port=55432 -c shared_buffers=32MB -c max_connections=5", 'start')
        started = True
        query((ROOT/'sql/research-catalog.sql').read_text())
        def pg_ingest():
            parts = ['BEGIN;', DDL]
            for table, rows in [('bar_workload', bars), ('run_workload', runs)]:
                stream = io.StringIO()
                csv.writer(stream, lineterminator='\n').writerows(rows)
                parts += [f'COPY {table} FROM STDIN WITH (FORMAT csv);', stream.getvalue() + '\\.']
            parts += ['COMMIT;']
            query('\n'.join(parts))
        _, report['postgres_ingest'] = measured(pg_ingest, 1)
        query('ANALYZE bar_workload; ANALYZE run_workload;')
        def pg_rows(statement):
            return list(csv.reader(io.StringIO(query(f'COPY ({statement}) TO STDOUT WITH (FORMAT csv);'))))
        pg_range, report['postgres_range'] = measured(lambda: pg_rows(RANGE))
        pg_groups, report['postgres_results'] = measured(lambda: pg_rows(RESULTS))
        assert pg_range == file_range and pg_groups == file_groups
        assert pg_rows('SELECT * FROM bar_workload ORDER BY stamp') == stringify(bars)
        query('''DO $$ BEGIN
          BEGIN
            INSERT INTO bar_workload SELECT * FROM bar_workload LIMIT 1;
            RAISE EXCEPTION 'duplicate bar unexpectedly accepted';
          EXCEPTION WHEN unique_violation THEN NULL; END;
          BEGIN
            INSERT INTO bar_workload VALUES (0,40,30,10,25);
            RAISE EXCEPTION 'invalid OHLC unexpectedly accepted';
          EXCEPTION WHEN check_violation THEN NULL; END;
          BEGIN
            INSERT INTO artifact VALUES ('invalid','sample',1,'text/plain');
            RAISE EXCEPTION 'invalid hash unexpectedly accepted';
          EXCEPTION WHEN check_violation THEN NULL; END;
          BEGIN
            INSERT INTO instrument VALUES ('missing','absent','XAU','XAUUSD','USD/oz','unknown');
            RAISE EXCEPTION 'orphan instrument unexpectedly accepted';
          EXCEPTION WHEN foreign_key_violation THEN NULL; END;
        END $$;''')
        report['postgres_rejections'] = ['duplicate_bar', 'invalid_ohlc', 'invalid_hash', 'orphan_instrument']
        report['postgres_version'] = pg_rows('SELECT version()')[0][0]
        report['postgres_relation_bytes'] = int(pg_rows("SELECT pg_total_relation_size('bar_workload') + pg_total_relation_size('run_workload')")[0][0])
        report['file_bytes'] = sum((target/f).stat().st_size for f in ('bars.csv','runs.csv'))
        report['sqlite_bytes'] = (target/'benchmark.sqlite').stat().st_size
        report['range_rows'] = len(file_range)
        report['result_groups'] = len(file_groups)
        report['equality'] = 'full bars and both query outputs match'
        command('pg_ctl', '-D', str(pg), '-m', 'fast', '-w', '-t', '30', 'stop')
        started = False
        report['cluster_stopped'] = True
        report['cluster_allocated_bytes'] = sum(p.stat().st_blocks*512 for p in pg.rglob('*') if p.is_file())
        with (target/'report.json').open('x') as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
        print(json.dumps({k:v for k,v in report.items() if k != 'validation'}, indent=2))
    finally:
        if started or (pg / 'postmaster.pid').exists():
            command('pg_ctl', '-D', str(pg), '-m', 'fast', '-w', '-t', '30', 'stop')
        log.close()


if __name__ == '__main__':
    main()
