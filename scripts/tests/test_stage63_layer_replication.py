"""Stage63 layer replication: exact solve reuse, stream prefix, frozen rules on synthetic fixtures and sealed outputs.

The synthetic seats below are labelled test fixtures; nothing here is written to an application result."""
import json
import math
import unittest
import numpy as np
from scripts.layer_replication import decision as D
from scripts.layer_replication.common import ROOT, PREFIX, design, shape, QUANTITIES
from scripts.layer_replication.evaluation import gap, spread, populations
from scripts.layer_replication.simulate import reused_solves, replicate_bank
from scripts.composed_precision.stream import block_uniforms, national_block
from scripts.composed_precision.evaluation import year_inputs


def record(rng, k, scale=1.):
    win = rng.dirichlet(np.ones(k))
    return {'meansPP': (rng.normal(size=k) * scale).tolist(), 'crps': (np.abs(rng.normal(size=k)) * scale).tolist(), 'energy': float(abs(rng.normal())),
            'width50': (np.abs(rng.normal(size=k))).tolist(), 'width80': np.abs(rng.normal(size=k)).tolist(), 'width90': np.abs(rng.normal(size=k)).tolist(),
            'win': win.tolist()}


def synthetic_seat(kind='rep', replicates=8, k=3, seed=0):
    rng = np.random.default_rng(seed)
    singles = [record(rng, k, .1) for _ in range(replicates)]

    def average(items):
        return {q: (np.mean([r[q] for r in items], axis=0).tolist() if q != 'energy' else float(np.mean([r[q] for r in items]))) for q in (*QUANTITIES, 'win')}
    groups, m = {}, 1
    while m < replicates:
        groups[str(m)] = [average(singles[g * m:(g + 1) * m]) for g in range(replicates // m)]
        m *= 2
    blocks = [{'pooled': average([record(rng, k, .1) for _ in range(2)]), 'layerSd': spread(singles)} for _ in range(8)]
    return {'kind': kind, 'year': 2017, 'ids': list('abc'[:k]), 'groups': ['national', 'labour', 'other'][:k], 'replicates': replicates,
            'groupBanks': groups, 'full': average(singles), 'blocks': blocks}


class Solves(unittest.TestCase):
    def test_reused_solves_are_bit_identical_and_actually_reused(self):
        ctx = year_inputs(2017)
        row = ctx['rows'][0]
        cid = row['targetElectorateId']
        national, _ = national_block(2017, ctx['first'], 0, 4096)
        arguments = lambda s: (row, ctx['parties'][cid], national[:64], ctx['pfit'], ctx['fit'], s)
        plain = [replicate_bank(*arguments(s))[0] for s in (3, 4)]
        with reused_solves() as counts:
            cached = [replicate_bank(*arguments(s))[0] for s in (3, 4)]
        self.assertTrue(all(np.array_equal(a, b) for a, b in zip(plain, cached)))
        self.assertGreaterEqual(counts['hits'], 1)  # the second replicate reuses the local-layer solve
        self.assertFalse(np.array_equal(cached[0], cached[1]))

    def test_substitution_is_restored_after_the_context(self):
        from scripts.uncertainty_expectation import simulation
        before = simulation.solve_locations
        with reused_solves():
            self.assertIsNot(simulation.solve_locations, before)
        self.assertIs(simulation.solve_locations, before)


class Streams(unittest.TestCase):
    def test_first_512_points_of_a_4096_replicate_are_the_stage54_stream(self):
        for r in (0, 8):
            short, long = block_uniforms(2017, 512, r), block_uniforms(2017, 4096, r)
            self.assertEqual(short[0], long[0])
            self.assertTrue(np.array_equal(short[1], long[1][:512]))
        self.assertGreater(np.max(np.abs(block_uniforms(2017, 4096, 1)[1] - block_uniforms(2017, 4096, 2)[1])), .01)

    def test_populations_match_the_frozen_design(self):
        items = populations()
        self.assertEqual(sum(i[0] == 'rep' for i in items), 9)
        self.assertEqual([i[2] for i in items if i[0] == 'panel'], design()['populations']['winPanel']['seats'])
        reps = {i[2] for i in items if i[0] == 'rep'}
        self.assertTrue(reps.isdisjoint(i[2] for i in items if i[0] == 'panel'))
        self.assertTrue(all(i[3] == 64 and i[4] == 16 for i in items if i[0] == 'rep'))


class Rules(unittest.TestCase):
    def test_next_power_of_two(self):
        self.assertEqual([D.next_power_of_two(x) for x in (0.2, 1, 1.01, 5, 64)], [1, 1, 2, 8, 64])

    def test_gap_and_shape(self):
        mine = {'meansPP': [1., 2.], 'crps': [1.], 'energy': 1., 'width50': [1.], 'width80': [1.], 'width90': [1.], 'win': [1.]}
        theirs = {'meanPP': [1., 2.5], 'crpsPP': [1.], 'energyPP': 1., 'width50': [1.], 'width80': [1.], 'width90': [1.], 'win': [1.]}
        self.assertEqual(gap(mine, theirs), .5)
        theirs['crpsPP'] = [1., 1.]
        self.assertEqual(gap(mine, theirs), math.inf)
        self.assertEqual(shape({'a': [1., 2.], 'b': 'x'}), {'a': ['number', 'number'], 'b': 'str'})

    def test_spread_is_the_ddof_one_sd(self):
        rng = np.random.default_rng(1)
        records = [record(rng, 3) for _ in range(5)]
        got = spread(records)
        self.assertTrue(np.allclose(got['crps'], np.std([r['crps'] for r in records], axis=0, ddof=1)))
        self.assertAlmostEqual(got['energy'], float(np.std([r['energy'] for r in records], ddof=1)))

    def test_layer_gate_requirement_and_scaling_on_synthetic_banks(self):
        spec = design()
        ev = {'seats': {f's{i}': synthetic_seat(replicates=64, seed=i) for i in range(2)}}
        rounds = D.layer_gate(ev, spec)
        self.assertEqual([r['arm'] for r in rounds], [2, 4, 8, 16, 32, 64])
        manual = max(float(np.max(np.abs(np.array(s['full']['crps']) - np.array(s['groupBanks']['32'][0]['crps'])))) for s in ev['seats'].values())
        self.assertAlmostEqual(rounds[-1]['changesPP']['crps'], manual)
        need = D.requirement(ev, spec)
        s1 = max(float(np.max(D.single_sd(s, 'crps'))) for s in ev['seats'].values())
        self.assertEqual(need['crps']['requiredReplicates'], D.next_power_of_two((3 * s1 / .05) ** 2))
        ratio = D.scaling(ev, spec)
        self.assertTrue(all(.5 < ratio[m]['crps']['medianScaledRatio'] < 1.6 for m in ('1', '2', '4', '8', '16', '32')))  # i.i.d. synthetic layer noise

    def test_national_floor_is_zero_when_blocks_differ_only_by_layer_noise(self):
        seat = synthetic_seat(replicates=8, seed=3)
        for b in seat['blocks']:
            b['pooled'] = dict(seat['full'])
        floor, raw = D.floor_variance(seat, 'crps')
        self.assertTrue(np.all(floor == 0))
        self.assertTrue(np.all(raw <= 0))

    def test_win_probability_standard_errors_follow_the_formula(self):
        spec = design()
        ev = {'seats': {'a': synthetic_seat(replicates=64, seed=5), 'p': synthetic_seat('panel', 8, seed=6)}}
        w = D.win_probability(ev, spec)['all']
        self.assertAlmostEqual(w['standardErrorAtHalf']['4']['relativeToPool'], math.sqrt(.25 * w['layerDesignEffect'] / (4096 * 4)))
        self.assertGreaterEqual(w['standardErrorAtHalf']['1']['relativeToPopulation'], w['standardErrorAtHalf']['1']['relativeToPool'])
        self.assertGreaterEqual(w['seatCandidates'], 0)

    def test_equivalence_flags_a_shifted_half(self):
        spec = design()
        seats = {f's{i}': synthetic_seat(replicates=64, seed=10 + i) for i in range(3)}
        ok = D.equivalence({'seats': seats}, spec)
        self.assertEqual(ok['verdict'], 'EQUIVALENT')
        bad = {k: json.loads(json.dumps(s)) for k, s in seats.items()}
        for s in bad.values():
            s['groupBanks']['32'][0]['crps'] = [v + 5 for v in s['groupBanks']['32'][0]['crps']]
        self.assertEqual(D.equivalence({'seats': bad}, spec)['verdict'], 'FLAG')


class Sealed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / PREFIX / 'decision.json').read_text())
        cls.spec = design()

    def test_design_is_frozen_and_does_not_adopt(self):
        self.assertEqual(self.spec['stage'], 63)
        self.assertIsNone(self.spec['operationalAdoption'])
        self.assertEqual(self.spec['gatesPP'], {'mean': .05, 'crps': .05, 'energy': .1, 'width50': .5, 'width80': .5, 'width90': .5})
        self.assertEqual(self.spec['arms']['nested'], [1, 2, 4, 8, 16, 32, 64])
        self.assertIsNone(self.d['operationalAdoption'])

    def test_harness_reproduces_stage54_exactly(self):
        self.assertEqual(self.d['harness']['verdict'], 'MATCHES_STAGE54')
        self.assertEqual(self.d['harness']['maxAbsDifference'], 0.)
        self.assertEqual(self.d['harness']['seats'], 18)

    def test_verdict_follows_the_frozen_rule(self):
        g = self.d['gateB']
        sigma = max(v['requiredReplicates'] for v in self.d['requirement'].values())
        self.assertEqual(g['sigmaRequiredReplicates'], sigma)
        safe = [m for m in g['passingArms'] if m >= sigma]
        expected = ('CAPS_MET_BY_REPLICATION' if safe and sigma <= 64 else 'CAPS_MET_NOT_3SIGMA_SAFE' if g['passingArms'] else 'CAPS_NOT_MET_BY_64')
        self.assertEqual(g['verdict'], expected)
        self.assertEqual(self.d['gateBVerdict'], expected)

    def test_no_data_sources_edit_or_new_inference(self):
        m = json.loads((ROOT / PREFIX / 'manifest.json').read_text())
        self.assertFalse(m['dataSourcesJsonTouched'] or m['newSourcesOrAcquisition'] or m['newNationalInference'])
        v = json.loads((ROOT / PREFIX / 'verification.json').read_text())
        self.assertTrue(v['passed'])


if __name__ == '__main__':
    unittest.main()
