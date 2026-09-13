"""Six-election panel contracts, source preservation and failure boundaries."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.transform.historical_panel import build_panel, validate_panel, encode, verify_legacy_slice
from scripts.transform.panel_config import YEARS, COUNTS, CONTRACT, canonical

ROOT=Path(__file__).resolve().parents[2]


class FullPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs=build_panel(ROOT)
        cls.panel={name[:-5]:value['records'] for name,value in cls.outputs.items() if name!='manifest.json'}

    def reject(self, mutation):
        panel=copy.deepcopy(self.panel)
        mutation(panel)
        with self.assertRaises(ValueError):validate_panel(panel)

    def test_exact_coverage_and_per_year_counts(self):
        self.assertEqual(YEARS,(2008,2011,2014,2017,2020,2023))
        counts=self.outputs['manifest.json']['recordCounts']
        self.assertEqual(counts,{'electorates':384,'party-votes':6210,'candidate-votes':2833,'split-votes':384,'election-controls':6})
        for y,expected in COUNTS.items():
            self.assertEqual(tuple(sum(r['year']==y for r in self.panel[k]) for k in ('electorates','party-votes','candidate-votes')),expected)

    def test_deterministic_order_and_election_local_identities(self):
        electorates=self.panel['electorates']
        order=[(e['year'],e['sourceElectorateNumber']) for e in electorates]
        self.assertEqual(order,sorted(order))
        self.assertEqual(len({e['electionId'] for e in electorates}),6)
        self.assertEqual(len({e['boundaryVersionId'] for e in electorates}),6)
        candidates=self.panel['candidate-votes']
        self.assertEqual(len({c['id'] for c in candidates}),2833)
        self.assertTrue(all(c['personId'] is None and c['id'].startswith(c['electorateId']+'-candidate-') for c in candidates))
        for records in self.panel.values():self.assertEqual([r['year'] for r in records],sorted(r['year'] for r in records))

    def test_held_and_cancelled_contests(self):
        cancelled=[e for e in self.panel['electorates'] if e.get('candidateContestStatus','held')=='cancelled']
        self.assertEqual([(e['year'],e['name']) for e in cancelled],[(2023,'Port Waikato')])
        e=cancelled[0];self.assertEqual(e['validPartyVotes'],42399)
        self.assertIsNone(e['winnerCandidateId']);self.assertIsNone(e['majority'])
        candidates=[c for c in self.panel['candidate-votes'] if c['electorateId']==e['id']]
        self.assertEqual(len(candidates),9)
        self.assertTrue(all(c['votes']==0 and c['share'] is None and c['elected'] is None for c in candidates))
        matrices=self.panel['split-votes']
        self.assertEqual(sum(m.get('behaviouralEvidence',True) for m in matrices),383)
        self.assertEqual(sum(m.get('behaviouralEvidence') is False for m in matrices),1)

    def test_all_split_evidence_layers_preserved(self):
        for control in self.panel['election-controls']:
            y=control['year'];original=json.loads((ROOT/f'data/processed/split-votes/{y}.json').read_bytes())
            for key,value in original.items():
                if key not in ('schemaVersion','year','matrices'):self.assertEqual(control[key],value)
        old=self.panel['election-controls'][0]
        self.assertIsNone(old['aggregateMatrices']);self.assertIsNone(old['officialSplitSummary'])
        self.assertEqual(old['aggregateSplitAvailability'],'not-collected')
        control=next(c for c in self.panel['election-controls'] if c['year']==2020)
        self.assertEqual(len(control['supportingMatrices']),1)

    def test_known_discrepancy_propagates_exactly(self):
        source=json.loads((ROOT/'data/processed/elections/2023-validation.json').read_bytes())
        manifest=self.outputs['manifest.json'];control=self.panel['election-controls'][-1]
        self.assertEqual(len(source['discrepancies']),21)
        self.assertEqual(manifest['knownSourceDiscrepancies'],source['discrepancies'])
        self.assertEqual(control['sourceDiscrepancies'],source['discrepancies'])
        self.assertEqual(control['perYearValidation']['splitStatus'],'validated-with-source-discrepancies')
        self.assertEqual(control['aggregateMatrices']['general']['cancelledContestAllocation']['partyVotesIncludedInPublishedDenominator'],42657)

    def test_rename_aliases_preserve_original_labels(self):
        for left,right in [('newconservative','conservative'),('newconservatives','conservative'),('tepatimaori','maoriparty'),('newzeal','oneparty'),('nzoutdoorsfreedomparty','nzoutdoorsparty'),('socialcredit','democratsforsocialcredit')]:
            self.assertEqual(canonical(left),canonical(right))
        for a,b in [('internetparty','internetmana'),('manamovement','internetmana'),('nzpublicparty','advancenz'),('nzoutdoorsfreedomparty','freedomsnz'),('visionnewzealand','freedomsnz'),('theopportunitiespartytop','opportunity')]:
            self.assertNotEqual(canonical(a),canonical(b))
        maori=[r for r in self.panel['party-votes'] if r['year']==2023 and r['partyKey']=='tepatimaori']
        self.assertEqual(len(maori),65)
        self.assertTrue(all(r['partyName']=='Te Pāti Māori' and r['canonicalPartyId']=='maoriparty' for r in maori))

    def test_manifest_hashes_and_legacy_projection(self):
        manifest=self.outputs['manifest.json']
        self.assertEqual(len(manifest['inputSha256']),18)
        for name,digest in manifest['outputSha256'].items():self.assertEqual(hashlib.sha256(encode(self.outputs[name])).hexdigest(),digest)
        for path,digest in manifest['integrationCodeSha256'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        contract=json.loads((ROOT/CONTRACT).read_bytes())
        compatibility=verify_legacy_slice(self.outputs,contract)
        self.assertEqual(len(compatibility['outputSha256']),6)
        self.assertEqual(compatibility['status'],'byte-identical serialized subsets')
        for name,digest in compatibility['outputSha256'].items():self.assertEqual(digest,contract['legacyPanel'][name]['sha256'])

    def test_bad_foreign_keys_and_duplicates_rejected(self):
        for mutation in [lambda p:p['candidate-votes'][-1].update(electorateId=p['electorates'][0]['id']),lambda p:p['party-votes'][0].update(electionId='nz-general-2023'),lambda p:p['split-votes'][-1]['rows'][0]['cells'][0].update(candidateId=p['candidate-votes'][0]['id']),lambda p:p['electorates'][0].update(id=p['electorates'][1]['id'])]:
            self.reject(mutation)

    def test_missingness_and_cancelled_mutations_rejected(self):
        eid='nz-general-2023-electorate-39'
        def fake_winner(p):next(e for e in p['electorates'] if e['id']==eid)['winnerCandidateId']=eid+'-candidate-01'
        def fake_share(p):next(c for c in p['candidate-votes'] if c['electorateId']==eid)['share']=0
        def fake_behaviour(p):next(m for m in p['split-votes'] if m['electorateId']==eid)['behaviouralEvidence']=True
        for mutation in [fake_winner,fake_share,fake_behaviour,lambda p:p['election-controls'][0].update(aggregateMatrices=0),lambda p:p['candidate-votes'][0].update(personId='guessed')]:self.reject(mutation)

    def test_new_discrepancy_or_false_resolution_rejected(self):
        self.reject(lambda p:p['election-controls'][-1]['perYearValidation']['discrepancies'].append({'id':'new'}))
        self.reject(lambda p:p['election-controls'][-1].update(sourceDiscrepancies=[]))

    def test_corrupt_share_boundary_alias_and_denominator_rejected(self):
        for mutation in [lambda p:p['party-votes'][0].update(share=.5),lambda p:p['electorates'][0].update(validPartyVotes=1),lambda p:p['electorates'][0].update(boundaryVersionId='constant-boundaries'),lambda p:p['candidate-votes'][-1].update(canonicalPartyId='freedomsnz')]:self.reject(mutation)

    def test_processed_input_mutation_rejected_before_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for relative in ('data/source-plans','data/processed/elections','data/processed/split-votes'):
                shutil.copytree(ROOT/relative,root/relative)
            shutil.copyfile(ROOT/'data/sources.json',root/'data/sources.json')
            path=root/'data/processed/elections/2008.json';path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'Altered per-election input'):build_panel(root)
