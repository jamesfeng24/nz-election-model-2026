"""Stage 21 certified-join correction without historical scoring."""

import json
import unittest
from copy import deepcopy

from scripts.models.historical_split_ticket.correction import (
    certified_pair_for_row, corrected_inventory)
from scripts.models.historical_split_ticket.correction_run import (
    DEST, ROOT, build, encode)
from scripts.models.historical_split_ticket.evidence import YEARS


def read(path):
    return json.loads((ROOT / path).read_bytes())


class Stage11GeographyRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = read('data/processed/models/historical-split-ticket/applicability.json')
        cls.corrected = read(DEST / 'corrected-applicability.json')
        cls.frame = read('data/processed/checkpoints/complete-candidate-baseline/input-inventory.json')
        cls.elections = {year: read(f'data/processed/elections/{year}.json') for year in YEARS}
        cls.splits = {year: read(f'data/processed/split-votes/{year}.json') for year in YEARS}
        cls.continuity = read('data/processed/models/party-vote-transform/party-continuity.json')['records']

    def test_all_eight_certified_label_changes_recover_expected_source_contests(self):
        repaired = self.corrected['correction']['repairedSourceTargetPairs']
        self.assertEqual({row['sourceElectorateId'].rsplit('-', 1)[1]: row['newPartialCandidateCount']
                          for row in repaired},
                         {'20': 5, '22': 4, '35': 4, '36': 6,
                          '42': 3, '48': 4, '50': 3, '52': 4})
        self.assertEqual(sum(row['newPartialCandidateCount'] for row in repaired), 33)
        old = {row['targetOccurrenceId']: row for row in self.original['records']}
        new = {row['targetOccurrenceId']: row for row in self.corrected['records']}
        for repaired_seat in repaired:
            rows = [row for row in new.values() if row.get('sourceElectorateId') ==
                    repaired_seat['sourceElectorateId']]
            self.assertTrue(rows)
            for row in rows:
                source, target = certified_pair_for_row(row, self.elections)
                self.assertNotEqual(source['name'], target['name'])
                self.assertEqual(source['id'], repaired_seat['sourceElectorateId'])
                self.assertEqual(target['id'], repaired_seat['targetElectorateId'])
                self.assertIsNotNone(row['sourceMatrixId'])
                self.assertIn('missing_comparable_source_seat_or_local_matrix',
                              old[row['targetOccurrenceId']]['exclusionReasons'])

    def test_original_common_sample_is_unchanged(self):
        before = {row['targetOccurrenceId']: row for row in self.original['records']
                  if row['conditionalPartialApplicability']}
        after = {row['targetOccurrenceId']: row for row in self.corrected['records']
                 if row['conditionalPartialApplicability']}
        self.assertEqual(len(before), 803)
        self.assertEqual(len(after), 836)
        self.assertTrue(set(before) <= set(after))
        for candidate_id, original in before.items():
            restored = {k: v for k, v in after[candidate_id].items()
                        if k not in ('sourceElectorateId', 'targetElectorateId')}
            self.assertEqual(original, restored)

    def test_rejects_changed_boundary_and_ambiguous_certified_joins(self):
        frame = deepcopy(self.frame)
        frame['records'][0]['sourceYear'] = 2011
        with self.assertRaises(ValueError):
            corrected_inventory(self.original, frame, self.elections,
                                self.splits, self.continuity)
        frame = deepcopy(self.frame)
        frame['records'][1]['targetElectorateId'] = frame['records'][0]['targetElectorateId']
        with self.assertRaises(ValueError):
            corrected_inventory(self.original, frame, self.elections,
                                self.splits, self.continuity)
        row = next(row for row in self.corrected['records']
                   if row['conditionalPartialApplicability'])
        changed = {**row, 'sourceElectorateId': 'invalid-source'}
        with self.assertRaisesRegex(ValueError, 'missing'):
            certified_pair_for_row(changed, self.elections)

    def test_winner_flags_cannot_change_geography_or_applicability(self):
        changed = deepcopy(self.elections)
        for election in changed.values():
            for seat in election['electorates']:
                seat['winnerCandidateId'] = None
                for candidate in seat['candidates']:
                    candidate['elected'] = not candidate['elected']
        rebuilt = corrected_inventory(self.original, self.frame, changed,
                                      self.splits, self.continuity)
        self.assertEqual(rebuilt, self.corrected)

    def test_manifest_reproduces_original_and_corrected_artifacts(self):
        output = build()
        self.assertEqual(len(output['original-artifact-hashes.json']['artifacts']), 12)
        for name, value in output.items():
            self.assertEqual((ROOT / DEST / name).read_bytes(), encode(value))


if __name__ == '__main__':
    unittest.main()
