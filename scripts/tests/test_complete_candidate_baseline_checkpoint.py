"""Synthetic accounting and preserved-input inventory contracts; no history scored."""

import copy
import unittest
from math import isclose

from scripts.checkpoints import complete_candidate_baseline as checkpoint


class CompleteCandidateBaselineCheckpointTests(unittest.TestCase):
    def assert_conserved_witness(self, routes, witness):
        self.assertEqual(set(routes), set(witness))
        self.assertTrue(isclose(sum(witness.values()), 1))
        for destination, value in witness.items():
            self.assertLessEqual(routes[destination][0] - 1e-12, value)
            self.assertLessEqual(value, routes[destination][1] + 1e-12)

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
        destinations = ['candidate_a', 'informal', 'party_only', 'candidate_disallowed']
        result = checkpoint.contest_bounds({
            'valid_party': {'mass': 30, 'routes': {
                'candidate_a': [0.9, 0.9], 'informal': [0, 0],
                'party_only': [0.1, 0.1], 'candidate_disallowed': [0, 0]}},
            'informal_party': {'mass': 5, 'routes': {
                'candidate_a': [1, 1], 'informal': [0, 0],
                'party_only': [0, 0], 'candidate_disallowed': [0, 0]}},
            'party_disallowed': {'mass': 2, 'routes': {
                'candidate_a': [0, 0], 'informal': [0, 0],
                'party_only': [0, 0], 'candidate_disallowed': [1, 1]}},
        }, destinations, ['candidate_a'])
        self.assertEqual(result['ballotMass'], 37)
        self.assertEqual(result['validCandidateDenominatorBounds'], [32, 32])
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

    def test_pool_rounding_is_distinct_from_source_seat_heterogeneity(self):
        pool = checkpoint.synthetic_source_pool([
            {'complete': True, 'mass': 100, 'routes': {'A': [0.795, 0.805],
                                                       'B': [0.195, 0.205]}},
            {'complete': True, 'mass': 300, 'routes': {'A': [0.195, 0.205],
                                                       'B': [0.795, 0.805]}},
        ], ['A', 'B'])
        self.assertEqual(pool['totalMass'], 400)
        self.assertEqual(pool['supportedCategories'], ['A', 'B'])
        for actual, expected in zip(pool['pooledMarginalBounds']['A'], [0.345, 0.355]):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(pool['pooledMarginalBounds']['B'], [0.645, 0.655]):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(pool['heterogeneityMarginalEnvelope']['A'],
                                    [0.195, 0.805]):
            self.assertAlmostEqual(actual, expected)
        self.assert_conserved_witness(pool['sourceRows'][0]['routes'], {'A': 0.8, 'B': 0.2})
        self.assert_conserved_witness(pool['sourceRows'][1]['routes'], {'A': 0.2, 'B': 0.8})
        self.assertAlmostEqual((100 * 0.8 + 300 * 0.2) / 400, 0.35)
        self.assertGreater(sum(bounds[1] for bounds in pool['pooledMarginalBounds'].values()), 1)
        self.assertGreater(sum(bounds[1] for bounds in pool['heterogeneityMarginalEnvelope'].values()), 1)

    def test_absent_source_party_is_structural_zero_with_row_weight(self):
        pool = checkpoint.synthetic_source_pool([
            {'complete': True, 'mass': 100, 'routes': {'A': [0.6, 0.6],
                                                       'B': [0.4, 0.4]}},
            {'complete': True, 'mass': 100, 'routes': {'A': [1, 1]}},
        ], ['A', 'B'])
        self.assertEqual(pool['sourceRows'][1]['routes']['B'], [0, 0])
        self.assertEqual(pool['supportedCategories'], ['A', 'B'])
        self.assertEqual(pool['pooledMarginalBounds']['B'], [0.2, 0.2])
        self.assertEqual(pool['heterogeneityMarginalEnvelope']['B'], [0, 0.4])
        self.assert_conserved_witness({'A': [0.8, 0.8], 'B': [0.2, 0.2]},
                                      {'A': 0.8, 'B': 0.2})
        with self.assertRaises(ValueError):
            checkpoint.synthetic_source_pool([{'complete': True, 'mass': 0,
                                               'routes': {'A': [1, 1]}}], ['A'])
        with self.assertRaises(ValueError):
            checkpoint.synthetic_source_pool([{'mass': 100,
                                               'routes': {'A': [1, 1]}}], ['A', 'B'])
        unsupported = checkpoint.synthetic_source_pool([
            {'complete': True, 'mass': 100, 'routes': {'A': [1, 1]}}], ['A', 'B'])
        self.assertEqual(unsupported['supportedCategories'], ['A'])
        self.assertEqual(unsupported['pooledMarginalBounds']['B'], [0, 0])
        routes = checkpoint.synthetic_point_target_routes(
            {'A': 1, 'B': 0}, unsupported['supportedCategories'],
            {'A': 'candidate_a', 'B': 'candidate_b'},
            ['candidate_a', 'candidate_b', 'party_only'])
        self.assertEqual(routes['candidate_b'], [0, 1])

    def test_absent_target_category_releases_only_its_mass(self):
        routes = checkpoint.synthetic_point_target_routes(
            {'A': 0.7, 'B': 0.3}, {'A', 'B'}, {'A': 'candidate_a'},
            ['candidate_a', 'party_only'])
        self.assertEqual(routes, {'candidate_a': [0.7, 1.0], 'party_only': [0, 0.3]})
        self.assert_conserved_witness(routes, {'candidate_a': 0.7, 'party_only': 0.3})
        self.assert_conserved_witness(routes, {'candidate_a': 1, 'party_only': 0})
        result = checkpoint.contest_bounds({'g': {'mass': 100, 'routes': routes}},
                                           list(routes), ['candidate_a'])
        self.assertEqual(result['ballotMass'], 100)
        self.assertEqual(result['destinationVoteBounds']['candidate_a'], [70, 100])

    def test_entrant_and_independent_have_nonzero_feasible_allocation(self):
        source = {'A': 0.7, 'B': 0.3}
        for category in ('entrant_party', 'independent_candidate'):
            destinations = ['candidate_a', 'candidate_b', 'new_candidate', 'party_only']
            routes = checkpoint.synthetic_point_target_routes(
                source, {'A', 'B'}, {'A': 'candidate_a', 'B': 'candidate_b',
                         category: 'new_candidate'}, destinations)
            self.assertEqual(routes['new_candidate'], [0, 1])
            self.assert_conserved_witness(routes, {
                'candidate_a': 0, 'candidate_b': 0,
                'new_candidate': 1, 'party_only': 0})
            result = checkpoint.contest_bounds({'g': {'mass': 100, 'routes': routes}},
                                               destinations, destinations[:3])
            self.assertEqual(result['destinationVoteBounds']['new_candidate'], [0, 100])
            self.assertEqual(result['ballotMass'], 100)

    def test_personal_identity_labels_do_not_change_party_routing(self):
        source = {'A': 0.7, 'B': 0.3}
        candidates = [{'id': 'candidate_a', 'party': 'A', 'personId': 'source_person'},
                      {'id': 'candidate_b', 'party': 'B', 'personId': None}]
        def routes_for(records):
            return checkpoint.synthetic_point_target_routes(
                source, {'A', 'B'}, {row['party']: row['id'] for row in records},
                ['candidate_a', 'candidate_b', 'party_only'])
        expected = routes_for(candidates)
        changed = copy.deepcopy(candidates)
        changed[0]['personId'] = 'different_person'
        changed[1]['personId'] = 'unknown_person'
        self.assertEqual(routes_for(changed), expected)
        self.assertEqual(expected['candidate_a'], [0.7, 0.7])
        self.assert_conserved_witness(expected, {'candidate_a': 0.7,
                                                 'candidate_b': 0.3,
                                                 'party_only': 0})


if __name__ == '__main__':
    unittest.main()
