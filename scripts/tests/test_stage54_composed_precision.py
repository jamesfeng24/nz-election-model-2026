"""Stage54 composed Monte Carlo precision: stream substitution, estimators, frozen rules and sealed outputs."""
import json
import math
import unittest
import numpy as np
from scripts.composed_precision import decision as D
from scripts.composed_precision.common import ROOT, PREFIX, design, equivalent, YEARS
from scripts.composed_precision.evaluation import gap
from scripts.composed_precision.simulate import winner_probabilities
from scripts.composed_precision.stream import (BLOCK, POOL, block_uniforms, chain_of, national_block, pool_order, scrambled, seed)
from scripts.uncertainty_tails import streams as base


class Streams(unittest.TestCase):
    def test_block_zero_is_the_stage46_stream_exactly(self):
        original = base.uniforms(2017, BLOCK)
        mine = block_uniforms(2017, BLOCK, 0)
        self.assertEqual(original[0], mine[0])
        self.assertTrue(np.array_equal(original[1], mine[1]))
        self.assertGreater(np.max(np.abs(block_uniforms(2017, BLOCK, 1)[1] - mine[1])), 0.01)
        self.assertEqual(seed(2020, 0), 462066)
        self.assertEqual(seed(2020, 3), 465066)

    def test_substitution_reaches_noise_and_is_restored(self):
        inventory = json.loads((ROOT / 'data/processed/uncertainty/inventory.json').read_text())
        row = next(r for r in inventory['candidateRecords'] if r['targetYear'] == 2017)
        scales = {'balance': {'shared': .1, 'seat': .2}, 'mass': {'shared': .1, 'seat': .2}, 'within': {'shared': .1, 'seat': .2}}
        before = base.noise(row, scales, BLOCK)[0]['balance']
        with scrambled(0):
            same = base.noise(row, scales, BLOCK)[0]['balance']
        with scrambled(2):
            other = base.noise(row, scales, BLOCK)[0]['balance']
        after = base.noise(row, scales, BLOCK)[0]['balance']
        self.assertTrue(np.array_equal(before, same) and np.array_equal(before, after))
        self.assertFalse(np.array_equal(before, other))

    def test_blocks_are_disjoint_and_cover_the_cached_subset(self):
        party = {'ids': None}
        order = pool_order(2017, party)
        flat = np.concatenate(order)
        self.assertEqual(len(order), POOL // BLOCK)
        self.assertEqual(sorted(flat.tolist()), list(range(POOL)))

    def test_national_block_zero_is_the_stage48_frame_and_chains_are_balanced(self):
        inventory = json.loads((ROOT / 'data/processed/uncertainty/inventory.json').read_text())
        party = next(r for r in inventory['partyRecords'] if r['targetYear'] == 2017)
        from scripts.balance_scale.simulate import national_inputs
        draws, ids = national_block(2017, party, 0)
        self.assertTrue(np.array_equal(draws, national_inputs(2017, party, BLOCK)))
        pool = [i for b in range(POOL // BLOCK) for i in national_block(2017, party, b)[1]]
        self.assertEqual(len(set(pool)), POOL)
        counts = {c: sum(chain_of(i) == c for i in pool) for c in (1, 2, 3, 4)}
        self.assertEqual(counts, {1: 1024, 2: 1024, 3: 1024, 4: 1024})
        self.assertEqual(chain_of('gauss-2017-attempt1-chain3-draw0012'), 3)


class Estimators(unittest.TestCase):
    def test_gap_is_structural_and_numeric(self):
        self.assertEqual(gap({'a': [1., 2.]}, {'a': [1., 2.5], 'b': 1}), .5)
        self.assertEqual(gap({'a': [1.]}, {'a': [1., 2.]}), math.inf)
        self.assertEqual(gap({'a': 1.}, {}), math.inf)
        self.assertEqual(gap({'a': True}, {'a': False}), 1.)

    def test_winner_probabilities_split_ties_and_sum_to_one(self):
        q = np.array([[.5, .3, .2], [.4, .4, .2], [.1, .2, .7], [.3, .3, .4]])
        p = winner_probabilities(q)
        self.assertAlmostEqual(p.sum(), 1.)
        np.testing.assert_allclose(p, [.25 + .125, .125, .5])

    def test_power_of_two_requirement_and_floor(self):
        self.assertEqual(D.next_power_of_two(513, 512), 1024)
        self.assertEqual(D.next_power_of_two(10, 512), 512)
        self.assertEqual(D.next_power_of_two(1024, 512), 1024)

    def test_settled_states(self):
        self.assertEqual(D.state((-.05, -.02), .01), 'SETTLED_MATERIAL')
        self.assertEqual(D.state((-.015, -.005), .01), 'SETTLED_SIGN')
        self.assertEqual(D.state((-.02, .01), .01), 'UNRESOLVED')
        self.assertEqual(D.state((.02, .05), .01), 'SETTLED_MATERIAL')

    def test_estimate_uses_t_interval_on_block_values(self):
        spec = design()
        e = D.estimate([-.02, -.01, -.03, -.02], spec)
        self.assertAlmostEqual(e['mean'], -.02)
        self.assertAlmostEqual(e['standardError'], np.std([-.02, -.01, -.03, -.02], ddof=1) / 2)
        half = 3.182446305 * e['standardError']
        self.assertAlmostEqual(e['interval95'][1] - e['interval95'][0], 2 * half, places=6)

    def test_spread_is_sample_sd_per_column(self):
        np.testing.assert_allclose(D.spread([[1., 10.], [3., 10.], [5., 10.]]), [2., 0.])

    def test_doubling_gate_marks_failure(self):
        spec = design()
        ladder = lambda x: {'meansPP': [x], 'crps': [x], 'energy': x, 'width50': [x], 'width80': [x], 'width90': [x]}
        ev = {'representatives': {'s': {'ladder': {'512': ladder(1.), '1024': ladder(1.2), '2048': ladder(1.4), '4096': ladder(1.6)}}}}
        result = D.gate(ev, spec)
        self.assertEqual(result['verdict'], 'CAPS_NOT_ATTAINABLE_WITHIN_CACHED_BANK')
        ev['representatives']['s']['ladder']['4096'] = ladder(1.41)
        self.assertEqual(D.gate(ev, spec)['verdict'], 'CAPS_MET_AT_CACHED_BANK')

    def test_requirement_scales_with_squared_ratio(self):
        spec = design()
        stats = {n: {'representatives': {'max': 0.1}} for n in spec['requirement']['quantities']}
        out = D.requirement(stats, spec)
        # 512 * (3 * 0.1 / 0.05)^2 = 18432 -> 32768 for the 0.05pp caps
        self.assertEqual(out['mean']['requiredDraws'], 32768)
        self.assertAlmostEqual(out['crps']['unroundedDraws'], 512 * 36., places=6)
        self.assertEqual(out['energy']['requiredDraws'], 8192)


class Contract(unittest.TestCase):
    def test_caps_are_the_frozen_stage48_caps_and_documented(self):
        spec = design()
        inherited = json.loads((ROOT / 'data/processed/balance-scale/design-contract.json').read_text())['gatesPP']
        for key, value in spec['gatesPP'].items():
            self.assertEqual(value, inherited[key])
        text = (ROOT / 'docs/stage54-composed-precision-design.md').read_text()
        for needle in ('0.05pp', '0.1pp', '0.5pp', '460046 + year + 1000 s', 'CAPS_MET_AT_CACHED_BANK', 'CAPS_NOT_ATTAINABLE_WITHIN_CACHED_BANK',
                       'SETTLED_MATERIAL', '120 CPU minutes', '0.01pp'):
            self.assertIn(needle, text)
        self.assertIsNone(spec['operationalAdoption'])
        self.assertEqual(spec['ladder'], [512 * 2 ** k for k in range(4)])
        self.assertEqual(spec['blocks'], {'allSeats': 4, 'representatives': 8, 'blockZeroIsStage48Frame': True})
        self.assertEqual(spec['years'], list(YEARS))

    def test_equivalence_tolerance(self):
        self.assertTrue(equivalent({'a': [1.0, 2.0]}, {'a': [1.0 + 1e-12, 2.0]}))
        self.assertFalse(equivalent({'a': 1.0}, {'a': 1.1}))


class SealedOutputs(unittest.TestCase):
    def read(self, name):
        path = ROOT / PREFIX / name
        return json.loads(path.read_text()) if path.exists() else None

    def test_decision_follows_the_frozen_rule(self):
        d, ev = self.read('decision.json'), self.read('evaluation.json')
        if d is None or ev is None:
            self.skipTest('Stage54 not generated')
        self.assertEqual(d['harness']['verdict'], 'MATCHES_STAGE48')
        self.assertEqual(d['gateVerdict'], d['gate']['verdict'])
        last = d['gate']['rounds'][-1]
        self.assertEqual(last['later'], 4096)
        self.assertEqual(d['gateVerdict'] == 'CAPS_MET_AT_CACHED_BANK', last['allPassed'])
        self.assertEqual(len(ev['seats']), 193)
        self.assertEqual(len(ev['representatives']), 9)
        self.assertIsNone(d['operationalAdoption'])
        for seat in ev['seats'].values():
            self.assertEqual(sorted(seat['blocks']), ['0', '1', '2', '3'])
            if 'representativeBlocks' in seat:
                self.assertEqual(sorted(seat['representativeBlocks']), ['4', '5', '6', '7'])
                self.assertEqual(sorted(seat['layerOnly']), ['10', '8', '9'])


if __name__ == '__main__':
    unittest.main()
