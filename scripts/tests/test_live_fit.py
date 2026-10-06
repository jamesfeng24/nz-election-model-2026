"""Stage62 live 2026 national poll fit: committed-artifact check and pure-function tests (numpy only; no inference)."""
import dataclasses
import unittest
from datetime import date

import numpy as np

from scripts.polling.live_fit import check, common, prepare, summarize


@dataclasses.dataclass
class FakePoll:
    pollster_raw: str
    date_to: date
    mid_date: date
    shares: dict
    is_election_result: bool = False


class LiveFitTests(unittest.TestCase):
    def test_committed_outputs_are_consistent(self):
        rec, inspected, env = check.run()
        self.assertTrue(all(rec['assertions'].values()))
        self.assertEqual(rec['datasetPolls2026'], 119)
        self.assertEqual({i['arm'] for i in inspected}, set(summarize.ORDER) | {common.ENV_CHECK})

    def test_arm_registry_matches_frozen_design(self):
        self.assertEqual(list(common.ARMS), ['A', 'A2', 'B1', 'B2', 'E', 'T'])
        self.assertEqual(common.ARMS['A']['seed'], 2034)
        self.assertEqual(common.ARMS['A2']['seed'], 2035)
        self.assertEqual(common.ARMS['B1']['window'], '2026-06-01')
        self.assertEqual(common.ARMS['B2']['window'], '2026-08-11')
        self.assertEqual((common.CUTOFF, common.TARGET_YEAR), ('2026-10-06', 2026))
        self.assertEqual(common.PRIMARY, {'chains': 4, 'warmup': 2000, 'samples': 2000, 'target_accept': .95, 'max_tree_depth': 12})
        self.assertEqual(common.RETRY['warmup'], 4000)

    def test_arm_transformations_touch_only_the_current_cycle(self):
        old = FakePoll('Curia', date(2023, 5, 1), date(2023, 5, 1), {'National': .4})
        early = FakePoll('Curia', date(2026, 3, 1), date(2026, 3, 1), {'National': .3})
        late = FakePoll('Anacta', date(2026, 9, 10), date(2026, 9, 7), {'National': .3})
        result = FakePoll('2023 election result', date(2023, 10, 14), date(2023, 10, 14), {'National': .38}, True)
        polls = [old, early, late, result]
        self.assertEqual(len(prepare.arm_polls(polls, 'A')), 4)
        b2 = prepare.arm_polls(polls, 'B2')
        self.assertIn(old, b2); self.assertIn(result, b2); self.assertNotIn(early, b2); self.assertIn(late, b2)
        merged = prepare.arm_polls(polls, 'T')
        self.assertEqual(sorted(p.pollster_raw for p in merged if p.date_to.year == 2026), ['Curia', 'Talbot Mills'])

    def test_evidence_grade_arm_drops_exactly_the_flagged_waves(self):
        flagged = {prepare.panel_key(r) for r in prepare.panel_records() if r.get('evidenceGrade') == 'aggregator_only'}
        self.assertEqual(len(flagged), 2)
        may = FakePoll('Talbot Mills', date(2024, 5, 10), date(2024, 5, 5), {'National': .35, 'Labour': .32})
        april = FakePoll('Talbot Mills', date(2026, 4, 16), date(2026, 4, 16), {'National': .29, 'Labour': .36, 'Green': .07, 'ACT': .08, 'NZ First': .15})
        keep = FakePoll('Talbot Mills', date(2026, 3, 12), date(2026, 3, 7), {'National': .32, 'Labour': .35, 'Green': .11, 'ACT': .07, 'NZ First': .11})
        kept = prepare.arm_polls([may, april, keep], 'E')
        self.assertEqual(kept, [keep])

    def test_state_summary_and_margin(self):
        x = np.tile([.3, .2, .5], (1000, 1))
        s = summarize.state_summary(x, ['NAT', 'LAB', 'OTH'])
        self.assertAlmostEqual(s['NAT']['mean'], 30.0); self.assertAlmostEqual(s['LAB']['sd'], 0.0)
        self.assertAlmostEqual(summarize.margin_summary(x, ['NAT', 'LAB', 'OTH'])['mean'], 10.0)

    def test_house_effect_is_relative_to_the_equal_weight_mean(self):
        d, k = 200, 3
        pi = np.tile([.4, .35, .25], (d, 1))
        off = np.zeros((d, 2, k)); off[:, 0, 0] = .1; off[:, 1, 0] = -.1
        eff = summarize.house_effects(off, pi, ['P1', 'P2'], ['NAT', 'LAB', 'OTH'])
        self.assertGreater(eff['P1']['NAT']['effectPP']['mean'], 0)
        self.assertLess(eff['P2']['NAT']['effectPP']['mean'], 0)
        self.assertAlmostEqual(eff['P1']['NAT']['effectPP']['mean'], -eff['P2']['NAT']['effectPP']['mean'], delta=0.1)  # softmax is not exactly symmetric
        zero = summarize.house_effects(np.zeros((d, 2, k)), pi, ['P1', 'P2'], ['NAT', 'LAB', 'OTH'])
        self.assertAlmostEqual(zero['P1']['NAT']['effectPP']['mean'], 0.0)

    def test_comparison_flags_follow_the_frozen_thresholds(self):
        def arm(shift, width):
            row = lambda m: {'mean': m, 'sd': 2.0, 'q05': m - 1.645 * 2 * width, 'q25': m, 'q50': m, 'q75': m, 'q95': m + 1.645 * 2 * width}
            st = {c: row(30.0 + (shift if c == 'NAT' else 0)) for c in ('NAT', 'LAB')}
            mg = {'mean': 0.0, 'sd': 1.0, 'q05': 0, 'q50': 0, 'q95': 0}
            return {'status': 'accepted', 'codes': ['NAT', 'LAB'], 'lastData': st, 'electionWeek': st, 'marginNatMinusLabLastData': mg, 'marginNatMinusLabElectionWeek': mg}
        out = summarize.compare({'A': arm(0, 1), 'X': arm(0.5, 1.1), 'Y': arm(1.2, 1.0), 'Z': arm(0, 1.3)})
        self.assertFalse(out['X']['material']); self.assertTrue(out['Y']['material']); self.assertTrue(out['Z']['material'])

    def test_outputs_may_not_contain_probability_or_seat_fields(self):
        summarize.scan({'lastData': {'NAT': {'mean': 1.0}}})
        for bad in ('winProbability', 'seatCount', 'blocShare', 'governmentFormation'):
            with self.assertRaises(ValueError):
                summarize.scan({bad: 1})

    def test_close_tolerates_float_noise_only(self):
        self.assertTrue(summarize.close({'a': [1.0, 2.0]}, {'a': [1.0 + 1e-12, 2.0]}))
        self.assertFalse(summarize.close({'a': 1.0}, {'a': 1.001}))
        self.assertFalse(summarize.close({'a': 1.0}, {'b': 1.0}))


if __name__ == '__main__':
    unittest.main()
