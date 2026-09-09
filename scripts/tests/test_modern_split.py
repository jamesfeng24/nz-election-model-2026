"""Focused mutations of preserved official 2017 split evidence."""
from pathlib import Path
import unittest

from scripts.transform.historical import key
from scripts.transform.modern_tables import candidate_table, party_table, turnout_table
from scripts.transform.modern_split import checked_table, local_matrix, split_summary


ROOT = Path(__file__).resolve().parents[2] / 'data/raw/elections/2017/statistics/csv'


def source(name):
    return (ROOT / name).read_bytes(), name


def first_electorate():
    candidate = candidate_table(source('candidate-votes-by-voting-place-1.csv')[0])
    party = party_table(source('votes-for-registered-parties-by-electorate.csv')[0])
    ballots = {}
    for kind in ('party', 'candidate'):
        rows, _ = turnout_table(source(kind+'-votes-and-turnout-by-electorate.csv')[0])
        ballots[kind] = next(r for r in rows if r['name'] == 'Auckland Central')
    for i, c in enumerate(candidate['candidates']):
        c.update(id=f'2017-1-{i}', partyKey=key(c['party']))
    return {'id': '2017-1', 'year': 2017, 'name': 'Auckland Central', 'sourceElectorateNumber': 1,
            'partyBallot': ballots['party'], 'candidateBallot': ballots['candidate'],
            'validCandidateVotes': candidate['validVotes'], 'candidates': candidate['candidates'],
            'parties': party['records']['aucklandcentral']['parties']}


class ModernSplitTests(unittest.TestCase):
    def test_exact_nested_parenthesis_candidate_match(self):
        matrix = local_matrix(source, first_electorate())
        cells = matrix['rows'][0]['cells']
        top = next(c for c in cells if '(TOP)' in c['candidateLabel'])
        self.assertIsNotNone(top['candidateId'])
        self.assertTrue(all(c['count'] is None for row in matrix['rows'] for c in row['cells']))
        self.assertEqual(matrix['precision']['decimalPlaces'], 2)

    def test_unknown_candidate_label_fails(self):
        electorate = first_electorate()
        electorate['candidates'][0]['name'] = 'UNKNOWN, Name'
        with self.assertRaisesRegex(ValueError, 'mapping'):
            local_matrix(source, electorate)

    def test_altered_candidate_count_fails(self):
        electorate = first_electorate()
        electorate['candidates'][0]['votes'] += 100
        with self.assertRaisesRegex(ValueError, 'column'):
            local_matrix(source, electorate)

    def test_missing_local_percentage_fails(self):
        raw, sid = source('split-votes-electorate-1.csv')
        with self.assertRaisesRegex(ValueError, 'Missing nonzero split'):
            checked_table(raw.replace(b',19.87,', b',,', 1), sid)

    def test_exact_summary_and_mutation(self):
        aggregate = checked_table(*source('split-votes-all.csv'))
        result = split_summary(source, aggregate)
        informal = next(r for r in result['rows'] if r['partyLabel'] == 'Informal Party Votes')
        self.assertEqual(informal['nonSplitCandidateVotes'], 350)
        def altered(name):
            raw, sid = source(name)
            return raw.replace(b',2449,', b',2450,', 1), sid
        with self.assertRaisesRegex(ValueError, 'count sum'):
            split_summary(altered, aggregate)


if __name__ == '__main__':
    unittest.main()
