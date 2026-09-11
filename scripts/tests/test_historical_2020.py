"""2020 official-data regressions and failures against isolated source copies."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.transform.modern_election import build_core, build_year, encode

ROOT = Path(__file__).resolve().parents[2]


class SourceMutationMixin:
    def temporary_sources(self, root):
        shutil.copytree(ROOT/'data/raw/elections/2020', root/'data/raw/elections/2020')
        (root/'data/source-plans').mkdir()
        shutil.copy2(ROOT/'data/source-plans/historical-2020.json', root/'data/source-plans/historical-2020.json')
        return json.loads((ROOT/'data/sources.json').read_text())

    def assert_source_mutation(self, filename, old, new, message, update_checksum=True, split=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.temporary_sources(root)
            path = root/'data/raw/elections/2020/statistics/csv'/filename
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
                (build_year if split else build_core)(root, year=2020)


class Historical2020CoreTest(SourceMutationMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.election, cls.all_electorates = build_core(ROOT, year=2020)

    def test_general_and_supporting_coverage_and_controls(self):
        general = self.election['electorates']
        self.assertEqual(len(general), 65)
        self.assertEqual(len(self.all_electorates), 72)
        self.assertEqual(sum(e['kind'] == 'maori' for e in self.all_electorates), 7)
        self.assertEqual(sum(len(e['candidates']) for e in general), 561)
        self.assertEqual(sum(len(e['parties']) for e in general), 1105)
        self.assertEqual(sum(len(e['candidates']) for e in self.all_electorates), 601)
        controls = self.election['nationalControls']
        self.assertEqual(controls['party']['national']['validVotes'], 2886420)
        self.assertEqual(controls['candidate']['national']['validVotes'], 2824198)
        self.assertEqual(controls['party']['national']['informalVotes'], 21372)
        self.assertEqual(controls['candidate']['national']['informalVotes'], 57138)
        self.assertEqual(controls['party']['national']['votesCast'], 2919073)

    def test_local_identity_unicode_denominators_and_winners(self):
        candidates = [c for e in self.all_electorates for c in e['candidates']]
        self.assertEqual(len({c['id'] for c in candidates}), len(candidates))
        self.assertTrue(all(c['personId'] is None for c in candidates))
        self.assertIn('SWARBRICK, Chlöe Charlotte', {c['name'] for c in candidates})
        self.assertIn('Kaikōura', {e['name'] for e in self.all_electorates})
        self.assertEqual(len({e['sourceElectorateNumber'] for e in self.all_electorates}), 72)
        for electorate in self.all_electorates:
            self.assertEqual(electorate['year'], 2020)
            self.assertEqual(sum(p['votes'] for p in electorate['parties']), electorate['validPartyVotes'])
            self.assertEqual(sum(c['votes'] for c in electorate['candidates']), electorate['validCandidateVotes'])
            winners = [c for c in electorate['candidates'] if c['elected']]
            self.assertEqual([c['id'] for c in winners], [electorate['winnerCandidateId']])
            ordered = sorted((c['votes'] for c in electorate['candidates']), reverse=True)
            self.assertEqual(ordered[0] - ordered[1], electorate['majority'])
            for candidate in electorate['candidates']:
                self.assertEqual(candidate['share'], candidate['votes'] / electorate['validCandidateVotes'])
            for party in electorate['parties']:
                self.assertEqual(party['share'], party['votes'] / electorate['validPartyVotes'])

    def test_changed_official_winner_rejected(self):
        self.assert_source_mutation('winning-electorate-candidates.csv', b',12631,1068,', b',12632,1068,', 'Official winner')

    def test_changed_official_majority_rejected(self):
        self.assert_source_mutation('winning-electorate-candidates.csv', b',12631,1068,', b',12631,1069,', 'Official majority')

    def test_missing_count_is_not_zero(self):
        self.assert_source_mutation('votes-for-registered-parties-by-electorate.csv', b'Auckland Central,2724,198,', b'Auckland Central,,198,', 'Missing or invalid count')

    def test_negative_count_rejected(self):
        self.assert_source_mutation('votes-for-registered-parties-by-electorate.csv', b'Auckland Central,2724,198,', b'Auckland Central,-2724,198,', 'Missing or invalid count')

    def test_malformed_percentage_rejected(self):
        self.assert_source_mutation('winning-electorate-candidates.csv', b',35.48%,Yes', b',135.48%,Yes', 'percentage')

    def test_national_total_mutation_rejected(self):
        self.assert_source_mutation('overall-results-summary.csv', b',219031,7.59,', b',219032,7.59,', 'Overall vote sum')

    def test_checksum_mutation_rejected_before_parsing(self):
        self.assert_source_mutation('winning-electorate-candidates.csv', b',12631,1068,', b',12632,1068,', 'Raw hash mismatch', False)

    def test_ambiguous_plan_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.temporary_sources(root)
            (root/'data/sources.json').write_text(json.dumps(registry))
            path = root/'data/source-plans/historical-2020.json'
            plan = json.loads(path.read_text())
            entries = [e for e in plan['resources'] if e['role'] == 'general candidate']
            entries[1]['sourceElectorateNumber'] = entries[0]['sourceElectorateNumber']
            path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, 'plan coverage'):
                build_core(root, year=2020)


class Historical2020CompleteTest(SourceMutationMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build_year(ROOT, year=2020)

    def test_deterministic_complete_outputs(self):
        paths = {'elections': 'elections/2020.json', 'validation': 'elections/2020-validation.json',
                 'split': 'split-votes/2020.json'}
        for kind, path in paths.items():
            self.assertEqual((ROOT/'data/processed'/path).read_bytes(), encode(self.outputs[kind]))
        report = self.outputs['validation']
        self.assertEqual(report['sourceFilesConsumed'], 147)
        self.assertEqual(report['splitMatrices'], 65)
        self.assertEqual(report['discrepancies'], [])
        self.assertEqual(report['labelMappings'], [])

    def test_entire_inventory_consumed_with_provenance(self):
        sources = [s for s in json.loads((ROOT/'data/sources.json').read_text())['sources']
                   if s['dateOrElection'] == '2020 general election']
        self.assertEqual(len(sources), 147)
        referenced = set(self.outputs['elections']['sourceIds'])
        split = self.outputs['split']
        for matrix in split['matrices'] + list(split['aggregateMatrices'].values()):
            referenced.update(matrix['sourceIds'])
        referenced.update(split['officialSplitSummary']['sourceIds'])
        self.assertEqual(referenced, {s['id'] for s in sources})
        for source in sources:
            self.assertEqual(hashlib.sha256((ROOT/source['rawPath']).read_bytes()).hexdigest(), source['sha256'])

    def test_split_coverage_and_precision(self):
        split = self.outputs['split']
        self.assertEqual(len(split['matrices']), 65)
        self.assertEqual(len(split['aggregateMatrices']), 3)
        for matrix in split['matrices'] + list(split['aggregateMatrices'].values()):
            self.assertEqual(matrix['precision']['representation'], 'rounded-percentage')
            self.assertFalse(matrix['precision']['exactJointCountsAvailable'])
            self.assertTrue(all(c['count'] is None for r in matrix['rows'] for c in r['cells']))
        summary = split['officialSplitSummary']
        for row in summary['rows']:
            self.assertIsInstance(row['nonSplitCandidateVotes'], int)
            self.assertIsInstance(row['splitCandidateVotes'], int)
            self.assertEqual(row['nonSplitCandidateVotes'] + row['splitCandidateVotes'], row['totalPartyVotes'])

    def test_split_semantic_mutation_rejected(self):
        self.assert_source_mutation('split-votes-electorate-1.csv', b',13.22,', b',23.22,', 'rounding', split=True)


if __name__ == '__main__':
    unittest.main()
