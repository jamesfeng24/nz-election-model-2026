"""Focused modern-format parser tests using preserved 2017 source evidence."""
from pathlib import Path
import unittest

from scripts.transform.modern_tables import (
    candidate_table, overall_table, party_table, turnout_table, winners_table,
)

RAW = Path(__file__).resolve().parents[2] / 'data/raw/elections/2017/statistics/csv'


class ModernTablesTests(unittest.TestCase):
    def raw(self, name):
        return (RAW / name).read_bytes()

    def test_turnout_controls_and_unicode(self):
        for ballot in ('party', 'candidate'):
            records, totals = turnout_table(self.raw(f'{ballot}-votes-and-turnout-by-electorate.csv'))
            self.assertEqual(len(records), 71)
            self.assertEqual(sum(r['scope'] == 'general' for r in records), 64)
            self.assertIn('Te Tai Hauāuru', [r['name'] for r in records])
            self.assertEqual(totals['national']['votesCast'], 2630173)

    def test_candidate_details_and_percentage_units(self):
        result = candidate_table(self.raw('candidate-votes-by-voting-place-1.csv'))
        self.assertEqual(result['validVotes'], 29170)
        self.assertEqual(result['winnerName'], 'KAYE, Nicola Laura')
        winner = next(c for c in result['candidates'] if c['name'] == result['winnerName'])
        self.assertEqual(winner['reportedPercent'], 45.25)
        self.assertEqual(winner['sourceShare'], .4525)
        self.assertEqual(result['majority'], 1581)

    def test_party_and_winner_coverage(self):
        parties = party_table(self.raw('votes-for-registered-parties-by-electorate.csv'))
        winners = winners_table(self.raw('winning-electorate-candidates.csv'))
        self.assertEqual(set(parties['records']), set(winners))
        self.assertEqual(len(parties['partyLabels']), 16)
        self.assertEqual(parties['totals']['national']['validVotes'], 2591896)

    def test_candidate_only_zero_is_preserved(self):
        result = overall_table(self.raw('overall-results-summary.csv'))
        climate = next(p for p in result['parties'] if p['name'] == 'Climate First')
        self.assertEqual(climate['partyVotes'], 0)
        self.assertEqual(climate['candidateVotes'], 55)
        self.assertEqual(climate['sourceGroup'], 'Unregistered Parties')
        self.assertEqual(result['validCandidateVotes'], 2529531)

    def test_candidate_mutations_rejected(self):
        raw = self.raw('candidate-votes-by-voting-place-1.csv')
        for old, new in [(b'majority 1581', b'majority 1582'),
                         (b'"20"', b'"-20"'),
                         (b'45.25', b'55.25')]:
            # Some numeric cells are unquoted in the official CSV.
            if old not in raw and old == b'"20"':
                old, new = b',20,1,32,', b',-20,1,32,'
            self.assertIn(old, raw)
            with self.subTest(old=old), self.assertRaises(ValueError):
                candidate_table(raw.replace(old, new, 1))

    def test_missing_party_count_rejected(self):
        raw = self.raw('votes-for-registered-parties-by-electorate.csv')
        self.assertIn(b',317,71,', raw)
        with self.assertRaises(ValueError):
            party_table(raw.replace(b',317,71,', b',,71,', 1))


if __name__ == '__main__':
    unittest.main()
