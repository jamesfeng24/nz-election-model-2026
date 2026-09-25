"""Search order and acquired-resource integrity checks."""

from copy import deepcopy
import json
import unittest

from scripts.checkpoints import acquired_sources, search_identity
from scripts.checkpoints.identity_evidence_pass import LEDGER, PRESERVED, ROOT
from scripts.checkpoints.profile_supplement import OUTPUT as PROFILE_SUPPLEMENT


class Stage13SourcesAndSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial = json.loads((ROOT / LEDGER).read_text())
        cls.audit = json.loads((ROOT / PRESERVED).read_text())
        cls.supplement = json.loads((ROOT / PROFILE_SUPPLEMENT).read_text())
        cls.plan = json.loads((ROOT / acquired_sources.PLAN).read_text())
        cls.older = [json.loads((ROOT / path).read_text()) for path in acquired_sources.OLDER_PLANS]

    def test_fixed_search_request_ignores_outcome_and_inherited_confidence(self):
        expected = search_identity.batch_requests(self.audit, self.initial, self.supplement, 15, 2)
        changed = deepcopy(self.audit)
        for row in changed['records']:
            row['winner'] = True
            row['residual'] = 999
            row['reassessedOccurrenceConfidence'] = 'probable'
        actual = search_identity.batch_requests(changed, self.initial, self.supplement, 15, 2)
        self.assertEqual([row['candidateOccurrenceId'] for row in actual],
                         [row['candidateOccurrenceId'] for row in expected])
        self.assertEqual([row['queries'] for row in actual], [row['queries'] for row in expected])

    def test_search_batch_replay_rejects_skip_and_third_search(self):
        record = self.initial['records'][0]
        sample = {'startOrder': 1, 'records': [{**record, 'state': 'searched',
                                               'searchAttempts': []}]}
        self.assertEqual(search_identity.merge_batches(self.initial, [sample])['nextOrder'], 2)
        sample['startOrder'] = 2
        with self.assertRaisesRegex(ValueError, 'skipped'):
            search_identity.merge_batches(self.initial, [sample])
        sample['startOrder'] = 1
        sample['records'][0]['searchAttempts'] = [{'number': i, 'query': 'q',
                                                   'searchedAt': '2026-09-25T00:00:00Z'}
                                                  for i in range(1, 4)]
        with self.assertRaisesRegex(ValueError, 'two searches'):
            search_identity.merge_batches(self.initial, [sample])

    def test_new_source_duplicate_and_bytes_rejected(self):
        read = lambda path: (ROOT / path).read_bytes()
        self.assertEqual(acquired_sources.validate_sources(self.plan, self.older, read),
                         len(self.plan['sources']))
        duplicate = deepcopy(self.plan)
        duplicate['sources'].append(deepcopy(duplicate['sources'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            acquired_sources.validate_sources(duplicate, self.older, read)
        with self.assertRaisesRegex(ValueError, 'Changed Stage 13 raw bytes'):
            acquired_sources.validate_sources(self.plan, self.older, lambda path: b'changed')
        unsafe = deepcopy(self.plan)
        unsafe['sources'][0]['rawPath'] = 'data/raw/identity-stage13/../other'
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            acquired_sources.validate_sources(unsafe, self.older, read)


if __name__ == '__main__':
    unittest.main()
