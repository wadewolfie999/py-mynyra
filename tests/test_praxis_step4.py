"""Synthetic contracts only: never read historical prices or compute market results."""

import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import random
import unittest
from unittest.mock import patch

from mynyra.datasets import Candle
from mynyra.experiment import (DEFAULT_CONFIG, settings, step4_settings, step4_cases,
                              step4_select, step4_report, lower_expectancy)
from mynyra.simulation import Costs, simulate
from mynyra.strategies import Decision, decisions, expanded_decisions, reference_exit

START=datetime(2026,3,2,6,tzinfo=timezone.utc)
MINUTE=timedelta(minutes=1)


def bars(values,start=START,radius='0.1'):
    out=[]
    for i,v in enumerate(values):
        v=D(str(v));r=D(radius)
        out.append(Candle(start+i*MINUTE,v,v+r,v-r,v))
    return out


def calculate(data,cfg=None,start=None):
    cfg=cfg or step4_settings()
    return expanded_decisions(data,cfg,start or data[0].time,decisions(data,settings(DEFAULT_CONFIG))['sma_cross'])


class ExpandedRules(unittest.TestCase):
    def test_prefix_invariance_all_candidates_and_unchanged_sma(self):
        rng=random.Random(849)
        values=[D(100)]
        for i in range(1100):values.append(values[-1]+D(rng.randint(-10,10))/10)
        data=bars(values)
        full=calculate(data)
        for length in (61,142,301,900,1040):
            prefix=calculate(data[:length])
            for name in full:self.assertEqual(prefix[name],full[name][:length],name)
        self.assertEqual(full['sma_cross'],decisions(data,settings(DEFAULT_CONFIG))['sma_cross'])

    def test_constant_series_and_gap_require_entire_warmup(self):
        data=bars([100]*1000)
        self.assertTrue(all(not s.entry for signals in calculate(data).values() for s in signals))
        tail=bars([100+i%3 for i in range(65)],start=data[-1].time+2*MINUTE)
        result=calculate(data+tail)
        for name,signals in result.items():
            self.assertTrue(all(not s.entry for s in signals[1000:1060]),name)

    def test_london_range_exact_cross_frozen_exit_and_one_event(self):
        data=bars([100]*75+[102,100,103,100],start=START.replace(hour=7))
        r=calculate(data)['P01']
        self.assertEqual([i for i,s in enumerate(r) if s.entry],[75])
        self.assertEqual(r[75].frozen_exit,('inside',D('99.9'),D('100.1')))
        missing=data[:65]+data[66:]
        self.assertFalse(any(s.entry for s in calculate(missing)['P01']))

    def test_london_dst_and_half_open_window(self):
        for day,hour in ((27,7),(30,6)):
            data=bars([100]*75+[102],start=datetime(2026,3,day,hour,tzinfo=timezone.utc))
            self.assertEqual(calculate(data)['P01'][-1].entry,1)
        data=bars([100]*179+[102],start=START.replace(hour=7))
        self.assertFalse(any(s.entry for s in calculate(data)['P01']))

    def test_clock_momentum_anchor_uses_thirty_minutes(self):
        for day,hour in ((27,9),(30,8)):
            data=bars([100+i for i in range(91)],start=datetime(2026,3,day,hour,tzinfo=timezone.utc))
            r=calculate(data)['P10']
            self.assertEqual([i for i,s in enumerate(r) if s.entry],[89])
            self.assertEqual(r[89].entry,1)
        data=bars([100+i for i in range(100)],start=datetime(2026,3,28,9,tzinfo=timezone.utc))
        self.assertFalse(any(s.entry for s in calculate(data)['P10']))

    def test_previous_day_completeness_and_monday_skip(self):
        prior=bars([100]*1440,start=datetime(2026,3,2,tzinfo=timezone.utc))
        current=bars([100]*360+[102,100,103],start=datetime(2026,3,3,tzinfo=timezone.utc))
        r=calculate(prior+current)['P02']
        self.assertEqual([i for i,s in enumerate(r) if s.entry],[1800])
        self.assertEqual(r[1800].frozen_exit,('le',D('100.1')))
        self.assertFalse(any(s.entry for s in calculate(prior[:1000]+current)['P02']))
        sunday=bars([100]*1440,start=datetime(2026,3,1,tzinfo=timezone.utc))
        monday=bars([100]*360+[102],start=datetime(2026,3,2,tzinfo=timezone.utc))
        self.assertFalse(any(s.entry for s in calculate(sunday+monday)['P02']))

    def test_failed_break_reentry_expiry_and_partition_no_setup_leak(self):
        data=bars([100]*65+[102,100])
        r=calculate(data)['P03']
        self.assertEqual(r[65].entry,0)
        self.assertEqual(r[66].entry,-1)
        self.assertEqual(r[66].frozen_exit,('le',D(100)))
        self.assertEqual(calculate(data,start=data[66].time)['P03'][66].entry,0)
        for delay,expected in ((4,-1),(5,0)):
            data=bars([100]*65+[102]+[102]*delay+[100])
            self.assertEqual(calculate(data)['P03'][-1].entry,expected)

    def test_compression_uses_excluding_current_width_history(self):
        data=bars([100]*141+[102])
        r=calculate(data)['P04']
        self.assertEqual(r[-1].entry,1)
        self.assertFalse(any(s.entry for s in r[:-1]))

    def test_pullback_cross_after_rising_slow_average(self):
        values=[D(100)+D(i)/10 for i in range(100)]
        values += [D(108),D(109),D(110)]
        r=calculate(bars(values))['P05']
        self.assertEqual(r[-2].entry,1)
        self.assertEqual(r[-1].entry,0)

    def test_impulse_continuation_and_exhaustion_are_separate(self):
        # A jump arms at 65; a valid five-bar flag breaks only on bar 71.
        data=bars([100]*65+[104]+[104]*5+[105])
        r=calculate(data)
        self.assertEqual([i for i,s in enumerate(r['P06']) if s.entry],[71])
        self.assertEqual(r['P06'][71].frozen_exit,('lt',D('103.9')))
        self.assertFalse(any(s.entry for s in r['P07']))
        data=bars([100]*65+[104,101])
        r=calculate(data)
        self.assertEqual(r['P07'][-1].entry,-1)
        self.assertEqual(r['P07'][-1].frozen_exit,('gt',D('104.1')))
        self.assertFalse(any(s.entry for s in r['P06']))
        # Cancellation on extending the original extreme has priority.
        data=bars([100]*65+[104,105,101])
        self.assertFalse(any(s.entry for s in calculate(data)['P07']))

    def test_impulse_partition_and_gap_cannot_seed_a_trade(self):
        data=bars([100]*65+[104,101])
        self.assertEqual(calculate(data,start=data[-1].time)['P07'][-1].entry,0)
        data[-1]=replace(data[-1],time=data[-1].time+MINUTE)
        self.assertEqual(calculate(data)['P07'][-1].entry,0)

    def test_m15_only_complete_bars_and_reset_on_missing_constituent(self):
        start=START.replace(hour=0)
        values=[D(100)+D(i//15)/10 for i in range(910)]
        values[-1]=D(120)
        data=bars(values,start=start,radius='0')
        r=calculate(data)['P08']
        self.assertEqual(r[-1].entry,1)
        self.assertFalse(any(s.entry for s in r[:899]))
        damaged=data[:850]+data[851:]
        self.assertFalse(any(s.entry for s in calculate(damaged)['P08']))

    def test_regression_reentry_is_trailing_and_zero_rms_is_safe(self):
        values=[D(100)+D(i%2)/10 for i in range(65)]+[D(98),D('99.8')]
        r=calculate(bars(values))['P09']
        self.assertEqual(r[-1].entry,1)
        self.assertEqual(r[-2].entry,0)
        self.assertFalse(any(s.entry for s in calculate(bars([100]*100))['P09']))

    def test_frozen_exit_belongs_to_position_not_new_signal(self):
        cfg=step4_settings()
        data=bars([100,100,101,102,102],radius='0')
        sig=[Decision(1,atr=D(10),frozen_exit=('ge',D(101))),
             Decision(1,atr=D(10),frozen_exit=('ge',D(200))),Decision(),Decision(),Decision()]
        r=simulate(data,sig,'P03',cfg,Costs(D(0),D(0),'mid',D(0),D('.01')),'signal',data[0].time,data[-1].time+MINUTE)
        self.assertEqual(r['trades'][0]['exit_time'],data[3].time.isoformat())
        self.assertEqual(r['trades'][0]['reason'],'signal_exit')
        self.assertEqual(len(r['trades']),1)

    def test_rejected_event_is_not_retried_in_either_view(self):
        cfg=step4_settings()
        data=bars([100]*65+[104,101,101,101])
        sig=calculate(data)['P07']
        cfg['account']['risk_fraction']='0.000001'
        r=simulate(data,sig,'P07',cfg,Costs(D('.58'),D('.15'),'mid',D('.00003'),D('.01')),'account',data[0].time,data[-1].time+MINUTE)
        self.assertEqual(r['counts'].get('risk_minimum_skip'),1)
        self.assertEqual(r['trade_count'],0)

    def test_reference_predicates_and_unknown_rejection(self):
        for rule,value,expected in [(('inside',D(1),D(2)),D(1),True),(('lt',D(1)),D(1),False),(('gt',D(1)),D(2),True),(('le',D(1)),D(1),True),(('ge',D(1)),D(1),True)]:
            self.assertEqual(reference_exit(rule,value),expected)
        with self.assertRaises(ValueError):reference_exit(('unknown',),D(1))


class ExpandedExperiment(unittest.TestCase):
    def test_exact_case_inventory_and_seal(self):
        cfg=step4_settings();cases=step4_cases(cfg)
        self.assertEqual(len(cases),1344)
        self.assertEqual(len({(p,n,c.key,v) for p,n,c,v,a,b in cases}),1344)
        self.assertTrue(all(b<=datetime(2026,4,1,tzinfo=timezone.utc) for p,n,c,v,a,b in cases))
        self.assertEqual(cfg['selection']['max_finalists'],0)
        self.assertEqual(cfg['selection']['minimum_active_days'],60)

    def test_no_finalist_even_with_favorable_synthetic_economics(self):
        cfg=step4_settings()
        runs={}
        for p,n,c,v,a,b in step4_cases(cfg):
            runs[p,n,c.key,v]={'net':'100','trade_count':200,'active_days':22,'counts':{},'modeled_max_drawdown':'1','ounce_turnover':400,
                'daily':{'2026-03-02':{'net':'50','trades':100},'2026-03-20':{'net':'50','trades':100}}}
        with patch('mynyra.experiment.lower_expectancy',return_value=D(1)):
            decision=step4_select(runs,cfg)
        self.assertEqual(decision['finalists'],[])
        self.assertEqual(decision['research_priorities'],[])
        self.assertEqual(decision['evaluation'],{'status':'not_opened','reason':'independent_data_unavailable'})
        self.assertTrue(all(r['classification']=='inconclusive' for r in decision['decisions']))

    def test_step4_bootstrap_seed_quantile_and_zero_trade_days(self):
        cfg=step4_settings()['selection']
        self.assertEqual(lower_expectancy({'2026-03-02':{'net':'0','trades':0}},cfg),0)
        self.assertEqual(lower_expectancy({'2026-03-02':{'net':'10','trades':2}},cfg),5)


class ExpandedBoundaryTests(unittest.TestCase):
    def test_short_events_for_all_ten_mechanisms(self):
        fixtures={
            'P01':bars([100]*75+[102],start=START.replace(hour=7)),
            'P02':bars([100]*1440,start=datetime(2026,3,2,tzinfo=timezone.utc))+bars([100]*360+[102],start=datetime(2026,3,3,tzinfo=timezone.utc)),
            'P03':bars([100]*65+[102,100]),
            'P04':bars([100]*141+[102]),
            'P05':bars([D(100)+D(i)/10 for i in range(100)]+[D(108),D(109)]),
            'P06':bars([100]*65+[104]+[104]*5+[105]),
            'P07':bars([100]*65+[104,101]),
            'P08':bars([D(100)+D(i//15)/10 for i in range(909)]+[D(120)],start=START.replace(hour=0),radius='0'),
            'P09':bars([D(100)+D(i%2)/10 for i in range(65)]+[D(98),D('99.8')]),
            'P10':bars([100+i for i in range(90)],start=START.replace(hour=9)),
        }
        for name,data in fixtures.items():
            mirror=[Candle(b.time, D(400)-b.open,D(400)-b.low,D(400)-b.high,D(400)-b.close) for b in data]
            original=calculate(data)[name][-1]
            opposite=calculate(mirror)[name][-1]
            self.assertNotEqual(original.entry,0,name)
            self.assertEqual(opposite.entry,-original.entry,name)

    def test_impulse_expiry_and_invalid_five_bar_flag(self):
        for wait,entry in ((4,1),(5,0)):
            data=bars([100]*65+[104]+[104]*5+[104]*wait+[105])
            self.assertEqual(calculate(data)['P06'][-1].entry,entry)
        for wait,entry in ((4,-1),(5,0)):
            data=bars([100]*65+[104]+[104]*wait+[101])
            self.assertEqual(calculate(data)['P07'][-1].entry,entry)
        data=bars([100]*65+[104,100,104,104,104,104,105])
        self.assertFalse(any(s.entry for s in calculate(data)['P06']))

    def test_setup_cancel_at_common_session_end(self):
        # Arm at 18:58; the return at 18:59 would fill at excluded 19:00.
        data=bars([100]*65+[104,101],start=START.replace(hour=17,minute=53))
        self.assertFalse(any(s.entry for s in calculate(data)['P07']))

    def test_m15_close_not_partial_context_and_setup_reset_each_cohort(self):
        values=[D(100)+D(i//15)/10 for i in range(899)]
        early=bars(values[:898]+[D(120)],start=START.replace(hour=0),radius='0')
        complete=bars(values+[D(120)],start=START.replace(hour=0),radius='0')
        self.assertEqual(calculate(early)['P08'][-1].entry,0)
        self.assertEqual(calculate(complete)['P08'][-1].entry,1)
        data=bars([100]*65+[104]+[104]*5+[105])
        self.assertEqual(calculate(data,start=data[66].time)['P06'][-1].entry,0)

    def test_registered_guards_reject_changed_input_before_price_loading(self):
        from mynyra.config import ProbeError
        from mynyra.experiment import step4_inputs
        cfg=step4_settings()
        with patch('mynyra.experiment.archive_sha256',return_value='wrong'),patch('mynyra.experiment.read_normalized_minutes') as read:
            with self.assertRaises(ProbeError):step4_inputs(cfg)
            read.assert_not_called()

    def test_missing_case_prevents_selection(self):
        with self.assertRaises(KeyError):step4_select({},step4_settings())

    def test_evaluate_does_not_open_inputs(self):
        import tempfile,runpy,sys
        from pathlib import Path
        from mynyra.experiment import ROOT
        module=runpy.run_path(str(ROOT/'scripts/praxis-step4.py'))
        main=module['main']
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'closed.json'
            # Replace only filesystem/Git boundary functions; input loading is
            # forbidden even when a caller presents an arbitrary screen path.
            globals_=main.__globals__
            with patch.dict(globals_,{'private_path':lambda p:p,'step4_provenance':lambda:{'test':'freeze'},
                                     'step4_inputs':lambda cfg:self.fail('evaluation read prices'),
                                     'save':lambda p,v:p.write_text(__import__('json').dumps(v))}),patch('os.umask'),patch.object(sys,'argv',['praxis-step4.py','evaluate','--output',str(output)]):
                main()
            self.assertEqual(__import__('json').loads(output.read_text())['reason'],'independent_data_unavailable')
