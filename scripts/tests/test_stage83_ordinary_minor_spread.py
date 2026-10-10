"""Stage83 ordinary-seat minor-candidate spread: frozen design and flags, closed-form fit, sealed outputs, selection rule."""
import unittest
import numpy as np
from scripts.balance_scale.common import equivalent
from scripts.ordinary_minor_spread import decision as D, evaluation as E, fit as F
from scripts.ordinary_minor_spread.common import PREFIX, DECISION_YEARS, YEARS, ARMS, arms, design, flags, read


def load(name):
    return read(PREFIX + '/' + name)


class FrozenDesign(unittest.TestCase):
    def test_flags_are_the_stage67_sets_unchanged(self):
        primary, sensitivity = flags('primary'), flags('sensitivity')
        self.assertEqual({y: len(v) for y, v in primary.items()}, {2014: 8, 2017: 6, 2020: 10, 2023: 14})
        self.assertEqual(sum(map(len, sensitivity.values())), 17)
        self.assertTrue(all(sensitivity[y] <= primary[y] for y in YEARS))

    def test_contract_pins_arms_rule_and_amendment(self):
        spec = design()
        self.assertEqual(list(arms()), ['control', 'within', 'within_mass', 'within_robust', 'within_mass_robust',
                                        'within17', 'within_mass17', 'within_robust17', 'within_mass_robust17'])
        self.assertEqual(set(ARMS), set(arms()) - {'control'})
        self.assertEqual(spec['decisionYears'], list(DECISION_YEARS))
        self.assertEqual(spec['decision']['qualifies']['minorCoverage80']['band'], [0.74, 0.86])
        self.assertEqual(spec['decision']['qualifies']['majorGuard']['coverage80FloorAbsolute'], 0.70)
        self.assertEqual(spec['amendments'][0]['number'], 1)
        self.assertTrue(spec['amendments'][0]['commitBeforeScoring'])
        self.assertIsNone(spec['decision']['operationalAdoption'])
        self.assertEqual(spec['decisionNumber'], 'D121')


class ClosedFormFit(unittest.TestCase):
    def test_multiplier_is_root_mean_ratio_capped_at_one(self):
        m = F.multiplier({2014: [0.25, 0.25], 2017: [0.25]}, [2014, 2017])
        self.assertAlmostEqual(m['multiplier'], 0.5)
        capped = F.multiplier({2014: [4.0]}, [2014])
        self.assertEqual(capped['multiplier'], 1.0)
        self.assertTrue(capped['capped'])
        self.assertEqual(F.multiplier({}, [])['multiplier'], 1.0)

    def test_robust_multiplier_recovers_gaussian_scale_despite_a_tail(self):
        z = np.random.default_rng(1).normal(0, 0.5, 4001)
        z[:20] = 12.0
        robust = F.multiplier({2014: z}, [2014], robust=True)['multiplier']
        moment = F.multiplier({2014: z ** 2}, [2014])['multiplier']
        self.assertAlmostEqual(robust, 0.5, delta=0.05)
        self.assertGreater(moment, 0.7)

    def test_arm_scales_touch_only_the_requested_components(self):
        fit = {'balance': {'seat': 1.0, 'shared': 0.5}, 'within': {'seat': 2.0, 'shared': 1.0}, 'mass': {'seat': 4.0, 'shared': 2.0}}
        out = E.arm_scales(fit, 0.6, 0.5, 1.0)
        self.assertEqual((out['balance']['seat'], out['balance']['shared']), (0.6, 0.5))
        self.assertEqual((out['within']['seat'], out['within']['shared']), (1.0, 0.5))
        self.assertEqual(out['mass'], fit['mass'])
        self.assertEqual(fit['within']['seat'], 2.0)


class SealedOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit, cls.evaluation, cls.decision = load('fit.json'), load('evaluation.json'), load('decision.json')

    def test_fits_reproduce_and_2014_is_control(self):
        self.assertTrue(equivalent(self.fit, F.build(), 1e-6))
        for kind in ('primary', 'sensitivity'):
            for c in ('within', 'mass'):
                for estimator in ('moment', 'robust'):
                    self.assertEqual(self.fit['folds']['2014'][kind][c][estimator]['multiplier'], 1.0)
                    for year in ('2017', '2020', '2023'):
                        self.assertLessEqual(self.fit['folds'][year][kind][c][estimator]['multiplier'], 1.0)

    def test_flagged_seats_are_identical_to_control_and_arms_share_streams(self):
        self.assertTrue(all(v == 0.0 for v in self.evaluation['flaggedSeatMaximumAbsoluteDifferenceFromControl'].values()))
        control = self.evaluation['records']['control']
        for arm in ARMS:
            kind, _, _ = ARMS[arm]
            rows = self.evaluation['records'][arm]
            self.assertEqual([r['id'] for r in rows], [r['id'] for r in control])
            for c, r in zip(control, rows):
                if not r['narrowed']:
                    self.assertEqual((r['multipliers']['within'], r['multipliers']['mass']), (1.0, 1.0))
                    self.assertEqual(c['groups'], r['groups'])
                self.assertEqual(r['multipliers']['balance'], c['multipliers']['balance'])
        self.assertEqual(sum(r['multipliers']['balance'] == 1.0 for r in control), 38)

    def test_some_seats_regenerate_exactly(self):
        fresh, _ = E.year_task(2023, 0, 16)
        for arm, rows in fresh.items():
            saved = {r['id']: r for r in self.evaluation['records'][arm]}
            for r in rows:
                self.assertTrue(equivalent(saved[r['id']], r, 1e-10))

    def test_decision_reproduces_and_states_a_registered_finding(self):
        self.assertTrue(equivalent(self.decision, D.build(), 1e-9))
        self.assertIn(self.decision['finding'], design()['decision']['findings'])
        self.assertIsNone(self.decision['operationalAdoption'])

    def test_finding_follows_the_recorded_checks(self):
        results = self.decision['candidates']
        qualified = [a for a in design()['decision']['candidateArms'] + ['within_robust', 'within_mass_robust'] if results[a]['qualifies']]
        if qualified:
            self.assertEqual(self.decision['finding'], f"recommend_{self.decision['selectedArm']}_for_james_signoff")
        else:
            self.assertTrue(self.decision['finding'].startswith('keep_control'))
            self.assertIsNone(self.decision['selectedArm'])


class Selection(unittest.TestCase):
    def test_choose_prefers_the_plain_arm_unless_mass_adds_one_percent(self):
        def result(plain, mass, plain_ok=True, mass_ok=True):
            return {'within': {'qualifies': plain_ok, 'minorCRPSPP': {'arm': plain}},
                    'within_mass': {'qualifies': mass_ok, 'minorCRPSPP': {'arm': mass}}}
        group = ('within', 'within_mass')
        self.assertEqual(D.choose(result(1.0, 0.98), group), 'within_mass')
        self.assertEqual(D.choose(result(1.0, 0.995), group), 'within')
        self.assertEqual(D.choose(result(1.0, 0.9, mass_ok=False), group), 'within')
        self.assertEqual(D.choose(result(1.0, 0.9, plain_ok=False), group), 'within_mass')
        self.assertIsNone(D.choose(result(1.0, 0.9, False, False), group))


if __name__ == '__main__':
    unittest.main()
