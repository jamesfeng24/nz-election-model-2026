"""Synthetic feasibility and preserved-evidence Stage 17 design tests."""

import copy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts.checkpoints import candidate_baseline_design as inventory
from scripts.checkpoints.candidate_share_design import candidate_counts, candidate_shares


class CandidateBaselineDesignTests(unittest.TestCase):
    def test_complete_share_replacement_unknown_person_does_not_transfer_strength(self):
        slate = [{'candidateId': 'prior_name', 'partyKey': 'a'},
                 {'candidateId': 'other', 'partyKey': 'b'}]
        support = {'a': 0.6, 'b': 0.4}
        before = candidate_shares(slate, support, 0.01)['candidateShares']
        changed = copy.deepcopy(slate)
        changed[0].update(candidateId='replacement', personId=None,
                          elected=True, votes=9999)
        after = candidate_shares(changed, support, 0.01)['candidateShares']
        self.assertAlmostEqual(before['prior_name'], after['replacement'])
        self.assertAlmostEqual(after['replacement'], 0.61 / 1.02)
        self.assertAlmostEqual(sum(after.values()), 1)

    def test_entrant_independent_and_party_exit_preserve_positive_simplex(self):
        slate = [{'candidateId': 'standing', 'partyKey': 'a'},
                 {'candidateId': 'new_party', 'partyKey': 'new'},
                 {'candidateId': 'independent', 'partyKey': None,
                  'noRegisteredPartyGroup': True}]
        support = {'a': 0.45, 'departing': 0.55, 'new': 0.0}
        result = candidate_shares(slate, support, 0.02)['candidateShares']
        self.assertGreater(result['new_party'], 0)
        self.assertGreater(result['independent'], 0)
        self.assertEqual(result['new_party'], result['independent'])
        self.assertAlmostEqual(sum(result.values()), 1)
        unknown = copy.deepcopy(slate)
        del unknown[2]['noRegisteredPartyGroup']
        with self.assertRaises(ValueError):
            candidate_shares(unknown, support, 0.02)

    def test_changed_boundary_requires_target_party_scenario_not_candidate_transport(self):
        slate = [{'candidateId': 'x', 'partyKey': 'a', 'sourceSeat': 'old_1'},
                 {'candidateId': 'y', 'partyKey': 'b', 'sourceSeat': 'old_2'}]
        support = {'a': 0.7, 'b': 0.3}
        first = candidate_shares(slate, support, 0.01)
        changed = copy.deepcopy(slate)
        changed[0].update(sourceSeat='old_3', sourceCandidateVotes=9999)
        self.assertEqual(first, candidate_shares(changed, support, 0.01))

    def test_missing_support_is_unknown_not_zero(self):
        slate = [{'candidateId': 'x', 'partyKey': 'a'}]
        with self.assertRaises(ValueError):
            candidate_shares(slate, {'b': 1.0}, 0.01)
        with self.assertRaises(ValueError):
            candidate_shares(slate, {'a': 0.8}, 0.01)
        with self.assertRaises(ValueError):
            candidate_shares([], {'a': 1.0}, 0.01)
        with self.assertRaises(ValueError):
            candidate_shares(slate, {'a': 1.0}, 0)

    def test_candidate_denominator_is_separate_and_counts_conserve(self):
        slate = [{'candidateId': 'a', 'partyKey': 'a'},
                 {'candidateId': 'b', 'partyKey': 'b'}]
        shares = candidate_shares(slate, {'a': 0.6, 'b': 0.4}, 0.01)
        controls = {'votesCast': 1200, 'validCandidateVotes': 1000,
                    'informalCandidateVotes': 100, 'disallowedCandidateVotes': 100}
        counts = candidate_counts(shares, controls)
        self.assertAlmostEqual(sum(counts['expectedCandidateVotes'].values()), 1000)
        self.assertEqual(counts['votesCastScenario'], 1200)
        broken = controls | {'validCandidateVotes': 1200}
        with self.assertRaises(ValueError):
            candidate_counts(shares, broken)

    def test_shared_party_scenario_moves_seats_jointly(self):
        first = [{'candidateId': 'a1', 'partyKey': 'a'},
                 {'candidateId': 'b1', 'partyKey': 'b'}]
        second = [{'candidateId': 'a2', 'partyKey': 'a'},
                  {'candidateId': 'independent', 'partyKey': None,
                   'noRegisteredPartyGroup': True}]
        low = {'a': 0.4, 'b': 0.6}
        high = {'a': 0.7, 'b': 0.3}
        for slate in (first, second):
            low_share = candidate_shares(slate, low, 0.02)['candidateShares']
            high_share = candidate_shares(slate, high, 0.02)['candidateShares']
            self.assertGreater(high_share[slate[0]['candidateId']],
                               low_share[slate[0]['candidateId']])
            self.assertAlmostEqual(sum(low_share.values()), 1)
            self.assertAlmostEqual(sum(high_share.values()), 1)

    def test_outcome_and_person_fields_never_enter_share_construction(self):
        slate = [{'candidateId': 'x', 'partyKey': 'a', 'personId': 'one',
                  'votes': 0, 'elected': False},
                 {'candidateId': 'y', 'partyKey': None,
                  'noRegisteredPartyGroup': True, 'personId': None,
                  'votes': 100, 'elected': True}]
        original = candidate_shares(slate, {'a': 1.0}, 0.01)
        changed = copy.deepcopy(slate)
        for candidate in changed:
            candidate.update(votes=12345, elected=not candidate['elected'],
                             personId='later_winner')
        self.assertEqual(original, candidate_shares(changed, {'a': 1.0}, 0.01))

    def test_preserved_candidate_tables_and_inventory_reproduce(self):
        snapshot, outputs = inventory.build()
        self.assertEqual(inventory.SOURCE_PLAN.read_bytes(), inventory.encode(snapshot))
        for name, payload in outputs.items():
            self.assertEqual((inventory.DEST / name).read_bytes(), inventory.encode(payload))
        summary = outputs['target-inventory.json']['summary']
        self.assertEqual(summary['targetSeats'], 71)
        self.assertEqual(summary['rawCandidateTablesVerified'], 72)
        self.assertEqual(summary['unique2023CandidateOccurrences'], 495)
        self.assertEqual(summary['target2026SlateAvailableSeats'], 0)
        self.assertEqual(summary['historicalCandidateLeadGeography']
                         ['observed_2023_count_on_certified_unchanged_geography'], 117)
        self.assertEqual(summary['historicalCandidateLeadGeography']
                         ['cancelled_source_no_valid_candidate_share'], 9)
        contract = inventory.read('data/processed/checkpoints/candidate-baseline-design/design-contract.json')
        self.assertIsNone(contract['selection']['selectedOperationalCandidateBaseline'])
        self.assertIn('no_historical_prediction_or_score_in_stage17', contract['exclusions'])

    def test_source_snapshot_accepts_additions_but_rejects_required_changes(self):
        registry = inventory.read('data/sources.json')
        saved = inventory.source_snapshot(registry)
        self.assertEqual(len(saved['sources']), 72)
        extra = copy.deepcopy(registry['sources'][0])
        extra['id'] = 'unrelated-future-stage17-source'
        extra['rawPath'] = 'data/raw/unrelated-future-stage17-source'
        added = copy.deepcopy(registry)
        added['sources'].append(extra)
        inventory.verify_source_snapshot(saved, added)
        changed = copy.deepcopy(registry)
        required = next(row for row in changed['sources']
                        if row['id'] == saved['sources'][0]['id'])
        required['limitations'] = ['changed']
        with self.assertRaises(ValueError):
            inventory.verify_source_snapshot(saved, changed)
        removed = copy.deepcopy(registry)
        removed['sources'] = [row for row in removed['sources']
                              if row['id'] != saved['sources'][0]['id']]
        with self.assertRaises(ValueError):
            inventory.verify_source_snapshot(saved, removed)
        duplicate = copy.deepcopy(registry)
        duplicate['sources'].append(copy.deepcopy(saved['sources'][0]))
        with self.assertRaises(ValueError):
            inventory.verify_source_snapshot(saved, duplicate)

    def test_changed_required_raw_bytes_fail(self):
        registry = inventory.read('data/sources.json')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in inventory.required_raw_paths():
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(inventory.ROOT / path, destination)
            with patch.object(inventory, 'ROOT', root):
                inventory.source_snapshot(registry)
                corrupted = root / inventory.required_raw_paths()[0]
                corrupted.write_bytes(corrupted.read_bytes() + b'changed')
                with self.assertRaises(ValueError):
                    inventory.source_snapshot(registry)


if __name__ == '__main__':
    unittest.main()
