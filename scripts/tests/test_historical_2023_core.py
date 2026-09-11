"""Official 2023 cancellation evidence must not become candidate performance."""
import unittest
from pathlib import Path

from scripts.transform.modern_tables import candidate_table, overall_table, turnout_table

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/elections/2023/statistics/csv'


class Historical2023CoreTests(unittest.TestCase):
    def test_cancelled_candidate_evidence(self):
        data = (RAW / 'candidate-votes-by-voting-place-39.csv').read_bytes()
        result = candidate_table(data, cancelled=True)
        self.assertEqual(len(result['candidates']), 9)
        self.assertIsNone(result['winnerName'])
        self.assertIsNone(result['majority'])
        for candidate in result['candidates']:
            self.assertEqual(candidate['votes'], 0)
            self.assertEqual(candidate['reportedPercent'], 0)
            self.assertIsNone(candidate['sourceShare'])
            self.assertIsNone(candidate['share'])
        with self.assertRaisesRegex(ValueError, 'cancellation marker'):
            candidate_table(data)
        with self.assertRaisesRegex(ValueError, 'cancelled|Cancelled'):
            candidate_table(data.replace(b'Electorate Candidate Valid Votes,Party,,,', b'Electorate Candidate Valid Votes,Party,,,BAYLY - majority 0'), cancelled=True)

    def test_normal_contest_cannot_be_cancelled(self):
        with self.assertRaisesRegex(ValueError, 'cancellation marker'):
            candidate_table((RAW / 'candidate-votes-by-voting-place-1.csv').read_bytes(), cancelled=True)

    def test_cancelled_candidate_turnout_is_separate(self):
        data = (RAW / 'candidate-votes-and-turnout-by-electorate.csv').read_bytes()
        records, _ = turnout_table(data, ('Port Waikato',))
        record = next(r for r in records if r['name'] == 'Port Waikato')
        self.assertEqual(record['validVotes'], 0)
        self.assertEqual(record['votesCast'], 804)
        self.assertEqual(record['specialDisallowed'], 804)
        with self.assertRaises(ValueError):
            turnout_table(data)
        with self.assertRaises(ValueError):
            turnout_table(data, ('Auckland Central',))

    def test_overall_complementary_rows_preserve_missingness(self):
        result = overall_table((RAW / 'overall-results-summary.csv').read_bytes())
        self.assertEqual(result['validPartyVotes'], 2851211)
        freedom = next(p for p in result['parties'] if p['name'] == 'Freedoms NZ')
        self.assertEqual(freedom['partyVotes'], 9586)
        self.assertEqual(freedom['candidateVotes'], 0)
        self.assertEqual(len(freedom['sourceRows']), 2)
        vision = next(p for p in result['parties'] if p['name'] == 'Vision New Zealand')
        self.assertIsNone(vision['partyVotes'])
        self.assertEqual(vision['candidateVotes'], 10466)


if __name__ == '__main__':
    unittest.main()
