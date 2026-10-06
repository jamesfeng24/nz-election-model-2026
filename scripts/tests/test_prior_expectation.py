"""Fast independent arithmetic tests for Stage47 saved-scale attribution."""
from copy import deepcopy
import math
import unittest

from scripts.uncertainty_expectation import prior


def fold_fixture():
    moments = [{'year': 2014, 'moments': {'balance': {'shared': .01, 'seat': .04, 'records': 20}}}]
    return {'layer': 'candidate', 'targetYear': 2017, 'trainingYears': [2014],
            'moments': moments, 'scales': {'balance': {'shared': math.sqrt(.01), 'seat': math.sqrt(.0775)}},
            'contributions': {'balance': {
                'shared': {'environments': 1, 'historicalVarianceContribution': .0025,
                           'priorVarianceContribution': .0075},
                'seat': {'environments': 1, 'historicalVarianceContribution': .01,
                         'priorVarianceContribution': .0675}}}}


def scales_fixture():
    return {name: {'shared': .15, 'seat': .35} for name in ('balance', 'mass', 'within')}


class PriorAttributionTests(unittest.TestCase):
    def test_prior_weight_is_distinct_from_actual_variance_fraction(self):
        record = prior.scale_entry(fold_fixture(), 'balance', 'seat', .3, 3)
        self.assertAlmostEqual(record['priorWeight'], .75)
        self.assertAlmostEqual(record['actualPriorVarianceFraction'], .0675 / .0775)
        self.assertNotAlmostEqual(record['priorWeight'], record['actualPriorVarianceFraction'])
        self.assertAlmostEqual(record['empiricalOnlySD'], .2)
        self.assertEqual(record['availableYears'], [2014])

    def test_missing_rank_moment_is_not_zero_environment(self):
        fold = fold_fixture()
        fold['moments'][0]['moments']['balance']['shared'] = None
        fold['scales']['balance']['shared'] = .1
        fold['contributions']['balance']['shared'] = {
            'environments': 0, 'historicalVarianceContribution': 0., 'priorVarianceContribution': .01}
        record = prior.scale_entry(fold, 'balance', 'shared', .1, 3)
        self.assertEqual(record['earlierEnvironments'], 0)
        self.assertEqual(record['unavailableYears'], [2014])
        self.assertEqual(record['actualPriorVarianceFraction'], 1.)
        self.assertIsNone(record['empiricalOnlySD'])

    def test_saved_scale_corruption_is_rejected(self):
        fold = fold_fixture()
        fold['scales']['balance']['seat'] *= 1.01
        with self.assertRaisesRegex(ValueError, 'differs'):
            prior.scale_entry(fold, 'balance', 'seat', .3, 3)

    def test_heldout_or_later_environment_is_rejected_before_arithmetic(self):
        fold = fold_fixture()
        fold['trainingYears'] = [2017]
        fold['moments'][0]['year'] = 2017
        with self.assertRaisesRegex(ValueError, 'non-earlier'):
            prior.scale_entry(fold, 'balance', 'seat', .3, 3)

    def test_every_saved_fold_contribution_reconstructs_without_residual_refit(self):
        saved = prior.read(prior.SCALES)
        specification = prior.read('data/processed/uncertainty-revision/specification.json')
        count = 0
        for layer, folds in saved['folds'].items():
            for fold in folds:
                for coordinate in ('balance', 'mass', 'within'):
                    for kind in ('shared', 'seat'):
                        record = prior.scale_entry(fold, coordinate, kind,
                                                   specification['priors'][layer][coordinate][kind], 3)
                        self.assertEqual(record['targetYear'], fold['targetYear'])
                        self.assertEqual(record['availableYears'], fold['trainingYears'])
                        count += 1
        self.assertEqual(count, 54)


class AggregateMomentTests(unittest.TestCase):
    def test_product_variance_has_nonnegative_interaction_and_competition_covariance(self):
        mass = {'mean': .7, 'secondMoment': .51, 'variance': .02}
        ratio = {'mean': .6, 'secondMoment': .39, 'variance': .03}
        value = prior.product_variance(mass, ratio)
        self.assertAlmostEqual(value['nationalVariance'], .0225)
        self.assertAlmostEqual(value['nonlinearInteraction'], .0006)
        self.assertAlmostEqual(value['nationalLabourCovariance'], -.0105)
        self.assertTrue(value['quantileWidthsAreNotAdditive'])

    def test_symmetric_logistic_moments_and_zero_faces(self):
        first = prior.logistic_moments(.5, .8, 81)
        second = prior.logistic_moments(.5, .8, 161)
        self.assertAlmostEqual(first['mean'], .5, places=12)
        self.assertAlmostEqual(first['secondMoment'], second['secondMoment'], places=12)
        self.assertGreater(first['variance'], 0.)
        for p in (0., 1.):
            face = prior.logistic_moments(p, 3., 81)
            self.assertEqual(face['mean'], p)
            self.assertEqual(face['variance'], 0.)
            self.assertTrue(face['zeroFace'])

    def test_outcomes_and_remainder_coordinate_count_do_not_change_major_variance(self):
        row = {'layer': 'candidate', 'targetYear': 2023, 'targetElectorateId': 'synthetic',
               'groups': ['national', 'labour', 'other'], 'mean': [.4, .3, .3],
               'actual': [.1, .8, .1], 'winner': 'labour'}
        before = prior.major_variance(row, scales_fixture())
        changed = deepcopy(row)
        changed['actual'] = [.8, .1, .1]
        changed['winner'] = 'national'
        self.assertEqual(before, prior.major_variance(changed, scales_fixture()))
        changed['groups'] += ['other', 'other']
        changed['mean'] = [.4, .3, .1, .1, .1]
        self.assertEqual(before, prior.major_variance(changed, scales_fixture()))
        self.assertFalse(before['outcomesUsed'])

    def test_missing_major_omits_unidentified_balance(self):
        row = {'layer': 'candidate', 'targetYear': 2017, 'targetElectorateId': 'synthetic',
               'groups': ['national', 'other'], 'mean': [.8, .2]}
        self.assertEqual(prior.major_variance(row, scales_fixture())['status'], 'major_balance_absent')


if __name__ == '__main__':
    unittest.main()
