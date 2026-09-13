"""Real-source 2023 regression checks, including fail-closed publication exceptions."""
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from fractions import Fraction
from scripts.transform.modern_election import build_year, build_core, encode
from scripts.transform.split_intervals import SourceDiscrepancies

ROOT = Path(__file__).resolve().parents[2]


class Historical2023Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = build_year(ROOT,2023)
        cls.core, cls.all_electorates = build_core(ROOT,year=2023)

    def mutate(self, filename, change, checksum=True):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copytree(ROOT/'data/raw/elections/2023',root/'data/raw/elections/2023')
            shutil.copytree(ROOT/'data/source-plans',root/'data/source-plans')
            registry=json.loads((ROOT/'data/sources.json').read_text())
            record=next(s for s in registry['sources'] if s['dateOrElection']=='2023 general election' and Path(s['rawPath']).name==filename)
            path=root/record['rawPath']
            raw=path.read_bytes()
            rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
            change(rows)
            out=io.StringIO(newline='');csv.writer(out).writerows(rows)
            path.write_bytes(out.getvalue().encode('utf-8'))
            if checksum:record['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            (root/'data/sources.json').write_text(json.dumps(registry))
            return build_year(root,2023)

    def test_counts_and_controls(self):
        report=self.output['validation']
        self.assertEqual((report['sourceFilesConsumed'],report['generalElectorates'],report['supportingMaoriElectorates'],report['candidateRecords'],report['partyVoteRecords']),(147,65,7,468,1105))
        self.assertEqual(len(self.all_electorates),72)
        self.assertEqual(sum(e['candidateContestStatus']=='held' for e in self.all_electorates),71)
        for e in self.all_electorates:
            self.assertEqual(sum(p['votes'] for p in e['parties']),e['validPartyVotes'])
            self.assertEqual(sum(c['votes'] for c in e['candidates']),e['validCandidateVotes'])
            if e['candidateContestStatus']=='held':
                self.assertEqual(sum(c['elected'] for c in e['candidates']),1)
                self.assertAlmostEqual(sum(c['share'] for c in e['candidates']),1)
        self.assertEqual(sum(e['validPartyVotes'] for e in self.all_electorates),2851211)

    def test_cancelled_outcomes_are_unavailable(self):
        cancelled=[e for e in self.all_electorates if e['candidateContestStatus']=='cancelled']
        self.assertEqual([e['name'] for e in cancelled],['Port Waikato'])
        e=cancelled[0]
        self.assertEqual(e['validPartyVotes'],42399)
        self.assertEqual(len(e['candidates']),9)
        self.assertIsNone(e['winnerCandidateId']);self.assertIsNone(e['majority'])
        for c in e['candidates']:
            self.assertIsNone(c['share']);self.assertIsNone(c['sourceShare']);self.assertIsNone(c['elected'])
            self.assertEqual(c['votes'],0)

    def test_no_person_linking_and_original_affiliations(self):
        candidates=[c for e in self.all_electorates for c in e['candidates']]
        self.assertTrue(all(c['personId'] is None for c in candidates))
        self.assertEqual(len({c['id'] for c in candidates}),len(candidates))
        self.assertTrue({'Vision New Zealand','NZ Outdoors & Freedom Party','Rock the Vote NZ'} <= {c['party'] for c in candidates})
        self.assertEqual(len(self.output['validation']['labelMappings']),2)

    def test_split_coverage_precision_and_summary(self):
        split=self.output['split'];self.assertEqual(len(split['matrices']),65)
        self.assertEqual(sum(m.get('behaviouralEvidence') is False for m in split['matrices']),1)
        self.assertEqual(set(split['aggregateMatrices']),{'general','maori','national'})
        for m in split['matrices']+list(split['aggregateMatrices'].values()):
            self.assertTrue(all(c['count'] is None for r in m['rows'] for c in r['cells']))
        total=split['officialSplitSummary']['rows'][-1]
        self.assertEqual((total['totalPartyVotes'],total['nonSplitCandidateVotes'],total['splitCandidateVotes']),(2867478,1849366,1018112))

    def test_impossible_interval_is_exposed_not_rescaled(self):
        report=self.output['validation']
        self.assertEqual(report['splitStatus'],'validated-with-source-discrepancies')
        self.assertEqual(len(report['discrepancies']),21)
        r=next(r for r in report['discrepancies'] if r['id']=='local-general:Te Pāti Māori:Party Vote Only')
        self.assertEqual(Fraction(r['minimumGapVotes']),Fraction('38.84245'))
        table=self.output['split']['aggregateMatrices']['general']
        row=next(r for r in table['rows'] if r['partyLabel']=='Te Pāti Māori')
        self.assertEqual(row['totalPartyVotes'],29607)
        self.assertEqual(row['cells'][-1]['reportedPercent'],6.69)
        self.assertEqual(table['cancelledContestAllocation']['partyVotesIncludedInPublishedDenominator'],42657)

    def test_exception_fingerprint_changes_fail(self):
        expected=self.output['validation']['discrepancies']
        r=expected[0];left=tuple(map(Fraction,r['leftInterval']));right=tuple(map(Fraction,r['rightInterval']))
        with self.assertRaisesRegex(ValueError,'Unreviewed'):
            SourceDiscrepancies(expected).compare(r['id'],(left[0]+1,left[1]+1),right,r['sourceIds'])
        with self.assertRaisesRegex(ValueError,'inventory changed'):SourceDiscrepancies(expected).finish()

    def test_changed_winner_rejected(self):
        def change(rows):rows[2][3]=str(int(rows[2][3])+1)
        with self.assertRaisesRegex(ValueError,'Official winner'):self.mutate('winning-electorate-candidates.csv',change)

    def test_fake_cancelled_winner_rejected(self):
        def change(rows):
            row=rows[2].copy();row[0]='Port Waikato';rows.append(row)
        with self.assertRaisesRegex(ValueError,'winner coverage'):self.mutate('winning-electorate-candidates.csv',change)

    def test_negative_and_missing_votes_rejected(self):
        for value in ('-1',''):
            def change(rows):rows[2][1]=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.mutate('votes-for-registered-parties-by-electorate.csv',change)

    def test_changed_party_aggregate_rejected(self):
        def change(rows):rows[2][1]=str(int(rows[2][1])+1)
        with self.assertRaises(ValueError):self.mutate('votes-for-registered-parties-by-electorate.csv',change)

    def test_checksum_change_rejected(self):
        def change(rows):rows[2][3]=str(int(rows[2][3])+1)
        with self.assertRaisesRegex(ValueError,'Raw hash mismatch'):self.mutate('winning-electorate-candidates.csv',change,False)

    def test_changed_split_evidence_rejected(self):
        def change(rows):
            row=next(r for r in rows if r and r[0]=='Te Pāti Māori');row[-2]='6.70'
        with self.assertRaises(ValueError):self.mutate('split-votes-general.csv',change)

    def test_deterministic_committed_outputs(self):
        for kind,value in self.output.items():
            path=ROOT/('data/processed/split-votes/2023.json' if kind=='split' else 'data/processed/elections/2023'+('-validation' if kind=='validation' else '')+'.json')
            self.assertEqual(path.read_bytes(),encode(value))
