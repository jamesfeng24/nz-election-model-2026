"""Full 2017 regression and semantic failures against temporary source copies."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.transform.modern_election import build_year, encode

ROOT = Path(__file__).resolve().parents[2]


class Historical2017Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build_year(ROOT)

    def test_deterministic_complete_outputs(self):
        paths = {'elections': 'elections/2017.json', 'validation': 'elections/2017-validation.json',
                 'split': 'split-votes/2017.json'}
        for kind, path in paths.items():
            self.assertEqual((ROOT/'data/processed'/path).read_bytes(), encode(self.outputs[kind]))
        report = self.outputs['validation']
        self.assertEqual((report['generalElectorates'], report['supportingMaoriElectorates'],
                          report['candidateRecords'], report['partyVoteRecords'], report['splitMatrices']),
                         (64, 7, 431, 1024, 64))
        self.assertEqual(report['discrepancies'], [])

    def test_entire_acquired_inventory_consumed_with_provenance(self):
        sources = [s for s in json.loads((ROOT/'data/sources.json').read_text())['sources']
                   if s['dateOrElection'] == '2017 general election']
        self.assertEqual(len(sources), 145)
        self.assertEqual(self.outputs['validation']['sourceFilesConsumed'], len(sources))
        ids = {s['id'] for s in sources}
        referenced = set(self.outputs['elections']['sourceIds'])
        split = self.outputs['split']
        for matrix in split['matrices'] + list(split['aggregateMatrices'].values()):
            referenced.update(matrix['sourceIds'])
        referenced.update(split['officialSplitSummary']['sourceIds'])
        self.assertEqual(referenced, ids)
        for source in sources:
            self.assertEqual(hashlib.sha256((ROOT/source['rawPath']).read_bytes()).hexdigest(), source['sha256'])

    def test_identity_unicode_and_precision(self):
        electorates = self.outputs['elections']['electorates']
        self.assertIn('Kaikōura', {e['name'] for e in electorates})
        candidates = [c for e in electorates for c in e['candidates']]
        self.assertEqual(len({c['id'] for c in candidates}), len(candidates))
        self.assertTrue(all(c['personId'] is None for c in candidates))
        for electorate in electorates:
            winners = [c for c in electorate['candidates'] if c['elected']]
            self.assertEqual([c['id'] for c in winners], [electorate['winnerCandidateId']])
        for matrix in self.outputs['split']['matrices']:
            self.assertEqual(matrix['precision']['representation'], 'rounded-percentage')
            self.assertTrue(all(c['count'] is None for r in matrix['rows'] for c in r['cells']))

    def temporary_sources(self, root):
        shutil.copytree(ROOT/'data/raw/elections/2017', root/'data/raw/elections/2017')
        (root/'data/source-plans').mkdir()
        shutil.copy2(ROOT/'data/source-plans/historical-2017.json', root/'data/source-plans/historical-2017.json')
        return json.loads((ROOT/'data/sources.json').read_text())

    def assert_source_mutation(self, filename, old, new, message, update_checksum=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.temporary_sources(root)
            path = root/'data/raw/elections/2017/statistics/csv'/filename
            raw = path.read_bytes()
            self.assertIn(old, raw)
            raw = raw.replace(old, new, 1)
            path.write_bytes(raw)
            if update_checksum:
                for source in registry['sources']:
                    if source['rawPath'] == path.relative_to(root).as_posix():
                        source['sha256'] = hashlib.sha256(raw).hexdigest()
            (root/'data/sources.json').write_text(json.dumps(registry))
            with self.assertRaisesRegex(ValueError, message):
                build_year(root)

    def test_changed_official_winner_rejected(self):
        self.assert_source_mutation('winning-electorate-candidates.csv', b',13198,1581,', b',13199,1581,', 'Official winner')

    def test_missing_count_is_not_zero(self):
        self.assert_source_mutation('votes-for-registered-parties-by-electorate.csv', b'Auckland Central,317,71,', b'Auckland Central,,71,', 'Missing or invalid count')

    def test_negative_count_rejected(self):
        self.assert_source_mutation('votes-for-registered-parties-by-electorate.csv', b'Auckland Central,317,71,', b'Auckland Central,-317,71,', 'Missing or invalid count')

    def test_checksum_mutation_rejected_before_parsing(self):
        self.assert_source_mutation('winning-electorate-candidates.csv', b',13198,1581,', b',13199,1581,', 'Raw hash mismatch', False)

    def test_split_semantic_mutation_rejected(self):
        self.assert_source_mutation('split-votes-electorate-1.csv', b',19.87,', b',29.87,', 'rounding')

    def test_ambiguous_plan_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.temporary_sources(root)
            (root/'data/sources.json').write_text(json.dumps(registry))
            path = root/'data/source-plans/historical-2017.json'
            plan = json.loads(path.read_text())
            entries = [e for e in plan['resources'] if e['role'] == 'general candidate']
            entries[1]['sourceElectorateNumber'] = entries[0]['sourceElectorateNumber']
            path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, 'plan coverage'):
                build_year(root)


if __name__ == '__main__':
    unittest.main()
