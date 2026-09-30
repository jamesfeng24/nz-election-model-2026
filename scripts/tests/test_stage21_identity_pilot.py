"""Stage21 fixed relationship pilot selection and acquisition safeguards."""

from copy import deepcopy
import unittest

from scripts.checkpoints import stage21_identity_pilot as pilot
from scripts.checkpoints import stage21_identity_preserved as preserved


class IdentityPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = [pilot.read(path) for path in pilot.INPUTS]

    def test_complete_certified_frame_and_fixed_selection(self):
        output = pilot.build(*self.inputs)
        ledger = output['claim-ledger.json']
        self.assertEqual(ledger['summary']['allClaimCases'], 888)
        self.assertEqual(ledger['summary']['selected'], 24)
        self.assertEqual(ledger['summary']['byTransition'],
                         {'2008-2011': 297, '2014-2017': 303, '2020-2023': 288})
        self.assertEqual(ledger['summary']['selectedByType'],
                         {'different_label_general': 6, 'different_label_maori': 3,
                          'exact_same_label_general': 9, 'name_variant_general': 6})
        self.assertEqual(len(set(ledger['selectedCaseIdsInFixedSearchOrder'])), 24)
        self.assertEqual(sum(r['selectedForPilot'] for r in ledger['cases']), 24)
        self.assertTrue(all(r['sourceOfficialIds'] and r['targetOfficialIds']
                            for r in ledger['cases']))

    def test_outcomes_residuals_and_inherited_confidence_do_not_select_cases(self):
        original = pilot.build(*self.inputs)['claim-ledger.json']['selectedCaseIdsInFixedSearchOrder']
        changed = deepcopy(self.inputs)
        for record in changed[3]['records']:
            record['sourceWasElected'] = not record.get('sourceWasElected')
            record['priorResidual'] = 999
            record['targetResidual'] = -999
            record['sourceIdentityStatus'] = 'synthetic_mutation'
            record['targetIdentityStatus'] = 'synthetic_mutation'
            record['sourcePersonId'] = 'synthetic_mutation'
            record['targetPersonId'] = 'synthetic_mutation'
        for record in changed[1]['records']:
            record['personId'] = 'synthetic_mutation'
            record['normalizedPremium'] = 999
        revised = pilot.build(*changed)['claim-ledger.json']['selectedCaseIdsInFixedSearchOrder']
        self.assertEqual(original, revised)

    def test_name_categories_are_questions_not_identity_answers(self):
        self.assertEqual(pilot.ambiguity('SMITH, Jane', 'SMITH, Jane', 'general'),
                         'exact_same_label_general')
        self.assertEqual(pilot.ambiguity('SMITH, Jane A', 'SMITH, Jane', 'general'),
                         'name_variant_general')
        self.assertEqual(pilot.ambiguity('SMITH, Jane', 'JONES, Jane', 'maori'),
                         'different_label_maori')
        row = next(r for r in pilot.build(*self.inputs)['claim-ledger.json']['cases']
                   if r['ambiguityType'] == 'exact_same_label_general')
        self.assertIn('unresolved', row['relationshipClaim'])

    def test_duplicate_and_ambiguous_candidatures_fail(self):
        duplicate = deepcopy(self.inputs)
        duplicate[1]['records'].append(deepcopy(duplicate[1]['records'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate candidate occurrence'):
            pilot.build(*duplicate)
        ambiguous = deepcopy(self.inputs)
        first_case = pilot.build(*self.inputs)['claim-ledger.json']['cases'][0]
        seat = next(r for r in ambiguous[0]['records'] if
                    r['sourceElectorateId'] == first_case['sourceElectorateId'])
        seat['sourceOccurrenceIds'].append(first_case['sourceOccurrenceId'])
        with self.assertRaisesRegex(ValueError, 'Ambiguous same-party'):
            pilot.build(*ambiguous)

    def test_presearch_budget_and_zero_attempt_ledger(self):
        output = pilot.build(*self.inputs)
        plan = output['acquisition-plan.json']
        searches = output['search-ledger.json']
        self.assertEqual(plan['searchProcedure']['collectionQueriesMaximum'], 8)
        self.assertEqual(plan['searchProcedure']['targetedQueriesPerSelectedCaseMaximum'], 2)
        self.assertEqual(plan['searchProcedure']['newUniqueResourceMaximum'], 30)
        self.assertEqual(searches['collectionQueries'], [])
        self.assertEqual(searches['newResourceIds'], [])
        self.assertEqual(len(searches['caseQueries']), 24)
        self.assertTrue(all(not entries for entries in searches['caseQueries'].values()))

    def test_preserved_profiles_do_not_promote_pair_relationships(self):
        review = preserved.build()['preserved-review.json']
        self.assertEqual(review['reviewedCases'], 24)
        self.assertEqual(len(review['records']), 24)
        self.assertTrue(any(r['preservedProfileIds'] for r in review['records']))
        self.assertTrue(all(r['relationshipFinding'] ==
                            'unresolved_explicit_cross_occurrence_bridge'
                            for r in review['records']))


if __name__ == '__main__':
    unittest.main()
