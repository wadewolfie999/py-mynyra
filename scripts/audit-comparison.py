#!/usr/bin/env python3
"""Audit completed private evidence independently of simulator state transitions."""

import argparse
from decimal import Decimal
from pathlib import Path

from mynyra.datasets import archive_sha256
from mynyra.experiment import DEFAULT_CONFIG, load_runs, provenance, save, screen_cases, settings

D = Decimal
TOLERANCE = D("0.000000000000000001")


def equal(actual, expected):
    if abs(D(actual) - D(expected)) > TOLERANCE:
        raise ValueError("Evidence accounting mismatch")


def audit(folder, replay=None, cfg=None, prov=None, cases=None):
    cfg = cfg or settings(DEFAULT_CONFIG)
    prov = prov or provenance(DEFAULT_CONFIG)
    cases = cases or screen_cases(cfg)
    index, runs = load_runs(folder, prov, cases)
    total_trades = 0
    for (_, name, _, view), run in runs.items():
        trades = run["trades"]
        if run["trade_count"] != len(trades):
            raise ValueError("Trade count mismatch")
        prior_exit = None
        for trade in trades:
            entry, exit_price = D(trade["entry"]), D(trade["exit"])
            q, direction = trade["ounces"], trade["direction"]
            if direction not in (-1, 1) or not isinstance(q, int) or q < 1:
                raise ValueError("Invalid exposure")
            if view == "signal" and q != 1:
                raise ValueError("Signal measurement was resized")
            if view == "account" and q > cfg["account"]["max_ounces"]:
                raise ValueError("Symbol size bound exceeded")
            if trade["entry_time"] > trade["exit_time"] or (prior_exit is not None and trade["entry_time"] < prior_exit):
                raise ValueError("Trade timing/overlap mismatch")
            prior_exit = trade["exit_time"]
            commission = (entry + exit_price) * q * D(cfg["execution"]["commission_rate"])
            executed_gross = (exit_price - entry) * direction * q
            equal(trade["commission"], commission)
            equal(trade["net"], executed_gross - commission + D(trade["swaps"]))
            equal(trade["execution_drag"], D(trade["raw_gross"]) - executed_gross)
        for field in ("net", "raw_gross", "execution_drag", "commission", "swaps"):
            equal(run[field], sum((D(t[field]) for t in trades), D(0)))
        equal(run["net"], sum((D(day["net"]) for day in run["daily"].values()), D(0)))
        if sum(day["trades"] for day in run["daily"].values()) != len(trades):
            raise ValueError("Daily attribution mismatch")
        stages = run["stage_completions"]
        reset_stages = stages[:-1] if run["status"] == "completed" else stages
        initial = D(cfg["account"]["initial_balance"])
        expected_balance = initial + D(run["net"]) - sum((D(stage["balance"]) - initial for stage in reset_stages), D(0))
        equal(run["final_stage_balance"], expected_balance)
        if len(stages) > cfg["account"]["stages"] or (run["status"] == "failed") != (run["counts"].get("failures", 0) == 1):
            raise ValueError("Account lifecycle mismatch")
        if name == "no_trade":
            if trades or stages or D(run["modeled_max_drawdown"]) != 0 or D(run["net"]) != 0:
                raise ValueError("No-trade baseline changed")
            equal(run["final_stage_balance"], initial)
        total_trades += len(trades)
    result = {"status": "passed", "runs": len(runs), "scenario_trade_records": total_trades,
              "checks": ["artifact_hashes", "registered_coverage", "execution_commission_arithmetic",
                         "gross_drag_net_reconciliation", "daily_attribution", "integer_exposure",
                         "nonoverlapping_positions", "stage_balance_resets", "no_trade_baseline"],
              "index_sha256": archive_sha256(folder / "index.json")}
    if replay is not None:
        replay_index, _ = load_runs(replay, prov, cases)
        if index != replay_index:
            raise ValueError("Independent replay index differs")
        result["replay_index_sha256"] = archive_sha256(replay / "index.json")
        result["checks"].append("all_replay_artifact_hashes_identical")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.screen, args.replay)
    save(args.output, result)
    print(f"Audit passed for {result['runs']} cases; private evidence saved.")
