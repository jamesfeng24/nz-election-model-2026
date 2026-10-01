"""Synthetic numerical checks and frozen Stage22 construction boundaries."""

from copy import deepcopy
import unittest
from unittest.mock import patch

import numpy as np

from scripts.checkpoints import stage22_prefit as prefit
from scripts.checkpoints.stage22_construction import (
    build, construct_fold, contextual_predictions, scenario_rows)
from scripts.checkpoints.stage22_fit import (
    Profile, candidate_arrays, choose_tied, earlier_actuals, fit, means_for_training,
    predict, selected_columns)


class Stage22FitTests(unittest.TestCase):
    def test_frozen_objective_tie_chooses_smaller_parameter(self):
        self.assertEqual(choose_tied([(1.0, .02), (1.0 + 5e-13, .01)], float)[1], .01)

    def test_synthetic_boundary_and_solver_failure_abstention(self):
        profile = Profile(np.array([.9, .1] * 2), np.zeros((4, 2)),
                          np.array([0, 2]), np.array([.5, .5] * 2), 'baseline')
        self.assertEqual(fit(profile)['boundary'], 'upper')
        with patch('scripts.checkpoints.stage22_fit.shgo',
                   return_value=type('Failed', (), {'success': False, 'fun': 0})()):
            with self.assertRaisesRegex(ValueError, 'SHGO failed'):
                fit(profile)

    def test_synthetic_gradient_matches_finite_difference(self):
        # Synthetic slates, not historical results.
        profile = Profile(np.array([.2, .3, .1, .25]),
                          np.array([[.2, .1], [.4, -.1], [.2, .2], [.6, -.2]]),
                          np.array([0, 2]), np.array([.4, .6, .2, .8]),
                          'baseline_plus_S_plus_V')
        theta = np.array([.1, -.2])
        loss, gradient = profile.value_gradient(.01, theta)
        self.assertGreater(loss, 0)
        for i in range(2):
            plus, minus = theta.copy(), theta.copy()
            plus[i] += 1e-6
            minus[i] -= 1e-6
            difference = (profile.value_gradient(.01, plus)[0] -
                          profile.value_gradient(.01, minus)[0]) / 2e-6
            self.assertAlmostEqual(gradient[i], difference, places=8)
        self.assertEqual([selected_columns(m) for m in
                          ('baseline', 'baseline_plus_S', 'baseline_plus_V',
                           'baseline_plus_S_plus_V')], [(), (0,), (1,), (0, 1)])

    def test_scenario_coupling_and_training_only_means(self):
        features = prefit.read('data/processed/checkpoints/stage22-shared-group-prefit/amended-features.json')
        contract = prefit.read('data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json')
        by_id = {r['targetElectorateId']: r for r in features['records']}
        fold = contract['folds'][0]
        training = [by_id[x] for x in fold['trainingContestIds']]
        target = [by_id[x] for x in fold['commonEvaluationContestIds']]
        lower = scenario_rows(training, 'selected_lower')
        upper = scenario_rows(training, 'selected_upper')
        for lo, hi in zip(lower, upper):
            for a, b in zip(lo['candidates'], hi['candidates']):
                if a['s0Reported'] is not None:
                    self.assertLessEqual(a['s0Reported'], b['s0Reported'])
        means = means_for_training(training, 'printed')
        changed_target = deepcopy(target)
        for seat in changed_target:
            for candidate in seat['candidates']:
                candidate['s0Reported'] = None
        self.assertEqual(means, means_for_training(training, 'printed'))
        base, values, starts = candidate_arrays(training, means, 'printed')
        self.assertEqual(len(base), fold['trainingCandidates'])
        self.assertEqual(values.shape, (fold['trainingCandidates'], 2))
        self.assertEqual(len(starts), fold['trainingContests'])

    def test_target_outcomes_do_not_enter_fold_constructor(self):
        features = prefit.read('data/processed/checkpoints/stage22-shared-group-prefit/amended-features.json')
        contract = prefit.read('data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json')
        by_id = {r['targetElectorateId']: r for r in features['records']}
        fold = contract['folds'][0]
        training = [by_id[x] for x in fold['trainingContestIds']]
        target = [by_id[x] for x in fold['commonEvaluationContestIds']]
        earlier = {2011: prefit.read(prefit.ELECTIONS[2011])}
        outcomes = earlier_actuals(training, earlier)
        self.assertEqual(len(outcomes), fold['trainingCandidates'])
        self.assertAlmostEqual(sum(outcomes), fold['trainingContests'])
        target_doc = deepcopy(prefit.read(prefit.ELECTIONS[2017]))
        for seat in target_doc['electorates']:
            for candidate in seat['candidates']:
                candidate['votes'] = 0
                candidate['winner'] = True
                candidate['personId'] = 'synthetic changed identity'
        def synthetic_fit(profile):
            return {'kappa': .01, 'theta': [0.0] * profile.features.shape[1]}
        with patch('scripts.checkpoints.stage22_construction.fit', side_effect=synthetic_fit):
            original = construct_fold(training, target, earlier, 'printed')
            changed_target = deepcopy(target)
            for seat in changed_target:
                for candidate in seat['candidates']:
                    candidate['originalAffiliation'] = 'synthetic changed identity label'
            mutated = construct_fold(training, changed_target,
                                     {**earlier, 2017: target_doc}, 'printed')
        self.assertEqual(original, mutated)
        self.assertEqual(len(earlier_actuals(training, earlier)), len(outcomes))

    def test_prediction_conservation_and_restricted_comparator(self):
        features = prefit.read('data/processed/checkpoints/stage22-shared-group-prefit/amended-features.json')
        seat = next(r for r in features['records'] if r['status'] == 'constructed')
        means = {'S': 0.5, 'V': 0.0}
        fitted = {'kappa': .01, 'theta': []}
        result = predict([seat], means, 'printed', 'baseline', fitted)[0]
        self.assertAlmostEqual(sum(result['candidateShares'].values()), 1)
        self.assertEqual(set(result['candidateShares']),
                         {c['targetOccurrenceId'] for c in seat['candidates']})
        comparison = contextual_predictions([seat])[0]
        self.assertAlmostEqual(sum(comparison['uniform'].values()), 1)
        if comparison['restrictedZeroFloor'] is not None:
            self.assertAlmostEqual(sum(comparison['restrictedZeroFloor'].values()), 1)

    def test_runner_isolates_holdout_outcomes_but_uses_earlier_outcomes(self):
        features = prefit.read('data/processed/checkpoints/stage22-shared-group-prefit/amended-features.json')
        contract = prefit.read('data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json')
        elections = {year: prefit.read(prefit.ELECTIONS[year]) for year in (2011, 2017)}

        def synthetic_fit(profile):
            # Deliberately outcome-sensitive synthetic stand-in for the solver.
            return {'kappa': .001 + .001 * float(np.mean(profile.actual ** 2)),
                    'theta': [0.0] * profile.features.shape[1]}

        with patch('scripts.checkpoints.stage22_construction.fit', side_effect=synthetic_fit):
            original_fit, original_predictions = build(features, contract, elections)
            altered = deepcopy(elections)
            for seat in altered[2017]['electorates']:
                if len(seat['candidates']) >= 2:
                    a = next(c for c in seat['candidates'] if c['votes'] > 1)
                    b = next(c for c in seat['candidates'] if c is not a)
                    a['votes'] -= 1
                    b['votes'] += 1
                    a['winner'], b['winner'] = True, False
            altered_fit, altered_predictions = build(features, contract, altered)
        self.assertEqual(original_fit['folds'][0], altered_fit['folds'][0])
        self.assertEqual(original_predictions['folds'][0], altered_predictions['folds'][0])
        self.assertNotEqual(original_fit['folds'][1]['scenarios']['printed']['fits']['baseline'],
                            altered_fit['folds'][1]['scenarios']['printed']['fits']['baseline'])


if __name__ == '__main__':
    unittest.main()
