"""Pre-acquisition identity-cohort and source-contract regression checks."""

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from scripts.checkpoints import identity_evidence_pass as evidence


class IdentityEvidencePassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cohort, _ = evidence._read(evidence.COHORT)
        cls.occurrences, _ = evidence._read(evidence.OCCURRENCES)
        cls.stage8, _ = evidence._read(evidence.STAGE8)
        cls.stage9, _ = evidence._read(evidence.STAGE9)
        cls.stage10, _ = evidence._read(evidence.STAGE10)
        cls.registry, _ = evidence._read(evidence.REGISTRY)

    def audit(self, occurrences=None, stage8=None):
        return evidence.build_preserved_audit(
            self.cohort, occurrences or self.occurrences, stage8 or self.stage8,
            self.stage9, self.stage10, {})[0]

    def test_order_is_fixed_without_outcomes_or_inherited_labels(self):
        expected = evidence.ordered_occurrences(self.cohort)
        encoded = ('\n'.join(expected) + '\n').encode()
        self.assertEqual(sha256(encoded).hexdigest(),
                         '62deeebe5abe4f99c62805a6a297c57c34ff8e7cf1d90ec95f8c2036e30773b8')
        changed = deepcopy(self.occurrences)
        for row in changed['records']:
            row['elected'] = True
            row['normalizedPremium'] = -999
        changed_links = deepcopy(self.stage8)
        for link in changed_links['links']:
            link['inheritedConfidenceForSelection'] = 'unresolved'
        audit = self.audit(changed, changed_links)
        self.assertEqual([row['candidateOccurrenceId'] for row in audit['records']], expected)

    def test_duplicate_and_conflicting_direct_evidence(self):
        with self.assertRaisesRegex(ValueError, '415 distinct'):
            cohort = deepcopy(self.cohort)
            selected = next(row for row in cohort['frame'] if row['selected'])
            selected['sourceOccurrenceIds'][0] = selected['sourceOccurrenceIds'][1]
            evidence.ordered_occurrences(cohort)
        route = {'confidence': 'confirmed', 'personId': 'one'}
        other = {'confidence': 'confirmed', 'personId': 'two'}
        self.assertEqual(evidence._reassess(route, other),
                         ('unresolved', None, 'conflicting_confirmed_person_ids'))

    def test_winner_anchor_confirms_only_its_own_occurrence(self):
        link = next(row for row in self.stage8['links'] if row['status'] == 'confirmed')
        own = evidence._stage8_route(link, link['candidateOccurrenceId'])
        self.assertEqual(own['confidence'], 'confirmed')
        projected = deepcopy(link)
        projected['status'] = 'probable'
        self.assertEqual(evidence._stage8_route(projected, 'another-occurrence')['confidence'],
                         'probable')
        with self.assertRaisesRegex(ValueError, 'Unsupported inherited confirmed'):
            evidence._stage8_route(link, 'another-occurrence')

    def test_fact_publication_and_retrieval_dates_are_separate(self):
        row = next(row for row in self.stage10['links'] if row['publicationDate'])
        route = evidence._stage10_route(row)
        self.assertEqual(route['factDate'], row['historicalFactDate'])
        self.assertEqual(route['publicationDate'], row['publicationDate'])
        self.assertEqual(route['retrievedAt'], row['retrievalAt'])
        self.assertNotEqual(route['retrievedAt'], route['factDate'])

    def test_required_source_record_and_raw_bytes_are_pinned(self):
        audit, source_ids = evidence.build_preserved_audit(
            self.cohort, self.occurrences, self.stage8, self.stage9, self.stage10, {})
        snapshot = evidence.build_snapshot(source_ids, self.registry)
        evidence.verify_snapshot(snapshot, self.registry)
        self.assertEqual(len(audit['records']), 415)
        changed_registry = deepcopy(self.registry)
        required_id = snapshot['requiredSourceRecords'][0]['id']
        changed_registry['sources'] = [row for row in changed_registry['sources'] if row['id'] != required_id]
        with self.assertRaisesRegex(ValueError, 'Changed or removed'):
            evidence.verify_snapshot(snapshot, changed_registry)
        changed_snapshot = deepcopy(snapshot)
        changed_snapshot['requiredSourceRecords'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed or removed|Changed required raw'):
            evidence.verify_snapshot(changed_snapshot, self.registry)
        plans = [evidence._read(path)[0] for path in evidence.IDENTITY_PLANS]
        identity_snapshot = evidence.build_identity_snapshot(audit, plans)
        evidence.verify_identity_snapshot(identity_snapshot, plans)
        changed_identity = deepcopy(identity_snapshot)
        changed_identity['requiredSourceRecords'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed or missing'):
            evidence.verify_identity_snapshot(changed_identity, plans)


if __name__ == '__main__':
    unittest.main()
