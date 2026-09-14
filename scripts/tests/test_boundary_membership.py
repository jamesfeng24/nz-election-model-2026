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
