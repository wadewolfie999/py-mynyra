import tempfile
from pathlib import Path
from zipfile import ZipFile

from twisted.trial import unittest

from mynyra.config import ProbeError
from mynyra.datasets import (
    audit_faraz_archives,
    normalize_faraz_archives,
    validate_normalized_faraz,
)


class DatasetAuditTests(unittest.TestCase):
    def test_valid_faraz_csv_is_audited_without_extracting_prn(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "FXCM_XAUUSD/general-platforms/1minute/FXCM_XAUUSD-1minute.csv",
                    "2026.01.01,00:00,100,101,99,100.5,4\n"
                    "2026.01.01,00:01,100.5,102,100,101,0\n",
                )
                archive.writestr(
                    "FXCM_XAUUSD/advanced-get/1minute/FXCM_XAUUSD-1minute.prn",
                    "ignored",
                )
            result = audit_faraz_archives([path])
            self.assertEqual(result["series_count"], 1)
            self.assertEqual(result["row_count"], 2)
            self.assertEqual(result["quality"]["zero_volume_rows"], 1)
            self.assertTrue(result["quality"]["structurally_usable"])
            self.assertEqual(result["archives"][0]["ignored_prn_count"], 1)
            self.assertEqual(len(result["archives"][0]["sha256"]), 64)
            self.assertEqual(result["format"]["timestamp_timezone"], "Asia/Tehran")

    def test_bad_rows_are_reported_and_clock_repeats_are_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "FXCM_EURUSD/general-platforms/60minute/FXCM_EURUSD-60minute.csv",
                    "2022.09.21,23:30,1,2,0.5,1.5,1\n"
                    "2022.09.21,23:30,1.5,1.4,1,1.2,1\n"
                    "not,a,valid,row\n",
                )
            result = audit_faraz_archives([path])
            item = result["series"][0]
            self.assertEqual(item["non_increasing_timestamp_rows"], 1)
            self.assertEqual(item["non_increasing_timestamp_examples"], [{
                "previous": "2022-09-21T23:30",
                "current": "2022-09-21T23:30",
            }])
            self.assertEqual(item["invalid_ohlc_rows"], 1)
            self.assertEqual(item["malformed_rows"], 1)
            self.assertFalse(result["quality"]["structurally_usable"])
            self.assertTrue(result["quality"]["requires_timestamp_normalization"])

    def test_tehran_clock_rollback_is_preserved_as_increasing_utc(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.zip"
            output = Path(folder) / "normalized"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "FXCM_XAUUSD/general-platforms/30minute/FXCM_XAUUSD-30minute.csv",
                    "2022.09.21,22:30,100,101,99,100.5,4\n"
                    "2022.09.21,23:00,100,101,99,100.5,4\n"
                    "2022.09.21,23:30,100,101,99,100.5,4\n"
                    "2022.09.21,23:00,100,101,99,100.5,4\n"
                    "2022.09.21,23:30,100,101,99,100.5,4\n"
                    "2022.09.22,00:00,100,101,99,100.5,4\n",
                )
            result = normalize_faraz_archives([path], output)
            self.assertEqual(result["row_count"], 6)
            self.assertEqual(result["ambiguous_local_rows"], 4)
            self.assertEqual(result["second_fold_rows"], 2)
            self.assertEqual(result["nonexistent_local_rows_shifted_forward"], 0)
            rows = (output / "XAUUSD" / "30minute.csv").read_text().splitlines()
            self.assertEqual(rows[1].split(",")[0], "2022-09-21T18:00:00Z")
            self.assertEqual(rows[5].split(",")[0], "2022-09-21T20:00:00Z")
            self.assertEqual(validate_normalized_faraz(output)["row_count"], 6)
            self.assertRaises(ProbeError, normalize_faraz_archives, [path], output)

    def test_nonexistent_tehran_midnight_is_shifted_through_clock_gap(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.zip"
            output = Path(folder) / "normalized"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "FXCM_XAUUSD/general-platforms/1day/FXCM_XAUUSD-1day.csv",
                    "2022.03.21,00:00,100,101,99,100.5,4\n"
                    "2022.03.22,00:00,100,101,99,100.5,4\n"
                    "2022.03.23,00:00,100,101,99,100.5,4\n",
                )
            result = normalize_faraz_archives([path], output)
            self.assertEqual(result["nonexistent_local_rows_shifted_forward"], 1)
            rows = (output / "XAUUSD" / "1day.csv").read_text().splitlines()
            self.assertEqual(rows[2].split(",")[0], "2022-03-21T20:30:00Z")

    def test_normalized_hash_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.zip"
            output = Path(folder) / "normalized"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "FXCM_EURUSD/general-platforms/1minute/FXCM_EURUSD-1minute.csv",
                    "2026.01.01,00:00,1,2,0.5,1.5,1\n",
                )
            normalize_faraz_archives([path], output)
            with (output / "EURUSD" / "1minute.csv").open("a") as stream:
                stream.write("changed\n")
            self.assertRaises(ProbeError, validate_normalized_faraz, output)

    def test_unsafe_archive_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("../unsafe.csv", "data")
            self.assertRaises(ProbeError, audit_faraz_archives, [path])
