"""Canonical Stage25 geography: certification, bounds and provenance."""
import copy
from fractions import Fraction
import unittest
from unittest.mock import patch

from scripts.checkpoints import stage25_geography as geo


class Stage25GeographyTests(unittest.TestCase):
    def test_all_targets_and_originals_are_unique(self):
        output, manifest = geo.build()
        self.assertEqual(len(output['records']), 356)
        self.assertEqual(len({r['geographyId'] for r in output['records']}), 356)
        self.assertEqual(manifest['outputSha256'], geo.digest(
            'data/processed/checkpoints/stage25-historical-geography/geography.json'))

    def test_reported_identity_is_not_two_sided_identity(self):
        rows = geo.build()[0]['records']
        a = [r for r in rows if r['targetYear'] == 2014 and r['scope'] == 'general']
        b = [r for r in rows if r['targetYear'] == 2020 and r['scope'] == 'general']
        self.assertEqual((sum(r['reportedIncomingMembershipIdentity'] for r in a),
                          sum(r['certifiedTwoSidedExact'] for r in a)), (29, 20))
        self.assertEqual((sum(r['reportedIncomingMembershipIdentity'] for r in b),
                          sum(r['certifiedTwoSidedExact'] for r in b)), (34, 34))
        one_sided = [r for r in a if r['reportedIncomingMembershipIdentity']
                     and not r['certifiedTwoSidedExact']]
        self.assertEqual(len(one_sided), 9)
        self.assertTrue(all('incoming_identity_but_predecessor_has_other_successor'
                            in r['unresolvedReasons'] for r in one_sided))
        self.assertTrue(all(geo.fraction(r['dominantTargetInheritanceLower']) == 1 and
                            geo.fraction(r['dominantSourceRetentionLower']) < 1
                            for r in one_sided))

    def test_nested_and_exclusive_overlap_tiers(self):
        summary = {(r['targetYear'], r['scope']): r for r in geo.build()[0]['summary']}
        self.assertEqual((summary[2014, 'general']['targetOverlap95'],
                          summary[2014, 'general']['targetOverlap90']), (39, 45))
        self.assertEqual((summary[2020, 'general']['targetOverlap95'],
                          summary[2020, 'general']['targetOverlap90']), (46, 49))
        self.assertEqual((summary[2014, 'general']['twoSided95'],
                          summary[2014, 'general']['twoSided90']), (28, 37))
        self.assertEqual((summary[2020, 'general']['twoSided95'],
                          summary[2020, 'general']['twoSided90']), (41, 47))
        self.assertEqual(summary[2014, 'general']['exclusiveTiers'], {
            'exact': 20, 'approximate_two_sided_95': 8,
            'approximate_two_sided_90_only': 9, 'not_two_sided_90': 27})
        self.assertEqual(geo.tier(False, Fraction(96, 100), Fraction(89, 100)),
                         'not_two_sided_90')

    def test_multiple_predecessors_and_label_encoding_are_explicit(self):
        rows = geo.build()[0]['records']
        contested = [r for r in rows if r['targetYear'] == 2014 and
                     r['scope'] == 'general' and len(r['predecessors']) > 1]
        self.assertTrue(contested)
        self.assertTrue(all(not r['certifiedTwoSidedExact'] for r in contested))
        for row in contested:
            self.assertEqual(len({p['sourceElectorateId'] for p in row['predecessors']}),
                             len(row['predecessors']))
        labels = [r for r in rows if r.get('targetElectionLocalLabelMatch') is False]
        self.assertEqual([(r['targetYear'], r['targetElectorateId']) for r in labels],
                         [(2014, 'nz-general-2014-electorate-43')])

    def test_winner_and_vote_mutation_cannot_change_geography(self):
        original = geo.build()[0]
        occurrences = copy.deepcopy(geo.read(geo.OCCURRENCES))
        for row in occurrences['records']:
            row['sourcePublishedCandidateVotes'] = 999999
            row['candidateShare'] = .99
            row['normalizedPremium'] = .5
        real = geo.read

        def changed(path):
            return occurrences if path == geo.OCCURRENCES else real(path)

        with patch.object(geo, 'read', side_effect=changed):
            rebuilt = geo.build()[0]
        self.assertEqual(original, rebuilt)

    def test_changed_crosswalk_raw_dependency_rejected(self):
        real = geo.digest

        def changed(path):
            return '0' * 64 if path.endswith('population-2020.csv') else real(path)

        with patch.object(geo, 'digest', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'Changed certified boundary dependency'):
                geo.verify_crosswalk('2017-2020')


if __name__ == '__main__':
    unittest.main()
