"""Focused final pilot adjudication, budgets, and source dependency tests."""

import copy
import unittest
from unittest.mock import patch

from scripts.checkpoints import stage21_identity_final as final


class IdentityFinalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claims = final.read(final.CLAIMS)
        cls.plan = final.read(final.PLAN)
        cls.preserved = final.read(final.PRESERVED)
        cls.searches = final.read(final.SEARCHES)
        cls.winners = final.observed_winners(final.read(final.VOTES)['records'])
        cls.registry = final.read('data/sources.json')
        cls.sources = final.source_contract(cls.registry)

    def adjudicate(self, winners=None, searches=None):
        return final.adjudicate(self.claims, self.plan, self.preserved,
                                searches or self.searches,
                                self.winners if winners is None else winners,
                                self.sources)

    def test_all_selected_relationships_remain_unresolved(self):
        rows = self.adjudicate()
        self.assertEqual(len(rows), 24)
        self.assertEqual({r['relationship'] for r in rows}, {'unresolved'})
        self.assertEqual(sum(len(r['careerClaims']) for r in rows), 2)
        self.assertTrue(all(r['occurrenceLink']['sourceOfficialCandidature']
                            == 'established_election_local_only' for r in rows))

    def test_outcomes_cannot_change_adjudication_or_search_order(self):
        a = self.adjudicate()
        reversed_winners = {key: not value for key, value in self.winners.items()}
        b = self.adjudicate(reversed_winners)
        for left, right in zip(a, b):
            for key in ('sourceWinnerDiagnosticOnly', 'targetWinnerDiagnosticOnly'):
                left.pop(key)
                right.pop(key)
            self.assertEqual(left, right)

    def test_search_budget_and_fixed_coverage(self):
        extra = copy.deepcopy(self.searches)
        first = self.plan['selection']['selectedCaseIds'][0]
        extra['caseQueries'][first].append(copy.deepcopy(extra['caseQueries'][first][-1]))
        with self.assertRaisesRegex(ValueError, 'excessive'):
            self.adjudicate(searches=extra)
        missing = copy.deepcopy(self.searches)
        del missing['caseQueries'][first]
        with self.assertRaisesRegex(ValueError, 'fixed cohort'):
            self.adjudicate(searches=missing)
        claims = copy.deepcopy(self.claims)
        claims['cases'].append(copy.deepcopy(claims['cases'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate claim'):
            final.adjudicate(claims, self.plan, self.preserved, self.searches,
                             self.winners, self.sources)

    def test_maori_winner_diagnostic_matches_official_overlay(self):
        overlay = final.read('data/processed/models/replacement-candidate/maori-winner-overlay.json')
        self.assertEqual(len(overlay['records']), 21)
        self.assertTrue(all(self.winners.get(row['winnerOccurrenceId']) is True
                            for row in overlay['records']))

    def test_unrelated_registry_addition_allowed(self):
        changed = copy.deepcopy(self.registry)
        changed['sources'].append({'id': 'unrelated-stage22'})
        self.assertEqual(final.source_contract(changed), self.sources)

    def test_required_registry_record_and_raw_byte_checks(self):
        deleted = copy.deepcopy(self.registry)
        deleted['sources'] = [s for s in deleted['sources']
                              if s['id'] != final.SOURCE_IDS[0]]
        with self.assertRaisesRegex(ValueError, 'Missing or ambiguous'):
            final.source_contract(deleted)
        duplicate = copy.deepcopy(self.registry)
        duplicate['sources'].append(copy.deepcopy(self.sources[0]))
        with self.assertRaisesRegex(ValueError, 'Missing or ambiguous'):
            final.source_contract(duplicate)
        changed = copy.deepcopy(self.registry)
        next(s for s in changed['sources'] if s['id'] == final.SOURCE_IDS[0])['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed pilot raw source'):
            final.source_contract(changed)
        with patch.object(final, 'digest', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'Changed pilot raw source'):
                final.source_contract(self.registry)
        metadata_change = copy.deepcopy(self.registry)
        next(s for s in metadata_change['sources']
             if s['id'] == final.SOURCE_IDS[0])['organisation'] = 'changed'
        pinned = final.read('data/processed/checkpoints/stage21-identity-pilot/final-source-contract.json')
        self.assertNotEqual(final.source_contract(metadata_change), pinned['sourceRecords'])


if __name__ == '__main__':
    unittest.main()
