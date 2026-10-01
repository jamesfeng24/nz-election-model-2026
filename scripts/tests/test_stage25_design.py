"""Stage25 unfitted fold planning and source-composition contracts."""
import copy
import unittest

from scripts.checkpoints import stage25_design as design


class Stage25DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.composition, cls.register = design.build()

    def test_all_models_and_transitions_have_unique_plans(self):
        folds = self.plan['folds']
        self.assertEqual(len(folds), 30)
        self.assertEqual(len({f['foldId'] for f in folds}), 30)
        for fold in folds:
            self.assertEqual(len(fold['trainingIds']), len(set(fold['trainingIds'])))
            self.assertEqual(len(fold['evaluationIds']), len(set(fold['evaluationIds'])))
            self.assertFalse(set(fold['trainingIds']) & set(fold['evaluationIds']))
            self.assertTrue(all(y < fold['sourceYear'] for y in fold['trainingTransitionTargetYears']))
            self.assertEqual(set(fold['trainingIds']),
                             set(fold['originalTrainingIds']) | set(fold['addedTrainingIds']))
            self.assertEqual(set(fold['evaluationIds']),
                             set(fold['originalEvaluationIds']) | set(fold['addedEvaluationIds']))

    def test_first_two_candidate_folds_have_no_fitted_training(self):
        folds = {f['targetYear']: f for f in self.plan['folds']
                 if f['family'] == 'complete_share_baseline_s'}
        self.assertEqual((len(folds[2011]['trainingIds']), len(folds[2014]['trainingIds'])), (0, 0))
        self.assertFalse(folds[2014]['gates']['minimumTrainingContests'])
        self.assertEqual((len(folds[2020]['trainingIds']), len(folds[2020]['evaluationIds'])), (83, 34))
        self.assertEqual((len(folds[2023]['originalTrainingIds']),
                          len(folds[2023]['addedTrainingIds'])), (127, 20))
        self.assertEqual(folds[2020]['savedFixedFitTransport']['savedHoldoutYear'], 2017)
        self.assertEqual(folds[2020]['gates']['structuralWithinSlateRank'], 1)

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
        self.assertTrue(all(len(r['foldPlans']) == 5 for r in rows.values()))
        self.assertTrue(all((design.ROOT / r['existingSpecification']).is_file() for r in rows.values()))


if __name__ == '__main__':
    unittest.main()
