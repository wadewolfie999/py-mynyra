"""Causal, position-independent rules for the registered five-candidate screen.

No broker messages, account state, execution costs or future candles belong here.
The TOML owns numerical parameters; this module owns indicator and rule semantics.
"""

from collections import deque
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from mynyra.datasets import Candle

D = Decimal
MINUTE = timedelta(minutes=1)


@dataclass(frozen=True)
class Decision:
    entry: int = 0
    exit_long: bool = False
    exit_short: bool = False
    atr: Decimal = D(0)


def decisions(candles: list[Candle], config: dict) -> dict[str, list[Decision]]:
    """Return decisions available at each candle's close, including warm-up rows."""
    rules = config["strategies"]
    result = {name: [] for name in config["candidate_order"] + ["no_trade"]}
    lookback = config["execution"]["minimum_contiguous_bars"]
    window = deque(maxlen=lookback)
    atr_n = config["execution"]["atr_period"]
    rsi_n = rules["rsi_reentry"]["period"]
    ranges, gains, losses = [], [], []
    atr = gain = loss = None
    previous = None
    prior_diff = prior_lower = prior_upper = prior_rsi = None
    for bar in candles:
        if previous is None or bar.time - previous.time != MINUTE:
            window.clear()
            ranges, gains, losses = [], [], []
            atr = gain = loss = None
            prior_diff = prior_lower = prior_upper = prior_rsi = None
            previous = None
        tr = bar.high - bar.low
        if previous is not None:
            tr = max(tr, abs(bar.high - previous.close), abs(bar.low - previous.close))
            delta = bar.close - previous.close
            g, l = max(delta, D(0)), max(-delta, D(0))
            if gain is None:
                gains.append(g)
                losses.append(l)
                if len(gains) == rsi_n:
                    gain, loss = sum(gains) / rsi_n, sum(losses) / rsi_n
            else:
                gain = (gain * (rsi_n - 1) + g) / rsi_n
                loss = (loss * (rsi_n - 1) + l) / rsi_n
        if atr is None:
            ranges.append(tr)
            if len(ranges) == atr_n:
                atr = sum(ranges) / atr_n
        else:
            atr = (atr * (atr_n - 1) + tr) / atr_n
        window.append(bar)
        values = list(window)
        closes = [b.close for b in values]
        rsi = None
        if gain is not None:
            rsi = D(50) if gain == loss == 0 else (
                D(100) if loss == 0 else D(100) - D(100) / (1 + gain / loss)
            )
        ma = rules["sma_cross"]
        diff = None
        if len(values) >= ma["slow"]:
            diff = sum(closes[-ma["fast"]:]) / ma["fast"] - sum(closes[-ma["slow"]:]) / ma["slow"]
        bb = rules["band_reentry"]
        mean = lower = upper = None
        if len(values) >= bb["lookback"]:
            sample = closes[-bb["lookback"]:]
            mean = sum(sample) / len(sample)
            sd = (sum((p - mean) ** 2 for p in sample) / len(sample)).sqrt()
            lower, upper = mean - D(bb["deviations"]) * sd, mean + D(bb["deviations"]) * sd
        row = {name: Decision(atr=atr or D(0)) for name in result}
        if len(values) >= lookback and atr is not None and atr > 0:
            entry = 1 if prior_diff <= 0 < diff else -1 if prior_diff >= 0 > diff else 0
            row["sma_cross"] = Decision(entry, diff <= 0, diff >= 0, atr)
            ch = rules["channel_break"]
            entry_window = values[-ch["entry_lookback"] - 1:-1]
            exit_window = values[-ch["exit_lookback"] - 1:-1]
            entry = 1 if bar.close > max(b.high for b in entry_window) else (
                -1 if bar.close < min(b.low for b in entry_window) else 0
            )
            row["channel_break"] = Decision(entry, bar.close < min(b.low for b in exit_window),
                                             bar.close > max(b.high for b in exit_window), atr)
            mo = rules["hour_momentum"]
            delta = bar.close - values[-mo["lookback"] - 1].close
            entry = (1 if delta > 0 else -1 if delta < 0 else 0) if (bar.time + MINUTE).minute == 0 else 0
            row["hour_momentum"] = Decision(entry, False, False, atr)
            entry = 0
            if lower <= bar.close <= upper:
                if previous.close < prior_lower and bar.close < mean:
                    entry = 1
                elif previous.close > prior_upper and bar.close > mean:
                    entry = -1
            row["band_reentry"] = Decision(entry, bar.close >= mean, bar.close <= mean, atr)
            rs = rules["rsi_reentry"]
            neutral, lo, hi = D(rs["neutral"]), D(rs["lower"]), D(rs["upper"])
            entry = 1 if prior_rsi < lo <= rsi < neutral else (
                -1 if prior_rsi > hi >= rsi > neutral else 0
            )
            row["rsi_reentry"] = Decision(entry, rsi >= neutral, rsi <= neutral, atr)
        for name in result:
            result[name].append(row[name])
        previous = bar
        prior_diff, prior_lower, prior_upper, prior_rsi = diff, lower, upper, rsi
    return result
