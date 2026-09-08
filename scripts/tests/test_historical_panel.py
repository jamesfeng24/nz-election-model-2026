"""Real preserved data regression tests; mutations are synthetic and never exported."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from scripts.transform.historical_panel import YEARS, DEST, build_panel, canonical, encode, validate_panel

ROOT = Path(__file__).resolve().parents[2]


class HistoricalPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build_panel(ROOT)
        cls.panel = {k[:-5]: v['records'] for k, v in cls.outputs.items() if k != 'manifest.json'}

    def test_committed_panel_and_determinism(self):
        rebuilt = build_panel(ROOT)
        for name, value in self.outputs.items():
            self.assertEqual(encode(value), encode(rebuilt[name]))
            self.assertEqual((ROOT / DEST / name).read_bytes(), encode(value))
        for path, digest in self.outputs['manifest.json']['inputSha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)

    def test_lossless_projection_and_precision(self):
        for year in YEARS:
            election = json.loads((ROOT / f'data/processed/elections/{year}.json').read_bytes())
            split = json.loads((ROOT / f'data/processed/split-votes/{year}.json').read_bytes())
            self.assertEqual([m for m in self.panel['split-votes'] if m['year'] == year], split['matrices'])
            control = next(c for c in self.panel['election-controls'] if c['year'] == year)
            self.assertEqual(control['nationalControls'], election['nationalControls'])
            for key in ('aggregateMatrices', 'officialSplitSummary', 'partyGrouping'):
                self.assertEqual(control[key], split.get(key))
            for e in election['electorates']:
                meta = next(r for r in self.panel['electorates'] if r['id'] == e['id'])
                self.assertEqual(meta, {k: v for k, v in e.items() if k not in ('parties', 'candidates')})
                for kind, field in [('party-votes', 'parties'), ('candidate-votes', 'candidates')]:
                    actual = [r for r in self.panel[kind] if r['electorateId'] == e['id']]
                    self.assertEqual(len(actual), len(e[field]))
                    for old, new in zip(e[field], actual):
                        self.assertEqual(old, {k: new[k] for k in old})
                        self.assertEqual(new['sourceIds'], e['sourceIds'])

    def test_party_identity_and_2014_affiliations(self):
        self.assertEqual(canonical('conservativeparty'), canonical('conservative'))
        self.assertEqual(canonical('mana'), canonical('manamovement'))
        self.assertIsNone(canonical('independent'))
        self.assertEqual(len({canonical(k) for k in ('internetmana', 'internetparty', 'manamovement')}), 3)
        rows = [c for c in self.panel['candidate-votes'] if c['year'] == 2014 and c['party'] in ('Internet Party', 'MANA Movement')]
        self.assertTrue(rows)
        self.assertTrue(all(c['canonicalPartyId'] != 'internetmana' for c in rows))
        self.assertTrue(any('Māori' in c['party'] for c in self.panel['candidate-votes']))
        self.assertIsNone(self.panel['election-controls'][0]['aggregateMatrices'])
        self.assertEqual(self.panel['election-controls'][0]['aggregateSplitAvailability'], 'not-collected')

    def test_reject_corrupt_integrations(self):
        mutations = [
            lambda p: p['party-votes'][0].update(votes=-1),
            lambda p: p['party-votes'][0].update(share=0.8),
            lambda p: p['candidate-votes'][0].update(personId='guessed-person'),
            lambda p: p['candidate-votes'][0].update(id=p['candidate-votes'][1]['id']),
            lambda p: p['electorates'][0].update(winnerCandidateId='wrong'),
            lambda p: p['split-votes'][0]['rows'][0]['cells'][0].update(count=10),
            lambda p: p['split-votes'][0].update(year=2017),
            lambda p: p['party-votes'][0].update(canonicalPartyId='invented'),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                panel = copy.deepcopy(self.panel)
                mutation(panel)
                with self.assertRaises(ValueError):
                    validate_panel(panel)


if __name__ == '__main__':
    unittest.main()
