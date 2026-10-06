"""Stage67 ordinary/exceptional balance scale: frozen flags and rule, harness equality with Stage60, sealed outputs."""
import unittest
import numpy as np
from scripts.balance_scale.common import equivalent
from scripts.exceptional_balance_scale import decision as D, evaluation as E, fit as F
from scripts.exceptional_balance_scale.common import PREFIX, design, flags, read, YEARS


def load(name):
    return read(PREFIX + '/' + name)


class FrozenDesign(unittest.TestCase):
    def test_flag_sets_are_frozen(self):
        primary, sensitivity = flags('primary'), flags('sensitivity')
        self.assertEqual({y: len(v) for y, v in primary.items()}, {2014: 8, 2017: 6, 2020: 10, 2023: 14})
        self.assertEqual(sum(map(len, sensitivity.values())), 17)
        self.assertTrue(all(sensitivity[y] <= primary[y] for y in YEARS))

    def test_contract_pins_arms_rule_and_amendment(self):
        spec = design()
        self.assertEqual(spec['armOrder'], ['control', 'free', 'twogroup', 'twogroup_exc1', 'twogroup17'])
        self.assertEqual(spec['decision']['candidateArms'], ['twogroup', 'twogroup_exc1'])
        self.assertEqual(spec['decision']['improves']['crpsMaterialityPP'], 0.01)
        floors = spec['decision']['groupCoverageFloors']
        self.assertEqual((floors['ordinary']['nominalMargin'], floors['exceptional']['nominalMargin']), (0.10, 0.15))
        self.assertEqual(spec['amendments'][0]['number'], 1)
        self.assertIsNone(spec['decision']['operationalAdoption'])


class SealedOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit, cls.evaluation, cls.decision = load('fit.json'), load('evaluation.json'), load('decision.json')

    def test_fits_reproduce_and_pass_independent_checks(self):
        self.assertTrue(equivalent(self.fit, F.build(), 1e-6))
        for year in ('2017', '2020', '2023'):
            for arm in ('twogroup', 'twogroup17', 'twogroup_exc1'):
                r = self.fit['folds'][year][arm]
                self.assertLessEqual(r['powell']['objectiveDifference'], 1e-6)
                self.assertLessEqual(r['centralDifferenceGradientMaxDifference'], 1e-6)
                self.assertFalse(any(r['boundContact']))
        self.assertEqual(self.fit['folds']['2014']['twogroup']['ordinaryMultiplier'], 1.0)

    def test_control_and_free_equal_stage60_seat_by_seat(self):
        stage60 = read('data/processed/balance-shrink/evaluation.json')['records']
        for arm in ('control', 'free'):
            for x, y in zip(stage60[arm], self.evaluation['records'][arm]):
                self.assertEqual((x['id'], x['crpsPP'], x['energyPP']), (y['id'], y['crpsPP'], y['energyPP']))

    def test_exc1_holds_flagged_seats_at_the_frozen_scale(self):
        for r in self.evaluation['records']['twogroup_exc1']:
            if r['exceptional']:
                self.assertEqual(r['multiplier'], 1.0)
        self.assertLessEqual(self.evaluation['maximumDrawGapAcrossArms'], 1e-12)

    def test_two_seats_regenerate_exactly(self):
        records = self.evaluation['records']['control']
        picks = [next(r['id'] for r in records if r['year'] == 2023 and r['exceptional']),
                 next(r['id'] for r in records if r['year'] == 2023 and not r['exceptional'])]
        fresh, _, _ = E.year_task(2023, only=set(picks))
        for arm, rows in fresh.items():
            saved = {r['id']: r for r in self.evaluation['records'][arm]}
            for r in rows:
                self.assertTrue(equivalent(saved[r['id']], r, 1e-10))

    def test_decision_reproduces_and_states_finding(self):
        self.assertTrue(equivalent(self.decision, D.build(), 1e-10))
        self.assertIn(self.decision['finding'], design()['decision']['findings'])
        self.assertIsNone(self.decision['operationalAdoption'])


class Selection(unittest.TestCase):
    def test_selection_rule(self):
        q = lambda ok, label: {'qualifies': ok, 'label': label}
        self.assertEqual(D.select({'twogroup': q(True, 'IMPROVES'), 'twogroup_exc1': q(True, 'IMPROVES')}, {'label': 'NEGLIGIBLE'}),
                         'recommend_twogroup_exc1_for_james_signoff')
        self.assertEqual(D.select({'twogroup': q(True, 'IMPROVES'), 'twogroup_exc1': q(True, 'IMPROVES')}, {'label': 'IMPROVES'}),
                         'recommend_twogroup_for_james_signoff')
        self.assertEqual(D.select({'twogroup': q(False, 'IMPROVES'), 'twogroup_exc1': q(False, 'NEGLIGIBLE')}, {'label': 'MIXED'}),
                         'floor_blocked_report_to_james')
        self.assertEqual(D.select({'twogroup': q(False, 'NEGLIGIBLE'), 'twogroup_exc1': q(False, 'NEGLIGIBLE')}, {'label': 'MIXED'}),
                         'negligible_keep_single_scale')


if __name__ == '__main__':
    unittest.main()
