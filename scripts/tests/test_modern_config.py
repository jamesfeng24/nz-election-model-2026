"""Year configuration and a preserved 2020 sample through shared orchestration."""
import json
from pathlib import Path
import unittest

from scripts.transform.historical import key
from scripts.transform.modern_config import election_config
from scripts.transform.modern_election import Sources, make_electorate
from scripts.transform.modern_tables import party_table, turnout_table, winners_table

ROOT = Path(__file__).resolve().parents[2]


class ModernConfigTests(unittest.TestCase):
    def test_only_inspected_elections_are_supported(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported modern election'):
            election_config(2023)
        self.assertEqual(election_config(2017).total_electorates, 71)
        self.assertEqual(election_config(2020).total_electorates, 72)

    def test_sources_are_election_scoped(self):
        old = Sources(ROOT)
        new = Sources(ROOT, 2020)
        for source, year in ((old, 2017), (new, 2020)):
            _, source_id = source('overall-results-summary.csv')
            self.assertIn(f'ec-{year}-', source_id)
            self.assertEqual(source.config.year, year)

    def test_2020_sample_has_election_local_identity(self):
        source = Sources(ROOT, 2020)
        plan = json.loads((ROOT / source.config.source_plan).read_text())
        entry = next(e for e in plan['resources'] if e['role'] == 'general candidate')
        party_ballots, _ = turnout_table(source('party-votes-and-turnout-by-electorate.csv')[0])
        candidate_ballots, _ = turnout_table(source('candidate-votes-and-turnout-by-electorate.csv')[0])
        parties = party_table(source('votes-for-registered-parties-by-electorate.csv')[0])
        winners = winners_table(source('winning-electorate-candidates.csv')[0])
        name = entry['electorateName']
        result = make_electorate(
            entry, next(b for b in party_ballots if b['name'] == name),
            next(b for b in candidate_ballots if b['name'] == name),
            parties['records'][key(name)], winners[key(name)], source, [],
            [b['name'] for b in party_ballots],
        )
        self.assertEqual(result['year'], 2020)
        self.assertEqual(result['boundaryVersionId'], 'historical-election-2020-as-published')
        self.assertTrue(result['id'].startswith('nz-general-2020-electorate-'))
        self.assertTrue(all(c['id'].startswith(result['id']) and c['personId'] is None for c in result['candidates']))


if __name__ == '__main__':
    unittest.main()
