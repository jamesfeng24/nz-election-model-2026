"""Synthetic Stage38 interfaces: complete partitions, no inferred fine detail."""
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from scripts.polling.external_comparison.common import coarsen, digest
from scripts.polling.external_comparison.metrics import distribution, interval_score, major
from scripts.polling.external_comparison.evaluation import pool
from scripts.polling.external_comparison.inference import constant_mask, signature
from scripts.polling.national_model.metrics import point


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

    def test_actual_cache_signature_pins_cutoff_settings_inputs_and_config(self):
        from scripts.polling.external_comparison import inference
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'config').mkdir()
            (root/'config/model.yml').write_text('synthetic: true\n')
            (root/'specification.json').write_text('{"synthetic":true}')
            (root/'input-contract.json').write_text('{"sha256":{}}')
            (root/'environment.json').write_text('{"packages":{"synthetic":"1"}}')
            ds = SimpleNamespace(cutoff=date(2020, 8, 22), fingerprint=lambda: 'fixed-array-hash')
            settings = {'seed': 2034, 'chains': 4, 'samples': 2000}
            with patch.object(inference, 'OUT', root), patch.object(inference, 'UPSTREAM', root):
                base = signature(ds, settings)
                self.assertEqual(base, signature(ds, dict(settings)))
                ds.cutoff = date(2020, 8, 23)
                self.assertNotEqual(base, signature(ds, settings))
                ds.cutoff = date(2020, 8, 22)
                self.assertNotEqual(base, signature(ds, dict(settings, seed=2035)))
                (root/'input-contract.json').write_text('{"sha256":{"new":"input"}}')
                self.assertNotEqual(base, signature(ds, settings))
                (root/'input-contract.json').write_text('{"sha256":{}}')
                (root/'config/model.yml').write_text('synthetic: changed\n')
                self.assertNotEqual(base, signature(ds, settings))


class ForecastScoreTests(unittest.TestCase):
    def test_exact_two_draw_crps_energy_and_intervals(self):
        draws = np.array([[1., 0., 0., 0., 0., 0.],
                          [0., 1., 0., 0., 0., 0.]])
        actual = np.array([.25, .75, 0., 0., 0., 0.])
        result = distribution(draws, actual)
        # CRPS = E|X-y| - E|X-X'|/2 using the empirical joint distribution.
        self.assertAlmostEqual(result['parties'][0]['CRPSpp'], 25.)
        self.assertAlmostEqual(result['parties'][1]['CRPSpp'], 25.)
        self.assertAlmostEqual(result['meanCRPSpp'], 50./6)
        self.assertAlmostEqual(result['energyScorePP'], 25.*2**.5)
        self.assertEqual(result['subsampleIndices'], [0, 1])
        for label, width in [('50', 100./6), ('90', 30.)]:
            self.assertEqual(result['coveredCount'+label], 6)
            self.assertEqual(result['coverage'+label], 1)
            self.assertAlmostEqual(result['width'+label+'PP'], width)
            self.assertAlmostEqual(result['intervalScore'+label+'PP'], width)

    def test_interval_score_penalizes_misses_and_rejects_invalid_levels(self):
        self.assertAlmostEqual(interval_score(.2, .4, .3, .5), 20.)
        self.assertAlmostEqual(interval_score(.2, .4, .1, .5), 60.)
        self.assertAlmostEqual(interval_score(.2, .4, .5, .5), 60.)
        self.assertAlmostEqual(interval_score(.2, .4, .1, .9), 220.)
        for level in (0, 1, -.1, 1.1):
            with self.subTest(level=level), self.assertRaises(ValueError):
                interval_score(.2, .4, .3, level)
        with self.assertRaises(ValueError):
            interval_score(.4, .2, .3, .5)

    def test_point_mass_has_no_invented_forecast_spread(self):
        forecast = np.array([[1., 0., 0., 0., 0., 0.]])
        actual = np.array([0., 1., 0., 0., 0., 0.])
        result = distribution(forecast, actual)
        self.assertAlmostEqual(result['energyScorePP'], 100.*2**.5)
        self.assertAlmostEqual(result['meanCRPSpp'], 200./6)
        self.assertEqual(result['width90PP'], 0)
        self.assertEqual(result['coveredCount90'], 4)
        self.assertAlmostEqual(result['intervalScore90PP'], 4000./6)

    def test_equal_election_pool_averages_squared_errors_before_root(self):
        names = ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'REST']
        actual = [.4, .4, .05, .05, .05, .05]
        rows = []
        for year, delta, draw_count in [(2017, .1, 10), (2023, .2, 10000)]:
            forecast = [.4+delta, .4-delta, .05, .05, .05, .05]
            score = point(forecast, actual, names)
            rows.append({'year': year, 'systems': {'average': {
                'point': score, 'major': major(score),
                'probability': None, 'drawCount': draw_count}}})
        result = pool(rows, ['average'])
        self.assertEqual(result['weightPerElection'], .5)
        self.assertEqual(result['categoryCases'], 12)
        self.assertEqual(result['majorPartyCases'], 4)
        score = result['systems']['average']
        self.assertAlmostEqual(score['MAEpp'], 5)
        self.assertAlmostEqual(score['RMSEpp'], (1000./12)**.5)
        self.assertAlmostEqual(score['majorMAEpp'], 15)
        self.assertAlmostEqual(score['majorRMSEpp'], 250.**.5)
        self.assertAlmostEqual(score['partyBias'][0]['biasPP'], 15)
        self.assertAlmostEqual(score['partyBias'][1]['biasPP'], -15)
        self.assertIsNone(score['probability'])

    def test_distribution_requires_complete_joint_schema(self):
        for draws in ([[.5, .5]], [[.5, .4, 0., 0., 0., 0.]],
                      [[.5, .5, 0., 0., 0., float('nan')]]):
            with self.subTest(draws=draws), self.assertRaises(ValueError):
                distribution(draws, [.4, .4, .05, .05, .05, .05])


