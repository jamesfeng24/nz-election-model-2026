import copy
import unittest
from scripts.models.nat_lab_elasticity.model import fit,predict,chronological_fit
from scripts.models.nat_lab_elasticity.records import build,extract

class ElasticityTests(unittest.TestCase):
    def fixture(self):
        return [{'id':str(i),'party':'nationalparty','scope':'general','sourceYear':2008,'targetYear':2011,'sourceCandidateShare':.3,'targetCandidateShare':.3+.6*x,'sourcePartyShare':.2,'targetPartyShare':.2+x,'deltaParty':x,'deltaCandidate':.6*x,'stage5PredictedTargetParty':{m:.2+x for m in ['additive','proportional','log_odds']}} for i,x in enumerate([-.1,.1,.2])]
    def test_zero_intercept_and_benchmarks(self):
        rows=self.fixture();self.assertAlmostEqual(fit(rows)['beta'],.6)
        for r in rows:
            self.assertAlmostEqual(predict(r,0),.3)
            self.assertAlmostEqual(predict(r,1),.3+r['deltaParty'])
            for m in ['additive','proportional','log_odds']:self.assertAlmostEqual(predict(r,.6,m),r['targetCandidateShare'])
        rows[0]['party']='labourparty'
        with self.assertRaises(ValueError):fit(rows)
    def test_temporal_leakage(self):
        rows=self.fixture();test=copy.deepcopy(rows);test[0]['sourceYear']=2014
        for r in test:r['sourceYear']=2014;r['targetYear']=2017
        self.assertAlmostEqual(chronological_fit(rows,test)['beta'],.6)
        with self.assertRaises(ValueError):chronological_fit(test,rows)
    def test_missing_cancelled_and_corrupt_denominator(self):
        e={'validCandidateVotes':100,'candidates':[{'party':'Other','votes':100,'share':1,'personId':None}]}
        self.assertEqual(extract(e,'nationalparty')[1],'missing_candidacy')
        e['candidateContestStatus']='cancelled';self.assertEqual(extract(e,'nationalparty')[1],'cancelled_contest')
        e['candidateContestStatus']='held';e['validCandidateVotes']=101
        with self.assertRaises(ValueError):extract(e,'nationalparty')
        e['validCandidateVotes']=100;e['candidates'][0]['votes']=0
        with self.assertRaises(ValueError):extract(e,'nationalparty')
    def test_real_eligibility_and_deltas(self):
        d=build();self.assertEqual(len(d['records']),403)
        self.assertEqual({(r['sourceYear'],r['targetYear']) for r in d['records']},{(2008,2011),(2014,2017),(2020,2023)})
        self.assertEqual(sum(r['targetReason']=='cancelled_contest' for r in d['excluded']),2)
        for r in d['records']:
            self.assertFalse(r['personIdentityInferred'])
            self.assertAlmostEqual(r['deltaParty'],r['targetPartyShare']-r['sourcePartyShare'])
            self.assertAlmostEqual(r['deltaCandidate'],r['targetCandidateShare']-r['sourceCandidateShare'])
    def test_changed_boundary_and_person_inference_fail(self):
        from pathlib import Path
        from unittest.mock import patch
        import json
        original=Path.read_bytes
        def changed(path):
            raw=original(path)
            if str(path).endswith('party-vote-transform/backtest-records.json'):
                d=json.loads(raw)
                for r in d['records']:
                    if r['primary'] and r['canonicalPartyId']=='nationalparty':r['boundaryRegime']='wrong';break
                return json.dumps(d).encode()
            return raw
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaises(ValueError):build()
        e={'validCandidateVotes':1,'candidates':[{'party':'National Party','votes':1,'share':1,'personId':'guessed'}]}
        with self.assertRaises(ValueError):extract(e,'nationalparty')
    def test_pinned_mutation_and_determinism(self):
        from pathlib import Path
        from unittest.mock import patch
        from scripts.models.nat_lab_elasticity.run import build as full
        a=full();self.assertEqual(a,full())
        for party in a['fits.json']['general'].values():self.assertEqual(party['full']['n'],191)
        original=Path.read_bytes
        def changed(path):
            raw=original(path)
            return raw+b' ' if str(path).endswith('elections/2023.json') else raw
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaises(ValueError):full()
