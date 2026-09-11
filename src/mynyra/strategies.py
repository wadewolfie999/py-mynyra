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
    # Immutable close-exit references belong to the entry event, not later setups.
    frozen_exit: tuple = ()


def reference_exit(reference: tuple, close: Decimal) -> bool:
    if not reference:
        return False
    kind, *levels = reference
    if kind == "inside":
        return levels[0] <= close <= levels[1]
    if kind == "le":
        return close <= levels[0]
    if kind == "ge":
        return close >= levels[0]
    if kind == "lt":
        return close < levels[0]
    if kind == "gt":
        return close > levels[0]
    raise ValueError("Unknown frozen exit predicate")


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


class _EMA:
    """Arithmetic seed followed by causal exponential updates; reset on gaps."""

    def __init__(self, length):
        self.length, self.seed, self.value = length, [], None

    def update(self, value):
        if self.value is None:
            self.seed.append(value)
            if len(self.seed) == self.length:
                self.value = sum(self.seed) / self.length
                self.seed.clear()
        else:
            self.value += D(2) / (self.length + 1) * (value - self.value)
        return self.value


def expanded_decisions(candles, config, start, sma):
    """Step 4 events, independent of execution/occupancy and reset at each split.

    Indicators may warm before start. Finite setups cannot. Entry events consume
    their setup even if an account later rejects them. Frozen exit predicates are
    carried by the event so another setup cannot mutate a held position's exit.
    """
    from zoneinfo import ZoneInfo

    rules, ex = config['strategies'], config['execution']
    # Read the exact registered TZif instead of depending on PYTHONTZPATH or a
    # previously cached ZoneInfo object from another environment.
    with open(config['evidence']['london_path'], 'rb') as timezone_file:
        london = ZoneInfo.from_file(timezone_file, key='Europe/London')
    result = {name: [] for name in config['candidate_order'] + ['no_trade']}
    previous = None
    day = None
    day_bars = []
    local_day = None
    opening = []
    used_range = used_day = False
    setups = {}
    for i, bar in enumerate(candles):
        gap = previous is None or bar.time - previous.time != MINUTE
        if gap:
            opening = []
            window = deque(maxlen=142)
            atrs = deque(maxlen=142)
            ranges = []
            atr = None
            fast, slow = _EMA(rules['P05']['fast']), _EMA(rules['P05']['slow'])
            slow_history = deque(maxlen=11)
            prior_fast = prior_band = prior_z = None
            widths = deque(maxlen=121)
            m15 = []
            mf, ms = _EMA(rules['P08']['fast']), _EMA(rules['P08']['slow'])
            m15_count = 0
            setups.clear()
        if day != bar.time.date():
            prior_range = None
            p2 = rules['P02']
            if day is not None and day == bar.time.date()-timedelta(days=1) and day.weekday() < 5 and len(day_bars) >= p2['minimum_day_bars']:
                if all((b.time-a.time).total_seconds() <= 60*p2['maximum_gap_minutes'] for a,b in zip(day_bars,day_bars[1:])):
                    prior_range = min(b.low for b in day_bars), max(b.high for b in day_bars)
            day, day_bars, used_day = bar.time.date(), [], False
        day_bars.append(bar)
        closed = bar.time + MINUTE
        local = bar.time.astimezone(london)
        if local_day != local.date():
            local_day, opening, used_range = local.date(), [], False
        local_minute = local.hour * 60 + local.minute
        p1 = rules['P01']
        if p1['range_start'] <= local_minute < p1['range_start'] + p1['range_minutes'] and bar.time >= start:
            opening.append(bar)
        tr = bar.high - bar.low
        if not gap:
            tr = max(tr, abs(bar.high - previous.close), abs(bar.low - previous.close))
        if atr is None:
            ranges.append(tr)
            if len(ranges) == ex['atr_period']:
                atr = sum(ranges) / len(ranges)
        else:
            atr = (atr * (ex['atr_period'] - 1) + tr) / ex['atr_period']
        window.append(bar)
        atrs.append(atr)
        w = list(window)
        closes = [b.close for b in w]
        ef, es = fast.update(bar.close), slow.update(bar.close)
        band = width = None
        p4 = rules['P04']
        if len(w) >= p4['lookback']:
            sample = closes[-p4['lookback']:]
            mean = sum(sample) / len(sample)
            sd = (sum((v - mean)**2 for v in sample) / len(sample)).sqrt()
            band = (mean - D(p4['deviations']) * sd, mean, mean + D(p4['deviations']) * sd)
            width = (band[2] - band[0]) / mean if mean else None
        p9 = rules['P09']
        z = None
        if len(w) > p9['lookback']:
            ys = closes[-p9['lookback']-1:-1]
            n = len(ys)
            xm, ym = D(n-1)/2, sum(ys)/n
            slope = sum((D(j)-xm)*(y-ym) for j,y in enumerate(ys)) / sum((D(j)-xm)**2 for j in range(n))
            rms = (sum((y-(ym+slope*(D(j)-xm)))**2 for j,y in enumerate(ys))/n).sqrt()
            if rms:
                z = (bar.close-(ym+slope*(D(n)-xm)))/rms
        p8 = rules['P08']
        if bar.time.minute % p8['context_minutes'] == 0:
            m15 = []
        m15.append(bar)
        if closed.minute % p8['context_minutes'] == 0:
            if len(m15) == p8['context_minutes'] and m15[0].time.minute % p8['context_minutes'] == 0:
                mf.update(bar.close)
                ms.update(bar.close)
                m15_count += 1
            else:
                mf, ms = _EMA(p8['fast']), _EMA(p8['slow'])
                m15_count = 0
            m15 = []
        row = {name: Decision(atr=atr or D(0)) for name in result}
        row['sma_cross'] = sma[i]
        # Exit indicators stay live outside entry windows. Reference exits are
        # evaluated against the immutable predicate on the actual position.
        if band and prior_band and not gap:
            row['P04'] = Decision(0, previous.close >= prior_band[1] and bar.close < band[1],
                                  previous.close <= prior_band[1] and bar.close > band[1], atr or D(0))
        if ef is not None and es is not None:
            # A direction becoming unsupported is equivalent to its adverse
            # crossover for a position that entered under the stated trend.
            row['P05'] = Decision(0, ef <= es, ef >= es, atr or D(0))
        row['P08'] = Decision(0, mf.value is None or ms.value is None or mf.value <= ms.value,
                              mf.value is None or ms.value is None or mf.value >= ms.value, atr or D(0))
        if z is not None:
            row['P09'] = Decision(0, z >= 0, z <= 0, atr or D(0))
        permitted = (bar.time >= start and closed.weekday() < 5 and
                     ex['entry_start_hour_utc'] <= closed.hour < ex['entry_end_hour_utc'])
        ready = permitted and len(w) >= ex['minimum_contiguous_bars'] and atr is not None and atr > 0
        if not permitted:
            setups.clear()
        def enter(name, direction, reference=()):
            old = row[name]
            row[name] = Decision(direction, old.exit_long, old.exit_short, atr, reference)
        if ready:
            # Frozen London range, one event per local date (not per account).
            minute = closed.astimezone(london).hour * 60 + closed.astimezone(london).minute
            if not used_range and len(opening) == p1['range_minutes'] and p1['range_start']+p1['range_minutes'] <= minute < p1['entry_end']:
                lo, hi = min(b.low for b in opening), max(b.high for b in opening)
                direction = 1 if previous.close <= hi < bar.close else -1 if previous.close >= lo > bar.close else 0
                if direction:
                    enter('P01', direction, ('inside', lo, hi))
                    used_range = True
            # Calendar-day completeness is metadata, not a rolling indicator;
            # the explicitly tolerated daily breaks do not erase that record.
            if not used_day and prior_range:
                lo, hi = prior_range
                direction = 1 if previous.close <= hi < bar.close else -1 if previous.close >= lo > bar.close else 0
                if direction:
                    enter('P02', direction, ('le',hi) if direction==1 else ('ge',lo))
                    used_day = True
            p3 = rules['P03']
            active = setups.get('P03')
            if active:
                armed, direction, lo, hi = active
                if lo < bar.close < hi:
                    enter('P03', direction, ('ge' if direction==1 else 'le',(lo+hi)/2))
                    del setups['P03']
                elif i-armed >= p3['expiry_bars']:
                    del setups['P03']
            elif len(w) >= p3['lookback']+2:
                now, before = w[-p3['lookback']-1:-1], w[-p3['lookback']-2:-2]
                lo, hi = min(b.low for b in now), max(b.high for b in now)
                direction = -1 if bar.close > hi and previous.close <= max(b.high for b in before) else 1 if bar.close < lo and previous.close >= min(b.low for b in before) else 0
                if direction:
                    setups['P03'] = (i,direction,lo,hi)
            if len(w) >= p4['warmup'] and width is not None and len(widths) == p4['width_history']+1 and all(v is not None for v in widths) and widths[-1] <= min(list(widths)[:-1]):
                direction = 1 if previous.close <= prior_band[2] and bar.close > band[2] else -1 if previous.close >= prior_band[0] and bar.close < band[0] else 0
                if direction:
                    enter('P04',direction)
            p5 = rules['P05']
            if len(w) >= p5['warmup'] and len(slow_history) >= p5['slope_bars'] and slow_history[-p5['slope_bars']] is not None:
                direction = 1 if es > slow_history[-p5['slope_bars']] and previous.close <= prior_fast and bar.close > ef and ef > es else -1 if es < slow_history[-p5['slope_bars']] and previous.close >= prior_fast and bar.close < ef and ef < es else 0
                if direction:
                    enter('P05',direction)
            for name in ('P06','P07'):
                p = rules[name]
                active = setups.get(name)
                if active:
                    age = i-active['armed']
                    direction, lo, hi = active['direction'], active['lo'], active['hi']
                    midpoint = (lo+hi)/2
                    if name == 'P07':
                        extended = bar.close > hi if direction==1 else bar.close < lo
                        crossed = previous.close >= midpoint > bar.close if direction==1 else previous.close <= midpoint < bar.close
                        if extended:
                            del setups[name]
                        elif crossed:
                            enter(name,-direction,('gt',hi) if direction==1 else ('lt',lo))
                            del setups[name]
                        elif age >= p['expiry_bars']:
                            del setups[name]
                    elif age <= p['consolidation_bars']:
                        active['bars'].append(bar)
                        failed = (bar.close < midpoint if direction==1 else bar.close > midpoint)
                        span = max(b.high for b in active['bars'])-min(b.low for b in active['bars'])
                        active['invalid'] = active.get('invalid', False) or failed or span > D(p['consolidation_atr'])*active['atr']
                        if age == p['consolidation_bars']:
                            if active['invalid']:
                                del setups[name]
                            else:
                                active['flag_lo'] = min(b.low for b in active['bars'])
                                active['flag_hi'] = max(b.high for b in active['bars'])
                    else:
                        flo, fhi = active['flag_lo'],active['flag_hi']
                        crossed = previous.close <= fhi < bar.close if direction==1 else previous.close >= flo > bar.close
                        if crossed:
                            enter(name,direction,('lt',flo) if direction==1 else ('gt',fhi))
                            del setups[name]
                        elif age >= p['consolidation_bars']+p['expiry_bars']:
                            del setups[name]
                else:
                    delta = bar.close-closes[-p['impulse_bars']-1]
                    old_atr = atrs[-p['impulse_bars']-1]
                    if old_atr and abs(delta) >= D(p['impulse_atr'])*old_atr:
                        impulse = w[-p['impulse_bars']:]
                        setups[name] = {'armed':i,'direction':1 if delta>0 else -1,'lo':min(b.low for b in impulse),
                                        'hi':max(b.high for b in impulse),'atr':atr,'bars':[]}
            if m15_count >= p8['slow'] and len(w) >= p8['entry_lookback']+2:
                now,before = w[-p8['entry_lookback']-1:-1],w[-p8['entry_lookback']-2:-2]
                direction = 1 if mf.value > ms.value and bar.close > max(b.high for b in now) and previous.close <= max(b.high for b in before) else -1 if mf.value < ms.value and bar.close < min(b.low for b in now) and previous.close >= min(b.low for b in before) else 0
                if direction:
                    enter('P08',direction)
            threshold = D(p9['threshold'])
            if z is not None and prior_z is not None:
                direction = 1 if prior_z < -threshold <= z < 0 else -1 if prior_z > threshold >= z > 0 else 0
                if direction:
                    enter('P09',direction)
            p10 = rules['P10']
            if minute in p10['anchors']:
                delta = bar.close-closes[-p10['lookback']-1]
                if delta:
                    enter('P10',1 if delta>0 else -1)
        for name in result:
            result[name].append(row[name])
        if width is not None:
            widths.append(width)
        else:
            widths.clear()
        slow_history.append(es)
        prior_fast, prior_band, prior_z = ef, band, z
        previous = bar
    return result