class DiagnosticConstantTests(unittest.TestCase):
    def test_only_structural_cholesky_coordinates_exempted(self):
        ds = SimpleNamespace(K=4, T=5, anchors_t=(0, 2))
        mask = constant_mask('L_corr', np.zeros((4, 2000, 9)), ds)
        self.assertEqual(np.flatnonzero(mask).tolist(), [0, 1, 2, 5])
        self.assertFalse(constant_mask('sigma', np.zeros((4, 2000, 3)), ds).any())
        self.assertFalse(constant_mask('industry_end_raw', np.zeros((4, 2000, 12)), ds).any())

    def test_fixed_anchor_path_exemptions_do_not_hide_future_state(self):
        ds = SimpleNamespace(K=4, T=5, anchors_t=(0, 2))
        for name, width in [('theta', 3), ('pi', 4)]:
            mask = constant_mask(name, np.zeros((4, 2000, 5*width)), ds).reshape(5, width)
            self.assertTrue(mask[[0, 2]].all())
            self.assertFalse(mask[[1, 3, 4]].any())


if __name__ == '__main__':
    unittest.main()

class OutcomeValidationTests(unittest.TestCase):
    def test_invalid_actual_or_interval_values_rejected(self):
        draws=[[.4,.3,.1,.05,.05,.1]]
        for actual in ([.4,.3,.1,.05,.05,.05],[.4,.3,.1,.05,.05,float('nan')]):
            with self.assertRaises(ValueError):distribution(draws,actual)
        for bounds in [(float('nan'),.4,.3),(.2,float('inf'),.3),(.2,.4,float('nan'))]:
            with self.assertRaises(ValueError):interval_score(*bounds,.5)


class RecordedInputBoundaryTests(unittest.TestCase):
    def test_actual_cached_cases_have_exact_cutoffs_and_only_earlier_result_anchors(self):
        from scripts.polling.external_comparison.common import OUT, read
        dates={2017:date(2017,9,23),2020:date(2020,10,17),2023:date(2023,10,14)}
        cases=read(OUT/'inventory.json')['cases']
        self.assertEqual([r['year'] for r in cases],[2017,2020,2023])
        for r in cases:
            self.assertEqual((dates[r['year']]-date.fromisoformat(r['cutoff'])).days,56)
            self.assertTrue(all(y<r['year'] for y in r['resultAnchors']))
            self.assertTrue(all(p['available']<=r['cutoff'] for p in r['polls']))
            self.assertEqual(len({p['id'] for p in r['polls']}),r['pollCount'])
            self.assertTrue(r['counterfactualsPassed'])


# Upstream imports are isolated; routine CI checks saved inputs without installing inference packages.
import importlib.util
from scripts.polling.external_comparison.common import UPSTREAM
@unittest.skipUnless(importlib.util.find_spec('polars') is not None and (UPSTREAM/'src').exists(),
                     'requires isolated external preparation environment and pinned checkout')
class ActualPinnedAdapterTests(unittest.TestCase):
    def test_heldout_results_postcutoff_polls_and_future_revisions_do_not_change_inputs(self):
        from scripts.polling.external_comparison.prepare import source_table, earlier_dataset, check_counterfactuals
        from scripts.polling.external_comparison.common import CASES
        cfg,table,results=source_table()
        for year,cutoff in CASES:
            ds=earlier_dataset(table,results,cfg,year,cutoff)
            check_counterfactuals(table,results,cfg,year,cutoff,ds)

    def test_permitted_earlier_results_can_change_anchor_inputs(self):
        from scripts.polling.external_comparison.prepare import source_table,earlier_dataset
        cfg,table,results=source_table();year=2023;cutoff='2023-08-19'
        ds=earlier_dataset(table,results,cfg,year,cutoff)
        changed={**results,2020:{**results[2020],'National':results[2020]['National']+.01,'Labour':results[2020]['Labour']-.01}}
        self.assertNotEqual(ds.fingerprint(),earlier_dataset(table,changed,cfg,year,cutoff).fingerprint())
