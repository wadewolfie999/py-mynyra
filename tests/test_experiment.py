"""Synthetic evidence for causal rules, execution and experiment seal contracts."""

import copy
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from twisted.trial import unittest

from mynyra.config import ProbeError
from mynyra.datasets import Candle, read_normalized_minutes, archive_sha256
from mynyra.experiment import (DEFAULT_CONFIG, evaluation_cases, freeze, inputs,
                               lower_expectancy, main, private_path, provenance,
                               read_private, save, screen_cases, select, settings,
                               load_runs, run_cases)
from mynyra.simulation import Costs, position_size, simulate
from mynyra.strategies import Decision, decisions

D = Decimal
START = datetime(2026, 3, 2, 6, tzinfo=timezone.utc)


def candle(minute=0, o="100", h=None, l=None, c=None, start=START):
    return Candle(start + timedelta(minutes=minute), D(o), D(h or o), D(l or o), D(c or o))


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.cfg = settings(DEFAULT_CONFIG)
        self.cost = Costs(D("0.48"), D("0.05"), "mid", D("0.00003"), D("0.01"))

    def run_case(self, bars, signals, view="signal", name="sma_cross"):
        return simulate(bars, signals, name, self.cfg, self.cost, view,
                        bars[0].time, bars[-1].time + timedelta(minutes=1))

    def test_long_next_open_costs_reconcile_by_hand(self):
        bars = [candle(0, "90"), candle(1), candle(2, "103")]
        sig = [Decision(1, atr=D(10)), Decision(exit_long=True), Decision()]
        r = self.run_case(bars, sig)
        t = r["trades"][0]
        self.assertEqual((t["entry"], t["exit"]), (D("100.29"), D("102.71")))
        self.assertEqual(t["net"], D("2.41391"))
        self.assertEqual(r["raw_gross"], D(3))
        self.assertEqual(r["raw_gross"] - r["execution_drag"] - r["commission"] + r["swaps"], r["net"])
        self.assertEqual(r["final_stage_balance"], D(3000) + r["net"])

    def test_short_pays_both_execution_sides_and_commissions(self):
        r = self.run_case([candle(), candle(1), candle(2, "97")],
                          [Decision(-1, atr=D(10)), Decision(exit_short=True), Decision()])
        self.assertEqual(r["trades"][0]["net"], D("2.41409"))
        self.assertEqual(r["trades"][0]["entry"], D("99.71"))

    def test_bid_ask_assumptions_and_adverse_tick_rounding(self):
        bid = Costs(D("0.49"), D("0.051"), "bid", D(0), D("0.01"))
        ask = Costs(D("0.49"), D("0.051"), "ask", D(0), D("0.01"))
        self.assertEqual(bid.fill(D(100), 1), D("100.55"))
        self.assertEqual(bid.fill(D(100), -1), D("99.94"))
        self.assertEqual(ask.fill(D(100), 1), D("100.06"))
        self.assertEqual(ask.fill(D(100), -1), D("99.45"))
        self.assertRaises(ValueError, Costs, D(-1), D(0), "mid", D(0), D("0.01"))

    def test_stop_can_trigger_on_entry_bar_before_close_signal(self):
        r = self.run_case([candle(), candle(1, h="110", l="97", c="109")],
                          [Decision(1, atr=D(1)), Decision(exit_long=True)])
        self.assertEqual(r["trades"][0]["exit"], D("97.71"))
        self.assertEqual(r["trades"][0]["reason"], "stop")
        self.assertLess(r["net"], 0)

    def test_short_stop_is_adverse_high(self):
        r = self.run_case([candle(), candle(1, h="103", l="90", c="91")],
                          [Decision(-1, atr=D(1)), Decision()])
        self.assertEqual(r["trades"][0]["exit"], D("102.29"))
        self.assertEqual(r["trades"][0]["reason"], "stop")

    def test_gap_through_stop_fills_at_open_and_flags_unknown_exposure(self):
        r = self.run_case([candle(), candle(1), candle(5, "90")],
                          [Decision(1, atr=D(1)), Decision(), Decision()])
        self.assertEqual(r["trades"][0]["exit"], D("89.71"))
        self.assertEqual(r["counts"]["gap_held"], 1)

    def test_pending_entry_canceled_across_gap(self):
        r = self.run_case([candle(), candle(2)], [Decision(1, atr=D(1)), Decision()])
        self.assertEqual(r["trade_count"], 0)
        self.assertEqual(r["counts"]["gap_canceled_entry"], 1)

    def test_size_rounds_down_instead_of_exceeding_loss_budget(self):
        q, _ = position_size(D(3000), D("100.29"), D("97.71"), 1, self.cost, self.cfg["account"])
        self.assertEqual(q, 2)
        q, reason = position_size(D(3000), D(100), D(80), 1, self.cost, self.cfg["account"])
        self.assertEqual((q, reason), (0, "risk_minimum_skip"))
        ac = dict(self.cfg["account"], leverage="0.001")
        self.assertEqual(position_size(D(3000), D(100), D(98), 1, self.cost, ac), (0, "margin_skip"))

    def test_signal_view_remains_visible_when_account_cannot_size(self):
        bars = [candle(), candle(1), candle(2, "103")]
        sig = [Decision(1, atr=D(10)), Decision(exit_long=True), Decision()]
        signal, account = self.run_case(bars, sig), self.run_case(bars, sig, "account")
        self.assertEqual(signal["trade_count"], 1)
        self.assertEqual(account["trade_count"], 0)
        self.assertEqual(account["counts"]["risk_minimum_skip"], 1)

    def test_failure_overrides_stage_target(self):
        self.cfg["account"].update(initial_balance="100", risk_fraction="1", total_floor="88", stage_target="90", max_ounces=1)
        r = self.run_case([candle(), candle(1, l="94", c="94")],
                          [Decision(1, atr=D(10)), Decision()], "account")
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["stage_completions"], [])

    def test_stop_does_not_prove_intrabar_floor_safety(self):
        self.cfg["account"].update(initial_balance="100", risk_fraction="0.03", total_floor="88", max_ounces=1)
        r = self.run_case([candle(), candle(1, l="80")],
                          [Decision(1, atr=D(1)), Decision()], "account")
        self.assertEqual(r["status"], "open")
        self.assertEqual(r["counts"]["unresolved_intrabar_floor"], 1)
        self.assertGreater(r["final_stage_balance"], D(96))

    def test_stage_reset_preserves_cumulative_pnl_and_stops_after_two(self):
        self.cfg["account"].update(initial_balance="1000", risk_fraction="0.1", total_floor="880", stage_target="1001", max_ounces=1)
        bars = [candle(i, "103" if i in (2, 6) else "100") for i in range(8)]
        sig = [Decision(1, atr=D(10)), Decision(exit_long=True), Decision(),
               Decision(1, atr=D(10)), Decision(), Decision(exit_long=True), Decision(), Decision()]
        r = self.run_case(bars, sig, "account")
        self.assertEqual(r["status"], "completed")
        self.assertEqual(len(r["stage_completions"]), 2)
        self.assertEqual(r["trade_count"], 2)
        self.assertEqual(r["net"], D("4.82782"))
        self.assertEqual(r["final_stage_balance"], D("1002.41391"))

    def test_day_floor_uses_new_opening_balance(self):
        self.cfg["account"].update(initial_balance="100", risk_fraction="1", total_floor="50", stage_target="1000", max_ounces=1)
        tomorrow = START + timedelta(days=1)
        bars = [candle(), candle(1), candle(2, "110"), candle(0, start=tomorrow),
                candle(1, start=tomorrow), candle(2, "105", start=tomorrow)]
        sig = [Decision(1, atr=D(10)), Decision(exit_long=True), Decision(),
               Decision(-1, atr=D(10)), Decision(), Decision()]
        r = self.run_case(bars, sig, "account")
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["counts"]["failures"], 1)

    def test_session_flat_and_time_exit_use_open_not_prior_close(self):
        self.cfg["strategies"]["sma_cross"]["max_hold_minutes"] = 1
        r = self.run_case([candle(), candle(1), candle(2, "102")],
                          [Decision(1, atr=D(10)), Decision(), Decision()])
        self.assertEqual(r["counts"]["time_exit"], 1)
        self.assertEqual(r["trades"][0]["exit"], D("101.71"))
        self.cfg["strategies"]["sma_cross"]["max_hold_minutes"] = 120
        start = START.replace(hour=18, minute=58)
        bars = [candle(i, start=start) for i in range(63)]
        r = self.run_case(bars, [Decision(1, atr=D(10))] + [Decision()] * 62)
        self.assertEqual(r["counts"]["session_exit"], 1)

    def test_late_session_signal_does_not_enter(self):
        start = START.replace(hour=18, minute=59)
        r = self.run_case([candle(start=start), candle(1, start=start)],
                          [Decision(1, atr=D(1)), Decision()])
        self.assertEqual(r["trade_count"], 0)
        self.assertEqual(r["counts"]["session_canceled_entry"], 1)

    def test_overnight_gap_applies_wednesday_triple_swap(self):
        start = START.replace(day=4, hour=18, minute=58)
        bars = [candle(start=start), candle(1, start=start), candle(900, start=start)]
        r = self.run_case(bars, [Decision(1, atr=D(10)), Decision(), Decision()])
        self.assertEqual(r["swaps"], D("-2.04"))
        self.assertEqual(r["counts"]["gap_held"], 1)

    def test_terminal_liquidation_charges_costs_and_does_not_carry_position(self):
        r = self.run_case([candle(), candle(1)], [Decision(1, atr=D(1)), Decision()])
        self.assertEqual(r["counts"]["terminal_exit"], 1)
        self.assertLess(r["net"], 0)

    def test_no_trade_is_exact_zero_for_both_views(self):
        for view in ("signal", "account"):
            r = self.run_case([candle(), candle(1, "1000")], [Decision(), Decision()], view, "no_trade")
            self.assertEqual((r["net"], r["modeled_max_drawdown"], r["trade_count"]), (D(0), D(0), 0))
            self.assertIsNone(r["mean_net_per_trade"])
            self.assertEqual(r["final_stage_balance"], D(3000))

    def test_prior_partition_signals_cannot_open_a_position(self):
        bars = [candle(i) for i in range(4)]
        sig = [Decision(1, atr=D(1)), Decision(1, atr=D(1)), Decision(), Decision()]
        r = simulate(bars, sig, "sma_cross", self.cfg, self.cost, "signal", bars[2].time,
                     bars[-1].time + timedelta(minutes=1))
        self.assertEqual(r["trade_count"], 0)

    def test_replay_is_identical(self):
        bars = [candle(), candle(1), candle(2, "103")]
        sig = [Decision(1, atr=D(1)), Decision(exit_long=True), Decision()]
        self.assertEqual(self.run_case(bars, sig), self.run_case(bars, sig))


