"""Synthetic failure tests for conservative official membership joins."""
import unittest
from scripts.boundaries.membership import index_rows, join_memberships


class MembershipTests(unittest.TestCase):
    def setUp(self):
        self.pop = {'1234567': {'GED2025_V1_00': '002', 'GED2025_V1_00_NAME': 'Target',
                               'MED2025_V1_00': '2', 'MED2025_V1_00_NAME': 'Māori target'}}
        self.source = {'1234567': {'GED2020_code': '001', 'GED2020_name': 'Source',
                                  'MED2020_code': '1', 'MED2020_name': 'Māori source'}}
        self.controls = {'general': {'001': 'Source'}, 'maori': {'1': 'Māori source'}}

    def test_exact_source_labels_and_unavailable_membership(self):
        row = join_memberships(self.pop, self.source, self.controls)[0]
        self.assertEqual(row['memberships']['maori']['sourceName'], 'Māori source')
        missing = join_memberships(self.pop, {}, self.controls)[0]
        self.assertEqual(missing['membershipStatus'], 'unresolved')
        self.assertIsNone(missing['memberships']['general']['sourceCode'])

    def test_duplicate_and_wrong_official_identity_fail(self):
        with self.assertRaises(ValueError):
            index_rows([{'id': '1'}, {'id': '1'}], 'id')
        self.source['1234567']['GED2020_name'] = 'Wrong'
        with self.assertRaises(ValueError):
            join_memberships(self.pop, self.source, self.controls)

    def test_similar_identifier_is_not_a_join(self):
        source = {'1234568': self.source['1234567']}
        self.assertEqual(join_memberships(self.pop, source, self.controls)[0]['membershipStatus'],
                         'unresolved')

    def test_lineage_requires_existing_predecessor_and_same_target(self):
        source = {'7654321': self.source['1234567']}
        link = {'1234567': {'MB2025_code': '7654321', 'GED2025_code': '002',
                            'GED2025_name': 'Target', 'MED2025_code': '2',
                            'MED2025_name': 'Māori target'}}
        row = join_memberships(self.pop, source, self.controls, link)[0]
        self.assertEqual(row['membershipStatus'], 'official_historical_code')
        self.assertEqual(row['sourceConcordanceMeshblockId'], '7654321')
        link['1234567']['GED2025_code'] = '099'
        with self.assertRaises(ValueError):
            join_memberships(self.pop, source, self.controls, link)

    def test_real_source_join_is_complete_and_deterministic(self):
        from scripts.boundaries.audit_membership import build, OUTPUT
        import json
        result = build()
        self.assertEqual(result['exactOfficialMembershipCount'], 57517)
        self.assertEqual(result['officialLineageMembershipCount'], 36)
        self.assertEqual(result['unresolvedMeshblocks'], [])
        self.assertEqual(result['status'], 'membership_complete')
        self.assertEqual((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode(),
                         OUTPUT.read_bytes())
