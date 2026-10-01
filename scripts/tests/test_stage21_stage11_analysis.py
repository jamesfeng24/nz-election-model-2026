"""Stage 11 corrected main and Stage 5 sensitivity adapter regression checks."""

import json
import unittest
from copy import deepcopy

from scripts.models.historical_split_ticket.analysis import _candidate_prediction, _pool
from scripts.models.historical_split_ticket.corrected_analysis import certified_name_bridge
from scripts.models.historical_split_ticket.corrected_analysis_run import build, score_encode
from scripts.models.historical_split_ticket.correction import certified_pair_for_row
from scripts.models.historical_split_ticket.correction_run import DEST, ROOT
from scripts.models.historical_split_ticket.evidence import YEARS


def read(path):
    return json.loads((ROOT / path).read_bytes())


class CorrectedSplitAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corrected = read(DEST / 'corrected-applicability.json')
        cls.old = read('data/processed/models/historical-split-ticket/applicability.json')
        cls.elections = {year: read(f'data/processed/elections/{year}.json') for year in YEARS}
        cls.splits = {year: read(f'data/processed/split-votes/{year}.json') for year in YEARS}
        cls.comparison = read(DEST / 'correction-comparison.json')

    def test_original_common_and_new_admissions_are_separate(self):
        self.assertEqual(self.comparison['originalCommonCandidateCount'], 803)
        self.assertEqual(self.comparison['newlyAdmittedCandidateCount'], 33)
        self.assertEqual(self.comparison['correctedFullCandidateCount'], 836)
        self.assertEqual([r['n'] for r in self.comparison['originalCommonScores']], [247, 285, 271])
        self.assertEqual([r['n'] for r in self.comparison['newAdmissionScores']], [33, 0, 0])
        self.assertEqual([r['n'] for r in self.comparison['correctedFullScores']], [280, 285, 271])
        old_scores = read('data/processed/models/historical-split-ticket/predictions.json')['transitionScores']
        for corrected, original in zip(self.comparison['originalCommonScores'], old_scores):
            for model in ('local', 'pooled', 'partyOnly'):
                self.assertEqual(corrected[model], original[model])

    def test_corrected_id_adapter_preserves_raw_labels_and_source_matrix(self):
        original = deepcopy(self.elections)
        bridged = certified_name_bridge(self.corrected, self.elections)
        self.assertEqual(original, self.elections)
        for row in self.corrected['records']:
            if not row['conditionalPartialApplicability']:
                continue
            source, target = certified_pair_for_row(row, self.elections)
            matching = [seat for seat in bridged[row['sourceYear']]['electorates']
                        if seat['kind'] == 'general' and seat['name'] == row['electorateName']]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]['id'], source['id'])
            self.assertEqual(row['sourceMatrixId'],
                             next(m['id'] for m in self.splits[row['sourceYear']]['matrices']
                                  if m['electorateId'] == source['id']))
            self.assertEqual(row['targetElectorateId'], target['id'])

    def test_target_split_cells_only_change_evaluation_for_recovered_candidate(self):
        old = {row['targetOccurrenceId'] for row in self.old['records']
               if row['conditionalPartialApplicability']}
        row = next(row for row in self.corrected['records']
                   if row['conditionalPartialApplicability'] and row['targetOccurrenceId'] not in old)
        source, target = certified_pair_for_row(row, self.elections)
        source_matrix = next(m for m in self.splits[row['sourceYear']]['matrices']
                             if m['electorateId'] == source['id'])
        target_matrix = next(m for m in self.splits[row['targetYear']]['matrices']
                             if m['electorateId'] == target['id'])
        continuity = read('data/processed/models/party-vote-transform/party-continuity.json')['records']
        party_map = {(r['sourceYear'], r['targetYear'], r['target']['sourceKey']):
                     r['source']['sourceKey'] for r in continuity if r['status'] == 'eligible'}
        pool = _pool(self.elections[row['sourceYear']], self.splits[row['sourceYear']])
        first = _candidate_prediction(row, source, target, source_matrix, target_matrix,
                                      party_map, pool)
        changed_matrix = deepcopy(target_matrix)
        cell = next(cell for split_row in changed_matrix['rows'][:-1]
                    if split_row['totalPartyVotes'] > 0 for cell in split_row['cells']
                    if cell['candidateId'] == row['targetOccurrenceId'])
        cell['reportedPercent'] += 1
        second = _candidate_prediction(row, source, target, source_matrix, changed_matrix,
                                       party_map, pool)
        for field in ('localMatchedVotes', 'pooledMatchedVotes', 'partyOnlyMatchedVotes',
                      'fullCandidateVoteBounds'):
            self.assertEqual(first[field], second[field])
        self.assertNotEqual(first['actualMatchedVotes'], second['actualMatchedVotes'])

    def test_stage5_sensitivity_and_selection_reproduce_without_rewriting_original(self):
        old_sensitivity = read('data/processed/models/historical-split-ticket/party-input-sensitivity.json')
        self.assertEqual(self.comparison['originalCommonStage5Sensitivity'], old_sensitivity)
        self.assertEqual([row['n'] for row in self.comparison['correctedFullStage5Sensitivity']['scores']],
                         [280, 285, 271])
        selection = read(DEST / 'corrected-selection.json')
        self.assertIsNone(selection['selectedOperationalSplitView'])
        self.assertFalse(selection['gates']['completePartyBallotMassMapping'])
        for name, value in build().items():
            self.assertEqual((ROOT / DEST / name).read_bytes(), score_encode(value))


if __name__ == '__main__':
    unittest.main()
