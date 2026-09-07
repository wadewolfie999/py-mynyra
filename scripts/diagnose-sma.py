#!/usr/bin/env python3
"""Explain frozen v1 SMA sizing using observed January-March data only.

No new strategy or threshold is optimized. Instrument the existing sizing call,
assert identical full replays, and value each account entry attempt independently.
The instrumented call depends on simulator local names and fails closed on drift.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from decimal import Decimal as D
import inspect
from pathlib import Path

from mynyra import simulation
from mynyra.datasets import archive_sha256
from mynyra.experiment import (DEFAULT_CONFIG, ROOT, inputs, json_value, load_runs,
                              private_path, provenance, save, screen_cases, settings, utc)
from mynyra.strategies import decisions, MINUTE


def equal(a, b):
    if abs(D(a) - D(b)) > D('1e-18'):
        raise ValueError('Diagnostic reconciliation failed')


def totals(trades, unit=False):
    return sum((D(t['net']) / (t['ounces'] if unit else 1) for t in trades), D(0))


def decomposition(signal, account):
    def keyed(rows):
        result = {(t['entry_time'], t['direction']): t for t in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate trade identity')
        return result
    s, a = keyed(signal['trades']), keyed(account['trades'])
    common = s.keys() & a.keys()
    s_only, a_only = s.keys() - a.keys(), a.keys() - s.keys()
    removed = -totals([s[k] for k in s_only])
    added = totals([a[k] for k in a_only], unit=True)
    exit_effect = sum((D(a[k]['net']) / a[k]['ounces'] - D(s[k]['net']) for k in common), D(0))
    size_effect = totals(account['trades']) - totals(account['trades'], unit=True)
    equal(D(account['net']) - D(signal['net']), removed + added + exit_effect + size_effect)
    return dict(signal_net=D(signal['net']), account_net=D(account['net']),
                shared_entries=len(common), signal_only_entries=len(s_only),
                account_only_entries=len(a_only), remove_signal_only_net=removed,
                add_account_only_unit_net=added, common_entry_exit_effect=exit_effect,
                additional_ounce_effect=size_effect,
                account_sequence_one_ounce_net=totals(account['trades'], unit=True))


def observed_account(bars, signals, cfg, cost, start, end):
    events = []
    original = simulation.position_size
    def observe(balance, entry, stop_exit, direction, costs, account):
        q, why = original(balance, entry, stop_exit, direction, costs, account)
        caller = inspect.currentframe().f_back
        try:
            if caller.f_code is not simulation.simulate.__code__:
                raise ValueError('Unexpected sizing caller')
            local = caller.f_locals
            bar, atr, distance = local['bar'], local['atr'], local['distance']
            events.append(dict(time=bar.time.isoformat(), direction=direction, ounces=q,
                               reason=why or 'executed', atr=atr, stop_distance=distance,
                               balance=balance, modeled_loss_one_ounce=direction * (entry-stop_exit)
                               + costs.commission * (entry+stop_exit)))
        finally:
            del caller
        return q, why
    simulation.position_size = observe
    try:
        result = simulation.simulate(bars, signals, 'sma_cross', cfg, cost, 'account', start, end)
    finally:
        simulation.position_size = original
    if sum(e['ounces'] > 0 for e in events) != result['trade_count']:
        raise ValueError('Executed sizing-event count differs from ledger')
    for why, n in Counter(e['reason'] for e in events if not e['ounces']).items():
        if result['counts'].get(why, 0) != n:
            raise ValueError('Skipped sizing-event count differs from ledger')
    return result, events


def isolated_attempt(bars, signals, lookup, event, cfg, cost, end):
    i = lookup[utc(event['time'])]
    # Include decision candle, then enough bars for the unchanged 120-minute exit.
    stop = min(len(bars), i + cfg['strategies']['sma_cross']['max_hold_minutes'] + 2)
    local_bars = bars[i-1:stop]
    local_signals = [replace(s, entry=0) for s in signals[i-1:stop]]
    local_signals[0] = signals[i-1]
    if local_signals[0].entry != event['direction'] or bars[i].time - bars[i-1].time != MINUTE:
        raise ValueError('Attempt does not match causal signal')
    run = simulation.simulate(local_bars, local_signals, 'sma_cross', cfg, cost, 'signal',
                              bars[i-1].time, end)
    if len(run['trades']) != 1 or run['trades'][0]['entry_time'] != event['time']:
        raise ValueError('Isolated attempt did not produce exactly its intended trade')
    return run['trades'][0]


def summarize(events, key):
    groups = defaultdict(list)
    for e in events:
        groups[key(e)].append(e)
    result = {}
    for name, rows in sorted(groups.items()):
        net = sum((r['counterfactual']['net'] for r in rows), D(0))
        result[name] = dict(attempts=len(rows), independent_unit_net=net,
                            mean_unit_net=net/len(rows),
                            mean_atr=sum((r['atr'] for r in rows), D(0))/len(rows),
                            mean_stop_distance=sum((r['stop_distance'] for r in rows), D(0))/len(rows),
                            wins=sum(r['counterfactual']['net'] > 0 for r in rows))
    return result


def diagnose(screen, output):
    output = private_path(output)
    if output.exists():
        raise FileExistsError('Choose a new diagnostic output path')
    cfg = settings(DEFAULT_CONFIG)
    prov = provenance(DEFAULT_CONFIG)
    _, frozen = load_runs(screen, prov, screen_cases(cfg))
    end = utc(cfg['periods']['evaluation_start'])
    bars, proof = inputs(ROOT / '.local/data/faraz/normalized_utc_20260904/XAUUSD/1minute.csv', cfg, end)
    if not bars or bars[-1].time >= end:
        raise ValueError('Evaluation seal violated')
    signals = decisions(bars, cfg)['sma_cross']
    lookup = {b.time: i for i, b in enumerate(bars)}
    ex, sel = cfg['execution'], cfg['selection']
    cost = simulation.Costs(D(sel['gate_spread']), D(sel['gate_slippage']), 'mid',
                            D(ex['commission_rate']), D(ex['tick']))
    report = dict(status='completed', exploratory=True, provenance=prov,
                  diagnostic_sha256=archive_sha256(Path(__file__)),
                  screen_index_sha256=archive_sha256(screen/'index.json'), data=proof,
                  scenario=cost.key, periods={})
    for period, a, b in [('development', 'development_start', 'selection_start'),
                          ('selection', 'selection_start', 'evaluation_start')]:
        start, finish = utc(cfg['periods'][a]), utc(cfg['periods'][b])
        signal = simulation.simulate(bars, signals, 'sma_cross', cfg, cost, 'signal', start, finish)
        account, events = observed_account(bars, signals, cfg, cost, start, finish)
        for view, run in [('signal', signal), ('account', account)]:
            run['period'] = period
            if json_value(run) != frozen[period, 'sma_cross', cost.key, view]:
                raise ValueError('Instrumented replay differs from frozen evidence')
        account_by_entry = {(t['entry_time'], t['direction']): t for t in account['trades']}
        for event in events:
            event['counterfactual'] = isolated_attempt(bars, signals, lookup, event, cfg, cost, finish)
            if period == 'selection' and event['ounces']:
                actual = account_by_entry[event['time'], event['direction']]
                equal(event['counterfactual']['net'], actual['net']/actual['ounces'])
        def stop_bucket(e):
            x = e['stop_distance']
            return 'le4' if x <= 4 else '4to6' if x <= 6 else '6to8' if x <= 8 else 'gt8'
        report['periods'][period] = dict(
            decomposition=decomposition(signal, account),
            actual_ounce_counts=dict(sorted(Counter(t['ounces'] for t in account['trades']).items())),
            attempt_counts=dict(Counter(e['reason'] for e in events)),
            by_outcome=summarize(events, lambda e: e['reason']),
            by_stop_distance=summarize(events, lambda e: e['reason']+':'+stop_bucket(e)),
            by_entry_utc_hour=summarize(events, lambda e: e['reason']+':'+e['time'][11:13]),
            by_calendar_half=summarize(events, lambda e: e['reason']+':'+e['time'][:7]+('H1' if int(e['time'][8:10]) < 16 else 'H2')),
            events=events)
        print(f'{period}: replay matched; {len(events)} sizing attempts diagnosed', flush=True)
    save(output, report)
    print('Completed; private diagnostic saved.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', type=Path, default=ROOT/'.local/experiments/screen_v1')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    diagnose(args.screen, args.output)
