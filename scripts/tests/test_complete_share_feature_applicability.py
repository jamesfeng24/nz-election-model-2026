"""Stage 20 source joins, fallback, coupled rounding and outcome isolation."""

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.checkpoints import complete_share_feature_run as run
from scripts.checkpoints import complete_share_fit_contract as fit_contract
from scripts.checkpoints.complete_share_features import (
    _feature, build_feature_inventory, coupled_cell_percent, coupled_row_witness)
from scripts.checkpoints.complete_share_feature_rank import (
    design, rank_details, training_means)
from scripts.validate.source_files import verify_source_files


class CompleteShareFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = run.read(run.FRAME)
        cls.mapping = run.read(run.MAPPING)
        cls.elections = {year: run.read(path) for year, path in run.ELECTIONS.items()}
        cls.splits = {year: run.read(path) for year, path in run.SPLITS.items()}
        cls.continuity = run.read(run.CONTINUITY)['records']

    def build(self, *, elections=None, splits=None, mapping=None):
        return build_feature_inventory(self.frame, mapping or self.mapping,
                                       elections or self.elections, splits or self.splits,
                                       self.continuity)

    def test_fixed_frame_counts_and_training_gates(self):
        outputs = run.build()
        inventory = outputs['feature-inventory.json']
        audit = outputs['design-audit.json']
        self.assertEqual(len(inventory['records']), 213)
        self.assertEqual([inventory['summary'][str(y)]['constructedContests']
                          for y in (2011, 2017, 2023)], [63, 64, 44])
        self.assertEqual([inventory['summary'][str(y)]['constructedCandidates']
                          for y in (2011, 2017, 2023)], [423, 431, 312])
        self.assertEqual([inventory['summary'][str(y)]['contestsWithS']
                          for y in (2011, 2017, 2023)], [63, 64, 44])
        self.assertTrue(audit['allFittingGatesPass'])
        self.assertEqual(len(outputs['source-contract.json']['sources']), 612)

    def test_validated_seat_id_recovers_label_spelling_change(self):
        records = self.build()['records']
        seat = next(r for r in records if r['targetElectorateId'] ==
                    'nz-general-2011-electorate-20')
        self.assertEqual(seat['sourceElectorateId'], 'nz-general-2008-electorate-20')
        self.assertEqual(seat['status'], 'constructed')
        self.assertTrue(any(c['s0Reported'] is not None for c in seat['candidates']))
        self.assertNotEqual(self.elections[2008]['electorates'][19]['name'],
                            self.elections[2011]['electorates'][19]['name'])

    def test_coupled_rounding_tightens_cell_and_has_witnesses(self):
        row = {'cells': [{'category': 'candidate', 'candidateId': 'a',
                          'reportedPercent': 33.33},
                         {'category': 'candidate', 'candidateId': 'b',
                          'reportedPercent': 33.33},
                         {'category': 'party-vote-only', 'candidateId': None,
                          'reportedPercent': 33.33}]}
        printed, low, high = coupled_cell_percent(row, 'a')
        self.assertEqual(printed, 33.33)
        self.assertEqual(low, Fraction('33.33'))
        self.assertEqual(high, Fraction('33.335'))
        for endpoint in ('lower', 'upper'):
            witness = coupled_row_witness(row, 'a', endpoint)
            self.assertEqual(sum(witness), 100)
            self.assertEqual(witness[0], low if endpoint == 'lower' else high)
        row['cells'][0]['reportedPercent'] = 0.0
        row['cells'][1]['reportedPercent'] = 66.67
        self.assertEqual(coupled_cell_percent(row, 'a')[1], 0)
        self.assertGreater(coupled_cell_percent(row, 'a')[2], 0)

    def test_source_zero_mass_and_no_candidate_are_fallback_not_zero_feature(self):
        candidate = {'candidateOccurrenceId': 'target', 'partyKey': 'p',
                     'mappingStatus': 'mapped_registered_party_group',
                     'noRegisteredPartyGroup': False}
        source = {'parties': [{'partyKey': 'p', 'votes': 10}], 'validPartyVotes': 100,
                  'validCandidateVotes': 100,
                  'candidates': [{'id': 'source', 'partyKey': 'p', 'votes': 20}]}
        target = {'parties': [{'partyKey': 'p', 'votes': 50}], 'validPartyVotes': 100}
        row = {'totalPartyVotes': 10,
               'cells': [{'category': 'candidate', 'candidateId': 'source',
                          'reportedPercent': 50.0},
                         {'category': 'party-vote-only', 'candidateId': None,
                          'reportedPercent': 50.0}]}
        matrix = {'id': 'source-matrix', 'sourceIds': ['official-source']}
        continuity = {(2008, 2011, 'p'): {'status': 'eligible',
                                          'source': {'sourceKey': 'p'}}}
        present = _feature(candidate, source, target, {'p': row}, matrix,
                           continuity, 2008, 2011)
        self.assertAlmostEqual(present['v0'], .1)
        self.assertAlmostEqual(present['s0Reported'], .5)
        self.assertEqual(present['sourceValidCandidateVotes'], 100)
        self.assertEqual(present['sourceValidPartyVotes'], 100)
        zero_source = deepcopy(source)
        zero_source['parties'][0]['votes'] = 0
        zero_row = deepcopy(row)
        zero_row['totalPartyVotes'] = 0
        missing_s = _feature(candidate, zero_source, target, {'p': zero_row}, matrix,
                             continuity, 2008, 2011)
        self.assertIsNone(missing_s['s0Reported'])
        self.assertAlmostEqual(missing_s['v0'], .2)
        self.assertIn('zero_mass_source_party_row_s_unavailable',
                      missing_s['fallbackReasons'])
        no_candidate = deepcopy(source)
        no_candidate['candidates'] = []
        missing_both = _feature(candidate, no_candidate, target, {'p': row}, matrix,
                                continuity, 2008, 2011)
        self.assertIsNone(missing_both['v0'])
        self.assertIsNone(missing_both['s0Reported'])
        self.assertIn('source_party_without_candidate_destination',
                      missing_both['fallbackReasons'])
        entrant = _feature(candidate, source, target, {'p': row}, matrix,
                           {(2008, 2011, 'p'): {'status': 'entrant', 'source': None}},
                           2008, 2011)
        self.assertIsNone(entrant['s0Reported'])
        self.assertIsNone(entrant['v0'])
        self.assertIn('documented_party_category_entry', entrant['fallbackReasons'])

    def test_missing_source_table_or_row_abstains_and_stage18_mapping_persists(self):
        splits = deepcopy(self.splits)
        splits[2008]['matrices'] = splits[2008]['matrices'][1:]
        seat = self.build(splits=splits)['records'][0]
        self.assertEqual(seat['status'], 'abstained')
        self.assertEqual(seat['reason'], 'missing_or_nonbehavioural_source_matrix')
        splits = deepcopy(self.splits)
        splits[2008]['matrices'][0]['rows'].pop(0)
        seat = self.build(splits=splits)['records'][0]
        self.assertEqual(seat['status'], 'abstained')
        self.assertEqual(seat['reason'], 'Incomplete source split party-row population')
        original = self.build()['records']
        self.assertEqual(sum(r['reason'] == 'stage18_ambiguous_mapping' for r in original), 20)

    def test_target_outcomes_and_identity_labels_cannot_change_features(self):
        before = self.build()
        elections = deepcopy(self.elections)
        for year in (2011, 2017, 2023):
            for seat in elections[year]['electorates']:
                for candidate in seat['candidates']:
                    candidate['votes'] = 0
                    candidate['elected'] = not candidate['elected']
                    candidate['personId'] = 'synthetic-mutated-identity'
                    candidate['name'] = 'SYNTHETIC CHANGED NAME'
        mapping = deepcopy(self.mapping)
        for record in mapping['frame']:
            for candidate in record.get('candidates', []):
                candidate['sourceAffiliation'] = 'SYNTHETIC LABEL'
        self.assertEqual(before, self.build(elections=elections, mapping=mapping))

    def test_within_slate_rank_rejects_redundant_features(self):
        seats = [r for r in self.build()['records'] if r['targetYear'] == 2011
                 and r['status'] == 'constructed']
        duplicate = deepcopy(seats)
        for seat in duplicate:
            for candidate in seat['candidates']:
                candidate['v0'] = candidate['s0Reported']
        means = training_means(duplicate)
        self.assertEqual(rank_details(design(duplicate, means, .01), [1, 2])['rank'], 1)

    def test_required_source_contract_rejects_mutation_and_duplicate(self):
        registry = run.read('data/sources.json')
        stage11 = run.read(run.STAGE11_SOURCES)
        stage18 = run.read(run.STAGE18_SOURCES)
        valid = run.source_snapshot(self.frame, self.elections, self.splits,
                                    registry, stage11, stage18)
        changed = deepcopy(registry)
        required = valid['sources'][0]['id']
        next(r for r in changed['sources'] if r['id'] == required)['limitations'] = ['changed']
        with self.assertRaisesRegex(ValueError, 'Changed, missing'):
            run.source_snapshot(self.frame, self.elections, self.splits,
                                changed, stage11, stage18)
        duplicate = deepcopy(registry)
        duplicate['sources'].append(duplicate['sources'][0])
        with self.assertRaisesRegex(ValueError, 'Ambiguous live'):
            run.source_snapshot(self.frame, self.elections, self.splits,
                                duplicate, stage11, stage18)
        unrelated = deepcopy(registry)
        unrelated['sources'].append({'id': 'unrelated-new-source'})
        self.assertEqual(valid, run.source_snapshot(self.frame, self.elections,
                                                     self.splits, unrelated,
                                                     stage11, stage18))
        with TemporaryDirectory() as directory:
            selected = valid['sources'][0]
            path = Path(directory) / selected['rawPath']
            path.parent.mkdir(parents=True)
            path.write_bytes(b'synthetic changed raw bytes')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                verify_source_files(Path(directory),
                                    {'schemaVersion': 1, 'sources': [selected]})

    def test_prefit_contract_pins_four_restrictions_and_exact_common_samples(self):
        contract = fit_contract.build()['fit-contract.json']
        self.assertEqual([item['jointParameters'] for item in contract['restrictions']],
                         [['kappa'], ['kappa', 'thetaS'], ['kappa', 'thetaV'],
                          ['kappa', 'thetaS', 'thetaV']])
        self.assertEqual([(fold['trainingContests'], fold['trainingCandidates'],
                           fold['evaluationContests'], fold['evaluationCandidates'])
                          for fold in contract['folds']],
                         [(63, 423, 64, 431), (127, 854, 44, 312)])
        self.assertEqual(len(contract['earliestBenchmarkContestIds']), 63)
        self.assertIsNone(contract['operationalSelection'])
        for fold in contract['folds']:
            self.assertEqual(len(fold['trainingCandidateOccurrenceIds']),
                             fold['trainingCandidates'])
            self.assertEqual(len(fold['commonEvaluationCandidateOccurrenceIds']),
                             fold['evaluationCandidates'])
            self.assertEqual(len(set(fold['trainingCandidateOccurrenceIds'])),
                             fold['trainingCandidates'])
            self.assertTrue(set(fold['trainingCandidateOccurrenceIds']).isdisjoint(
                fold['commonEvaluationCandidateOccurrenceIds']))

    def test_prefit_contract_rejects_changed_evidence_or_failed_gate(self):
        original_read, original_digest = fit_contract.read, fit_contract.digest
        try:
            fit_contract.digest = lambda path: ('changed' if path == fit_contract.INVENTORY
                                                 else original_digest(path))
            with self.assertRaisesRegex(ValueError, 'Changed committed'):
                fit_contract.build()
            fit_contract.digest = original_digest
            fit_contract.read = lambda path: ({'allFittingGatesPass': False}
                                              if path == fit_contract.AUDIT
                                              else original_read(path))
            with self.assertRaisesRegex(ValueError, 'coverage or rank gate failed'):
                fit_contract.build()
        finally:
            fit_contract.read, fit_contract.digest = original_read, original_digest


if __name__ == '__main__':
    unittest.main()
