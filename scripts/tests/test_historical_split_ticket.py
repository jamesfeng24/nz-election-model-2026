"""Stage 11 split orientation, missingness, leakage and provenance contracts."""

import json
import tempfile
import unittest
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

from scripts.models.historical_split_ticket.analysis import (
    _candidate_prediction, _pool, _score)
from scripts.models.historical_split_ticket.analysis_run import build as build_analysis, encode
from scripts.models.historical_split_ticket.evidence import (
    YEARS, candidate_inventory, table_coverage, verify_snapshot)
from scripts.models.historical_split_ticket.run import DEST, ROOT, build as build_evidence


def read(path):
    return json.loads((ROOT / path).read_bytes())


class SplitEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elections = {year: read(f'data/processed/elections/{year}.json') for year in YEARS}
        cls.splits = {year: read(f'data/processed/split-votes/{year}.json') for year in YEARS}
        cls.continuity = read('data/processed/models/party-vote-transform/party-continuity.json')['records']
        cls.applicability = read('data/processed/models/historical-split-ticket/applicability.json')

    def test_orientation_denominator_rounding_and_maori_coverage(self):
        coverage = table_coverage(self.elections, self.splits)
        self.assertEqual([row['roundedLocalMatrices'] for row in coverage],
                         [63, 63, 64, 64, 65, 65])
        self.assertEqual([row['maoriElectoratesWithoutLocalMatrix'] for row in coverage],
                         [7, 7, 7, 7, 6, 7])
        self.assertEqual(coverage[-1]['cancelledOrNonbehavioural'], 1)
        self.assertEqual(coverage[-1]['officialSourceDiscrepancies'], 21)
        matrix = self.splits[2008]['matrices'][0]
        self.assertTrue(all(cell['count'] is None for row in matrix['rows']
                            for cell in row['cells']))
        changed = deepcopy(self.splits)
        changed[2008]['matrices'][0]['rows'][0]['totalPartyVotes'] += 1
        with self.assertRaisesRegex(ValueError, 'denominator'):
            table_coverage(self.elections, changed)

    def test_boundary_cancellation_and_unknown_identity_are_explicit(self):
        rows = self.applicability['records']
        self.assertTrue(any('changed_boundary_transition' in row['exclusionReasons'] for row in rows))
        self.assertTrue(any('cancelled_target_contest' in row['exclusionReasons'] for row in rows))
        partial = [row for row in rows if row['conditionalPartialApplicability']]
        self.assertEqual(len(partial), 803)
        self.assertEqual(sum(row['candidateMapping'] == 'unresolved_same_party_predecessor'
                             for row in partial), 523)
        self.assertFalse(any(row['conditionalLocalApplicability'] for row in rows))

    def test_target_and_later_winner_flags_do_not_change_eligibility(self):
        changed = deepcopy(self.elections)
        for year in YEARS:
            for seat in changed[year]['electorates']:
                seat['winnerCandidateId'] = None
                for candidate in seat['candidates']:
                    candidate['elected'] = not candidate['elected']
        self.assertEqual(candidate_inventory(changed, self.splits, self.continuity),
                         self.applicability)

    def test_required_source_records_and_raw_bytes_are_pinned(self):
        source = read('data/source-plans/stage11-local-split-sources.json')['sources'][0]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root / source['rawPath']
            raw.parent.mkdir(parents=True)
            raw.write_bytes((ROOT / source['rawPath']).read_bytes())
            snapshot = {'stage': 11, 'sources': [source]}
            split = {year: {'matrices': []} for year in YEARS}
            split[2008]['matrices'] = [{'sourceIds': [source['id']]}]
            registry = {'sources': [source]}
            verify_snapshot(root, registry, snapshot, split)
            verify_snapshot(root, {'sources': [source, {'id': 'unrelated'}]}, snapshot, split)
            altered = deepcopy(source)
            altered['licence'] = 'changed'
            with self.assertRaisesRegex(ValueError, 'Changed or deleted'):
                verify_snapshot(root, {'sources': [altered]}, snapshot, split)
            with self.assertRaisesRegex(ValueError, 'Changed or deleted'):
                verify_snapshot(root, {'sources': []}, snapshot, split)
            with self.assertRaisesRegex(ValueError, 'Ambiguous'):
                verify_snapshot(root, {'sources': [source, source]}, snapshot, split)
            raw.write_bytes(raw.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'Checksum'):
                verify_snapshot(root, registry, snapshot, split)


class SplitAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elections = {year: read(f'data/processed/elections/{year}.json') for year in YEARS}
        cls.splits = {year: read(f'data/processed/split-votes/{year}.json') for year in YEARS}
        cls.applicability = read('data/processed/models/historical-split-ticket/applicability.json')
        cls.continuity = read('data/processed/models/party-vote-transform/party-continuity.json')['records']

    def test_benchmark_interval_arithmetic(self):
        row = {'targetPartyBallots': 100,
               'actualMatchedVotes': (Fraction(20), Fraction(21)),
               'model': (Fraction(18), Fraction(19))}
        score = _score([row], 'model')
        self.assertEqual(score['maeLowerPP'], 1)
        self.assertEqual(score['maeUpperPP'], 3)
        self.assertEqual(score['rmseLowerPP'], 1)
        self.assertEqual(score['rmseUpperPP'], 3)

    def test_target_split_outcome_cannot_change_a_prediction(self):
        row = next(row for row in self.applicability['records']
                   if row['conditionalPartialApplicability'])
        source_year, target_year = row['sourceYear'], row['targetYear']
        source = next(seat for seat in self.elections[source_year]['electorates']
                      if seat['name'] == row['electorateName'] and seat['kind'] == 'general')
        target = next(seat for seat in self.elections[target_year]['electorates']
                      if seat['name'] == row['electorateName'] and seat['kind'] == 'general')
        source_matrix = next(m for m in self.splits[source_year]['matrices']
                             if m['electorateId'] == source['id'])
        target_matrix = next(m for m in self.splits[target_year]['matrices']
                             if m['electorateId'] == target['id'])
        party_map = {(c['sourceYear'], c['targetYear'], c['target']['sourceKey']):
                     c['source']['sourceKey'] for c in self.continuity if c['status'] == 'eligible'}
        pooled = _pool(self.elections[source_year], self.splits[source_year])
        before = _candidate_prediction(row, source, target, source_matrix, target_matrix,
                                       party_map, pooled)
        changed = deepcopy(target_matrix)
        cell = next(cell for r in changed['rows'][:-1] for cell in r['cells']
                    if cell['candidateId'] == row['targetOccurrenceId'] and
                    r['totalPartyVotes'] > 0)
        cell['reportedPercent'] += 1
        after = _candidate_prediction(row, source, target, source_matrix, changed,
                                      party_map, pooled)
        for name in ('localMatchedVotes', 'pooledMatchedVotes',
                     'partyOnlyMatchedVotes', 'fullCandidateVoteBounds'):
            self.assertEqual(before[name], after[name])
        self.assertNotEqual(before['actualMatchedVotes'], after['actualMatchedVotes'])

    def test_joint_mass_and_deterministic_generation(self):
        evidence = build_evidence()
        for name, value in evidence.items():
            self.assertEqual((DEST / name).read_bytes(), encode(value))
        analysis = build_analysis()
        for name, value in analysis.items():
            self.assertEqual((DEST / name).read_bytes(), encode(value))
        joint = analysis['predictions.json']['jointAccounting']
        self.assertTrue(joint)
        for row in joint:
            self.assertEqual(row['matchedPartyBallots'] + row['unmatchedPartyBallots'],
                             row['targetPartyBallots'])
            self.assertLessEqual(row['roundingEnclosure'][0], row['matchedPartyBallots'])
            self.assertGreaterEqual(row['roundingEnclosure'][1], row['matchedPartyBallots'])


if __name__ == '__main__':
    unittest.main()
