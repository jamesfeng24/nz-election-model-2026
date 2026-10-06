"""Numerical-law, chronology and attribution checks without historical rebuilding."""
from copy import deepcopy
from unittest.mock import patch
import unittest
import numpy as np
from scripts.uncertainty_expectation import attribution, construction, simulation, structural_diagnostics, pair_widths
from scripts.uncertainty_expectation.common import read, INVENTORY, SCALES
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty_revision.coordinates import partition
from scripts.uncertainty_tails.streams import noise


class ExpectationPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = read(INVENTORY)
        cls.scales = read(SCALES)
        cls.candidate = next(r for r in cls.inventory['candidateRecords'] if r['targetYear'] == 2023)
        cls.party = next(r for r in cls.inventory['partyRecords'] if r['targetElectorateId'] == cls.candidate['targetElectorateId'])
        cls.cs = scale_for(cls.scales, 'candidate', 2023)['scales']
        cls.ps = scale_for(cls.scales, 'local_party', 2023)['scales']

    def test_actual_pipeline_ignores_candidate_and_party_outcomes(self):
        national = np.broadcast_to(self.party['mean'], (8, len(self.party['mean'])))
        q, meta = simulation.composed(self.party, self.candidate, national, self.ps, self.cs)
        c, p = deepcopy(self.candidate), deepcopy(self.party)
        c['actual'], p['actual'] = list(reversed(c['actual'])), list(reversed(p['actual']))
        c['winnerId'] = 'counterfactual'
        other, details = simulation.composed(p, c, national, self.ps, self.cs)
        np.testing.assert_array_equal(q, other)
        self.assertEqual(meta, details)

    def test_component_batch_prefix_and_zero_faces(self):
        a, _ = simulation.component(self.candidate, self.cs, 16)
        b, _ = simulation.component(self.candidate, self.cs, 32)
        np.testing.assert_allclose(a, b[:16], atol=1e-12, rtol=0)
        np.testing.assert_allclose(a.sum(axis=1), 1, atol=1e-14, rtol=0)
        self.assertTrue(np.all(a >= 0))
        row = dict(self.candidate, mean=np.eye(1, len(self.candidate['ids']))[0].tolist())
        q, _ = simulation.component(row, self.cs, 16)
        np.testing.assert_array_equal(q, np.broadcast_to(row['mean'], q.shape))

    def test_all_saved_scale_windows_are_earlier_and_fixed(self):
        for folds in self.scales['folds'].values():
            for f in folds:
                self.assertTrue(all(y < f['targetYear'] for y in f['trainingYears']))
        self.assertEqual(scale_for(self.scales, 'candidate', 2014)['trainingYears'], [])
        self.assertNotIn(2011, [f['targetYear'] for f in self.scales['folds']['candidate']])

    def test_policy_removes_one_block_without_mutating_control(self):
        oldp, oldc = deepcopy(self.ps), deepcopy(self.cs)
        p, c = attribution.policy_scales('no_candidate_seat', self.ps, self.cs)
        self.assertEqual(p, self.ps)
        for direction in c:
            self.assertEqual(c[direction]['seat'], 0)
            self.assertEqual(c[direction]['shared'], self.cs[direction]['shared'])
        self.assertEqual(self.ps, oldp)
        self.assertEqual(self.cs, oldc)
        with self.assertRaises(ValueError):
            attribution.policy_scales('undocumented', self.ps, self.cs)

    def test_total_variance_matches_independent_scalar_identity(self):
        p = np.tile(self.candidate['mean'], (8, 1))
        q, _ = simulation.invert(p, self.candidate, self.cs, 8)
        value = attribution.total_variance(p, self.candidate['groups'], self.cs, q)
        for g in value['groups'].values():
            self.assertAlmostEqual(g['upstreamConditionalMeanVariancePP2'], 0, places=12)
            self.assertAlmostEqual(g['totalVariancePP2'], g['expectedConditionalCandidateVariancePP2'], places=12)
        n, l, other = partition(self.candidate['groups'])
        mass = p[:, n[0]]+p[:, l[0]]
        m, vm = attribution.vector_moments(mass, np.hypot(self.cs['mass']['shared'], self.cs['mass']['seat']))
        r, vr = attribution.vector_moments(p[:, n[0]]/mass, np.hypot(self.cs['balance']['shared'], self.cs['balance']['seat']))
        direct = np.mean((vm+m*m)*(vr+r*r)-(m*r)**2)*10000
        self.assertAlmostEqual(value['groups']['national']['totalVariancePP2'], direct, places=10)

    def test_within_remainder_cannot_change_major_draws(self):
        full, _ = simulation.component(self.candidate, self.cs, 16)
        _, c = attribution.policy_scales('no_candidate_within', self.ps, self.cs)
        removed, _ = simulation.component(self.candidate, c, 16)
        n, l, _ = partition(self.candidate['groups'])
        np.testing.assert_array_equal(full[:, n+l], removed[:, n+l])

    def test_shared_noise_same_across_seats_seat_noise_distinct(self):
        other = next(r for r in self.inventory['candidateRecords'] if r['targetYear'] == 2023 and r['targetElectorateId'] != self.candidate['targetElectorateId'])
        shared = {k: {'shared': v['shared'], 'seat': 0.} for k, v in self.cs.items()}
        a, _ = noise(self.candidate, shared, 16)
        b, _ = noise(other, shared, 16)
        np.testing.assert_array_equal(a['balance'], b['balance'])
        seat = {k: {'shared': 0., 'seat': v['seat']} for k, v in self.cs.items()}
        a, _ = noise(self.candidate, seat, 16)
        b, _ = noise(other, seat, 16)
        self.assertFalse(np.array_equal(a['balance'], b['balance']))

    def test_national_indices_are_original_shared_prefix(self):
        q, ids = construction.national_inputs(2023, self.party, 16)
        other, more = construction.national_inputs(2023, self.party, 32)
        np.testing.assert_array_equal(q, other[:16])
        self.assertEqual(ids['ids'], more['ids'][:16])
        self.assertEqual(len(set(ids['ids'])), 16)

    def test_missing_cache_fails_and_unknown_control_abstains(self):
        with patch.object(construction, 'restore', return_value=None):
            with self.assertRaises(ValueError):
                construction.arrays({'id': 'synthetic', 'draws': 16, 'kind': 'full'})
        with self.assertRaises(StopIteration):
            construction.control_case('candidate:2011')

    def test_future_contract_is_design_only_three_gaussian_restrictions(self):
        spec = read('data/processed/uncertainty-expectation/next-test-contract.json')
        self.assertTrue(spec['status'].startswith('frozen future design only'))
        self.assertEqual(len(spec['restrictions']), 3)
        self.assertEqual({k for k in spec['characteristics'] if k.startswith('x_')}, {'x_R','x_T'})
        self.assertIn('candidate seat National/Labour balance ONLY', spec['affectedDirection'])
        self.assertEqual(spec['decision'], 'B')

    def test_trace_is_fixed_coefficient_arithmetic_not_new_prediction(self):
        value = structural_diagnostics.build()
        self.assertEqual(len(value['fixedFeatureContributions']), 257)
        for r in value['fixedFeatureContributions']:
            self.assertTrue(r['noNewPredictionOrFit'])
            for c in r['candidates']:
                self.assertAlmostEqual(c['totalFeatureLogIntensity'],
                    r['coefficients']['S']*c['centeredS']+r['coefficients']['R']*c['centeredR'])
                if c['supportedMass']['R'] == 0:
                    self.assertEqual(c['RLogIntensityContribution'], 0)

    def test_individual_pair_widths_keep_original_units_and_order(self):
        row = {'id':'synthetic','year':2023,'ids':['a','b','c'],
            'ranking':{'predictionTimePair':{'ids':['b','a']}},'crpsPP':[2.,3.,4.],
            **{'interval'+str(level):{'covered':[True,False,True], 'widths':[10.,20.,30.],
                                     'scores':[11.,21.,31.]} for level in (50,80,90)}}
        result = pair_widths.selected_options(row)
        self.assertEqual(result['ids'], ['b','a'])
        self.assertEqual(result['interval90']['widths'], [20.,10.])
        self.assertEqual(result['interval90']['scores'], [21.,11.])
        self.assertEqual(result['crpsPP'], [3.,2.])

    def test_new_scoring_cannot_select_pair_from_actual_winner(self):
        from scripts.uncertainty_tails.metrics import record
        row = self.candidate
        q = np.broadcast_to(row['mean'], (16,len(row['mean'])))
        a = record(row,q,np.asarray(row['mean']))
        changed = dict(row,actual=list(reversed(row['actual'])),winnerId='counterfactual')
        b = record(changed,q,np.asarray(row['mean']))
        self.assertEqual(a['ranking']['predictionTimePair']['ids'], b['ranking']['predictionTimePair']['ids'])
        self.assertNotEqual(a['crpsPP'], b['crpsPP'])


if __name__ == '__main__':
    unittest.main()
