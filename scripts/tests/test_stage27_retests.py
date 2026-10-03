"""Real Stage27 adapters plus small synthetic arithmetic/failure fixtures."""
from copy import deepcopy
from fractions import Fraction
import unittest
from unittest.mock import patch

import numpy as np

from scripts.checkpoints import stage25_availability as available
from scripts.checkpoints.stage22_fit import Profile, candidate_arrays, predict
from scripts.models.conditional_nat_lab_response import model as response
from scripts.models.exact_geography_retests import adapters as a
from scripts.models.exact_geography_retests import construction as c
from scripts.models.exact_geography_retests import evaluation as e
from scripts.models.exact_geography_retests.common import *


class Stage27Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(DEST + 'inventory.json')
        cls.folds = read(DEST + 'folds.json')['folds']
        cls.elections, cls.splits = a.datasets()
        cls.predictions = read(DEST + 'predictions.json')
        cls.definitions = read(DEST + 'input-contract.json')['responseModels']

    def fold(self, family='complete_share_baseline_s', year=2023, protocol='expanding_window'):
        return next(f for f in self.folds if f['family'] == family and f['targetYear'] == year
                    and f['chronologyProtocol'] == protocol)

    def test_canonical_counts_and_chronology(self):
        for protocol, counts in (('expanding_window', [0, 63, 83, 147, 181]),
                                 ('more_separated', [0, 0, 63, 83, 147])):
            for year, n, ev in zip((2011, 2014, 2017, 2020, 2023), counts, (63, 20, 64, 34, 64)):
                f = self.fold(year=year, protocol=protocol)
                train, test = a.permitted_fold(f, self.data['shareRecords'])
                self.assertEqual((len(train), len(test)), (n, ev))
        bad = deepcopy(self.fold())
        bad['trainingIds'].append(bad['evaluationIds'][0])
        with self.assertRaisesRegex(ValueError, 'overlap'):
            a.permitted_fold(bad, self.data['shareRecords'])
        bad = deepcopy(self.fold(year=2014, protocol='more_separated'))
        bad['trainingIds'] = self.fold(year=2014)['trainingIds']
        with self.assertRaisesRegex(ValueError, 'chronology'):
            a.permitted_fold(bad, self.data['shareRecords'])

    def test_preprocessing_is_training_only_and_original_reproduction(self):
        f = self.fold(year=2017)
        train, test = a.permitted_fold(f, self.data['shareRecords'])
        mean = a.s_means(train, 'printed')
        changed = deepcopy(test)
        for r in changed:
            for candidate in r['candidates']:
                candidate['s0Reported'] = .99
        self.assertEqual(mean, a.s_means(train, 'printed'))
        self.assertNotEqual(mean, a.s_means(train + changed, 'printed'))
        self.assertTrue(self.predictions['originalReproduction']['passed'])
        self.assertEqual(len(self.predictions['originalReproduction']['checks']), 104)
        for check in self.predictions['originalReproduction']['checks']:
            if 'directSavedMaximumShareDiscrepancy' in check:
                self.assertLessEqual(check['directSavedMaximumShareDiscrepancy'], 1e-12)

    def test_group_mapping_conservation_and_duplicate_rejection(self):
        f = self.fold()
        case = next(r for r in self.predictions['candidateCases'] if r['foldId'] == f['foldId']
                    and r['trainingVariant'] == 'expanded')
        for scenario in case['scenarios'].values():
            for method in METHODS:
                for r in scenario['predictions'][method]:
                    self.assertAlmostEqual(sum(r['candidateShares'].values()), 1, places=12)
        mappings = available.mapped_contests(read(available.MAPPING))
        target = next(s for s in self.elections[2023]['electorates'] if s['id'] == f['evaluationIds'][0])
        mapping = deepcopy(mappings[(2023, target['id'])])
        groups = {p['partyKey'] for s in self.elections[2023]['electorates'] for p in s['parties']}
        mapping['candidates'].append(deepcopy(mapping['candidates'][0]))
        self.assertIsNone(available.target_candidates(mapping, target, groups)[0])
        constructed = [r for r in self.data['shareRecords'] if r['targetYear'] == 2023]
        for row in constructed:
            used = [c['targetPartyKey'] for c in row['candidates'] if c['targetPartyKey']]
            self.assertEqual(len(used), len(set(used)))
        self.assertTrue(any(c['targetPartyKey'] == 'freedomsnz' for r in constructed for c in r['candidates']))

    def test_full_adapter_holdout_mutations_do_not_change_fits_or_predictions(self):
        changed = deepcopy(self.elections)
        for seat in changed[2023]['electorates']:
            seat['winnerCandidateId'] = 'synthetic_forbidden_winner'
            seat['validCandidateVotes'] = 17
            for cand in seat['candidates']:
                cand.update(votes=999, elected=True, share=.999, personId='synthetic_identity',
                            residual=888, identityConfidence='confirmed')
        data = a.inventory(changed, self.splits, read(GEO + 'geography.json'),
                           read(GEO + 'availability.json'), read(available.MAPPING), read(available.CONTINUITY)['records'])
        self.assertEqual(self.data, data)
        cache = read(DEST + 'fit-cache.json')
        f = self.fold()
        result = c.candidate_case(f, data, changed, 'expanded', {}, cache)
        saved = next(r for r in self.predictions['candidateCases'] if r['foldId'] == f['foldId'] and r['trainingVariant'] == 'expanded')
        self.assertEqual(result, saved)
        f = self.fold(family='nat_lab_response')
        result = c.response_case(f, data, changed, 'expanded', self.definitions)
        saved = next(r for r in self.predictions['responseCases'] if r['foldId'] == f['foldId'] and r['trainingVariant'] == 'expanded')
        self.assertEqual(result, saved)
        with self.assertRaisesRegex(ValueError, 'denominator'):
            e.actuals(data, changed)

    def test_completed_training_outcomes_can_change_later_response_fit(self):
        f = self.fold(family='nat_lab_response', year=2014)
        changed = deepcopy(self.elections)
        for seat in changed[2011]['electorates']:
            for candidate in seat['candidates']:
                candidate['votes'] += 123
        before = c.response_case(f, self.data, self.elections, 'expanded', self.definitions)
        after = c.response_case(f, self.data, changed, 'expanded', self.definitions)
        self.assertNotEqual(before['parties']['nationalparty']['common_intercept']['fit'],
                            after['parties']['nationalparty']['common_intercept']['fit'])

    def test_source_victory_is_source_fact_not_target_status(self):
        changed = deepcopy(self.elections)
        source = next(s for s in changed[2020]['electorates'] if any(c['id'] == s['winnerCandidateId'] and c['partyKey'] in ('nationalparty', 'labourparty') for c in s['candidates']))
        source['winnerCandidateId'] = 'synthetic_source_change'
        with self.assertRaisesRegex(ValueError, 'source victory'):
            a.inventory(changed, self.splits, read(GEO + 'geography.json'),
                        read(GEO + 'availability.json'), read(available.MAPPING), read(available.CONTINUITY)['records'])

    def test_rank_failure_and_numerical_failure_are_abstentions(self):
        train, _ = a.permitted_fold(self.fold(year=2014), self.data['shareRecords'])
        bad = deepcopy(train)
        for row in bad:
            for candidate in row['candidates']:
                candidate['s0Reported'] = .5
        self.assertFalse(a.rank_gate(bad, a.s_means(bad, 'printed'), 'printed')['passes'])
        with patch.object(c, 'fit', side_effect=ValueError('synthetic_solver_failure')):
            fitted, _ = c.candidate_fit(train, {2011: self.elections[2011]}, 'printed', 'baseline', {})
        self.assertEqual(fitted['reason'], 'numerical_failure')
        self.assertIn('synthetic_solver_failure', fitted['detail'])

    def test_missing_party_input_does_not_become_zero(self):
        row = deepcopy(self.data['shareRecords'][0])
        row['candidates'][0]['targetPartySupport'] = None
        with self.assertRaisesRegex(ValueError, 'baseline'):
            candidate_arrays([row], {'S': .5, 'V': 0}, 'printed')
        candidates = [c for r in self.data['shareRecords'] for c in r['candidates']]
        self.assertTrue(any(c['targetPartySupport'] == 0 and c['targetPartyKey'] is None for c in candidates))
        self.assertTrue(all(c['v0'] is None for c in candidates))

    def test_coupled_rounding_witnesses_and_sensitivity(self):
        for r in self.data['roundingWitnesses']:
            self.assertEqual(sum(Fraction(v) for v in r['rowPercentWitness']), 100)
        for r in self.data['shareRecords']:
            for candidate in r['candidates']:
                if candidate['s0Reported'] is not None:
                    lo, hi = map(Fraction, candidate['coupledSamePartyPercent'])
                    self.assertLessEqual(lo, hi)
                    self.assertGreaterEqual(lo, 0)
                    self.assertLessEqual(hi, 100)

    def test_benchmark_metrics_ties_and_no_clipping(self):
        candidate = [{'targetOccurrenceId': str(i), 'targetPartyKey': 'test', 'mappingStatus': 'test',
                      's0Reported': .5, 'v0': None} for i in range(2)]
        actual = {'candidateShares': {'0': .8, '1': .2}, 'winnerCandidateId': '0'}
        base = e.contest_error({'0': .5, '1': .5}, actual, candidate)
        model = e.contest_error({'0': .7, '1': .3}, actual, candidate)
        row = {'targetElectorateId': 'synthetic', 'methods': {'baseline': base, 'baseline_plus_S': model}}
        self.assertEqual(base['predictedWinnerSet'], ['0', '1'])
        self.assertTrue(base['tieContainsWinner'])
        self.assertAlmostEqual(e.score_rows([row], 'baseline')['contestEqualRmsePP'], 30)
        self.assertAlmostEqual(e.paired([row], 'baseline_plus_S', 'baseline')['maeGainPP'], 20)
        r = {'id': 'synthetic', 'c0': .9, 'p0': .1, 'sourceWon': 0,
             'partyInputs': {'actual_observed_local_party': [.9, .9]}}
        pred = response.predict(r, {'status': 'available', 'alpha': 0, 'beta': 1, 'gamma': 0}, 'actual_observed_local_party')
        self.assertGreater(pred['point'], 1)
        self.assertTrue(pred['outOfRangeCertain'])

    def test_analytic_gradient_matches_finite_differences(self):
        train, _ = a.permitted_fold(self.fold(year=2014), self.data['shareRecords'])
        means = a.s_means(train, 'printed')
        base, features, starts = candidate_arrays(train, means, 'printed')
        actual = c.earlier_actuals(train, {2011: self.elections[2011]})
        profile = Profile(base, features, starts, actual, 'baseline_plus_S')
        loss, gradient = profile.value_gradient(.01, np.array([.7]))
        h = 1e-6
        numeric = (profile.value_gradient(.01, np.array([.7 + h]))[0] -
                   profile.value_gradient(.01, np.array([.7 - h]))[0]) / (2*h)
        self.assertAlmostEqual(gradient[0], numeric, places=8)

    def test_earliest_fold_keeps_parameter_free_controls(self):
        observed = e.actuals(self.data, self.elections)
        case = next(r for r in self.predictions['candidateCases'] if r['targetYear'] == 2011)
        rows = e.share_rows(case, 'printed', keyed(self.data['shareRecords'], 'targetElectorateId'),
                            keyed(observed['candidateActuals'], 'targetElectorateId'))
        summary = e.candidate_summary(rows)
        self.assertEqual(summary['restrictedZeroFloorContests'], 43)
        self.assertEqual(summary['fittedRestrictedCommonContests'], 0)
        self.assertEqual(summary['parameterFreeRestricted']['restrictedZeroFloor']['contests'], 43)

    def test_portable_evaluation_matches_existing_kernel(self):
        by_id = keyed(self.data['shareRecords'], 'targetElectorateId')
        for case in self.predictions['candidateCases']:
            if case['trainingVariant'] != 'expanded' or not case['trainingIds']:
                continue
            rows = [by_id[k] for k in case['evaluationIds']]
            for scenario, details in case['scenarios'].items():
                for method in METHODS:
                    numerical = predict(rows, details['trainingOnlyMeans'], scenario, method, details['fits'][method])
                    portable = details['predictions'][method]
                    for original, stable in zip(numerical, portable):
                        for key, value in original['candidateShares'].items():
                            self.assertLessEqual(abs(value - stable['candidateShares'][key]), 1e-12)

    def test_pinned_inputs_and_constructed_bytes_are_protected(self):
        from scripts.models.exact_geography_retests import common
        with patch.object(common, 'digest', return_value='synthetic_changed_bytes'):
            with self.assertRaisesRegex(ValueError, 'Changed required input'):
                common.verify_inputs()
            with self.assertRaisesRegex(ValueError, 'Changed constructed output'):
                common.verify_outputs(DEST + 'construction-manifest.json')

    def test_inventory_reproduces_without_git_history(self):
        from scripts.models.exact_geography_retests.inventory import outputs
        with patch('subprocess.check_output', side_effect=AssertionError('Git history unavailable in shallow checkout')):
            generated = outputs()
        self.assertEqual(generated['inventory.json'], self.data)
        self.assertEqual(generated['prior-data-contract.json'], read(DEST + 'prior-data-contract.json'))

    def test_squared_errors_use_portable_multiplication(self):
        from statistics import mean
        actual = keyed(e.actuals(self.data, self.elections)['candidateActuals'], 'targetElectorateId')
        by_id = keyed(self.data['shareRecords'], 'targetElectorateId')
        for case in self.predictions['candidateCases']:
            if case['trainingVariant'] != 'expanded':
                continue
            rows = e.share_rows(case, 'printed', by_id, actual)
            for row in rows:
                for score in row['methods'].values():
                    if score is not None:
                        errors = [c['errorPP'] for c in score['candidateErrors']]
                        self.assertEqual(score['contestMsePP2'], mean(x * x for x in errors))

    def test_provenance_and_preservation(self):
        verify_inputs()
        self.assertEqual(verify_preservation(), 1362)
        self.assertEqual(len(self.data['fullFrame']), 356)
        self.assertEqual(len(self.data['shareRecords']), 245)
        self.assertEqual(len(self.data['responseRecords']), 490)


if __name__ == '__main__':
    unittest.main()
