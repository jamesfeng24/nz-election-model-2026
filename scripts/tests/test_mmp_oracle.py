"""Official seat-table oracle regenerates from preserved raw CSVs and matches known sizes."""
import json
import unittest
from scripts.mmp import oracle


class MmpOracleTests(unittest.TestCase):
    def test_committed_oracle_regenerates_byte_for_byte(self):
        self.assertEqual(oracle.OUT.read_text(encoding='utf-8'), oracle.render(oracle.build()))

    def test_known_parliament_sizes_and_totals(self):
        data = json.loads(oracle.OUT.read_text(encoding='utf-8'))
        sizes = {e['year']: e['officialParliamentSize'] for e in data['elections']}
        self.assertEqual(sizes, {2008: 122, 2011: 121, 2014: 121, 2017: 120, 2020: 120, 2023: 122})
        for e in data['elections']:
            self.assertEqual(e['constituencySeatsOutsidePartyBallot'], 0)
            self.assertTrue(all(p['partyVotes'] >= 0 for p in e['listedParties']))

    def test_parser_distinguishes_unlisted_parties(self):
        raw = ("Summary\nRegistered Parties with List\n"
               "A,3,100,50.0,5,1,90,50.0,5\nB,,,,,2,40,20.0,1\nUnregistered Parties\nIndependent,0,0,0,0,1,5,.1,1\n").encode()
        parsed = oracle.parse_summary(raw)
        self.assertEqual(parsed['listedParties'], [
            {'partyName': 'A', 'partyVotes': 100, 'officialListSeats': 3, 'constituencySeats': 1}])
        self.assertEqual(parsed['constituencySeatsOutsidePartyBallot'], 3)


if __name__ == '__main__':
    unittest.main()
