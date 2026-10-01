"""Stage 23 synthetic conservation, input and outcome-boundary tests."""
import copy
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from scripts.models.complete_party_vector.common import ROOT, verify_contract
from scripts.models.complete_party_vector.construction import (
    construct_inventory, construct_vector, validate_simplex,
)
from scripts.models.complete_party_vector.evaluation import contest_errors, metrics, national_gap
from scripts.models.complete_party_vector.inventory import frame_rows
from scripts.models.party_vote_transform.inputs import Inputs


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

    def test_coupled_geographic_bounds_cannot_become_midpoints(self):
        categories, source, scenario = case()
        source['a']['sourceLocalShare'] = {'lower': .5, 'upper': .7}
        with self.assertRaisesRegex(ValueError, 'Invalid continuing source party evidence'):
            construct_vector(categories, source, scenario)
        categories, source, scenario = case()
        scenario['a'] = [.3, .5]
        with self.assertRaisesRegex(ValueError, 'Invalid nonnegative vector'):
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

    def test_inventory_adapter_does_not_read_target_local_shares(self):
        inventory = json.loads((ROOT / 'data/processed/models/complete-party-vector/input-inventory.json').read_text())
        elections = Inputs().elections()
        groups = {(x['sourceYear'], x['targetYear']): x['categories']
                  for x in inventory['categoryRelationships']}
        frame = json.loads((ROOT / 'data/processed/checkpoints/complete-candidate-baseline/input-inventory.json').read_text())['records']
        original = frame_rows(elections, frame, groups)
        changed = copy.deepcopy(elections)
        for scope in changed[2023]['scopes'].values():
            for electorate in scope.values():
                for party in electorate['parties'].values():
                    party['share'] = .123
                    party['votes'] = 999
        self.assertEqual(original, frame_rows(changed, frame, groups))

    def test_metric_denominator_and_weights(self):
        mae, mse = contest_errors({'a': .6, 'b': .4}, {'a': .5, 'b': .5})
        self.assertAlmostEqual(mae, 10)
        self.assertAlmostEqual(mse, 100)
        rows = [{'contestMaePP': 10, 'contestMsePP2': 100, 'actualLocalShares': {'a': .5, 'b': .5}},
                {'contestMaePP': 20, 'contestMsePP2': 400, 'actualLocalShares': {'a': .5, 'b': .5}}]
        self.assertAlmostEqual(metrics(rows)['maePP'], 15)
        self.assertAlmostEqual(metrics(rows)['rmsePP'], math.sqrt(250))
        self.assertAlmostEqual(metrics(rows, [1, 3])['maePP'], 17.5)

    def test_national_gap_uses_full_population_and_oracle_weights_only(self):
        predictions = [
            {'targetYear': 2011, 'applicability': 'constructed',
             'localPartyShares': {'a': .8, 'b': .2}, 'suppliedNationalScenario': {'a': .5, 'b': .5}},
            {'targetYear': 2011, 'applicability': 'constructed',
             'localPartyShares': {'a': .4, 'b': .6}, 'suppliedNationalScenario': {'a': .5, 'b': .5}},
        ]
        actuals = [{'targetObservedValidPartyVotes': 1}, {'targetObservedValidPartyVotes': 3}]
        gap = national_gap(predictions, actuals, 2011)
        self.assertAlmostEqual(gap['categoryGapsPP']['a'], 0)
        predictions[1]['applicability'] = 'abstain'
        self.assertEqual(national_gap(predictions, actuals, 2011)['status'],
                         'abstain_incomplete_population')

    def test_stage_specific_required_bytes_and_unrelated_additions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            required = root / 'raw' / 'required.csv'
            required.parent.mkdir(parents=True)
            required.write_bytes(b'original')
            contract = root / 'data/processed/models/complete-party-vector/source-contract.json'
            contract.parent.mkdir(parents=True)
            contract.write_text(json.dumps({'inputHashes': {
                'raw/required.csv': hashlib.sha256(b'original').hexdigest()}}))
            verify_contract(root)
            (root / 'raw' / 'unrelated.csv').write_bytes(b'new')
            verify_contract(root)
            required.write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError, 'Changed Stage23 input'):
                verify_contract(root)
            required.unlink()
            with self.assertRaises(FileNotFoundError):
                verify_contract(root)

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

    def test_stage22_candidate_ballot_keys_without_candidate_scoring(self):
        construction = json.loads((ROOT / 'data/processed/models/complete-party-vector/construction.json').read_text())
        mapping = json.loads((ROOT / 'data/processed/checkpoints/stage22-shared-group-prefit/amended-mapping.json').read_text())
        by_seat = {(r['targetYear'], r['targetElectorateId']): r for r in construction['records']}
        checked = 0
        for contest in mapping['frame']:
            if contest['status'] != 'complete':
                continue
            party_keys = set(by_seat[contest['targetYear'], contest['targetElectorateId']]['targetPartyGroupKeys'].values())
            for candidate in contest['candidates']:
                if candidate['partyKey'] is not None:
                    self.assertIn(candidate['partyKey'], party_keys)
                    checked += 1
        self.assertEqual(checked, 1192)


if __name__ == '__main__':
    unittest.main()
