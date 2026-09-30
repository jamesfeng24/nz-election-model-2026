"""Synthetic and adapter checks for the frozen conditional share baseline."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from scripts.models.conditional_candidate_share import evaluate, inventory, model
from scripts.validate.source_files import verify_source_files


class CandidateShareTests(unittest.TestCase):
    def setUp(self):
        self.elections = {year: inventory.read(path)
                          for year, path in zip(inventory.YEARS, inventory.ELECTION_PATHS)}
        self.frame = inventory.read(inventory.FRAME)

    def test_inventory_full_frame_and_all_earlier_training_seats(self):
        data = inventory.build_inventory(self.elections, self.frame)
        self.assertEqual(data['summary']['frameContests'], 213)
        self.assertEqual(data['summary']['heldGeneralCandidates'], 1313)
        self.assertEqual(sum(row['status'] == 'complete' for row in
                             data['trainingGeneralContests'] if row['year'] == 2008), 63)
        self.assertEqual(sum(row['status'] == 'ambiguous_mapping' for row in
                             data['trainingGeneralContests'] if row['year'] == 2014), 26)

    def test_report_only_alias_is_ambiguous_not_zero(self):
        seat = next(s for s in self.elections[2014]['electorates']
                    if s['kind'] == 'general' and any(c['partyKey'] == 'internetparty'
                                                     for c in s['candidates']))
        keys = {p['partyKey'] for s in self.elections[2014]['electorates']
                for p in s['parties']}
        links = inventory.classify(seat, keys, 2014)
        party = next(c for c in links if c['sourcePartyKey'] == 'internetparty')
        self.assertEqual(party['mappingStatus'], 'ambiguous_report_only_alliance')
        self.assertFalse(party['noRegisteredPartyGroup'])
        self.assertIsNone(party['partyKey'])

    def test_independent_and_unregistered_have_positive_possible_support(self):
        slate = [{'candidateOccurrenceId': 'party', 'partyKey': 'a',
                  'noRegisteredPartyGroup': False},
                 {'candidateOccurrenceId': 'independent', 'partyKey': None,
                  'noRegisteredPartyGroup': True},
                 {'candidateOccurrenceId': 'unregistered', 'partyKey': None,
                  'noRegisteredPartyGroup': True}]
        predictions = model.predict(slate, {'a': 0.7, 'b': 0.3}, 0.01)
        fitted = predictions['fitted_floor']
        self.assertAlmostEqual(sum(fitted.values()), 1)
        self.assertGreater(fitted['independent'], 0)
        self.assertEqual(fitted['independent'], fitted['unregistered'])
        self.assertIsNone(predictions['restricted_zero_floor'])
        self.assertEqual(model.winner_set(fitted), ['party'])
        self.assertEqual(model.winner_set(predictions['uniform']),
                         ['independent', 'party', 'unregistered'])
        self.assertEqual(model.winner_set(model.predict(
            slate, {'a': 0.7, 'b': 0.3}, 0.1)['fitted_floor']), ['party'])

    def test_ambiguous_missing_and_duplicate_mapping_rejected(self):
        seat = deepcopy(next(s for s in self.elections[2011]['electorates']
                             if s['kind'] == 'general'))
        keys = {p['partyKey'] for s in self.elections[2011]['electorates']
                for p in s['parties']}
        seat['candidates'][0]['partyKey'] = 'fictitiousregistered'
        links = inventory.classify(seat, keys | {'fictitiousregistered'}, 2011)
        self.assertEqual(links[0]['mappingStatus'], 'missing_local_registered_party_group')
        seat['candidates'][0]['id'] = seat['candidates'][1]['id']
        with self.assertRaises(ValueError):
            inventory.classify(seat, keys, 2011)

    def test_floor_optimizer_gates_and_bounds(self):
        case = {'year': 2008, 'id': 'synthetic', 'base': np.array([0.8, 0.0]),
                'actual': np.array([0.1, 0.9]), 'hasNoGroupOrZeroSupport': True}
        self.assertEqual(model.fit_floor([case] * 19)['status'], 'insufficient_training')
        high = model.fit_floor([case] * 20)
        self.assertEqual(high['boundary'], 'upper')
        self.assertEqual(high['kappa'], 0.1)
        low_case = case | {'actual': np.array([1.0, 0.0])}
        low = model.fit_floor([low_case] * 20)
        self.assertEqual(low['boundary'], 'lower')
        self.assertEqual(low['kappa'], 0.0001)

    def test_transform_requires_complete_joint_point(self):
        seat = {'parties': [{'partyKey': 'a'}, {'partyKey': 'b'}]}
        rows = [{'canonicalPartyId': key,
                 'predictions': {'additive': {'point': point, 'lower': point,
                                              'upper': point, 'clippingPossible': False}}}
                for key, point in [('a', 0.6), ('b', 0.4)]]
        self.assertEqual(model.transformed_party_vector(seat, rows, 'additive')[0],
                         {'a': 0.6, 'b': 0.4})
        self.assertEqual(model.transformed_party_vector(seat, rows[:1], 'additive')[1],
                         'incomplete_party_category_coverage')
        bad = deepcopy(rows)
        bad[1]['predictions']['additive']['point'] = 0.5
        self.assertEqual(model.transformed_party_vector(seat, bad, 'additive')[1],
                         'party_vector_not_jointly_normalized')

    def test_target_outcomes_and_identity_do_not_change_holdout_construction(self):
        base_inventory = inventory.build_inventory(self.elections, self.frame)
        rows = []
        before = model.construct_holdout(2011, base_inventory, self.elections, rows)
        changed = deepcopy(self.elections)
        for year in (2011, 2014, 2017, 2020, 2023):
            for seat in changed[year]['electorates']:
                seat['winnerCandidateId'] = 'counterfactual'
                for candidate in seat['candidates']:
                    candidate['votes'] = 0
                    candidate['share'] = 0
                    candidate['elected'] = not candidate['elected']
                    candidate['personId'] = 'counterfactual-person'
        after_inventory = inventory.build_inventory(changed, self.frame)
        after = model.construct_holdout(2011, after_inventory, changed, rows)
        self.assertEqual(before, after)
        earlier = deepcopy(self.elections)
        seat = next(s for s in earlier[2008]['electorates'] if s['kind'] == 'general')
        seat['candidates'][0]['votes'] += 1
        seat['candidateBallot']['validVotes'] += 1
        seat['validCandidateVotes'] += 1
        self.assertNotEqual(model.fit_floor(model.training_cases(2011, base_inventory, earlier))['kappa'],
                            before['fit']['kappa'])

    def test_source_snapshot_detects_missing_and_ambiguous_id(self):
        registry = inventory.read('data/sources.json')
        baseline = inventory.source_snapshot(registry, self.elections)
        self.assertTrue(baseline['sources'])
        deleted = {'sources': [r for r in registry['sources']
                               if r['id'] != baseline['sources'][0]['id']]}
        with self.assertRaises(ValueError):
            inventory.source_snapshot(deleted, self.elections)
        duplicate = {'sources': registry['sources'] + [registry['sources'][0]]}
        with self.assertRaises(ValueError):
            inventory.source_snapshot(duplicate, self.elections)
        added = {'sources': registry['sources'] + [{
            'id': 'unrelated-synthetic', 'rawPath': 'not-a-stage18-source'}]}
        self.assertEqual(inventory.source_snapshot(added, self.elections), baseline)

    def test_required_raw_bytes_are_checked(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            raw = root / 'data/raw/elections/sample.csv'
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b'preserved official bytes')
            record = {'id': 'sample', 'rawPath': 'data/raw/elections/sample.csv',
                      'sha256': sha256(raw.read_bytes()).hexdigest()}
            verify_source_files(root, {'schemaVersion': 1, 'sources': [record]})
            raw.write_bytes(b'altered official bytes')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                verify_source_files(root, {'schemaVersion': 1, 'sources': [record]})

    def test_contest_equal_metric_and_ties_arithmetic(self):
        def row(key, error, winners):
            return {'targetYear': 2011, 'targetElectorateId': key,
                    'actualWinnerCandidateId': 'a',
                    'methods': {'uniform': {'predictedWinnerSet': winners,
                                            'candidateErrors': [
                                                {'candidateOccurrenceId': 'a', 'errorPP': error,
                                                 'sourcePartyKey': 'a',
                                                 'mappingStatus': 'mapped_registered_party_group',
                                                 'slateSizeStratum': '2-5'},
                                                {'candidateOccurrenceId': 'b', 'errorPP': -error,
                                                 'sourcePartyKey': 'b',
                                                 'mappingStatus': 'mapped_registered_party_group',
                                                 'slateSizeStratum': '2-5'}]}}}
        metric = evaluate._metrics([row('one', 2, ['a', 'b']),
                                    row('two', 4, ['a', 'b'])], 'uniform')
        self.assertEqual(metric['contestEqualMaePP'], 3)
        self.assertAlmostEqual(metric['contestEqualRmsePP'], 10 ** 0.5)
        self.assertEqual(metric['predictedTieCount'], 2)
        self.assertEqual(metric['tiedSetContainsActualCount'], 2)
        self.assertEqual(metric['overallSignedBiasPPAccountingCheck'], 0)

    def test_target_outcomes_enter_evaluation_only(self):
        # Real adapters, saved construction, and a copied target election.
        construction = inventory.read(
            'data/processed/models/conditional-candidate-share/construction.json')
        before = evaluate.actuals(construction, self.elections)
        changed = deepcopy(self.elections)
        target = next(s for s in changed[2011]['electorates']
                      if s['id'] == before['records'][0]['targetElectorateId'])
        target['candidates'][0]['votes'] += 1
        target['candidates'][1]['votes'] -= 1
        after = evaluate.actuals(construction, changed)
        self.assertNotEqual(before, after)


if __name__ == '__main__':
    unittest.main()
