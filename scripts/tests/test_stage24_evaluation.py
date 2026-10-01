"""Stage24 paired evaluation arithmetic and outcome-boundary checks."""
import copy
import math
import unittest
from unittest.mock import patch

from scripts.checkpoints import stage24_common as common
from scripts.checkpoints import stage24_construction as construction
from scripts.checkpoints import stage24_evaluation as evaluation


def synthetic_score(predicted, observed=(.6, .4), winner='major'):
    candidates = [
        {'candidateOccurrenceId': 'major', 'partyBallotGroupKey': 'nationalparty'},
        {'candidateOccurrenceId': 'independent', 'partyBallotGroupKey': None},
    ]
    actual = {'candidateShares': dict(zip(('major', 'independent'), observed)),
              'winnerCandidateId': winner}
    return evaluation.score_contest(
        dict(zip(('major', 'independent'), predicted)), actual, candidates)


class Stage24EvaluationTests(unittest.TestCase):
    def test_paired_interaction_sign_and_contest_weighting(self):
        predictions = {'A': (.6, .4), 'B': (.7, .3),
                       'C': (.5, .5), 'D': (.55, .45)}
        first = {'targetElectorateId': 'one',
                 'cells': {cell: synthetic_score(values) for cell, values in predictions.items()}}
        second = {'targetElectorateId': 'two',
                  'cells': {cell: synthetic_score(values, (.5, .5))
                            for cell, values in predictions.items()}}
        rows = [first, second]
        scores = evaluation.score_cells(rows)
        summary, paired = evaluation.paired_summary(rows, scores)
        self.assertAlmostEqual(paired[0]['interactionPP'], -15)
        self.assertAlmostEqual(summary['interactionPP'],
                               (paired[0]['interactionPP'] + paired[1]['interactionPP']) / 2)
        self.assertAlmostEqual(summary['interactionPP'],
                               (scores['D']['contestEqualMaePP'] - scores['C']['contestEqualMaePP']) -
                               (scores['B']['contestEqualMaePP'] - scores['A']['contestEqualMaePP']))

    def test_group_denominators_and_no_group_share_effect(self):
        row = {'targetElectorateId': 'one',
               'cells': {'A': synthetic_score((.6, .4)),
                         'B': synthetic_score((.6, .4)),
                         'C': synthetic_score((.7, .3)),
                         'D': synthetic_score((.7, .3))}}
        groups = evaluation.group_summary([row])
        independent = groups['affirmative_no_party_group']
        self.assertEqual((independent['candidates'], independent['contestsContainingGroup']), (1, 1))
        self.assertAlmostEqual(independent['pairedCandidateEqualMaePP']
                               ['baseline_substitution_C_minus_A'], 10)
        self.assertEqual(groups['labour']['contestsContainingGroup'], 0)

    def test_ties_and_winner_set_transitions(self):
        tied = synthetic_score((.5, .5))
        self.assertEqual(tied['predictedWinnerSet'], ['independent', 'major'])
        self.assertFalse(tied['uniqueCorrect'])
        self.assertTrue(tied['tieContainsWinner'])
        exact = synthetic_score((.6, .4))
        row = {'targetElectorateId': 'one', 'cells': {'A': tied, 'C': exact}}
        transitions = evaluation.ranking_transitions([row], 'A', 'C')
        self.assertEqual(transitions['changedPredictedWinnerSets'], 1)
        self.assertEqual(transitions['notUniqueCorrectToUniqueCorrect'], 1)
        self.assertEqual(transitions['tieStatusChanged'], 1)

    def test_actual_mutation_changes_evaluation_only(self):
        original, _ = construction.outputs()
        changed = copy.deepcopy(common.read(common.STAGE22 + 'actuals.json'))
        target_id = original['folds'][0]['commonEvaluationContestIds'][0]
        first = next(r for r in changed['records'] if r['targetElectorateId'] == target_id)
        first['candidateShares'] = {cid: 1 / len(first['candidateShares'])
                                    for cid in first['candidateShares']}
        first['winnerCandidateId'] = next(reversed(first['candidateShares']))
        real_read = evaluation.read

        def altered_actuals(path):
            return changed if path == common.STAGE22 + 'actuals.json' else real_read(path)

        with patch.object(evaluation, 'read', side_effect=altered_actuals):
            altered_scores = evaluation.build()
        saved_scores = common.read(common.PREFIX + 'diagnostics.json')
        self.assertNotEqual(altered_scores['folds'][0]['cells']['A']['contestEqualMaePP'],
                            saved_scores['folds'][0]['cells']['A']['contestEqualMaePP'])
        # The real construction runner never reads target candidate actuals.
        rebuilt, _ = construction.outputs()
        self.assertEqual(original, rebuilt)

    def test_deterministic_regeneration_and_scenarios(self):
        diagnostics, manifest = evaluation.outputs()
        self.assertEqual(common.encode(diagnostics),
                         common.encode(common.read(common.PREFIX + 'diagnostics.json')))
        self.assertEqual(manifest, common.read(common.PREFIX + 'evaluation-manifest.json'))
        self.assertEqual({(f['targetYear'], f['scenario']) for f in diagnostics['folds']},
                         {(year, scenario) for year in (2017, 2023)
                          for scenario in evaluation.SCENARIOS})
        for fold in diagnostics['folds']:
            self.assertEqual(fold['coverage']['contests'], 64)
            self.assertFalse(fold['coverage']['abstentions'])
            self.assertTrue(math.isfinite(fold['paired']['interactionPP']))

    def test_independent_raw_prediction_metric_recalculation(self):
        predictions = common.read(common.PREFIX + 'predictions.json')
        actuals = {r['targetElectorateId']: r['candidateShares']
                   for r in common.read(common.STAGE22 + 'actuals.json')['records']}
        diagnostics = common.read(common.PREFIX + 'diagnostics.json')
        for fold in predictions['folds']:
            year = fold['targetYear']
            scores = {cell: [] for cell in 'ABCD'}
            squared = {cell: [] for cell in 'ABCD'}
            for cell in 'ABCD':
                for contest in fold['scenarios']['printed'][cell]:
                    target = actuals[contest['targetElectorateId']]
                    predicted = contest['candidateShares']
                    self.assertEqual(set(target), set(predicted))
                    absolute = [abs(100 * (predicted[c] - target[c])) for c in target]
                    scores[cell].append(sum(absolute) / len(absolute))
                    squared[cell].append(sum(e * e for e in absolute) / len(absolute))
            reported = next(r for r in diagnostics['folds']
                            if r['targetYear'] == year and r['scenario'] == 'printed')
            for cell in 'ABCD':
                self.assertAlmostEqual(sum(scores[cell]) / 64,
                                       reported['cells'][cell]['contestEqualMaePP'])
                self.assertAlmostEqual(math.sqrt(sum(squared[cell]) / 64),
                                       reported['cells'][cell]['contestEqualRmsePP'])
            direct_i = sum((d - c) - (b - a) for a, b, c, d in zip(
                scores['A'], scores['B'], scores['C'], scores['D'])) / 64
            self.assertAlmostEqual(direct_i, reported['paired']['interactionPP'])

    def test_direct_formula_for_shared_group_and_no_group(self):
        inventory = common.read(common.PREFIX + 'input-inventory.json')
        constructed = common.read(common.PREFIX + 'predictions.json')
        fold = inventory['folds'][1]
        seat = next(r for r in fold['contests'] if any(
            c['mappingStatus'] == 'mapped_shared_group_single_local_destination'
            for c in r['candidates']))
        parameters = fold['scenarios']['printed']['parameters']
        mean_s = fold['scenarios']['printed']['trainingOnlyMeans']['S']
        for cell, model in (('C', 'baseline'), ('D', 'baseline_plus_S')):
            fit = parameters[model]
            intensities = {}
            for c in seat['candidates']:
                value = c['predictedTargetPartySupport'] + fit['kappa']
                if model == 'baseline_plus_S' and c['s0Reported'] is not None:
                    value *= math.exp(fit['theta'][0] * (c['s0Reported'] - mean_s))
                intensities[c['candidateOccurrenceId']] = value
            total = sum(intensities.values())
            saved = next(r for r in constructed['folds'][1]['scenarios']['printed'][cell]
                         if r['targetElectorateId'] == seat['targetElectorateId'])
            for cid, value in intensities.items():
                self.assertAlmostEqual(value / total, saved['candidateShares'][cid])


if __name__ == '__main__':
    unittest.main()