class CausalRuleTests(unittest.TestCase):
    def setUp(self):
        self.cfg = settings(DEFAULT_CONFIG)

    def test_prefix_invariance_future_prices_cannot_change_decisions(self):
        bars = [candle(i, str(100 + (i % 27) * 2)) for i in range(160)]
        full, prefix = decisions(bars, self.cfg), decisions(bars[:110], self.cfg)
        for name in full:
            self.assertEqual(full[name][:110], prefix[name])

    def test_gap_resets_warmup_and_cancels_indicator_state(self):
        bars = [candle(i, str(100 + i)) for i in range(70)] + [candle(100 + i, "300") for i in range(60)]
        result = decisions(bars, self.cfg)
        for rows in result.values():
            self.assertTrue(all(r.entry == 0 for r in rows[70:]))

    def test_constant_series_has_no_signals_or_nonfinite_indicators(self):
        result = decisions([candle(i) for i in range(100)], self.cfg)
        self.assertTrue(all(r.entry == 0 and r.atr == 0 for rows in result.values() for r in rows))

    def test_atr_seed_and_wilder_update(self):
        bars = [candle(i, h="102", l="98") for i in range(14)] + [candle(14, h="114", l="86")]
        rows = decisions(bars, self.cfg)["sma_cross"]
        self.assertEqual(rows[13].atr, D(4))
        self.assertEqual(rows[14].atr, D(80) / 14)

    def test_channel_excludes_current_high_and_momentum_uses_close_time(self):
        bars = [candle(i, str(100 + i), str(101 + i), str(99 + i)) for i in range(121)]
        rows = decisions(bars, self.cfg)
        self.assertEqual(rows["channel_break"][61].entry, 0)  # equals prior high
        bars[61] = candle(61, "161.5", "162", "160")
        rows = decisions(bars, self.cfg)
        self.assertEqual(rows["channel_break"][61].entry, 1)
        self.assertEqual(rows["hour_momentum"][119].entry, 1)
        self.assertEqual(rows["hour_momentum"][120].entry, 0)

    def test_rsi_reentry_and_neutral_exit_match_wilder_decay(self):
        bars = [candle(i, str(100 + i)) for i in range(70)]
        bars += [candle(69 + k, str(169 - k)) for k in range(1, 15)]
        rows = decisions(bars, self.cfg)["rsi_reentry"]
        # After k equal downward increments RSI = 100 * (13/14)**k.
        self.assertTrue(all(rows[i].entry == 0 for i in range(70, 74)))
        self.assertEqual(rows[74].entry, -1)
        self.assertFalse(rows[78].exit_short)
        self.assertTrue(rows[79].exit_short)
        mirrored = [Candle(b.time, 400-b.open, 400-b.low, 400-b.high, 400-b.close) for b in bars]
        reverse = decisions(mirrored, self.cfg)["rsi_reentry"]
        self.assertEqual(reverse[74].entry, 1)
        self.assertTrue(reverse[79].exit_long)

    def test_bands_require_reentry_and_do_not_fade_first_touch(self):
        for extreme, returned, direction in (("70", "85", 1), ("130", "115", -1)):
            bars = [candle(i) for i in range(70)] + [candle(70, extreme), candle(71, returned), candle(72)]
            rows = decisions(bars, self.cfg)["band_reentry"]
            self.assertEqual(rows[70].entry, 0)
            self.assertEqual(rows[71].entry, direction)
            self.assertTrue(rows[72].exit_long if direction == 1 else rows[72].exit_short)


