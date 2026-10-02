"""Stage25 unfitted fold planning and source-composition contracts."""
import copy
import unittest

from scripts.checkpoints import stage25_design as design
from scripts.checkpoints import stage25_availability as availability


class Stage25DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.composition, cls.register = design.build()

    def test_all_models_and_transitions_have_unique_plans(self):
        folds = self.plan['folds']
        self.assertEqual(len(folds), 60)
        self.assertEqual(len({f['foldId'] for f in folds}), 60)
        for fold in folds:
            self.assertEqual(len(fold['trainingIds']), len(set(fold['trainingIds'])))
            self.assertEqual(len(fold['evaluationIds']), len(set(fold['evaluationIds'])))
            self.assertFalse(set(fold['trainingIds']) & set(fold['evaluationIds']))
            years = fold['trainingTransitionTargetYears']
            self.assertTrue(all(y < fold['targetYear'] for y in years))
            if fold['chronologyProtocol'] == 'more_separated':
                self.assertTrue(all(y < fold['sourceYear'] for y in years))
            else:
                self.assertTrue(all(y <= fold['sourceYear'] for y in years))
            self.assertEqual(set(fold['trainingIds']),
                             set(fold['originalTrainingIds']) | set(fold['addedTrainingIds']))
            self.assertEqual(set(fold['evaluationIds']),
                             set(fold['originalEvaluationIds']) | set(fold['addedEvaluationIds']))

    def test_more_separated_preserves_original_design_ids(self):
        folds = {f['targetYear']: f for f in self.plan['folds']
                 if f['family'] == 'complete_share_baseline_s' and
                 f['chronologyProtocol'] == 'more_separated'}
        self.assertEqual((len(folds[2011]['trainingIds']), len(folds[2014]['trainingIds'])), (0, 0))
        self.assertFalse(folds[2014]['gates']['minimumTrainingContests'])
        self.assertEqual((len(folds[2020]['trainingIds']), len(folds[2020]['evaluationIds'])), (83, 34))
        self.assertEqual((len(folds[2023]['originalTrainingIds']),
                          len(folds[2023]['addedTrainingIds'])), (127, 20))
        self.assertEqual(folds[2020]['savedFixedFitTransport']['savedHoldoutYear'], 2017)
        self.assertEqual(folds[2020]['gates']['structuralWithinSlateRank'], 1)

    def test_expanding_window_admits_completed_overlapping_transition(self):
        folds = {f['targetYear']: f for f in self.plan['folds']
                 if f['family'] == 'complete_share_baseline_s' and
                 f['chronologyProtocol'] == 'expanding_window'}
        self.assertEqual([len(folds[y]['trainingIds']) for y in sorted(folds)], [0, 63, 83, 147, 181])
        self.assertEqual(folds[2014]['trainingTransitionTargetYears'], [2011])
        self.assertEqual(folds[2014]['overlappingTrainingTargetYears'], [2011])
        self.assertTrue(folds[2014]['gates']['minimumTrainingContests'])
        self.assertEqual(folds[2014]['gates']['structuralWithinSlateRank'], 1)
        ids = set(folds[2014]['preprocessing']['trainingContestIds'])
        rows = design.read(design.AVAILABILITY)['records']
        self.assertEqual(sum(len(r['candidateOccurrenceIds']) for r in rows
                             if r['targetElectorateId'] in ids), 423)
        self.assertEqual(len(folds[2014]['evaluationIds']), 20)

    def test_target_later_and_invalid_protocol_rejected(self):
        years = [2011, 2014, 2017, 2020, 2023]
        self.assertEqual(design.training_years(years, 2011, 2014, 'expanding_window'), [2011])
        self.assertEqual(design.training_years(years, 2011, 2014, 'more_separated'), [])
        self.assertEqual(design.training_years(list(reversed(years)), 2017, 2020,
                                              'expanding_window'), [2011, 2014, 2017])
        with self.assertRaises(ValueError):
            design.training_years(years, 2014, 2014, 'expanding_window')
        with self.assertRaises(ValueError):
            design.training_years(years, 2011, 2014, 'unregistered')

    def test_training_centering_excludes_holdout_features_and_results(self):
        rows = design.read(design.AVAILABILITY)['records']
        train = [r for r in rows if r['targetYear'] == 2011 and
                 r['targetElectorateId'] in design.ids_for_family(rows, 'complete_share_baseline_s')]
        holdout = [r for r in rows if r['targetYear'] == 2014]
        before = design.feature_rank(holdout, train)['trainingOnlyMeanS']
        changed = copy.deepcopy(holdout)
        for row in changed:
            for feature in row['candidateFeatures']:
                feature['s0Printed'] = 1.0
            row['targetCandidateVotes'] = -1
            row['identityEvidence'] = {'claim': 'changed'}
        self.assertEqual(design.feature_rank(changed, train)['trainingOnlyMeanS'], before)

    def test_family_gates_and_parameter_free_exclusions(self):
        folds = {(f['family'], f['targetYear'], f['chronologyProtocol']): f
                 for f in self.plan['folds']}
        response = folds['nat_lab_response', 2014, 'expanding_window']
        self.assertEqual(len(response['trainingIds']), 126)
        self.assertTrue(all(g['minimumFiveInEachSourceVictoryGroup'] for g in
                            response['gates']['trainingByParty'].values()))
        for family in ('complete_party_vector', 'stage11_matched_split'):
            self.assertTrue(folds[family, 2011, 'expanding_window']['preprocessing']['parameterFree'])
        cancelled = 'nz-general-2023-electorate-39'
        self.assertNotIn(cancelled, folds['complete_share_baseline_s', 2023,
                                         'expanding_window']['evaluationIds'])

    def test_fold_applicability_ignores_added_target_outcomes_and_identity(self):
        geography = design.read(design.GEOGRAPHY)['records']
        availability = design.read(design.AVAILABILITY)['records']
        baseline = design.fold_plans(geography, availability, self.plan['stableExactSeatChains'])
        for row in availability:
            row['targetWinner'] = 'changed'
            row['targetCandidateVotes'] = -1
            row['identityEvidence'] = {'confidence': 'changed'}
            row['modelError'] = 999
        self.assertEqual(design.fold_plans(geography, availability,
                                          self.plan['stableExactSeatChains']), baseline)

    def test_actual_adapter_rejects_holdout_outcome_influence(self):
        elections = {year: copy.deepcopy(design.read(path))
                     for year, path in design.ELECTIONS.items()}
        for year, document in elections.items():
            if year < 2014:
                continue
            for seat in document['electorates']:
                seat['winnerCandidateId'] = None
                seat['validCandidateVotes'] = 99999
                for candidate in seat['candidates']:
                    candidate['votes'] = 0
                    candidate['elected'] = not candidate['elected']
        updated = availability.build(elections=elections)['records']
        changed = design.fold_plans(design.read(design.GEOGRAPHY)['records'], updated,
                                    self.plan['stableExactSeatChains'])
        self.assertEqual([f for f in changed if f['targetYear'] == 2014],
                         [f for f in self.plan['folds'] if f['targetYear'] == 2014])

    def test_original_geography_and_evidence_bytes_are_preserved(self):
        original = design.read(design.ORIGINAL_DESIGN)
        for path, expected in original['preservedArtifacts'].items():
            self.assertEqual(design.sha256((design.ROOT / path).read_bytes()).hexdigest(), expected)

    def test_stable_chains_are_geographic_and_not_name_only(self):
        chains = self.plan['stableExactSeatChains']
        self.assertEqual(len(chains), 10)
        geography = {(r['targetYear'], r['targetElectorateId']): r
                     for r in design.read(design.GEOGRAPHY)['records']}
        for chain in chains:
            for i, target_id in enumerate(chain['targetElectorateIds']):
                row = geography[chain['targetYears'][i], target_id]
                self.assertTrue(row['certifiedTwoSidedExact'])
                if i:
                    self.assertEqual(row['dominantPredecessorId'], chain['targetElectorateIds'][i-1])

    def test_excluded_composition_uses_only_source_year_descriptors(self):
        source = {year: design.read(path) for year, path in design.ELECTIONS.items()}
        baseline = design.source_composition(design.read(design.GEOGRAPHY)['records'], source)
        for year in (2014, 2020):
            for seat in source[year]['electorates']:
                seat['winnerCandidateId'] = None
                for candidate in seat['candidates']:
                    candidate['votes'] = 0
                    candidate['elected'] = not candidate['elected']
        changed = design.source_composition(design.read(design.GEOGRAPHY)['records'], source)
        self.assertEqual(baseline, changed)
        self.assertEqual([(r['targetYear'], r['group'], r['targetCount']) for r in baseline],
                         [(2014, 'strict_exact', 20), (2014, 'excluded', 44),
                          (2020, 'strict_exact', 34), (2020, 'excluded', 31)])

    def test_register_has_distinct_outcome_contracts(self):
        rows = {r['experimentId']: r for r in self.register['records']}
        self.assertEqual(len(rows), 6)
        self.assertNotEqual(rows['stage11_matched_split']['outcomeAndDenominator'],
                            rows['complete_share_baseline_s']['outcomeAndDenominator'])
        self.assertTrue(all(len(r['foldPlans']) == 10 for r in rows.values()))
        self.assertTrue(all((design.ROOT / r['existingSpecification']).is_file() for r in rows.values()))


if __name__ == '__main__':
    unittest.main()
