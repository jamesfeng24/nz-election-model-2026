"""Stage 23 synthetic conservation, input and outcome-boundary tests."""
import copy
import json
import math
import unittest

from scripts.models.complete_party_vector.common import ROOT, verify_contract
from scripts.models.complete_party_vector.construction import (
    construct_inventory, construct_vector, validate_simplex,
)


def case():
    categories = [
        {'categoryId': 'a', 'relationship': 'continuing', 'sourceNationalShare': .5},
        {'categoryId': 'b', 'relationship': 'continuing', 'sourceNationalShare': .3},
        {'categoryId': 'entrant', 'relationship': 'entrant', 'sourceNationalShare': None},
        {'categoryId': 'gone', 'relationship': 'exit', 'sourceNationalShare': .2},
    ]
    source = {
        'a': {'sourceLocalShare': .6, 'sourceLocalStatus': 'observed_positive'},
        'b': {'sourceLocalShare': 0, 'sourceLocalStatus': 'observed_zero'},
        'entrant': {'sourceLocalShare': None, 'sourceLocalStatus': 'entrant_no_source_category'},
    }
    return categories, source, {'a': .4, 'b': .3, 'entrant': .3}


class CompletePartyVectorTests(unittest.TestCase):
    def test_entrant_exit_zero_and_simplex(self):
        categories, source, scenario = case()
        vector, status = construct_vector(categories, source, scenario)
        self.assertEqual(set(vector), {'a', 'b', 'entrant'})
        self.assertEqual(vector['b'], 0)
        self.assertGreater(vector['entrant'], 0)
        self.assertAlmostEqual(vector['a'], .48 / .78)
        self.assertAlmostEqual(vector['entrant'], .3 / .78)
        self.assertEqual(status['entrant']['affinity'], 1)
        self.assertAlmostEqual(sum(vector.values()), 1)

    def test_missing_is_not_zero(self):
        categories, source, scenario = case()
        source['b']['sourceLocalStatus'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'Missing continuing'):
            construct_vector(categories, source, scenario)

    def test_duplicate_and_incomplete_category_rejected(self):
        categories, source, scenario = case()
        with self.assertRaisesRegex(ValueError, 'Ambiguous or incomplete'):
            construct_vector(categories, source, {'a': .7, 'b': .3})
        categories.append(copy.deepcopy(categories[0]))
        with self.assertRaisesRegex(ValueError, 'Ambiguous or incomplete'):
            construct_vector(categories, source, scenario)

    def test_incomplete_scenario_and_no_mass_rejected(self):
        categories, source, scenario = case()
        with self.assertRaisesRegex(ValueError, 'Incomplete party simplex'):
            construct_vector(categories, source, {'a': .4, 'b': .3, 'entrant': .2})
        source['a'] = {'sourceLocalShare': 0, 'sourceLocalStatus': 'observed_zero'}
        with self.assertRaisesRegex(ValueError, 'No supported target mass'):
            construct_vector(categories, source, {'a': .5, 'b': .5, 'entrant': 0})

    def test_joint_closure_not_independent_clipping(self):
        categories, source, scenario = case()
        vector, _ = construct_vector(categories, source, scenario)
        self.assertAlmostEqual(vector['a'] / vector['entrant'], .48 / .3)
        self.assertNotAlmostEqual(vector['a'], .48)

    def test_real_adapter_ignores_target_outcomes_and_identity(self):
        inventory = json.loads((ROOT / 'data/processed/models/complete-party-vector/input-inventory.json').read_text())
        original = construct_inventory(inventory)
        changed = copy.deepcopy(inventory)
        for row in changed['frame']:
            row['targetObservedValidPartyVotesEvaluationOnly'] = -99
            row['targetLocalPartyVotes'] = {'fabricated': 123}
            row['candidateResults'] = [999]
            row['winnerFlags'] = ['reversed']
            row['identityLabels'] = ['different']
            row['residuals'] = [1]
        altered = construct_inventory(changed)
        self.assertEqual(original['records'], altered['records'])

    def test_representative_independent_arithmetic_and_integrity(self):
        verify_contract()
        construction = json.loads((ROOT / 'data/processed/models/complete-party-vector/construction.json').read_text())
        inventory = json.loads((ROOT / 'data/processed/models/complete-party-vector/input-inventory.json').read_text())
        self.assertEqual(construction, construct_inventory(inventory))
        first = construction['records'][0]
        row = inventory['frame'][0]
        groups = next(x['categories'] for x in inventory['categoryRelationships'] if x['targetYear'] == row['targetYear'])
        expected = {}
        for group in groups:
            if group['relationship'] == 'exit':
                continue
            cid = group['categoryId']
            source = next(x for x in row['sourceCategories'] if x['categoryId'] == cid)
            factor = 1 if group['relationship'] == 'entrant' else source['sourceLocalShare'] / group['sourceNationalShare']
            expected[cid] = group['suppliedTargetNationalShare'] * factor
        total = math.fsum(expected.values())
        for cid, raw in expected.items():
            self.assertAlmostEqual(first['localPartyShares'][cid], raw / total)


if __name__ == '__main__':
    unittest.main()
