"""Deterministic reference-bar fills, separate signal/account views, no network.

The model deliberately exposes gaps and unknown intrabar floor ordering. It is
not a reconstruction of broker fills or a provider loss-rule implementation.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from mynyra.datasets import Candle
from mynyra.strategies import Decision, MINUTE, reference_exit

D = Decimal


@dataclass(frozen=True)
class Costs:
    spread: Decimal
    slippage: Decimal
    side: str
    commission: Decimal
    tick: Decimal

    def __post_init__(self):
        if self.side not in ("mid", "bid", "ask"):
            raise ValueError("Unsupported reference price side")
        if any(not x.is_finite() or x < 0 for x in (self.spread, self.slippage, self.commission)) or self.tick <= 0 or not self.tick.is_finite():
            raise ValueError("Invalid execution cost")

    @property
    def key(self) -> str:
        return f"{self.side}|{self.spread}|{self.slippage}"

    def fill(self, reference: Decimal, buy_sell: int) -> Decimal:
        shift = {"mid": D(0), "bid": self.spread / 2, "ask": -self.spread / 2}[self.side]
        price = reference + shift + buy_sell * (self.spread / 2 + self.slippage)
        rounding = ROUND_CEILING if buy_sell == 1 else ROUND_FLOOR
        return (price / self.tick).to_integral_value(rounding=rounding) * self.tick


@dataclass
class Position:
    direction: int
    ounces: int
    opened: datetime
    reference: Decimal
    execution: Decimal
    stop: Decimal
    commission: Decimal
    swaps: Decimal = D(0)
    adverse_excursion: Decimal = D(0)
    favorable_excursion: Decimal = D(0)
    frozen_exit: tuple = ()


def position_size(balance: Decimal, entry: Decimal, stop_exit: Decimal,
                  direction: int, costs: Costs, account: dict) -> tuple[int, str]:
    """Largest integer size within modeled loss budget AND margin allocation."""
    loss = direction * (entry - stop_exit) + costs.commission * (entry + stop_exit)
    if loss <= 0:
        return 0, "invalid_stop"
    risk_q = int(balance * D(account["risk_fraction"]) / loss)
    margin_q = int(balance * D(account["margin_fraction"]) * D(account["leverage"]) / entry)
    q = max(0, min(risk_q, margin_q, account["max_ounces"]))
    q = q // account["step_ounces"] * account["step_ounces"]
    if q < account["min_ounces"]:
        return 0, "margin_skip" if margin_q < account["min_ounces"] else "risk_minimum_skip"
    return q, ""


def simulate(candles: list[Candle], signals: list[Decision], name: str,
             config: dict, costs: Costs, view: str, start: datetime,
             end: datetime) -> dict:
    """Replay one candidate/scenario with one position and explicit flat resets."""
    if view not in ("signal", "account") or len(candles) != len(signals):
        raise ValueError("Invalid simulation inputs")
    if name not in config["candidate_order"] + ["no_trade"]:
        raise ValueError("Unknown strategy")
    ac, ex = config["account"], config["execution"]
    rule = config["strategies"].get(name)
    indices = [i for i, b in enumerate(candles) if start <= b.time < end]
    if not indices:
        raise ValueError("Empty simulation period")
    initial = D(ac["initial_balance"])
    balance = initial
    daily_floor = balance * D(ac["daily_floor_fraction"])
    total_pnl, peak, max_dd = D(0), initial, D(0)
    position = None
    pending = None
    pending_exit = False
    prior_bar = None
    current_day = None
    counts = Counter()
    ledger, stages = [], []
    status = "open"
    failure_reason = None
    daily = {candles[i].time.date().isoformat(): {"net": D(0), "trades": 0}
             for i in indices if candles[i].time.weekday() < 5}

    def mark(reference):
        nonlocal peak, max_dd
        unrealized = D(0)
        if position is not None:
            exit_price = costs.fill(reference, -position.direction)
            unrealized = position.ounces * (position.direction * (exit_price - position.execution) - costs.commission * exit_price)
        economic_equity = initial + total_pnl + unrealized
        peak = max(peak, economic_equity)
        max_dd = max(max_dd, peak - economic_equity)
        return balance + unrealized

    def breach(reference):
        equity = mark(reference)
        return view == "account" and equity <= max(daily_floor, D(ac["total_floor"]))

    def close(reference, stamp, reason):
        nonlocal position, balance, total_pnl, pending_exit
        p = position
        execution = costs.fill(reference, -p.direction)
        exit_fee = p.ounces * execution * costs.commission
        executed_gross = p.direction * (execution - p.execution) * p.ounces
        cash_delta = executed_gross - exit_fee
        balance += cash_delta
        total_pnl += cash_delta
        raw_gross = p.direction * (reference - p.reference) * p.ounces
        net = executed_gross - p.commission - exit_fee + p.swaps
        item = {"entry_time": p.opened.isoformat(), "exit_time": stamp.isoformat(),
                "direction": p.direction, "ounces": p.ounces, "entry": p.execution,
                "exit": execution, "raw_gross": raw_gross,
                "execution_drag": raw_gross - executed_gross,
                "commission": p.commission + exit_fee, "swaps": p.swaps,
                "net": net, "reason": reason,
                "modeled_mae_per_ounce": p.adverse_excursion,
                "modeled_mfe_per_ounce": p.favorable_excursion,
                "holding_minutes": D(str((stamp - p.opened).total_seconds())) / 60}
        ledger.append(item)
        day = stamp.date().isoformat()
        daily.setdefault(day, {"net": D(0), "trades": 0})
        daily[day]["net"] += net
        daily[day]["trades"] += 1
        counts[reason] += 1
        position = None
        pending_exit = False
        mark(reference)

    def stage_or_failure(stamp):
        nonlocal status, balance, daily_floor, pending, failure_reason
        if view != "account":
            return False
        if balance <= max(daily_floor, D(ac["total_floor"])):
            status, failure_reason = "failed", "loss_floor"
            counts["failures"] += 1
            return True
        if balance >= D(ac["stage_target"]):
            pending = None
            stages.append({"stage": len(stages) + 1, "time": stamp.isoformat(), "balance": balance})
            if len(stages) == ac["stages"]:
                status = "completed"
            else:
                balance = initial
                daily_floor = balance * D(ac["daily_floor_fraction"])
            return True
        return False

    for i in indices:
        bar, signal = candles[i], signals[i]
        if status != "open":
            break
        if current_day != bar.time.date():
            current_day = bar.time.date()
            daily_floor = balance * D(ac["daily_floor_fraction"])
        gap = prior_bar is not None and bar.time - prior_bar.time != MINUTE
        if gap:
            if pending is not None:
                counts["gap_canceled_entry"] += 1
            pending = None
            if position is not None:
                counts["gap_held"] += 1
                # Price-free time iteration charges missed rollover boundaries.
                swap_at = prior_bar.time.replace(hour=ex["swap_hour_utc"], minute=ex["swap_minute_utc"], second=0)
                while swap_at <= bar.time:
                    if swap_at > prior_bar.time:
                        rate = D(ex["swap_long_per_ounce"] if position.direction == 1 else ex["swap_short_per_ounce"])
                        factor = 3 if swap_at.weekday() == ex["triple_swap_weekday"] else 1
                        swap = rate * factor * position.ounces
                        position.swaps += swap
                        balance += swap
                        total_pnl += swap
                    swap_at += timedelta(days=1)
        exited = False
        if position is not None:
            p = position
            p.adverse_excursion = max(p.adverse_excursion, -p.direction * (bar.open - p.reference))
            p.favorable_excursion = max(p.favorable_excursion, p.direction * (bar.open - p.reference))
            reason = None
            if breach(bar.open):
                reason = "open_floor"
            elif gap:
                reason = "gap_exit"
            elif p.direction * (bar.open - p.stop) <= 0:
                reason = "open_stop"
            elif pending_exit:
                reason = "signal_exit"
            elif bar.time - p.opened >= timedelta(minutes=rule["max_hold_minutes"]):
                reason = "time_exit"
            elif bar.time.hour >= ex["flatten_hour_utc"]:
                reason = "session_exit"
            if reason:
                close(bar.open, bar.time, reason)
                exited = True
                if stage_or_failure(bar.time):
                    prior_bar = bar
                    continue
        if not exited and position is None and pending is not None:
            direction, atr, frozen_exit = pending
            if ex["entry_start_hour_utc"] <= bar.time.hour < ex["entry_end_hour_utc"] and bar.time.weekday() < 5:
                distance = (atr * D(rule["stop_atr"]) / costs.tick).to_integral_value(rounding=ROUND_CEILING) * costs.tick
                stop = bar.open - direction * distance
                entry = costs.fill(bar.open, direction)
                stop_exit = costs.fill(stop, -direction)
                if min(stop_exit, entry) <= 0 or distance <= 0:
                    counts["invalid_stop"] += 1
                else:
                    ounces, why = (1, "") if view == "signal" else position_size(balance, entry, stop_exit, direction, costs, ac)
                    if ounces:
                        fee = ounces * entry * costs.commission
                        position = Position(direction, ounces, bar.time, bar.open, entry, stop, fee,
                                            frozen_exit=frozen_exit)
                        balance -= fee
                        total_pnl -= fee
                    else:
                        counts[why] += 1
            else:
                counts["session_canceled_entry"] += 1
        pending = None
        if position is not None:
            p = position
            adverse = bar.low if p.direction == 1 else bar.high
            stopped = p.direction * (adverse - p.stop) <= 0
            effective = p.stop if stopped else adverse
            p.adverse_excursion = max(p.adverse_excursion, -p.direction * (effective - p.reference))
            if view == "account" and stopped:
                # Never claim a stop proves safety against an unknown intrabar jump.
                extreme_exit = costs.fill(adverse, -p.direction)
                extreme_equity = balance + p.ounces * (p.direction * (extreme_exit - p.execution) - costs.commission * extreme_exit)
                if extreme_equity <= max(daily_floor, D(ac["total_floor"])):
                    counts["unresolved_intrabar_floor"] += 1
            failed = breach(effective)
            if failed or stopped:
                close(effective, bar.time + MINUTE, "intrabar_floor" if failed else "stop")
                if stage_or_failure(bar.time + MINUTE):
                    prior_bar = bar
                    continue
            else:
                # An adverse-first path is a convention, not observed OHLC ordering.
                favorable = bar.high if p.direction == 1 else bar.low
                p.favorable_excursion = max(p.favorable_excursion, p.direction * (favorable - p.reference))
                mark(favorable)
                if breach(bar.close):
                    close(bar.close, bar.time + MINUTE, "close_floor")
                    if stage_or_failure(bar.time + MINUTE):
                        prior_bar = bar
                        continue
        if position is not None:
            pending_exit = signal.exit_long if position.direction == 1 else signal.exit_short
            pending_exit = pending_exit or reference_exit(position.frozen_exit, bar.close)
            if signal.entry:
                counts["overlap_signal"] += 1
        elif signal.entry:
            pending = (signal.entry, signal.atr, signal.frozen_exit)
            counts["flat_signal"] += 1
        prior_bar = bar
    if position is not None:
        last = candles[indices[-1]]
        close(last.close, last.time + MINUTE, "terminal_exit")
        stage_or_failure(last.time + MINUTE)
    net = sum((t["net"] for t in ledger), D(0))
    if abs(net - total_pnl) > D("0.000000000000000001"):
        raise ArithmeticError("Trade/account reconciliation failed")
    gross = sum((t["raw_gross"] for t in ledger), D(0))
    drag = sum((t["execution_drag"] for t in ledger), D(0))
    commission = sum((t["commission"] for t in ledger), D(0))
    swaps = sum((t["swaps"] for t in ledger), D(0))
    n = len(ledger)
    # Per-ounce cost budget weights each completed trade equally, not its size.
    budget = sum(((t["raw_gross"] - t["commission"] + t["swaps"]) / t["ounces"] for t in ledger), D(0)) / n if n else None
    return {"candidate": name, "scenario": costs.key, "view": view,
            "start": start.isoformat(), "end": end.isoformat(), "status": status,
            "failure_reason": failure_reason, "net": net, "raw_gross": gross,
            "execution_drag": drag, "commission": commission, "swaps": swaps,
            "final_stage_balance": balance, "modeled_max_drawdown": max_dd,
            "trade_count": n, "active_days": sum(v["trades"] > 0 for v in daily.values()),
            "ounce_turnover": sum(2 * t["ounces"] for t in ledger),
            "mean_net_per_trade": net / n if n else None,
            "mean_holding_minutes": sum((t["holding_minutes"] for t in ledger), D(0)) / n if n else None,
            "mean_modeled_mae_per_ounce": sum((t["modeled_mae_per_ounce"] for t in ledger), D(0)) / n if n else None,
            "conditional_cost_budget_per_ounce": budget,
            "stage_completions": stages, "counts": dict(counts), "daily": daily,
            "trades": ledger}
