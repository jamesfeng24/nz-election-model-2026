"""Synthetic accounting and preserved-evidence tests for the Stage 21 overlay."""

import copy
import unittest

from scripts.checkpoints import stage21_alliance_mapping as audit


class AllianceMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elections = {year: audit.read(f'data/processed/elections/{year}.json')
                         for year in (2014, 2023)}
        cls.splits = {year: audit.read(f'data/processed/split-votes/{year}.json')
                      for year in (2014, 2023)}
        cls.old = audit.read('data/processed/models/conditional-candidate-share/inventory.json')

    def test_preserved_counts_and_no_group_misclassification(self):
        overlay, _ = audit.build_overlay(self.elections, self.splits, self.old)
        summary = overlay['summary']
        self.assertEqual(summary['affectedSeatCount'], 53)
        self.assertEqual(summary['old2014AmbiguousTrainingSeats'], 26)
        self.assertEqual(summary['old2023AmbiguousHeldFrameSeats'], 20)
        self.assertEqual(summary['old2023IncorrectNoGroupHeldSeats'], 6)
        self.assertEqual(summary['potentialNew2014TrainingSeatsUnderSingleGroupRoute'], 26)
        self.assertEqual(summary['potentialNew2023FrameSeatsUnderSingleGroupRoute'], 20)
        self.assertEqual(len([r for r in overlay['records'] if not r['held']]), 1)

    def test_shared_group_mass_is_counted_once(self):
        # Synthetic fixture; this is not a historical prediction.
        allocation = audit.allocate_unique_group(.035, ['candidate-a'])
        self.assertEqual(allocation, {'candidate-a': .035})
        self.assertAlmostEqual(sum(allocation.values()), .035)
        for destinations in ([], ['candidate-a', 'candidate-b'],
                             ['candidate-a', 'candidate-a']):
            with self.assertRaises(ValueError):
                audit.allocate_unique_group(.035, destinations)

    def test_no_invented_constituent_allocation_with_two_candidates(self):
        elections = copy.deepcopy(self.elections)
        splits = copy.deepcopy(self.splits)
        old = copy.deepcopy(self.old)
        seat = next(s for s in elections[2023]['electorates']
                    if s['id'] == 'nz-general-2023-electorate-09')
        duplicate = copy.deepcopy(next(c for c in seat['candidates']
                                       if c['partyKey'] == 'visionnewzealand'))
        duplicate['id'] += '-synthetic-second-constituent'
        duplicate['partyKey'] = 'rockthevotenz'
        duplicate['party'] = 'Rock the Vote NZ'
        seat['candidates'].append(duplicate)
        old_seat = next(r for r in old['trainingGeneralContests']
                        if r['year'] == 2023 and r['electorateId'] == seat['id'])
        old_candidate = copy.deepcopy(next(c for c in old_seat['candidates']
                                           if c['sourcePartyKey'] == 'visionnewzealand'))
        old_candidate.update(candidateOccurrenceId=duplicate['id'],
                             sourcePartyKey='rockthevotenz',
                             sourceAffiliation='Rock the Vote NZ')
        old_seat['candidates'].append(old_candidate)
        matrix = next(m for m in splits[2023]['matrices']
                      if m['electorateId'] == seat['id'])
        matrix['rows'][0]['cells'].append(
            {'candidateId': duplicate['id'], 'category': 'candidate',
             'candidateLabel': 'SYNTHETIC SECOND CONSTITUENT',
             'reportedPercent': 0.0, 'count': None})
        overlay, _ = audit.build_overlay(elections, splits, old)
        synthetic = next(r for r in overlay['records'] if r['year'] == 2023
                         and r['electorateId'] == seat['id'])
        self.assertEqual(synthetic['status'],
                         'shared_group_multiple_destinations_unresolved')
        with self.assertRaises(ValueError):
            audit.allocate_unique_group(.035,
                                        [c['candidateOccurrenceId']
                                         for c in synthetic['candidates']])

    def test_missing_or_duplicate_group_rejected(self):
        for operation in ('remove', 'duplicate'):
            elections = copy.deepcopy(self.elections)
            seat = next(s for s in elections[2023]['electorates']
                        if s['id'] == 'nz-general-2023-electorate-09')
            group = next(p for p in seat['parties'] if p['partyKey'] == 'freedomsnz')
            if operation == 'remove':
                seat['parties'].remove(group)
            else:
                seat['parties'].append(copy.deepcopy(group))
            with self.assertRaisesRegex(ValueError, 'Missing or duplicate'):
                audit.build_overlay(elections, self.splits, self.old)

    def test_reject_conflicting_local_split_row(self):
        splits = copy.deepcopy(self.splits)
        matrix = next(m for m in splits[2014]['matrices']
                      if m['electorateId'] == 'nz-general-2014-electorate-01')
        row = next(r for r in matrix['rows'] if r['partyLabel'] == 'Internet MANA')
        row['totalPartyVotes'] += 1
        with self.assertRaisesRegex(ValueError, 'does not reconcile'):
            audit.build_overlay(self.elections, splits, self.old)

    def test_invariant_to_candidate_outcomes_and_identity(self):
        changed = copy.deepcopy(self.elections)
        for year in changed:
            for seat in changed[year]['electorates']:
                for candidate in seat['candidates']:
                    candidate['votes'] = 0
                    candidate['winner'] = not candidate.get('winner', False)
                    candidate['personId'] = 'synthetic-identity-label'
        baseline, _ = audit.build_overlay(self.elections, self.splits, self.old)
        counterfactual, _ = audit.build_overlay(changed, self.splits, self.old)
        self.assertEqual(baseline, counterfactual)

    def test_raw_and_registry_snapshot(self):
        outputs = audit.build()
        snapshot = outputs['source-contract.json']
        self.assertTrue(len(snapshot['sources']) >= 50)
        self.assertEqual(len({r['id'] for r in snapshot['sources']}),
                         len(snapshot['sources']))
        self.assertEqual(outputs['overlay.json']['summary']['affectedSeatCount'], 53)


if __name__ == '__main__':
    unittest.main()
