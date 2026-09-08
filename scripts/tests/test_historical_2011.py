"""Regression/mutation checks on preserved official inputs; mutations are temporary test fixtures."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from scripts.transform.historical import build_year

ROOT = Path(__file__).resolve().parents[2]


class Historical2011Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build_year(ROOT, 2011)

    def test_committed_outputs_regenerate_exactly(self):
        for kind, path in {'elections':'elections/2011.json', 'split':'split-votes/2011.json', 'validation':'elections/2011-validation.json'}.items():
            expected = (json.dumps(self.outputs[kind], ensure_ascii=False, indent=2)+'\n').encode()
            self.assertEqual((ROOT/'data/processed'/path).read_bytes(), expected)
        report = self.outputs['validation']
        self.assertEqual((report['generalElectorates'],report['candidateRecords'],report['partyVoteRecords'],report['splitMatrices']), (63,423,819,63))
        self.assertEqual(report['discrepancies'], [])

    def test_unicode_and_unavailable_joint_counts(self):
        names = {p['partyName'] for e in self.outputs['elections']['electorates'] for p in e['parties']}
        self.assertIn('Māori Party', names)
        for m in self.outputs['split']['matrices']:
            for row in m['rows']:
                self.assertTrue(all(c['count'] is None for c in row['cells']))
        self.assertTrue(all(c['personId'] is None for e in self.outputs['elections']['electorates'] for c in e['candidates']))

    def test_exact_aggregate_summary_is_not_joint_count_imputation(self):
        rows = self.outputs['split']['officialSplitSummary']['rows']
        act = next(r for r in rows if r['partyLabel'] == 'ACT New Zealand')
        self.assertEqual(act['nonSplitCandidateVotes'],4784)
        self.assertEqual(rows[-1]['totalPartyVotes'],2257336)

    def assert_mutation_rejected(self, relative, old, new, message):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT/'data/raw/elections/2011', root/'data/raw/elections/2011')
            registry = json.loads((ROOT/'data/sources.json').read_text())
            path = root/'data/raw/elections/2011'/relative
            raw = path.read_bytes()
            self.assertIn(old, raw)
            mutated = raw.replace(old,new,1)
            path.write_bytes(mutated)
            for record in registry['sources']:
                if record['rawPath'] == path.relative_to(root).as_posix():
                    record['sha256'] = hashlib.sha256(mutated).hexdigest()
            (root/'data/sources.json').write_text(json.dumps(registry))
            with self.assertRaisesRegex(ValueError,message):
                build_year(root,2011)

    def test_wrong_winner_vote_is_rejected(self):
        self.assert_mutation_rejected('e9/csv/e9_part6.csv',b'15038',b'15039','Official winner')

    def test_negative_party_count_is_rejected(self):
        self.assert_mutation_rejected('e9/csv/e9_part4.csv',b'"Auckland Central",404',b'"Auckland Central",-404','Missing or invalid count')

    def test_split_rounding_violation_is_rejected(self):
        self.assert_mutation_rejected('elect-splitvote-1.csv',b'12.87',b'22.87','rounding')

    def test_exact_summary_count_change_is_rejected(self):
        self.assert_mutation_rejected('elect-splitvote-summary.csv',b'4784',b'4785','summary count sum')
