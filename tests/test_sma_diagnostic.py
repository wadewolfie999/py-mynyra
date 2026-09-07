"""Accounting attribution and counterfactual isolation for the research script."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

from twisted.trial import unittest
from tests.test_experiment import candle, D, Decision
from mynyra.strategies import MINUTE
from mynyra.experiment import DEFAULT_CONFIG, settings
from mynyra import simulation

spec = importlib.util.spec_from_file_location('sma_diagnostic', Path(__file__).resolve().parents[1]/'scripts/diagnose-sma.py')
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


class DiagnosticTests(unittest.TestCase):
    def test_attribution_distinguishes_sequence_exit_and_size(self):
        def trade(time, net, q=1):
            return dict(entry_time=time, direction=1, net=D(net), ounces=q)
        signal = dict(net=D(-3), trades=[trade('a', 2), trade('b', -5)])
        account = dict(net=D(7), trades=[trade('a', 6, 2), trade('c', 1)])
        result = diag.decomposition(signal, account)
        self.assertEqual(result['remove_signal_only_net'], 5)
        self.assertEqual(result['add_account_only_unit_net'], 1)
        self.assertEqual(result['common_entry_exit_effect'], 1)
        self.assertEqual(result['additional_ounce_effect'], 3)
        self.assertEqual(result['account_sequence_one_ounce_net'], 4)

    def test_duplicate_entry_identity_is_rejected(self):
        t = dict(entry_time='a', direction=1, net='1', ounces=1)
        self.assertRaises(ValueError, diag.decomposition,
                          dict(net='2', trades=[t,t]), dict(net='0', trades=[]))

    def test_observer_counts_execution_and_skip_without_changing_replay(self):
        cfg = settings(DEFAULT_CONFIG)
        costs = simulation.Costs(D('0.58'), D('0.15'), 'mid', D('0.00003'), D('0.01'))
        bars = [candle(i) for i in range(6)]
        signals = [Decision(1, atr=D(10)), Decision(1, atr=D(1)),
                   Decision(exit_long=True), Decision(), Decision(), Decision()]
        start, end = bars[0].time, bars[-1].time+MINUTE
        expected = simulation.simulate(bars, signals, 'sma_cross', cfg, costs, 'account', start, end)
        actual, events = diag.observed_account(bars, signals, cfg, costs, start, end)
        self.assertEqual(actual, expected)
        self.assertEqual([e['reason'] for e in events], ['risk_minimum_skip', 'executed'])
        lookup = {b.time:i for i,b in enumerate(bars)}
        isolated = diag.isolated_attempt(bars, signals, lookup, events[0], cfg, costs, end)
        self.assertEqual(isolated['entry_time'], events[0]['time'])
        self.assertEqual(isolated['ounces'], 1)
        # Second entry instruction must not open a second counterfactual trade.
        self.assertEqual(isolated['exit_time'], bars[3].time.isoformat())

    def test_observer_restores_sizing_function_after_failure(self):
        original = simulation.position_size
        with patch.object(simulation, 'simulate', side_effect=RuntimeError('synthetic')):
            self.assertRaises(RuntimeError, diag.observed_account, [], [], {}, None, None, None)
        self.assertIs(simulation.position_size, original)
