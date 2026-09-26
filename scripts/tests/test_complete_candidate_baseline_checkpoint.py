"""Synthetic accounting and preserved-input inventory contracts; no history scored."""

import copy
import unittest

from scripts.checkpoints import complete_candidate_baseline as checkpoint


class CompleteCandidateBaselineCheckpointTests(unittest.TestCase):
    def test_fixed_inventory_and_determinism(self):
        result, manifest = checkpoint.build()
        self.assertEqual(result['summary']['frameContests'], 213)
        self.assertEqual(result['summary']['conditionalObservedInputEligible'], 191)
        self.assertEqual(result['summary']['strictPreElectionInputReady'], 0)
        self.assertEqual(sum(len(row['targetOccurrenceIds']) for row in result['records']
                             if row['contestStatus'] == 'held_both'), 1392)
        self.assertEqual(sum(row['sourceSupportingMaoriMatrixId'] is not None
                             for row in result['records']), 1)
        for name, value in [('input-inventory.json', result), ('manifest.json', manifest)]:
            self.assertEqual((checkpoint.ROOT / checkpoint.BASE / name).read_bytes(),
                             checkpoint.encode(value))

    def test_outcome_fields_do_not_enter_inventory(self):
        frame = checkpoint.read(checkpoint.COHORT)['frame']
        elections = {year: checkpoint.read(f'data/processed/elections/{year}.json')
                     for year in checkpoint.YEARS}
        splits = {year: checkpoint.read(f'data/processed/split-votes/{year}.json')
                  for year in checkpoint.YEARS}
        expected = checkpoint.inventory(frame, elections, splits)
        changed = copy.deepcopy(elections)
        for data in changed.values():
            for seat in data['electorates']:
                seat['winnerCandidateId'] = None
                for candidate in seat['candidates']:
                    candidate['elected'] = not candidate['elected']
                    candidate['votes'] = -1
        self.assertEqual(expected, checkpoint.inventory(frame, changed, splits))
        changed_split = copy.deepcopy(splits)
        changed_split[2011]['matrices'][0]['rows'][0]['cells'][0]['reportedPercent'] = -1
        self.assertEqual(expected, checkpoint.inventory(frame, elections, changed_split))

    def test_ambiguous_input_ids_fail(self):
        frame = checkpoint.read(checkpoint.COHORT)['frame']
        elections = {year: checkpoint.read(f'data/processed/elections/{year}.json')
                     for year in checkpoint.TARGET_YEARS}
        splits = {year: checkpoint.read(f'data/processed/split-votes/{year}.json')
                  for year in checkpoint.SOURCE_YEARS}
        changed = copy.deepcopy(splits)
        changed[2008]['matrices'].append(changed[2008]['matrices'][0])
        with self.assertRaises(ValueError):
            checkpoint.inventory(frame, elections, changed)

    def test_conservation_and_missing_route_bounds(self):
        destinations = ['candidate_a', 'candidate_b', 'informal', 'party_only']
        groups = {
            'party_a': {'mass': 100, 'routes': {
                'candidate_a': [0.6, 0.6], 'candidate_b': [0.2, 0.4],
                'informal': [0, 0.2], 'party_only': [0, 0]}},
            'unmatched_party': {'mass': 10, 'routes': {name: [0, 1] for name in destinations}},
        }
        result = checkpoint.contest_bounds(groups, destinations, ['candidate_a', 'candidate_b'])
        self.assertEqual(result['ballotMass'], 110)
        self.assertEqual(result['destinationVoteBounds']['candidate_a'], [60, 70])
        self.assertEqual(result['validCandidateDenominatorBounds'], [80, 110])
        self.assertFalse(result['pointCandidateVotesAvailable'])
        self.assertLessEqual(sum(bounds[0] for bounds in result['destinationVoteBounds'].values()), 110)
        self.assertGreaterEqual(sum(bounds[1] for bounds in result['destinationVoteBounds'].values()), 110)

    def test_absent_destination_is_not_renormalized(self):
        destinations = ['new_candidate', 'informal', 'party_only']
        unknown = {'departed_party': {'mass': 9,
                   'routes': {name: [0, 1] for name in destinations}}}
        result = checkpoint.contest_bounds(unknown, destinations, ['new_candidate'])
        self.assertEqual(result['destinationVoteBounds']['new_candidate'], [0, 9])
        self.assertEqual(result['validCandidateDenominatorBounds'], [0, 9])
        self.assertFalse(result['pointCandidateVotesAvailable'])

    def test_ballot_denominator_is_not_party_mass(self):
        destinations = ['candidate_a', 'informal', 'party_only']
        result = checkpoint.contest_bounds({
            'valid_party': {'mass': 30, 'routes': {
                'candidate_a': [1, 1], 'informal': [0, 0], 'party_only': [0, 0]}},
            'informal_party': {'mass': 5, 'routes': {
                'candidate_a': [0, 0], 'informal': [0, 0], 'party_only': [1, 1]}},
        }, destinations, ['candidate_a'])
        self.assertEqual(result['ballotMass'], 35)
        self.assertEqual(result['validCandidateDenominatorBounds'], [30, 30])
        self.assertTrue(result['pointCandidateVotesAvailable'])

    def test_invalid_or_hidden_mass_rejected(self):
        destinations = ['candidate_a', 'party_only']
        with self.assertRaises(ValueError):
            checkpoint.contest_bounds({'x': {'mass': 10, 'routes': {'candidate_a': [1, 1]}}},
                                      destinations, ['candidate_a'])
        with self.assertRaises(ValueError):
            checkpoint.contest_bounds({'x': {'mass': 10, 'routes': {
                'candidate_a': [0.8, 1], 'party_only': [0.8, 1]}}},
                                      destinations, ['candidate_a'])
        with self.assertRaises(ValueError):
            checkpoint.contest_bounds({'x': {'mass': float('nan'), 'routes': {
                'candidate_a': [1, 1], 'party_only': [0, 0]}}},
                                      destinations, ['candidate_a'])


if __name__ == '__main__':
    unittest.main()
