"""Offline experiment lifecycle: screen -> freeze -> sealed evaluation.

Run with python -m mynyra.experiment. Private outputs are immutable and bind input,
protocol and implementation hashes. This module never imports the cTrader adapter.
"""

import argparse
import hashlib
import itertools
import json
import platform
import random
import sys
import tomllib
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

from mynyra.config import ProbeError
from mynyra.datasets import archive_sha256, read_normalized_minutes, validate_normalized_faraz
from mynyra.market import write_capture
from mynyra.simulation import Costs, simulate
from mynyra.strategies import decisions

D = Decimal
NAMES = ["sma_cross", "channel_break", "hour_momentum", "band_reentry", "rsi_reentry"]
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "experiments/xauusd_m1_v1.toml"
PROTOCOL = ROOT / "docs/XAUUSD_COMPARISON_PROTOCOL.md"


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo != timezone.utc:
        raise ValueError("Expected UTC timestamp")
    return result


def json_value(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def private_path(path: Path) -> Path:
    resolved = path.absolute().resolve()
    root = (ROOT / ".local").resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ProbeError("Experiment artifacts must remain below project .local/.")
    return resolved


def save(path: Path, value: dict) -> None:
    path = private_path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_capture(path, json_value(value))


def read_private(path: Path) -> dict:
    if path.is_symlink():
        raise ProbeError("Experiment artifact must not be a symbolic link.")
    path = private_path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ProbeError("Experiment artifact must be a private regular file.")
    return json.loads(path.read_text())


def settings(path: Path) -> dict:
    cfg = tomllib.loads(path.read_text())
    if cfg["id"] != "xauusd_m1_v1" or cfg["schema"] != 1 or cfg["candidate_order"] != NAMES:
        raise ProbeError("Unsupported experiment or candidate registry.")
    if set(cfg["strategies"]) != set(NAMES) or cfg["variants_per_candidate"] != 1 or cfg["layers"] != 0:
        raise ProbeError("Variants and layers are outside this registered experiment.")
    periods = [utc(cfg["periods"][k]) for k in ("development_start", "selection_start", "evaluation_start", "evaluation_end")]
    if periods != sorted(set(periods)):
        raise ProbeError("Experiment periods are invalid.")
    return cfg


def provenance(config_path: Path) -> dict:
    paths = sorted((ROOT / "src/mynyra").glob("*.py")) + [ROOT / "requirements.lock", ROOT / "pyproject.toml"]
    source_hashes = {str(p.relative_to(ROOT)): archive_sha256(p) for p in paths}
    return {"config_sha256": archive_sha256(config_path),
            "protocol_sha256": archive_sha256(PROTOCOL),
            "implementation_sha256": hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest(),
            "source_hashes": source_hashes, "python": platform.python_version()}


def scenarios(cfg: dict) -> list[Costs]:
    ex = cfg["execution"]
    return [Costs(D(s), D(l), side, D(ex["commission_rate"]), D(ex["tick"]))
            for s, l, side in itertools.product(ex["spreads"], ex["slippages_per_side"], ex["price_sides"])]


def inputs(path: Path, cfg: dict, end: datetime):
    if path.name != "1minute.csv" or path.parent.name != "XAUUSD":
        raise ProbeError("Only the registered normalized XAUUSD M1 input is supported.")
    if archive_sha256(path) != cfg["input_sha256"]:
        raise ProbeError("Input hash differs from the preregistered dataset.")
    proof = validate_normalized_faraz(path.parent.parent)
    manifest = json.loads((path.parent.parent / "manifest.json").read_text())
    target = [s for s in manifest["series"] if s["path"] == "XAUUSD/1minute.csv"]
    if len(target) != 1 or target[0]["row_count"] != cfg["input_rows"]:
        raise ProbeError("The registered XAUUSD minute row count does not match.")
    bars = read_normalized_minutes(path, end)
    return bars, {"input_sha256": cfg["input_sha256"], "full_validation": proof,
                  "loaded_prefix_rows": len(bars), "loaded_last_timestamp": bars[-1].time.isoformat()}


def run_cases(bars, cfg, cases, output, prov, data_proof):
    output = private_path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    save(output / "registration.json", {"provenance": prov, "data": data_proof,
                                        "cases": [{"period": p, "candidate": n, "scenario": c.key,
                                                   "view": v, "start": a.isoformat(), "end": b.isoformat()}
                                                  for p, n, c, v, a, b in cases]})
    calculated = decisions(bars, cfg)
    entries = []
    for number, (period, name, cost, view, start, end) in enumerate(cases):
        filename = f"run_{number:04d}.json"
        result = simulate(bars, calculated[name], name, cfg, cost, view, start, end)
        result["period"] = period
        save(output / filename, result)
        entries.append({"file": filename, "sha256": archive_sha256(output / filename),
                        "period": period, "candidate": name, "scenario": cost.key, "view": view})
        if (number + 1) % 27 == 0:
            print(json.dumps({"status": "running", "completed": number + 1, "total": len(cases)}), flush=True)
    index = {"provenance": prov, "data": data_proof, "runs": entries,
             "registration_sha256": archive_sha256(output / "registration.json")}
    save(output / "index.json", index)
    print(json.dumps({"status": "completed", "runs": len(entries)}), flush=True)


def screen_cases(cfg):
    p = cfg["periods"]
    cases = []
    for period, start, end in (("development", p["development_start"], p["selection_start"]),
                               ("selection", p["selection_start"], p["evaluation_start"])):
        for name, cost, view in itertools.product(NAMES + ["no_trade"], scenarios(cfg), ("signal", "account")):
            cases.append((period, name, cost, view, utc(start), utc(end)))
    sel, ex = cfg["selection"], cfg["execution"]
    cost = Costs(D(sel["gate_spread"]), D(sel["gate_slippage"]), "mid", D(ex["commission_rate"]), D(ex["tick"]))
    for start in p["selection_cohorts"]:
        for name in NAMES + ["no_trade"]:
            cases.append(("cohort_" + start[:10], name, cost, "account", utc(start), utc(p["evaluation_start"])))
    return cases


def load_runs(folder: Path, prov: dict, expected_cases=None) -> tuple[dict, dict]:
    index = read_private(folder / "index.json")
    if index["provenance"] != prov:
        raise ProbeError("Experiment provenance changed; results cannot be selected or unsealed.")
    if archive_sha256(folder / "registration.json") != index["registration_sha256"]:
        raise ProbeError("Experiment registration hash mismatch.")
    registration = read_private(folder / "registration.json")
    if registration["provenance"] != prov or len(registration["cases"]) != len(index["runs"]):
        raise ProbeError("Experiment registration coverage mismatch.")
    result = {}
    for entry, case in zip(index["runs"], registration["cases"]):
        filename = entry["file"]
        if Path(filename).name != filename or not filename.startswith("run_"):
            raise ProbeError("Unsafe run artifact name.")
        path = folder / filename
        if archive_sha256(path) != entry["sha256"]:
            raise ProbeError("Experiment run hash mismatch.")
        item = read_private(path)
        for key in ("period", "candidate", "scenario", "view"):
            if item[key] != entry[key] or item[key] != case[key]:
                raise ProbeError("Run identity differs from registration.")
        if item["start"] != case["start"] or item["end"] != case["end"]:
            raise ProbeError("Run periods differ from registration.")
        key = (entry["period"], entry["candidate"], entry["scenario"], entry["view"])
        if key in result:
            raise ProbeError("Duplicate experiment result.")
        result[key] = item
    if expected_cases is not None:
        expected = {(p, n, c.key, v): (a.isoformat(), b.isoformat()) for p, n, c, v, a, b in expected_cases}
        if set(result) != set(expected) or any((r["start"], r["end"]) != expected[key] for key, r in result.items()):
            raise ProbeError("Screen is incomplete or differs from registered cases.")
    return index, result


def lower_expectancy(daily: dict, selection: dict) -> Decimal:
    pairs = [(D(v["net"]), v["trades"]) for _, v in sorted(daily.items())]
    if not pairs:
        return D(0)
    rng = random.Random(selection["bootstrap_seed"])
    replicates = []
    length, block = len(pairs), selection["bootstrap_block_days"]
    for _ in range(selection["bootstrap_samples"]):
        sample = []
        while len(sample) < length:
            start = rng.randrange(length)
            sample.extend(pairs[(start + j) % length] for j in range(block))
        sample = sample[:length]
        n = sum(v[1] for v in sample)
        replicates.append(sum((v[0] for v in sample), D(0)) / n if n else D(0))
    replicates.sort()
    index = int(D(len(replicates) - 1) * D(selection["lower_quantile"]))
    return replicates[index]


def select(runs: dict, cfg: dict, period: str = "selection") -> dict:
    sel = cfg["selection"]
    primary = f'mid|{sel["gate_spread"]}|{sel["gate_slippage"]}'
    gates = [f'mid|{sel["base_spread"]}|{sel["base_slippage"]}',
             f'mid|{sel["gate_spread"]}|{sel["base_slippage"]}', primary,
             f'bid|{sel["gate_spread"]}|{sel["gate_slippage"]}',
             f'ask|{sel["gate_spread"]}|{sel["gate_slippage"]}']
    records = []
    names = [name for name in NAMES if (period, name, primary, "signal") in runs]
    for name in names:
        failures = []
        for key in gates:
            for view in ("signal", "account"):
                item = runs[period, name, key, view]
                if D(item["net"]) <= 0:
                    failures.append(f"nonpositive:{key}:{view}")
                if view == "account":
                    for counter in ("failures", "gap_held", "unresolved_intrabar_floor"):
                        if item["counts"].get(counter, 0):
                            failures.append(f"{counter}:{key}")
        sig, acc = runs[period, name, primary, "signal"], runs[period, name, primary, "account"]
        lower = lower_expectancy(sig["daily"], sel)
        enough = sig["trade_count"] >= sel["minimum_trades"] and sig["active_days"] >= sel["minimum_active_days"]
        if not enough:
            failures.append("insufficient_trades_or_days")
        if lower <= 0:
            failures.append("nonpositive_bootstrap_lower")
        if period == "selection":
            halves = [sum((D(v["net"]) for day, v in sig["daily"].items() if (day < "2026-03-16") == first), D(0)) for first in (True, False)]
            if min(halves) <= 0:
                failures.append("nonpositive_march_half")
            for start in cfg["periods"]["selection_cohorts"]:
                cohort = runs["cohort_" + start[:10], name, primary, "account"]
                if any(cohort["counts"].get(c, 0) for c in ("failures", "gap_held", "unresolved_intrabar_floor")):
                    failures.append("unsafe_cohort:" + start[:10])
        economic_failure = any(f.startswith(("nonpositive:", "failures:", "gap_held:", "unresolved_intrabar_floor:", "unsafe_cohort:")) for f in failures)
        records.append({"candidate": name, "eligible": not failures,
                        "classification": "eligible" if not failures else "rejected" if economic_failure else "inconclusive",
                        "failed_gates": failures, "bootstrap_lower": str(lower),
                        "ranking_net": acc["net"], "ranking_drawdown": acc["modeled_max_drawdown"],
                        "ranking_turnover": acc["ounce_turnover"]})
    eligible = sorted((r for r in records if r["eligible"]),
                      key=lambda r: (-D(r["ranking_net"]), D(r["ranking_drawdown"]), r["ranking_turnover"], r["candidate"]))
    return {"decisions": records, "finalists": [r["candidate"] for r in eligible[:sel["max_finalists"]]]}


def freeze(screen: Path, output: Path, cfg: dict, prov: dict):
    index, runs = load_runs(screen, prov, screen_cases(cfg))
    result = select(runs, cfg)
    result.update({"provenance": prov, "screen_index_sha256": archive_sha256(screen / "index.json"),
                   "input_sha256": cfg["input_sha256"], "evaluation_start": cfg["periods"]["evaluation_start"]})
    save(output, result)
    print(json.dumps({"status": "frozen", "finalists": result["finalists"],
                      "freeze_sha256": archive_sha256(output)}))


def evaluation_cases(cfg, frozen):
    names = frozen["finalists"]
    if len(names) > cfg["selection"]["max_finalists"] or len(set(names)) != len(names) or not set(names).issubset(NAMES):
        raise ProbeError("Invalid frozen finalist list.")
    return [("evaluation", n, c, v, utc(cfg["periods"]["evaluation_start"]), utc(cfg["periods"]["evaluation_end"]))
            for n, c, v in itertools.product(names + ["no_trade"], scenarios(cfg), ("signal", "account"))]


def aggregate_report(runs: dict, cfg: dict) -> dict:
    """Safe aggregate export: no candle values, executions, timestamps or ledger."""
    sel = cfg["selection"]
    keys = [f'mid|{s}|{l}' for s, l in ((sel["base_spread"], sel["base_slippage"]),
                                       (sel["gate_spread"], sel["base_slippage"]),
                                       (sel["gate_spread"], sel["gate_slippage"]),
                                       ("0.80", "0.15"))]
    fields = ("period", "candidate", "scenario", "view", "net", "raw_gross", "execution_drag", "commission", "swaps",
              "trade_count", "active_days", "modeled_max_drawdown", "ounce_turnover",
              "conditional_cost_budget_per_ounce", "mean_holding_minutes", "mean_modeled_mae_per_ounce", "counts", "status")
    rows = [{**{f: r[f] for f in fields}, "stage_count": len(r["stage_completions"])}
            for key, r in runs.items() if key[2] in keys]
    bounds = []
    for period, name, view in itertools.product(("development", "selection", "evaluation"), NAMES + ["no_trade"], ("signal", "account")):
        group = [r for (p, n, _, v), r in runs.items() if (p, n, v) == (period, name, view)]
        if group:
            bounds.append({"period": period, "candidate": name, "view": view,
                           "min_net": min(D(r["net"]) for r in group), "max_net": max(D(r["net"]) for r in group)})
    primary = keys[2]
    relationships = []
    for a, b in itertools.combinations(NAMES, 2):
        if ("selection", a, primary, "signal") not in runs or ("selection", b, primary, "signal") not in runs:
            continue
        x, y = runs["selection", a, primary, "signal"], runs["selection", b, primary, "signal"]
        days = sorted(set(x["daily"]) | set(y["daily"]))
        dx = [D(x["daily"].get(day, {"net": 0})["net"]) for day in days]
        dy = [D(y["daily"].get(day, {"net": 0})["net"]) for day in days]
        mx, my = sum(dx) / len(days), sum(dy) / len(days)
        vx, vy = sum((d - mx)**2 for d in dx), sum((d - my)**2 for d in dy)
        correlation = sum((u - mx) * (v - my) for u, v in zip(dx, dy)) / (vx * vy).sqrt() if vx and vy else None
        # Intervals are sorted and nonoverlapping within a candidate. Count how
        # many A trades overlap at least one B trade; count is directional.
        overlap, j = 0, 0
        for trade in x["trades"]:
            while j < len(y["trades"]) and y["trades"][j]["exit_time"] <= trade["entry_time"]:
                j += 1
            if j < len(y["trades"]) and y["trades"][j]["entry_time"] < trade["exit_time"]:
                overlap += 1
        relationships.append({"a": a, "b": b, "daily_correlation": correlation,
                              "a_trades_overlapping_b": overlap, "a_trades": len(x["trades"])})
    return {"rows": rows, "scenario_bounds": bounds, "relationships": relationships}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("screen", "freeze", "evaluate", "report"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--input", type=Path, default=ROOT / ".local/data/faraz/normalized_utc_20260904/XAUUSD/1minute.csv")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--screen", type=Path)
    parser.add_argument("--freeze", type=Path)
    args = parser.parse_args(argv)
    try:
        if sys.version_info[:2] != (3, 11):
            raise ProbeError("Use the supported Python 3.11 runtime.")
        cfg, prov = settings(args.config), provenance(args.config)
        with localcontext() as context:
            context.prec = cfg["decimal_precision"]
            if args.command == "report":
                if args.screen is None:
                    raise ProbeError("Reporting requires a completed experiment directory.")
                index, runs = load_runs(args.screen, prov)
                report = aggregate_report(runs, cfg)
                report["index_sha256"] = archive_sha256(args.screen / "index.json")
                report["provenance"] = prov
                save(args.output, report)
                print(json.dumps({"status": "reported", "aggregate_rows": len(report["rows"])}))
            elif args.command == "freeze":
                if args.screen is None:
                    raise ProbeError("Freezing requires the completed screen directory.")
                freeze(args.screen, args.output, cfg, prov)
            elif args.command == "screen":
                bars, proof = inputs(args.input, cfg, utc(cfg["periods"]["evaluation_start"]))
                run_cases(bars, cfg, screen_cases(cfg), args.output, prov, proof)
            else:
                if args.freeze is None or args.screen is None:
                    raise ProbeError("Evaluation requires a frozen manifest and its completed screen.")
                frozen = read_private(args.freeze)
                _, runs = load_runs(args.screen, prov, screen_cases(cfg))
                if frozen["provenance"] != prov or frozen["input_sha256"] != cfg["input_sha256"]:
                    raise ProbeError("Frozen provenance does not match this implementation/input.")
                if frozen["screen_index_sha256"] != archive_sha256(args.screen / "index.json") or frozen["finalists"] != select(runs, cfg)["finalists"]:
                    raise ProbeError("Frozen finalists do not match the registered selection.")
                if not frozen["finalists"]:
                    save(args.output, {"status": "not_opened", "reason": "no_finalists", "freeze_sha256": archive_sha256(args.freeze)})
                    print(json.dumps({"status": "not_opened", "reason": "no_finalists"}))
                else:
                    bars, proof = inputs(args.input, cfg, utc(cfg["periods"]["evaluation_end"]))
                    proof["freeze_sha256"] = archive_sha256(args.freeze)
                    run_cases(bars, cfg, evaluation_cases(cfg, frozen), args.output, prov, proof)
    except (ProbeError, ValueError, KeyError, OSError, ArithmeticError) as error:
        # No source values, remote payloads, credentials or local paths in errors.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__,
                          "error": str(error) if isinstance(error, ProbeError) else "Offline experiment failed; inspect inputs and artifact state."}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
