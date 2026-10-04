"""Synthetic Stage38 interfaces: complete partitions, no inferred fine detail."""
import unittest

import numpy as np

from scripts.polling.external_comparison.common import coarsen, digest


class CompletePartitionTests(unittest.TestCase):
    def test_mri_top_and_minor_groups_enter_one_remainder(self):
        names = ['National', 'Labour', 'Green', 'ACT', 'NZ First',
                 'Te Pāti Māori', 'TOP', 'Other']
        draws = np.array([[.40, .30, .08, .07, .05, .03, .02, .05],
                          [.35, .32, .10, .09, .05, .02, .01, .06]])
        actual = coarsen(draws, names)
        np.testing.assert_allclose(actual[:, :5], draws[:, :5], atol=0, rtol=0)
        np.testing.assert_allclose(actual[:, -1], [.10, .09], atol=1e-15)
        np.testing.assert_allclose(actual.sum(-1), 1, atol=1e-15)
        # Joint row identity and dependence survive aggregation.
        self.assertLess(actual[1, 0], actual[0, 0])
        self.assertLess(actual[1, -1], actual[0, -1])

    def test_2020_folded_mri_has_same_complete_partition(self):
        fine = [.40, .30, .08, .07, .05, .03, .02, .05]
        names = ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'MRI', 'TOP', 'OTH']
        folded = fine[:5] + [sum(fine[5:])]
        np.testing.assert_allclose(coarsen(fine, names),
                                   coarsen(folded, names[:5] + ['Other']))

    def test_category_order_is_explicit_and_subset_not_renormalized(self):
        names = ['REST', 'NZF', 'LAB', 'NAT', 'ACT', 'GRN']
        coarse = coarsen([.10, .05, .30, .40, .07, .08], names)
        np.testing.assert_allclose(coarse, [.40, .30, .08, .07, .05, .10])
        self.assertAlmostEqual(coarse[:2].sum(), .70)
        self.assertAlmostEqual(coarse[0], .40)
        self.assertNotAlmostEqual(coarse[0], .40/.70)

    def test_genuine_zero_preserved_and_other_not_split(self):
        names = ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'OTH']
        result = coarsen([.5, .3, .1, 0, 0, .1], names)
        self.assertEqual(result[3], 0)
        self.assertEqual(result[4], 0)
        self.assertEqual(result[-1], .1)
        self.assertEqual(result.shape, (6,))

    def test_invalid_schemas_and_incomplete_vectors_rejected(self):
        cases = [
            ([.4, .3, .1, .05, .05], ['NAT', 'LAB', 'GRN', 'ACT', 'NZF']),
            ([.4, .3, .1, .05, .05, .1], ['NAT', 'LAB', 'GRN', 'ACT', 'OTH', 'REST']),
            ([.3, .3, .1, .05, .05, .1, .1],
             ['National', 'NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'Other']),
            ([.4, .3, .1, .05, .05, .1], ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'NZF']),
            ([.4, .3, .1, .05, .05, .1], ['NAT', 'LAB', 'GRN', 'ACT', 'NZF']),
        ]
        for values, names in cases:
            with self.subTest(names=names), self.assertRaises(ValueError):
                coarsen(values, names)

    def test_nonfinite_negative_and_nonunit_mass_rejected(self):
        names = ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'OTH']
        for values in ([.4, .3, .1, .05, .05, np.nan],
                       [.4, .3, .1, .05, .05, np.inf],
                       [.5, .3, .1, .05, .10, -.05],
                       [.4, .3, .1, .05, .05, .05]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                coarsen(values, names)


class ProvenanceEncodingTests(unittest.TestCase):
    def test_signature_is_deterministic_and_sensitive_to_information_contract(self):
        base = {'cutoff': '2020-08-22', 'seed': 2034, 'inputHash': 'synthetic',
                'settings': {'chains': 4, 'warmup': 2000}}
        reordered = {'settings': {'warmup': 2000, 'chains': 4},
                     'inputHash': 'synthetic', 'seed': 2034, 'cutoff': '2020-08-22'}
        self.assertEqual(digest(base), digest(reordered))
        for field, value in [('cutoff', '2020-08-23'), ('seed', 2035),
                             ('inputHash', 'different')]:
            self.assertNotEqual(digest(base), digest(dict(base, **{field: value})))

    def test_nonfinite_cache_contract_cannot_be_encoded(self):
        with self.assertRaises(ValueError):
            digest({'input': float('nan')})


if __name__ == '__main__':
    unittest.main()
