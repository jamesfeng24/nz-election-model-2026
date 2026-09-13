"""Narrow cancelled-contest checks using preserved 2023 source evidence."""
from copy import deepcopy
from pathlib import Path
import unittest

from scripts.transform.historical import key, split_rows
from scripts.transform.modern_split import checked_table, local_matrix


RAW = Path(__file__).resolve().parents[2] / 'data/raw/elections/2023/statistics/csv'


def source(name):
    return (RAW / name).read_bytes(), name


def cancelled_electorate():
    table = split_rows(source('split-votes-electorate-39.csv')[0])
    candidates = []
    for index, cell in enumerate(table['rows'][0]['cells'][:-2]):
        name, party = cell['candidateLabel'].rsplit(' (', 1)
        candidates.append({'id': f'2023-39-{index}', 'name': name, 'party': party[:-1], 'votes': 0})
    rows = table['rows'][:-1]
    return {'id': '2023-39', 'year': 2023, 'name': 'Port Waikato',
            'sourceElectorateNumber': 39, 'candidateContestStatus': 'cancelled',
            'candidates': candidates, 'validCandidateVotes': 0,
            'candidateBallot': {'informalVotes': 0},
            'partyBallot': {'informalVotes': next(r['totalPartyVotes'] for r in rows if r['partyLabel'] == 'Informal Party Votes')},
            'parties': [{'partyKey': key(r['partyLabel']), 'votes': r['totalPartyVotes']} for r in rows if r['partyLabel'] != 'Informal Party Votes']}


class CancelledSplitTests(unittest.TestCase):
    def test_cancelled_evidence_is_not_behaviour(self):
        matrix = local_matrix(source, cancelled_electorate())
        self.assertFalse(matrix['behaviouralEvidence'])
        self.assertEqual(matrix['candidateContestStatus'], 'cancelled')
        self.assertEqual(matrix['unallocatedPartyVotes'], 42657)
        self.assertTrue(all(c['count'] is None and c['reportedPercent'] == 0 for r in matrix['rows'] for c in r['cells']))

    def test_cancelled_cannot_be_an_ordinary_table(self):
        with self.assertRaisesRegex(ValueError, 'row total'):
            checked_table(*source('split-votes-electorate-39.csv'))
        electorate = cancelled_electorate()
        electorate['candidateContestStatus'] = 'held'
        with self.assertRaisesRegex(ValueError, 'cancellation status'):
            local_matrix(source, electorate)

    def test_arbitrary_electorate_cannot_be_cancelled(self):
        electorate = cancelled_electorate()
        electorate['name'] = 'Auckland Central'
        with self.assertRaisesRegex(ValueError, 'cancellation status'):
            local_matrix(source, electorate)

    def test_cancelled_distribution_mutation_fails(self):
        raw, sid = source('split-votes-electorate-39.csv')
        with self.assertRaisesRegex(ValueError, 'rounding|zero percentages'):
            checked_table(raw.replace(b',0.00,', b',1.00,', 1), sid, cancelled=True)

    def test_cancelled_candidate_count_mutation_fails(self):
        electorate = deepcopy(cancelled_electorate())
        electorate['candidates'][0]['votes'] = 1
        with self.assertRaisesRegex(ValueError, 'source counts'):
            local_matrix(source, electorate)


if __name__ == '__main__':
    unittest.main()
