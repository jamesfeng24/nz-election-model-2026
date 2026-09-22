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
