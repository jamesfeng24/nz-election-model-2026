"""Independent saved-fit selection, full adapters and bounded paired arithmetic."""
from copy import deepcopy
from math import exp, fsum, sqrt
import unittest
from unittest.mock import patch

from scripts.transport.comparison.common import PREFIX, MODELS, BRANCHES, read, verify
from scripts.transport.comparison.construction import build, centered, shares
from scripts.transport.comparison import evaluation
from scripts.models.joint_candidate_share.metrics import score
from scripts.transport.continuous.features import context, flow_index, links_for_geography, weighted
from scripts.transport.continuous.inventory import inventory
from scripts.transport.geography import all_rows


def component(source, mass, value):
    return {'sourceElectorateId': source, 'partyMassExact': str(mass),
            'valueFraction': value, 'reason': None}


class ContinuousArithmeticTests(unittest.TestCase):
    def test_centered_before_weighting_and_no_supported_mass_renormalization(self):
        source = [component('one', 10, .8), component('two', 30, None)]
        feature = weighted(source, .6)
        candidate = {'continuous': {'S': feature, 'R': weighted(source, .1),
                                    'RStrict': weighted([component('one', 10, None),
                                                        component('two', 30, None)], .1)}}
        self.assertAlmostEqual(centered(candidate, {'S': .6, 'R': .1}, 'S')[0], .05)
        self.assertAlmostEqual(centered(candidate, {'S': .6, 'R': .1}, 'joint')[1], .175)
        self.assertEqual(centered(candidate, {'S': .6, 'R': .1}, 'joint_strict')[1], 0)
        self.assertEqual(feature['supportedWeight'], .25)
        self.assertEqual(feature['unsupportedWeight'], .75)

    def test_all_unsupported_remains_neutral_under_nonzero_saved_means(self):
        feature = weighted([component('source', 100, None)], .6)
        candidate = {'continuous': dict.fromkeys(('S', 'R', 'RStrict'), feature)}
        for branch in BRANCHES:
            self.assertTrue(all(v == 0 for v in centered(candidate, {'S': .6, 'R': .6}, branch)))

    def test_independent_prediction_arithmetic_and_normalization(self):
        base = [.4, .3, 0]
        x = [[.1], [-.2], [0]]
        parameters = {'status': 'fitted', 'kappa': .02, 'theta': [1.5]}
        masses = [(b + .02) * exp(1.5 * feature[0]) for b, feature in zip(base, x)]
        result = shares(base, x, parameters)
        for q, mass in zip(result, masses):
            self.assertAlmostEqual(q, mass / fsum(masses), places=14)
        self.assertAlmostEqual(fsum(result), 1, places=14)
        # An unsupported/no-group candidate changes through the common denominator.
        neutral = shares(base, [[0], [0], [0]], parameters)
        self.assertNotEqual(result[2], neutral[2])

    def test_extreme_valid_inputs_and_frozen_parameter_rejections(self):
        parameters = {'status': 'fitted', 'kappa': .0001, 'theta': [4, -4]}
        q = shares([0, 1, 0], [[1, -1], [-1, 1], [0, 0]], parameters)
        self.assertAlmostEqual(fsum(q), 1, places=12)
        self.assertTrue(all(0 <= value <= 1 for value in q))
        for changed in (dict(parameters, kappa=.2), dict(parameters, theta=[4.1, 0]),
                        dict(parameters, status='failed'), dict(parameters, theta=[])):
            with self.assertRaises(ValueError):
                shares([.5, .5], [[0, 0], [0, 0]], changed)
        with self.assertRaises(ValueError):
            shares([.5, -.1], [[0, 0], [0, 0]], parameters)
        with self.assertRaises(ValueError):
            shares([.5], [[float('nan'), 0]], parameters)


class ActualComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = read('data/processed/continuous-transport/inventory.json')
        cls.manifest = read(PREFIX + '/sample-manifest.json')
        cls.saved = read('data/processed/models/joint-candidate-share/construction.json')
        cls.reference = read('data/processed/continuous-transport/construction.json')
        cls.predictions = build(cls.inventory, cls.manifest, cls.saved, cls.reference)

    def test_exact_frozen_complete_ids_and_stage42_joint_reproduction(self):
        for fold, sample, count, candidates in zip(self.predictions['folds'], self.manifest['folds'],
                                                   (64, 65), (451, 561)):
            self.assertFalse(fold['fittingPerformed'])
            self.assertFalse(fold['heldoutCandidateOutcomesConsumed'])
            self.assertTrue(fold['stage42JointReproductionWithin1eMinus12'])
            for branch in BRANCHES:
                rows = fold['predictions'][branch]
                self.assertEqual([r['targetElectorateId'] for r in rows], sample['comparisonIds'])
                self.assertEqual([cid for r in rows for cid in r['candidateShares']], sample['candidateIds'])
                self.assertEqual(len(rows), count)
                self.assertEqual(sum(len(r['candidateShares']) for r in rows), candidates)
                for row in rows:
                    self.assertAlmostEqual(fsum(row['candidateShares'].values()), 1, places=12)
            prior = next(f for f in self.reference['folds'] if f['targetYear'] == fold['targetYear'])
            for branch, previous in (('joint', 'continuous'), ('joint_strict', 'continuous_strict')):
                self.assertEqual(fold['predictions'][branch], prior['predictions'][previous])

    def test_independently_fitted_kappa_and_s_coefficient_are_not_joint_ablations(self):
        for fold in self.predictions['folds']:
            previous = next(f for f in self.saved['folds'] if f['id'] == fold['savedFoldId'])
            for model, key in MODELS.items():
                self.assertEqual(fold['fits'][model], previous['fits'][key])
            s = fold['fits']['S']['parameters']
            joint = fold['fits']['joint']['parameters']
            self.assertNotEqual(s['kappa'], joint['kappa'])
            self.assertNotEqual(s['theta'][0], joint['theta'][0])
            self.assertEqual(len(s['theta']), 1)
            self.assertEqual(len(joint['theta']), 2)
            self.assertEqual(fold['trainingOnlyMeans'], previous['trainingOnlyMeans'])

    def test_strict_sensitivity_changes_r_only_and_leaves_s_predictions_unchanged(self):
        changed = deepcopy(self.inventory)
        for row in changed['records']:
            for candidate in row['candidates']:
                candidate['continuous']['R'] = deepcopy(candidate['continuous']['RStrict'])
        strict_reference = deepcopy(self.reference)
        for fold in strict_reference['folds']:
            fold['predictions']['continuous'] = deepcopy(fold['predictions']['continuous_strict'])
        altered = build(changed, self.manifest, self.saved, strict_reference)
        for before, after in zip(self.predictions['folds'], altered['folds']):
            self.assertEqual(before['predictions']['S'], after['predictions']['S'])
            self.assertEqual(after['predictions']['joint'], before['predictions']['joint_strict'])
            for broad, strict in zip(before['predictions']['joint'], before['predictions']['joint_strict']):
                for cid in broad['centeredContributions']:
                    self.assertEqual(broad['centeredContributions'][cid][0], strict['centeredContributions'][cid][0])

    def test_changed_saved_parameters_means_or_training_are_rejected(self):
        for mutation in ('S', 'joint', 'means', 'training'):
            saved = deepcopy(self.saved)
            sample = self.manifest['folds'][0]
            fold = next(f for f in saved['folds'] if f['id'] == sample['savedFoldId'])
            if mutation in MODELS:
                fold['fits'][MODELS[mutation]]['parameters']['kappa'] += .001
            elif mutation == 'means':
                fold['trainingOnlyMeans']['S'] += .001
            else:
                fold['trainingIds'].append('nz-general-2023-electorate-01')
            with self.assertRaises(ValueError):
                build(self.inventory, self.manifest, saved, self.reference)

    def test_target_and_later_training_outcomes_rejected_even_when_manifests_agree(self):
        for year in (2014, 2023):
            manifest = deepcopy(self.manifest)
            saved = deepcopy(self.saved)
            sample = manifest['folds'][0]
            sample['trainingIds'].append(f'nz-general-{year}-electorate-01')
            previous = next(f for f in saved['folds'] if f['id'] == sample['savedFoldId'])
            previous['trainingIds'] = deepcopy(sample['trainingIds'])
            with self.assertRaisesRegex(ValueError, 'Target/later'):
                build(self.inventory, manifest, saved, self.reference)

    def test_wrong_saved_branch_or_chronology_rejected(self):
        for key, value in (('branch', 'observed_retrained'), ('protocol', 'more_separated')):
            saved = deepcopy(self.saved)
            fold = next(f for f in saved['folds'] if f['id'] == self.manifest['folds'][0]['savedFoldId'])
            fold[key] = value
            with self.assertRaisesRegex(ValueError, 'branch/chronology'):
                build(self.inventory, self.manifest, saved, self.reference)

    def test_changed_candidate_or_contest_membership_is_not_silently_trimmed(self):
        for mutation in ('candidate', 'contest'):
            changed = deepcopy(self.inventory)
            if mutation == 'candidate':
                changed['records'][0]['candidates'].pop()
            else:
                changed['records'].pop(0)
            with self.assertRaisesRegex(ValueError, 'common IDs'):
                build(changed, self.manifest, self.saved, self.reference)

    def test_actual_source_feature_path_ignores_heldout_outcomes_and_target_residuals(self):
        geo = all_rows()
        ctx = context()
        edges, links = links_for_geography(geo, ctx['occurrences'])
        flows = flow_index(geo, ctx['occurrences'])
        original = inventory(geo, ctx, flows, edges)
        for year in (2014, 2020):
            for seat in ctx['elections'][year]['electorates']:
                seat['winnerCandidateId'] = 'counterfactual'
                for candidate in seat['candidates']:
                    candidate.update(votes=999999, winner=True, residual=42, modelError=42)
        for occurrence in ctx['occurrences']:
            if occurrence['year'] in (2014, 2020):
                occurrence.update(votes=1, winner=True, residual=999)
        for residual in ctx['residuals'].values():
            if residual['year'] in (2014, 2020):
                residual.update(normalizedPremium=999, referenceId='changed-heldout-reference')
        changed_edges, changed_links = links_for_geography(geo, ctx['occurrences'])
        self.assertEqual(changed_edges, edges)
        self.assertEqual(changed_links, links)
        changed = inventory(geo, ctx, flows, changed_edges)
        self.assertEqual(changed, original)
        self.assertEqual(build(changed, self.manifest, self.saved, self.reference), self.predictions)

    def test_consumed_input_and_prior_artifact_preservation(self):
        self.assertGreater(verify(), 1744)
        with patch('scripts.transport.comparison.common.digest', return_value='corrupt'):
            with self.assertRaisesRegex(ValueError, 'Changed consumed input'):
                verify()


class PairedEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ActualComparisonTests.setUpClass()
        for key in ('inventory', 'manifest', 'saved', 'reference', 'predictions'):
            setattr(cls, key, getattr(ActualComparisonTests, key))
        cls.evaluation = evaluation.build(cls.predictions, cls.inventory)

    def test_fold_metrics_and_joint_minus_s_sign_have_independent_arithmetic(self):
        for fold in self.evaluation['folds']:
            rows = fold['records']
            full = fold['samples']['full']
            maes = {}
            for branch in BRANCHES:
                errors = [[c['errorPP'] for c in r['scores'][branch]['candidateErrors']] for r in rows]
                maes[branch] = fsum(fsum(abs(v) for v in es)/len(es) for es in errors)/len(errors)
                rmse = sqrt(fsum(fsum(v*v for v in es)/len(es) for es in errors)/len(errors))
                self.assertAlmostEqual(full['metrics'][branch]['contestEqualMaePP'], maes[branch], places=12)
                self.assertAlmostEqual(full['metrics'][branch]['contestEqualRmsePP'], rmse, places=12)
            for branch in ('joint', 'joint_strict'):
                paired = [r['scores'][branch]['contestMaePP'] - r['scores']['S']['contestMaePP'] for r in rows]
                self.assertAlmostEqual(full['pairs'][branch]['jointMinusSMaePP'], fsum(paired)/len(rows), places=12)
                self.assertAlmostEqual(full['pairs'][branch]['jointMinusSMaePP'], maes[branch]-maes['S'], places=12)
                self.assertEqual(full['pairs'][branch]['improvedContests'], sum(v < 0 for v in paired))
                self.assertEqual(full['pairs'][branch]['worsenedContests'], sum(v > 0 for v in paired))

    def test_full_geo_and_r_partitions_retain_every_primary_observation(self):
        for fold in self.evaluation['folds']:
            samples = fold['samples']
            self.assertEqual(sum(samples[t]['contests'] for t in ('exact', 'approximate_95', 'approximate_90', 'fallback')),
                             samples['full']['contests'])
            for key in ('R', 'RStrict'):
                self.assertEqual(samples[key+'_any']['contests'] + samples[key+'_none']['contests'], samples['full']['contests'])
            self.assertEqual(samples['full']['groups']['R_supported']['counts']['S'],
                             samples['full']['groups']['R_supported']['counts']['joint_strict'])
            self.assertEqual(sum(samples['full']['groups'][g]['counts']['S']['candidates'] for g in
                                 ('national', 'labour', 'other_mapped', 'affirmative_no_party_group')),
                             samples['full']['candidates'])

    def test_pooled_equal_contest_and_equal_election_are_distinct(self):
        folds = self.evaluation['folds']
        for branch in BRANCHES:
            means = [f['samples']['full']['metrics'][branch]['contestEqualMaePP'] for f in folds]
            counts = [f['samples']['full']['contests'] for f in folds]
            pooled = fsum(m*n for m, n in zip(means, counts))/sum(counts)
            self.assertAlmostEqual(self.evaluation['pooled']['metrics'][branch]['contestEqualMaePP'], pooled, places=12)
            self.assertAlmostEqual(self.evaluation['equalElection']['metrics'][branch]['maePP'], fsum(means)/2, places=12)
            rmses = [f['samples']['full']['metrics'][branch]['contestEqualRmsePP'] for f in folds]
            self.assertAlmostEqual(self.evaluation['equalElection']['metrics'][branch]['rmsePP'],
                                   sqrt(fsum(v*v for v in rmses)/2), places=12)

    def test_missing_paired_contest_cannot_reduce_only_one_branch(self):
        changed = deepcopy(self.predictions)
        changed['folds'][0]['predictions']['joint'].pop()
        with self.assertRaisesRegex(ValueError, 'Paired contest IDs'):
            evaluation.build(changed, self.inventory)

    def test_actual_candidate_outcomes_change_evaluation_only(self):
        elections = {y: read(f'data/processed/elections/{y}.json') for y in (2014, 2020)}
        cid = self.predictions['folds'][0]['predictions']['S'][0]['targetElectorateId']
        seat = next(s for s in elections[2014]['electorates'] if s['id'] == cid)
        votes = [c['votes'] for c in seat['candidates']]
        for c, value in zip(seat['candidates'], reversed(votes)):
            c['votes'] = value
        seat['winnerCandidateId'] = max(seat['candidates'], key=lambda c: c['votes'])['id']
        changed = evaluation.build(self.predictions, self.inventory, elections)
        self.assertNotEqual(changed, self.evaluation)
        self.assertEqual(build(self.inventory, self.manifest, self.saved, self.reference), self.predictions)


class SyntheticPairTests(unittest.TestCase):
    def test_ties_and_actual_top_two_margin_follow_saved_metric(self):
        row = {'candidates': [{'targetOccurrenceId': cid, 'partyBallotGroupKey': group,
            'R': {'broad': {'availabilityPattern': 'neither_feature'}}}
            for cid, group in (('a', 'nationalparty'), ('b', 'labourparty'), ('c', None))]}
        actual = {'candidateShares': {'a': .7, 'b': .2, 'c': .1}, 'winnerCandidateId': 'a'}
        tied = score({'a': 1/3, 'b': 1/3, 'c': 1/3}, actual, row, 'broad')
        self.assertFalse(tied['uniqueCorrect'])
        self.assertTrue(tied['tieContainsWinner'])
        self.assertEqual(len(tied['predictedWinnerSet']), 3)
        winner_reversed = score({'a': .35, 'b': .15, 'c': .5}, actual, row, 'broad')
        self.assertAlmostEqual(winner_reversed['actualTopTwoMarginAbsoluteErrorPP'], 30)


if __name__ == '__main__':
    unittest.main()
