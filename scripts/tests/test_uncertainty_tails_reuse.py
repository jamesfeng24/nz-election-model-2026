"""Draft safeguards for Stage46 same-equation array and conditional-input reuse."""
from copy import deepcopy
import math
import unittest
from unittest.mock import patch

import numpy as np
from scipy.stats import norm

from scripts.uncertainty.construction import national_case, scale_for
from scripts.uncertainty_tails import integration, simulation, streams
from scripts.uncertainty_tails.common import INVENTORY, PREFIX, equivalent, read


class PairedCompositionReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inventory = read(INVENTORY)
        cls.candidate = next(row for row in inventory['candidateRecords'] if row['targetYear'] == 2020)
        cls.party = next(row for row in inventory['partyRecords']
                         if row['targetElectorateId'] == cls.candidate['targetElectorateId'])
        methods = read(PREFIX + '/scales.json')['methods']
        cls.gaussian_party = scale_for(methods['robust_gaussian'], 'local_party', 2020)['scales']
        cls.gaussian_candidate = scale_for(methods['robust_gaussian'], 'candidate', 2020)['scales']
        cls.student_party = scale_for(methods['student'], 'local_party', 2020)['scales']
        cls.student_candidate = scale_for(methods['student'], 'candidate', 2020)['scales']
        # Reuse the preserved fine national posterior; no national fitting or
        # additional independent national scenarios are involved in this test.
        cached, _, _ = national_case(2020, cls.party['ids'], 4096)
        order = streams.permutation(4096, 'national:2020')
        cls.national = np.tile(cached[order], (2, 1))

    def test_pair_matches_independent_compositions_on_real_cached_8192_inputs(self):
        party, candidate = deepcopy(self.party), deepcopy(self.candidate)
        national = self.national.copy()
        frozen_party, frozen_candidate, frozen_national = deepcopy(party), deepcopy(candidate), national.copy()
        expected = {
            'robust_gaussian': simulation.compose(party, candidate, national,
                                                   self.gaussian_party, self.gaussian_candidate, 'robust_gaussian'),
            'student': simulation.compose(party, candidate, national,
                                         self.student_party, self.student_candidate, 'student'),
        }
        paired = simulation.compose_pair(party, candidate, national,
                                         self.gaussian_party, self.gaussian_candidate,
                                         self.student_party, self.student_candidate)
        self.assertEqual(set(paired), set(expected))
        for method, (reference_q, reference_meta) in expected.items():
            q, metadata = paired[method]
            np.testing.assert_allclose(q, reference_q, rtol=0, atol=1e-10)
            self.assertTrue(equivalent(reference_meta, metadata))
            np.testing.assert_allclose(q.sum(axis=1), 1., rtol=0, atol=1e-14)
            self.assertFalse(metadata['nationalRedrawn'])
        self.assertEqual(party, frozen_party)
        self.assertEqual(candidate, frozen_candidate)
        np.testing.assert_array_equal(national, frozen_national)

    def test_pair_rejects_incompatible_shared_or_reused_direction_scales(self):
        mutations = [('party', 'balance', 'seat'), ('party', 'within', 'shared'),
                     ('candidate', 'mass', 'seat'), ('candidate', 'within', 'shared'),
                     ('candidate', 'balance', 'shared')]
        for layer, direction, kind in mutations:
            with self.subTest(layer=layer, direction=direction, kind=kind):
                student_party, student_candidate = deepcopy(self.student_party), deepcopy(self.student_candidate)
                target = student_party if layer == 'party' else student_candidate
                target[direction][kind] += .001
                with self.assertRaises(ValueError):
                    simulation.compose_pair(self.party, self.candidate, self.national,
                                            self.gaussian_party, self.gaussian_candidate,
                                            student_party, student_candidate)


class RepeatedConditionalInputTests(unittest.TestCase):
    def probabilities(self):
        # Explicit synthetic compositions, separate from application data.
        return np.tile(np.array([[.6, .3, .1], [.2, .5, .3]]), (2048, 1))

    def test_exact_4096_repetitions_reuse_only_identical_conditional_inputs(self):
        prefix = self.probabilities()
        repeated = np.tile(prefix, (2, 1))
        untouched = repeated.copy()
        # A deterministic stand-in isolates reuse routing from the independently
        # tested conditional location solver and keeps this test bounded.
        with patch.object(integration, 'conditional_offsets', side_effect=lambda p, sd: np.asarray(p) * sd) as solve:
            result = integration.within_offsets(repeated, .3)
        self.assertEqual(solve.call_count, 1)
        np.testing.assert_array_equal(solve.call_args.args[0], prefix)
        np.testing.assert_array_equal(result, repeated * .3)
        np.testing.assert_array_equal(repeated, untouched)

    def test_changed_last_conditional_input_falls_back_to_complete_processing(self):
        altered = np.tile(self.probabilities(), (2, 1))
        altered[-1] = [.25, .45, .3]
        untouched = altered.copy()
        with patch.object(integration, 'conditional_offsets', side_effect=lambda p, sd: np.asarray(p) * sd) as solve:
            result = integration.within_offsets(altered, .3)
        self.assertEqual(solve.call_count, 1)
        np.testing.assert_array_equal(solve.call_args.args[0], altered)
        np.testing.assert_array_equal(result, altered * .3)
        np.testing.assert_array_equal(altered, untouched)

    def test_nonreplicated_count_uses_every_conditional_input(self):
        inputs = self.probabilities()[:12]
        with patch.object(integration, 'conditional_offsets', side_effect=lambda p, sd: np.asarray(p) * sd) as solve:
            result = integration.within_offsets(inputs, .3)
        np.testing.assert_array_equal(solve.call_args.args[0], inputs)
        np.testing.assert_array_equal(result, inputs * .3)


