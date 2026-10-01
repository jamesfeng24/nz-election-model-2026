"""Synthetic paired-error, tie, and denominator arithmetic for Stage22."""

import unittest
from copy import deepcopy

from scripts.checkpoints.stage22_evaluation import (
    contest_error, paired, score_rows, target_actuals, winner_set)
from scripts.checkpoints import stage22_prefit as prefit


class Stage22EvaluationTests(unittest.TestCase):
    def test_complete_slate_metric_arithmetic_and_ties(self):
        candidates = [{'targetOccurrenceId': 'a', 'targetPartyKey': 'p',
                       'mappingStatus': 'mapped', 's0Reported': .5, 'v0': .1},
                      {'targetOccurrenceId': 'b', 'targetPartyKey': None,
                       'mappingStatus': 'no_group', 's0Reported': None, 'v0': None}]
        actual = {'candidateShares': {'a': .7, 'b': .3}, 'winnerCandidateId': 'a'}
        model = contest_error({'a': .6, 'b': .4}, actual, candidates)
        control = contest_error({'a': .5, 'b': .5}, actual, candidates)
        self.assertAlmostEqual(model['contestMaePP'], 10)
        self.assertAlmostEqual(model['contestMsePP2'], 100)
        self.assertEqual(winner_set({'a': .5, 'b': .5}), ['a', 'b'])
        self.assertTrue(control['tieContainsWinner'])
        rows = [{'targetElectorateId': 'synthetic-seat',
                 'methods': {'model': model, 'control': control}}]
        self.assertAlmostEqual(paired(rows, 'model', 'control')['modelMinusControlMaePP'], -10)
        self.assertAlmostEqual(paired(rows, 'model', 'control')['modelMinusControlMsePP2'], -300)
        metrics = score_rows(rows, 'model')
        self.assertAlmostEqual(metrics['contestEqualRmsePP'], 10)
        self.assertAlmostEqual(metrics['candidateEqualMaePP'], 10)
        self.assertAlmostEqual(metrics['fullSlateSignedBiasPPAccountingCheck'], 0)

    def test_mismatched_destinations_and_mass_fail(self):
        candidates = [{'targetOccurrenceId': 'a', 'targetPartyKey': 'p',
                       'mappingStatus': 'mapped', 's0Reported': None, 'v0': None},
                      {'targetOccurrenceId': 'b', 'targetPartyKey': 'q',
                       'mappingStatus': 'mapped', 's0Reported': None, 'v0': None}]
        actual = {'candidateShares': {'a': .5, 'b': .5}, 'winnerCandidateId': 'a'}
        for prediction in ({'a': .5, 'c': .5}, {'a': .4, 'b': .4}):
            with self.assertRaisesRegex(ValueError, 'Incompatible'):
                contest_error(prediction, actual, candidates)

    def test_saved_construction_is_separate_from_target_actuals(self):
        predictions = prefit.read('data/processed/checkpoints/stage22-shared-group-experiment/predictions.json')
        elections = {year: prefit.read(prefit.ELECTIONS[year])
                     for year in (2011, 2017, 2023)}
        original = target_actuals(predictions, elections)
        changed = deepcopy(elections)
        seat = next(s for s in changed[2023]['electorates']
                    if s['id'] == predictions['folds'][1]['evaluationContestIds'][0])
        a, b = seat['candidates'][:2]
        a['votes'], b['votes'] = b['votes'], a['votes']
        altered = target_actuals(predictions, changed)
        self.assertNotEqual(original, altered)
        self.assertEqual(predictions['folds'][1]['evaluationContestIds'][0], seat['id'])


if __name__ == '__main__':
    unittest.main()
