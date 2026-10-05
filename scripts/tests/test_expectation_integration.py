"""Synthetic independent references for Gaussian conditional expectation repair."""
import unittest
import numpy as np
from scipy.integrate import quad
from scipy.special import expit
from scipy.stats import norm
from scripts.uncertainty_expectation import integration
from scripts.uncertainty_expectation.reference import assess_reference, cholesky_expectation


class ExpectationIntegrationTests(unittest.TestCase):
    def test_repeated_labels_have_shared_covariance_not_individual_noise(self):
        shared, seat = .37, .21
        result = integration.contrast_covariance(('a', 'a', 'b'), shared, seat)
        expected = np.array([[2*(shared**2+seat**2), 2*shared**2+seat**2],
                             [2*shared**2+seat**2, 2*(shared**2+seat**2)]])
        np.testing.assert_allclose(result, expected, rtol=0, atol=1e-16)
        same = integration.contrast_covariance(('a', 'a'), shared, seat)
        different = integration.contrast_covariance(('a', 'b'), shared, seat)
        self.assertAlmostEqual(same[0, 0], 2*seat**2)
        self.assertAlmostEqual(different[0, 0], 2*(shared**2+seat**2))

    def test_binary_gaussian_reference_has_reported_adaptive_error(self):
        p = np.array([.07, .93])
        for tags in (('same', 'same'), ('first', 'second')):
            offset, audit = integration.solve_locations(p, tags, .42, .25)
            self.assertTrue(audit[0]['passed'])
            variance = 2*.25**2 + (0 if tags[0] == tags[1] else 2*.42**2)
            logit = np.log(p[0]/p[1]) + offset[0] - offset[1]
            mean, error = quad(lambda z: expit(logit+np.sqrt(variance)*z)*norm.pdf(z),
                               -12, 12, epsabs=1e-12, epsrel=1e-12)
            self.assertLess(error, 1e-10)
            self.assertLess(abs(mean-p[0]), integration.COMPARISON_TOLERANCE)

    def test_cholesky_references_cover_unique_repeated_and_boundary_compositions(self):
        fixtures = [([.12, .31, .57], ('a', 'b', 'c')),
                    ([.15, .25, .6], ('a', 'a', 'b')),
                    ([.002, .08, .918], ('a', 'a', 'b')),
                    ([.000001, .419999, .58], ('a', 'b', 'c'))]
        for p, tags in fixtures:
            with self.subTest(p=p, tags=tags):
                offset, audits = integration.solve_locations(p, tags, .31, .28, tensor=True)
                reference = assess_reference(p, offset, tags, .31, .28)
                self.assertTrue(audits[0]['passed'], audits)
                self.assertLess(reference['referenceChangePP'], .01, reference)
                self.assertLess(reference['conditionalGapPP'], .05, reference)
                self.assertTrue(reference['referenceDifferenceIsNotRigorousErrorBound'])

    def test_four_option_repeated_label_reference_at_frozen_candidate_scale(self):
        from scripts.uncertainty_expectation.common import read, SCALES
        fold = next(f for f in read(SCALES)['folds']['candidate'] if f['targetYear'] == 2023)
        scales = fold['scales']['within']
        p = np.array([.001, .009, .19, .8])  # Synthetic small-option stress composition.
        tags = ('no_group', 'no_group', 'act', 'green')
        offset, audit = integration.solve_locations(p, tags, scales['shared'], scales['seat'], tensor=True)
        reference = assess_reference(p, offset, tags, scales['shared'], scales['seat'])
        self.assertTrue(audit[0]['passed'], audit)
        self.assertLess(reference['referenceChangePP'], .01, reference)
        self.assertLess(reference['conditionalGapPP'], .05, reference)

    def test_zero_faces_and_singleton_remain_locked(self):
        p = np.array([0., .16, .84, 0.])
        tags = ('unused', 'same', 'same', 'unused')
        offset, audit = integration.solve_locations(p, tags, .4, .3, tensor=True)
        reference = cholesky_expectation(p, offset, tags, .4, .3, 81)
        np.testing.assert_array_equal(reference[[0, 3]], [0, 0])
        np.testing.assert_allclose(reference, p, atol=.05/100, rtol=0)
        point = np.array([0., 1., 0.])
        offsets, checks = integration.solve_locations(point, ('x', 'y', 'x'), 1., 1.)
        np.testing.assert_array_equal(offsets, np.zeros(3))
        self.assertEqual(checks[0]['conditionalGapPP'], 0.)

    def test_shared_label_common_noise_cancels_on_same_label_face(self):
        p = np.array([.11, .32, .57])
        tags = ('shared',)*3
        first, checks = integration.solve_locations(p, tags, 0., .2, tensor=True)
        second, checks2 = integration.solve_locations(p, tags, 1.2, .2, tensor=True)
        np.testing.assert_allclose(first, second, rtol=0, atol=1e-12)
        self.assertTrue(checks[0]['passed'] and checks2[0]['passed'])
        offsets, _ = integration.solve_locations(p, tags, 2., 0.)
        np.testing.assert_allclose(offsets, 0., rtol=0, atol=1e-14)

    def test_batch_determinism_and_permutation_preserve_expectations(self):
        base = np.array([[.1, .3, .6], [.2, .7, .1], [.1, .3, .6]])
        tags = ('a', 'a', 'b')
        offset, checks = integration.solve_locations(base, tags, .3, .2, tensor=True)
        again, checks2 = integration.solve_locations(base, tags, .3, .2, tensor=True)
        np.testing.assert_array_equal(offset, again)
        self.assertEqual(checks, checks2)
        np.testing.assert_array_equal(offset[0], offset[2])
        for row, location in zip(base, offset):
            single, _ = integration.solve_locations(row, tags, .3, .2, tensor=True)
            np.testing.assert_allclose(location, single, rtol=0, atol=1e-12)
        order = [2, 0, 1]
        permuted, _ = integration.solve_locations(base[:, order], tuple(tags[i] for i in order), .3, .2, tensor=True)
        for row, location in zip(base[:, order], permuted):
            ref = assess_reference(row, location, tuple(tags[i] for i in order), .3, .2)
            self.assertLess(ref['conditionalGapPP'], .05)
        original_relative = offset[:, order]-offset[:, order[-1], None]
        np.testing.assert_allclose(permuted, original_relative, atol=.001, rtol=0)

    def test_invalid_simplexes_scales_and_qmc_sizes_fail(self):
        for p in ([.4, .4], [-.1, 1.1], [np.nan, 1.]):
            with self.subTest(p=p), self.assertRaisesRegex(ValueError, 'Invalid conditional simplex'):
                integration.solve_locations(p, ('a', 'b'), .1, .1)
        with self.assertRaisesRegex(ValueError, 'Invalid Gaussian scales'):
            integration.contrast_covariance(('a', 'b'), -1., 0.)
        with self.assertRaisesRegex(ValueError, 'power of two'):
            integration.rule(('a', 'b', 'c'), .1, .1, 33)

    def test_jacobian_matches_finite_difference_of_active_expectation(self):
        p = np.array([.2, .3, .5])
        offset = np.array([.1, -.08, 0.])
        nodes, weights = integration.rule(('a', 'a', 'b'), .25, .3, 41, tensor=True)
        value, analytic = integration.expectation(p, offset, nodes, weights, jacobian=True)
        columns = []
        for index in range(2):
            delta = np.zeros(3)
            delta[index] = 1e-5
            plus = integration.expectation(p, offset+delta, nodes, weights)
            minus = integration.expectation(p, offset-delta, nodes, weights)
            columns.append((plus[:-1]-minus[:-1])/(2e-5))
        np.testing.assert_allclose(analytic, np.stack(columns, axis=1), atol=1e-10, rtol=0)
        self.assertAlmostEqual(value.sum(), 1., places=14)


if __name__ == '__main__':
    unittest.main()
