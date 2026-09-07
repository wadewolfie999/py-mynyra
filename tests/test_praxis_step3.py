"""Mechanical proof helpers preserve the exact frozen CSV boundary."""

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "praxis_step3", Path(__file__).resolve().parents[1] / "scripts/praxis-step3.py"
)
step3 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(step3)


class PraxisStep3Tests(unittest.TestCase):
    def test_snapshot_keeps_exact_pre_april_timestamp_and_price_text(self):
        header = "timestamp_utc,open,high,low,close,volume\n"
        march = "2026-03-31T23:59:00Z,2345.678900,2346.000001,2345.000009,2345.100010,7\n"
        april = "2026-04-01T00:00:00Z,9999,9999,9999,9999,0\n"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.csv"
            export = root / "export.csv"
            repeat = root / "repeat.csv"
            source.write_text(header + march + april, encoding="utf-8", newline="")
            proof = step3.snapshot(source, export)
            repeated = step3.snapshot(source, repeat)
            self.assertEqual(export.read_bytes(), (header + march).encode())
            self.assertEqual(proof["row_count"], 1)
            self.assertTrue(proof["exact_csv_lines"])
            self.assertEqual(proof["export_sha256"], repeated["export_sha256"])
            self.assertEqual(proof["export_sha256"], hashlib.sha256(export.read_bytes()).hexdigest())