class StudentNoiseDispersionTests(unittest.TestCase):
    def test_total_balance_reports_student_sd_without_changing_shared_scale(self):
        row = read(INVENTORY)['candidateRecords'][0]
        scales = {direction: {'shared': .1, 'seat': .2} for direction in ['balance', 'mass', 'within']}
        _, gaussian = streams.noise(row, scales, 32)
        _, student = streams.noise(row, scales, 32, student=True)
        self.assertAlmostEqual(gaussian['balance'], math.sqrt(.1 ** 2 + .2 ** 2), places=14)
        self.assertAlmostEqual(student['balance'], math.sqrt(.1 ** 2 + 2 * .2 ** 2), places=14)
        self.assertEqual(student['balanceShared'], .1)
        self.assertEqual(student['balanceSeat'], .2)
        self.assertEqual(student['mass'], gaussian['mass'])
        self.assertEqual(student['within'], gaussian['within'])


class RemainderContrastDependenceTests(unittest.TestCase):
    def test_within_factor_matches_projected_label_incidence_covariance(self):
        tags, shared, seat = ['no_group', 'no_group', 'greenparty'], .3, .2
        factor = integration.within_factor(tags, shared, seat)
        raw_covariance = np.array([[shared ** 2 * (left == right) + seat ** 2 * (i == j)
                                    for j, right in enumerate(tags)] for i, left in enumerate(tags)])
        projection = np.eye(len(tags)) - np.ones((len(tags), len(tags))) / len(tags)
        expected = projection @ raw_covariance @ projection
        np.testing.assert_allclose(factor @ factor.T, expected, rtol=0, atol=1e-14)
        np.testing.assert_allclose(factor.sum(axis=0), 0., rtol=0, atol=1e-14)
        duplicate, distinct = np.array([1., -1., 0.]), np.array([1., 0., -1.])
        self.assertAlmostEqual(float(np.sum((duplicate @ factor) ** 2)), 2 * seat ** 2, places=14)
        self.assertAlmostEqual(float(np.sum((distinct @ factor) ** 2)), 2 * (seat ** 2 + shared ** 2), places=14)
        all_same = integration.within_factor(['no_group'] * 3, shared, seat)
        np.testing.assert_allclose(all_same @ all_same.T, seat ** 2 * projection, rtol=0, atol=1e-14)

    def test_duplicate_label_conditional_inverse_preserves_fixture_means_and_zero_faces(self):
        groups = ['national', 'labour', 'no_group', 'no_group', 'other']
        full_tags = ['nationalparty', 'labourparty', 'no_group', 'no_group', 'greenparty']
        tags = full_tags[2:]
        shared, seat, count = .35, .2, 64
        total = {'balance': 0., 'mass': 0., 'within': math.hypot(shared, seat),
                 'balanceShared': 0., 'balanceSeat': 0., 'withinShared': shared, 'withinSeat': seat}
        labels = sorted(set(tags))
        normals = norm.ppf(integration.quadrature(len(labels) + len(tags), count))
        # Independent incidence arithmetic reproduces the actual shared-label
        # disturbance, including a common effect for both no_group options.
        within = np.column_stack([shared * normals[:, labels.index(tag)]
                                  + seat * normals[:, len(labels) + index]
                                  for index, tag in enumerate(tags)])
        within -= within.mean(axis=1, keepdims=True)
        eta = {'balance': np.zeros(count), 'mass': np.zeros(count), 'within': within}
        for base in [[.3, .2, .3, .1, .1], [.3, .2, .35, .15, 0.], [.3, .2, .5, 0., 0.]]:
            with self.subTest(base=base):
                q, metadata = integration.conditional_inverse(base, groups, eta, total, tags=full_tags)
                np.testing.assert_allclose(q.mean(axis=0), base, rtol=0, atol=1e-10)
                np.testing.assert_allclose(q.sum(axis=1), 1., rtol=0, atol=1e-14)
                self.assertTrue(metadata['zeroLock'])
                self.assertTrue(np.all(q[:, np.asarray(base) == 0.] == 0.))

    def test_inverse_uses_repeated_label_covariance_for_conditional_location(self):
        from scripts.diagnostics.uncertainty_tails_reference import expectation
        from scipy.special import roots_hermitenorm
        labels=['same','same','other'];p=np.array([.5,.3,.2]);shared,seat=.3,.25
        raw=np.array([[shared**2*(a==b)+seat**2*(i==j) for j,b in enumerate(labels)] for i,a in enumerate(labels)])
        difference=np.array([[1.,0.,-1.],[0.,1.,-1.]])
        covariance=np.einsum('ij,jk,lk->il',difference,raw,difference,optimize=False)
        root=np.linalg.cholesky(covariance);nodes,weights=roots_hermitenorm(81)
        grid=np.stack(np.meshgrid(nodes,nodes,indexing='ij'),axis=-1).reshape(-1,2)
        normals=np.einsum('ij,kj->ik',grid,root,optimize=False)
        eta={'within':np.column_stack((normals,np.zeros(len(grid)))), 'balance':np.zeros(len(grid)), 'mass':np.zeros(len(grid))}
        scales={'balance':0.,'mass':0.,'within':np.hypot(shared,seat),'withinShared':shared,'withinSeat':seat}
        q,_=integration.conditional_inverse(p,['other']*3,eta,scales,tags=labels)
        weight=np.outer(weights,weights).ravel()/(2*np.pi)
        simulated=np.sum(q*weight[:,None],axis=0)
        offset=integration.conditional_offsets(p,scales['within'],tags=labels,shared=shared,seat=seat)
        reference=expectation(p,offset,labels,shared,seat,81)
        np.testing.assert_allclose(simulated,reference,rtol=0,atol=1e-14)
        # Record the real quadrature limitation rather than making this fixture
        # a claim that the frozen 0.05pp gate passed.
        self.assertGreater(float(100*np.max(np.abs(reference-p))),.05)

    def test_quadrature_factor_matches_shared_label_covariance(self):
        factor=integration.within_factor(['same','same','other'],.3,.2)
        covariance=np.einsum('ij,kj->ik',factor,factor,optimize=False)
        duplicate=np.array([1.,-1.,0.]);distinct=np.array([1.,0.,-1.])
        self.assertAlmostEqual(float(duplicate@covariance@duplicate),2*.2**2,places=14)
        self.assertAlmostEqual(float(distinct@covariance@distinct),2*(.2**2+.3**2),places=14)
        np.testing.assert_allclose(factor.sum(axis=0),0,atol=1e-16)

    def test_same_label_shared_noise_cancels_and_distinct_labels_retain_it(self):
        row = {'layer': 'candidate', 'targetYear': 2020, 'targetElectorateId': 'synthetic-labels',
               'groups': ['national', 'labour', 'no_group', 'no_group', 'other'],
               'ids': ['n', 'l', 'independent-a', 'independent-b', 'green'],
               'features': [{'group': tag} for tag in ['nationalparty', 'labourparty', None, None, 'greenparty']]}
        scales = {direction: {'shared': .3, 'seat': .2} for direction in ['balance', 'mass', 'within']}
        streams.uniforms.cache_clear()
        try:
            with patch.object(streams, 'read', return_value={'partyRecords': [], 'candidateRecords': [row]}):
                eta, _ = streams.noise(row, scales, 8192)
                names, bank = streams.uniforms(2020, 8192)
            keys = streams.keys(row)['within']
            gaussian = {name: norm.ppf(bank[:, names.index(name)]) for pair in keys for name in pair}
            duplicate = eta['within'][:, 0] - eta['within'][:, 1]
            distinct = eta['within'][:, 0] - eta['within'][:, 2]
            expected_duplicate = .2 * (gaussian[keys[0][1]] - gaussian[keys[1][1]])
            expected_distinct = (.3 * (gaussian[keys[0][0]] - gaussian[keys[2][0]])
                                 + .2 * (gaussian[keys[0][1]] - gaussian[keys[2][1]]))
            np.testing.assert_allclose(duplicate, expected_duplicate, rtol=0, atol=1e-14)
            np.testing.assert_allclose(distinct, expected_distinct, rtol=0, atol=1e-14)
            self.assertAlmostEqual(float(np.var(duplicate)), 2 * .2 ** 2, delta=.02 * 2 * .2 ** 2)
            self.assertAlmostEqual(float(np.var(distinct)), 2 * (.2 ** 2 + .3 ** 2),
                                   delta=.02 * 2 * (.2 ** 2 + .3 ** 2))
        finally:
            streams.uniforms.cache_clear()


if __name__ == '__main__':
    unittest.main()
