"""Focused checks for the outcome-blind evidence-repair cohort frame."""

from copy import deepcopy
import json
import unittest

from scripts.checkpoints.identity_cohort import (
    OCCURRENCES, READINESS, ROOT, build_inventory,
)


class IdentityCohortCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / OCCURRENCES).read_text())['records']
        cls.readiness = json.loads((ROOT / READINESS).read_text())

    def inventory(self, rows=None, readiness=None):
        return build_inventory(rows or self.rows, readiness or self.readiness, {})

    def test_frame_and_bounded_sample_cover_entire_seat_clusters(self):
        inventory = self.inventory()
        self.assertEqual(len(inventory['frame']), 213)
        self.assertEqual(inventory['selectionRule']['outcomeFieldsUsed'], [])
        chosen = [row for row in inventory['frame'] if row['selected']]
        self.assertEqual(len(chosen), 30)
        self.assertEqual(sum(len(row['sourceOccurrenceIds']) + len(row['targetOccurrenceIds'])
                             for row in chosen), 415)
        self.assertEqual(sum(row['selectedOccurrences'] for row in inventory['summary']), 415)
        self.assertFalse({'winner', 'residual', 'personId', 'elected'} & set(chosen[0]))

    def test_winner_and_residual_changes_cannot_select_cases(self):
        baseline = self.inventory()
        changed = deepcopy(self.rows)
        for row in changed:
            row['elected'] = True
            row['sourcePublishedCandidateVotes'] = -1
            row['normalizedPremium'] = 999
            row['personId'] = 'untrusted-later-profile'
        self.assertEqual(baseline, self.inventory(changed))

    def test_seat_name_alone_cannot_override_boundary_contract(self):
        readiness = deepcopy(self.readiness)
        readiness['comparisons'][0]['status'] = 'unvalidated'
        with self.assertRaisesRegex(ValueError, 'Unvalidated geography'):
            self.inventory(readiness=readiness)
        changed = deepcopy(self.rows)
        changed[0]['boundaryRegime'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'Seat regime'):
            self.inventory(changed)

    def test_duplicate_occurrence_and_non_alias_code_conflict_fail(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate candidate occurrence'):
            self.inventory(self.rows + [self.rows[0]])
        changed = deepcopy(self.rows)
        target = next(row for row in changed if row['year'] == 2011 and
                      row['electorateType'] == 'general' and
                      row['sourceElectorateNumber'] == 1)
        target['electorateName'] = 'Another electorate'
        with self.assertRaisesRegex(ValueError, 'Ambiguous election-local seat label|Seat code/name conflict'):
            self.inventory(changed)


if __name__ == '__main__':
    unittest.main()
