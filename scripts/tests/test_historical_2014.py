"""Focused 2014 regression checks; all mutated data stays in temporary test copies."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from scripts.transform.historical import build_year, split_party_key

ROOT = Path(__file__).resolve().parents[2]


class Historical2014Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build_year(ROOT, 2014)

    def test_2014_source_inventory_and_checksums(self):
        sources = [s for s in json.loads((ROOT/'data/sources.json').read_text())['sources'] if s['dateOrElection'] == '2014 general election']
        self.assertEqual(len(sources),145)
        for s in sources:
            self.assertEqual(hashlib.sha256((ROOT/s['rawPath']).read_bytes()).hexdigest(),s['sha256'])

    def test_outputs_regenerate_and_coverage_reconciles(self):
        for kind, path in {'elections':'elections/2014.json','split':'split-votes/2014.json','validation':'elections/2014-validation.json'}.items():
            expected=(json.dumps(self.outputs[kind],ensure_ascii=False,indent=2)+'\n').encode()
            self.assertEqual((ROOT/'data/processed'/path).read_bytes(),expected)
        r=self.outputs['validation']
        self.assertEqual((r['generalElectorates'],r['candidateRecords'],r['partyVoteRecords'],r['splitMatrices']),(64,451,960,64))
        self.assertEqual(r['discrepancies'],[])

    def test_split_grouping_does_not_replace_candidate_affiliation(self):
        e=self.outputs['elections']['electorates'][0]
        c=next(c for c in e['candidates'] if c['name'].startswith('PIERARD'))
        self.assertEqual(c['party'],'Internet Party')
        self.assertEqual(c['partyKey'],'internetparty')
        cell=next(c for c in self.outputs['split']['matrices'][0]['rows'][0]['cells'] if c['candidateLabel'].startswith('PIERARD'))
        self.assertEqual(cell['candidateId'],c['id'])
        self.assertIn('(Internet MANA)',cell['candidateLabel'])
        self.assertEqual(split_party_key('manamovement',2014),'internetmana')
        self.assertEqual(split_party_key('internetparty',2011),'internetparty')
        national={p['name']:p for p in self.outputs['elections']['nationalControls']['parties']}
        self.assertEqual(national['Internet Party']['candidateVotes'],4848)
        self.assertEqual(national['MANA Movement']['candidateVotes'],32333)
        self.assertEqual(national['Internet MANA']['candidateVotes'],0)

    def test_unicode_source_aliases_and_missingness_preserved(self):
        names={e['name'] for e in self.outputs['elections']['electorates']}
        self.assertIn('Kaikōura',names)
        e=next(e for e in self.outputs['elections']['electorates'] if e['name']=='Wellington Central')
        c=next(c for c in e['candidates'] if c['name']=='KARENA WHUIMAONO, Geoffrey')
        self.assertEqual(c['votes'],52)
        self.assertIsNone(c['personId'])
        for m in self.outputs['split']['matrices']:
            for r in m['rows']:
                self.assertTrue(all(c['count'] is None for c in r['cells']))
        summary=self.outputs['split']['officialSplitSummary']['rows']
        self.assertEqual(next(r for r in summary if r['partyLabel']=='ACT New Zealand')['nonSplitCandidateVotes'],4279)

    def assert_mutation_rejected(self,relative,old,new,message):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copytree(ROOT/'data/raw/elections/2014',root/'data/raw/elections/2014')
            registry=json.loads((ROOT/'data/sources.json').read_text())
            p=root/'data/raw/elections/2014'/relative
            raw=p.read_bytes()
            self.assertIn(old,raw)
            raw=raw.replace(old,new,1)
            p.write_bytes(raw)
            for s in registry['sources']:
                if s['rawPath']==p.relative_to(root).as_posix():
                    s['sha256']=hashlib.sha256(raw).hexdigest()
            (root/'data/sources.json').write_text(json.dumps(registry))
            with self.assertRaisesRegex(ValueError,message):
                build_year(root,2014)

    def test_bad_split_percentage_rejected(self):
        self.assert_mutation_rejected('elect-splitvote-1.csv',b'25.84',b'35.84','rounding')

    def test_wrong_winner_rejected(self):
        self.assert_mutation_rejected('e9/csv/e9_part6.csv',b'12494',b'12495','Official winner')

    def test_missing_party_count_not_zero_filled(self):
        self.assert_mutation_rejected('e9/csv/e9_part4.csv',b'"Auckland Central",329',b'"Auckland Central",','Missing or invalid count')
