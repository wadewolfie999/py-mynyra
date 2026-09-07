"""Precision and file/query contract tests for the bounded benchmark."""
import importlib.util
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('benchmark_data', Path(__file__).resolve().parents[1] / 'scripts/benchmark-data.py')
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)


class DataBenchmarkTests(unittest.TestCase):
    def test_fixed_exact_and_invalid(self):
        self.assertEqual(bench.fixed(Decimal('1234.567891')), 1234567891)
        for value in ('1.0000001', 'NaN', 'Infinity', '9223372036854.775808'):
            with self.assertRaises(ValueError):
                bench.fixed(Decimal(value))

    def test_file_create_only_and_grouping(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'runs.csv'
            rows = [(0,'sma','signal','completed'), (1,'sma','signal','completed'),
                    (2,'sma','account','failed')]
            bench.write_csv(path, rows)
            with self.assertRaises(FileExistsError):
                bench.write_csv(path, [])
            self.assertEqual(bench.file_results(path),
                             [['sma','account','failed','1'], ['sma','signal','completed','2']])

    def test_sqlite_rejects_duplicates_and_bad_prices(self):
        with bench.sqlite3.connect(':memory:') as db:
            db.executescript(bench.DDL)
            db.execute('INSERT INTO bar_workload VALUES (1,20,30,10,25)')
            with self.assertRaises(bench.sqlite3.IntegrityError):
                db.execute('INSERT INTO bar_workload VALUES (1,20,30,10,25)')
            with self.assertRaises(bench.sqlite3.IntegrityError):
                db.execute('INSERT INTO bar_workload VALUES (2,40,30,10,25)')