class ExperimentSafetyTests(unittest.TestCase):
    def setUp(self):
        self.cfg = settings(DEFAULT_CONFIG)

    def test_reader_stops_before_sealed_prices_are_parsed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "minute.csv"
            path.write_text("timestamp_utc,open,high,low,close,volume\n2026-03-31T23:59:00Z,100,101,99,100,1\n2026-04-01T00:00:00Z,SEALED,SEALED,SEALED,SEALED,1\n")
            path.chmod(0o600)
            result = read_normalized_minutes(path, datetime(2026, 4, 1, tzinfo=timezone.utc))
            self.assertEqual(len(result), 1)
            self.assertRaises(ProbeError, read_normalized_minutes, path, datetime(2026, 4, 2, tzinfo=timezone.utc))

    def test_reader_rejects_bad_order_ohlc_nonfinite_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "minute.csv"
            for body in ("2026-03-01T00:00:00Z,100,99,101,100,1\n",
                         "2026-03-01T00:00:00Z,NaN,101,99,100,1\n",
                         "2026-03-01T00:00:00Z,100,101,99,100,1\n" * 2):
                path.write_text("timestamp_utc,open,high,low,close,volume\n" + body)
                path.chmod(0o600)
                self.assertRaises(ProbeError, read_normalized_minutes, path, START)
            path.chmod(0o644)
            self.assertRaises(ProbeError, read_normalized_minutes, path, START)

    def test_input_hash_mismatch_fails_before_loading_prices(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "XAUUSD"
            root.mkdir()
            path = root / "1minute.csv"
            path.write_text("incorrect")
            self.assertRaises(ProbeError, inputs, path, self.cfg, START)

    def test_preregistered_grid_and_cohorts_are_complete(self):
        cases = screen_cases(self.cfg)
        self.assertEqual(len(cases), 672)
        self.assertEqual(len({(p, n, c.key, v) for p, n, c, v, _, _ in cases}), 672)
        self.assertTrue(all(end <= datetime(2026, 4, 1, tzinfo=timezone.utc) for *_, end in cases))

    def test_bootstrap_is_deterministic_and_keeps_zero_trade_days(self):
        daily = {f"2026-03-{d:02}": {"net": "2", "trades": 1} for d in range(1, 21)}
        daily["2026-03-21"] = {"net": "0", "trades": 0}
        self.assertEqual(lower_expectancy(daily, self.cfg["selection"]), D(2))
        self.assertEqual(lower_expectancy({}, self.cfg["selection"]), D(0))

    def test_artifacts_are_create_only_private_and_bounded_to_local(self):
        with tempfile.TemporaryDirectory() as folder, patch("mynyra.experiment.ROOT", Path(folder)):
            path = Path(folder) / ".local/evidence.json"
            save(path, {"amount": D("1.23")})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(read_private(path), {"amount": "1.23"})
            self.assertRaises(FileExistsError, save, path, {"overwrite": True})
            self.assertRaises(ProbeError, private_path, Path(folder) / "public.json")

    def test_evaluation_requires_a_freeze_before_any_input_read(self):
        with patch("mynyra.experiment.inputs") as loader:
            self.assertEqual(main(["evaluate", "--output", ".local/unused.json"]), 1)
            loader.assert_not_called()

    def test_finalist_list_rejects_unknown_duplicates_and_too_many(self):
        for names in (["other"], ["sma_cross", "sma_cross"], self.cfg["candidate_order"]):
            self.assertRaises(ProbeError, evaluation_cases, self.cfg, {"finalists": names})

    def test_completed_case_hashes_and_coverage_are_checked(self):
        with tempfile.TemporaryDirectory() as folder, patch("mynyra.experiment.ROOT", Path(folder)):
            output = Path(folder) / ".local/screen"
            case = ("selection", "no_trade", Costs(D("0.58"), D("0.15"), "mid", D("0.00003"), D("0.01")), "signal", START, START + timedelta(minutes=2))
            run_cases([candle(), candle(1)], self.cfg, [case], output, {"synthetic": True}, {})
            _, runs = load_runs(output, {"synthetic": True}, [case])
            self.assertEqual(len(runs), 1)
            self.assertRaises(ProbeError, load_runs, output, {"synthetic": False}, [case])
            self.assertRaises(ProbeError, load_runs, output, {"synthetic": True}, screen_cases(self.cfg))
            (output / "run_0000.json").write_text("tampered")
            self.assertRaises(ProbeError, load_runs, output, {"synthetic": True}, [case])

    def synthetic_results(self):
        result = {}
        for p, n, c, v, start, end in screen_cases(self.cfg):
            result[p, n, c.key, v] = {
                "net": "100", "counts": {}, "trade_count": 100, "active_days": 22,
                "modeled_max_drawdown": "10", "ounce_turnover": 200,
                "daily": {f"2026-03-{day:02}": {"net": "5", "trades": 5} for day in range(2, 30)},
            }
        return result

    def test_selection_requires_cost_survival_precision_and_cohort_safety(self):
        self.cfg["selection"]["bootstrap_samples"] = 50
        runs = self.synthetic_results()
        self.assertEqual(select(runs, self.cfg)["finalists"], ["band_reentry", "channel_break"])
        runs["selection", "band_reentry", "ask|0.58|0.15", "account"]["net"] = "-1"
        runs["selection", "channel_break", "mid|0.58|0.15", "signal"]["trade_count"] = 1
        runs["cohort_2026-03-09", "hour_momentum", "mid|0.58|0.15", "account"]["counts"] = {"gap_held": 1}
        selection = select(runs, self.cfg)
        decisions_by_name = {r["candidate"]: r for r in selection["decisions"]}
        self.assertEqual(selection["finalists"], ["rsi_reentry", "sma_cross"])
        self.assertEqual(decisions_by_name["band_reentry"]["classification"], "rejected")
        self.assertEqual(decisions_by_name["channel_break"]["classification"], "inconclusive")
        self.assertIn("unsafe_cohort:2026-03-09", decisions_by_name["hour_momentum"]["failed_gates"])

    def test_empty_finalist_freeze_keeps_evaluation_input_unread(self):
        prov = provenance(DEFAULT_CONFIG)
        frozen = {"provenance": prov, "input_sha256": self.cfg["input_sha256"], "finalists": [], "screen_index_sha256": "test"}
        with patch("mynyra.experiment.read_private", return_value=frozen), \
             patch("mynyra.experiment.load_runs", return_value=({}, {})), \
             patch("mynyra.experiment.select", return_value={"finalists": []}), \
             patch("mynyra.experiment.archive_sha256", return_value="test"), \
             patch("mynyra.experiment.provenance", return_value=prov), \
             patch("mynyra.experiment.inputs") as loader, patch("mynyra.experiment.save") as saver:
            self.assertEqual(main(["evaluate", "--screen", ".local/screen", "--freeze", ".local/freeze.json", "--output", ".local/sealed.json"]), 0)
            loader.assert_not_called()
            self.assertEqual(saver.call_args.args[1]["status"], "not_opened")

    def test_changed_implementation_or_forged_finalists_cannot_unseal(self):
        prov = provenance(DEFAULT_CONFIG)
        frozen = {"provenance": prov, "input_sha256": self.cfg["input_sha256"], "finalists": ["sma_cross"], "screen_index_sha256": "test"}
        with patch("mynyra.experiment.read_private", return_value=frozen), \
             patch("mynyra.experiment.load_runs", return_value=({}, {})), \
             patch("mynyra.experiment.select", return_value={"finalists": []}), \
             patch("mynyra.experiment.archive_sha256", return_value="test"), \
             patch("mynyra.experiment.provenance", return_value=prov), \
             patch("mynyra.experiment.inputs") as loader:
            args = ["evaluate", "--screen", ".local/screen", "--freeze", ".local/freeze.json", "--output", ".local/sealed.json"]
            self.assertEqual(main(args), 1)
            frozen["finalists"] = []
            frozen["provenance"] = {"changed": True}
            self.assertEqual(main(args), 1)
            loader.assert_not_called()
