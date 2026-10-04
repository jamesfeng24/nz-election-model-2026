"""Synthetic coupled transport contracts, not political evidence."""
import copy
from fractions import Fraction
import unittest
from unittest.mock import patch

from scripts.boundaries.coupled import PopulationSystem
from scripts.transport.party import (build_scope, certify_witness, combined_source_shares,
                                     lexicographic_witness, transport_votes)


def population_fixture():
    # Group A's two destinations share one total; independent marginal choices
    # would not preserve both destination controls and source accounting.
    groups = [{'id': 'A', 'source': 's1', 'targets': ['t1', 't2'], 'lower': 8, 'upper': 10},
              {'id': 'B', 'source': 's2', 'targets': ['t1'], 'lower': 2, 'upper': 4},
              {'id': 'C', 'source': 's2', 'targets': ['t2'], 'lower': 2, 'upper': 4}]
    return PopulationSystem(groups, {'t1': 8, 't2': 8})


def party_fixture():
    return {'s1': {'validVotes': 10, 'parties': [{'partyKey': 'a', 'votes': 10}, {'partyKey': 'b', 'votes': 0}]},
            's2': {'validVotes': 20, 'parties': [{'partyKey': 'a', 'votes': 5}, {'partyKey': 'b', 'votes': 15}]}}


def fraction(value):
    return Fraction(value['numerator'], value['denominator'])


class PartyTransportTests(unittest.TestCase):
    def test_lexicographic_multidestination_group_and_exact_controls(self):
        population = population_fixture()
        witness = lexicographic_witness(population)
        self.assertEqual(witness, [4, 4, 4, 4])
        self.assertEqual(certify_witness(population, witness), {'A': 8, 'B': 4, 'C': 4})
        self.assertEqual(lexicographic_witness(population), witness)

    def test_variable_input_order_does_not_change_lexicographic_choice(self):
        original = population_fixture()
        reordered = PopulationSystem(list(reversed(original.groups)), original.controls)
        first = dict(zip(original.variables, lexicographic_witness(original)))
        second = dict(zip(reordered.variables, lexicographic_witness(reordered)))
        self.assertEqual(first, second)

    def test_source_mass_denominator_and_structural_zero_conservation(self):
        population = population_fixture()
        result = transport_votes(population, lexicographic_witness(population), party_fixture())
        self.assertEqual(result['sourcePartyMass'], {'a': 15, 'b': 15})
        self.assertEqual(result['sourceValidPartyVotes'], 30)
        for target in result['targetPartyVectors']:
            self.assertEqual(fraction(target['validPartyVotesExact']), 15)
            self.assertEqual(sum(fraction(p['shareExact']) for p in target['parties']), 1)
            self.assertEqual({p['partyKey']: fraction(p['votesExact']) for p in target['parties']},
                             {'a': Fraction(15, 2), 'b': Fraction(15, 2)})
        self.assertEqual(sum(fraction(e['weight']) for e in result['aggregatedEdges'] if e['sourceCode'] == 's1'), 1)
        self.assertEqual(result['nationalSourceShares'], {'a': .5, 'b': .5})

    def test_missing_not_zero_and_duplicate_party_rejected(self):
        for change in ('missing', 'duplicate', 'unknown'):
            sources = party_fixture()
            if change == 'missing':
                sources['s1']['parties'].pop()
            elif change == 'duplicate':
                sources['s1']['parties'].append({'partyKey': 'a', 'votes': 0})
            else:
                sources['s1']['parties'][0]['votes'] = None
            with self.subTest(change=change), self.assertRaises(ValueError):
                transport_votes(population_fixture(), [4, 4, 4, 4], sources)

    def test_missing_source_and_corrupt_valid_denominator_rejected(self):
        for change in ('source', 'denominator', 'zero'):
            sources = party_fixture()
            if change == 'source':
                del sources['s2']
            else:
                sources['s1']['validVotes'] = 0 if change == 'zero' else 9
            with self.subTest(change=change), self.assertRaises(ValueError):
                transport_votes(population_fixture(), [4, 4, 4, 4], sources)

    def test_exact_integer_constraints_do_not_accept_incompatible_endpoints(self):
        population = population_fixture()
        for witness in ([4, 6, 4, 4], [4.0, 4, 4, 4], [4, 4, 4, 3]):
            with self.subTest(witness=witness), self.assertRaises(ValueError):
                certify_witness(population, witness)

    def test_infeasible_constraint_abstains(self):
        with self.assertRaisesRegex(ValueError, 'Infeasible'):
            PopulationSystem([{'id': 'x', 'source': 's', 'targets': ['t'], 'lower': 3, 'upper': 4}], {'t': 8})

    def test_failed_and_nonintegral_solver_not_used_as_point(self):
        population = population_fixture()
        class Failed:
            success = False
            message = 'synthetic solver failure'
        with patch('scripts.transport.party.linprog', return_value=Failed()):
            with self.assertRaisesRegex(ValueError, 'Unresolved'):
                lexicographic_witness(population)
        class Fractional:
            success = True
            x = [4.5, 3.5, 3.5, 4.5]
        with patch('scripts.transport.party.linprog', return_value=Fractional()):
            with self.assertRaisesRegex(ValueError, 'nonintegral'):
                lexicographic_witness(population)

    def test_complete_scopes_national_source_denominator(self):
        population = population_fixture()
        general = transport_votes(population, [4, 4, 4, 4], party_fixture())
        general['status'] = 'constructed'
        maori = copy.deepcopy(general)
        maori['sourceValidPartyVotes'] = 10
        maori['sourcePartyMass'] = {'a': 0, 'b': 10}
        result = combined_source_shares({'general': general, 'maori': maori})
        self.assertEqual(result['sourceValidPartyVotes'], 40)
        self.assertEqual(result['shares'], {'a': .375, 'b': .625})
        self.assertEqual(combined_source_shares({'general': general, 'maori': {'status': 'abstained'}})['status'], 'unavailable')

    def test_build_scope_retains_group_not_merely_aggregated_edge_constraints(self):
        population = population_fixture()
        scope = {'constraints': {'groups': population.groups,
                                 'destinationEquations': [{'target': t, 'sumIncomingPopulation': n}
                                                          for t, n in population.controls.items()]},
                 'targets': [{'code': t, 'name': 'Synthetic '+t} for t in population.controls]}
        result = build_scope(scope, party_fixture())
        self.assertEqual(result['status'], 'constructed')
        self.assertEqual(len(result['witnessVariables']), 4)
        self.assertEqual(result['solver']['sequentialMinimizations'], 4)
        self.assertEqual(result['groupWitnessTotals'], {'A': 8, 'B': 4, 'C': 4})


if __name__ == '__main__':
    unittest.main()
