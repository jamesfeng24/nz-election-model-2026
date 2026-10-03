"""Full adapters, frozen samples and post-construction arithmetic."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from scripts.models.joint_candidate_share import adapters,numerics,metrics,construction,evaluation
from scripts.models.joint_candidate_share.common import *
from scripts.checkpoints.joint_candidate_share.inventory import build as source_inventory
from scripts.models.expanded_party_substitution.inventory import candidate_frame
from scripts.models.exact_geography_retests import adapters as old_adapter
from scripts.checkpoints import stage25_availability as availability


def synthetic_row():
    return {'candidates':[{'targetOccurrenceId':cid,'partyBallotGroupKey':group,
        'R':{'broad':{'availabilityPattern':'neither_feature'}}} for cid,group in [('a','nationalparty'),('b','labourparty'),('c',None)]]}


class ScoreTests(unittest.TestCase):
    def test_paired_improvement_and_equal_contest_weights(self):
        row=synthetic_row();actual={'candidateShares':{'a':.7,'b':.2,'c':.1},'winnerCandidateId':'a'}
        qs={'baseline':[.5,.3,.2],'baseline_plus_S':[.6,.25,.15],
            'baseline_plus_R':[.65,.225,.125],'baseline_plus_S_plus_R':[.7,.2,.1]}
        scores={m:metrics.score(dict(zip(('a','b','c'),q)),actual,row,'broad') for m,q in qs.items()}
        result=metrics.summary([{'targetElectorateId':'synthetic:1','scores':scores}])
        self.assertAlmostEqual(result['methods']['baseline']['contestEqualMaePP'],40/3)
        self.assertAlmostEqual(result['pairs']['baseline_plus_S_plus_R__versus__baseline_plus_S']['maeImprovementPP'],20/3)
        self.assertAlmostEqual(result['groups']['affirmative_no_party_group']['methods']['baseline']['candidateEqualSignedBiasPP'],10)
        self.assertEqual(result['groups']['R_only']['candidates'],0)
    def test_observed_order_margin_and_ties(self):
        row=synthetic_row();actual={'candidateShares':{'a':.7,'b':.2,'c':.1},'winnerCandidateId':'a'}
        score=metrics.score({'a':.35,'b':.15,'c':.5},actual,row,'broad')
        self.assertAlmostEqual(score['actualTopTwoMarginAbsoluteErrorPP'],30)
        tie=metrics.score(dict.fromkeys(('a','b','c'),1/3),actual,row,'broad')
        self.assertFalse(tie['uniqueCorrect']);self.assertTrue(tie['tieContainsWinner']);self.assertEqual(len(tie['predictedWinnerSet']),3)
    def test_denominator_or_ID_mismatch_rejected(self):
        with self.assertRaises(ValueError):metrics.score({'a':.6,'b':.4},{'candidateShares':{'a':.5,'b':.5},'winnerCandidateId':'a'},synthetic_row(),'broad')


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folds,cls.inventory=adapters.folds_inventory();cls.elections={y:read(p) for y,p in ELECTIONS.items()}
    def test_actual_pipeline_heldout_exclusion(self):
        changed=deepcopy(self.elections)
        for seat in changed[2023]['electorates']:
            seat['winnerCandidateId']=seat['candidates'][-1]['id']
            for c in seat['candidates']:c['votes']+=11;c['winner']=False
            seat['validCandidateVotes']=sum(c['votes'] for c in seat['candidates'])
        # Exercise the Stage27->31->32 feature path, not just cached IDs.
        splits=old_adapter.datasets()[1]
        data=old_adapter.inventory(changed,splits,read(availability.GEO+'geography.json') if hasattr(availability,'GEO') else read('data/processed/checkpoints/stage25-historical-geography/geography.json'),
            read('data/processed/checkpoints/stage25-historical-geography/availability.json'),read(availability.MAPPING),read(availability.CONTINUITY)['records'])
        base=deepcopy(read('data/processed/models/expanded-party-substitution/input-inventory.json'));base['candidateRecords']=candidate_frame(data,read(availability.MAPPING))
        self.assertEqual(source_inventory(base=base),self.inventory)
        f=next(f for f in self.folds if f['branch']=='primary' and f['targetYear']==2023)
        for method in METHODS:self.assertEqual(adapters.prepare(f,self.inventory,self.elections,method),adapters.prepare(f,self.inventory,changed,method))
        cache=local('fit-cache.json')
        # Real complete runner uses the mutated election object, then exact-signature saved fits.
        a=construction.construct([f],self.inventory,self.elections,cache)
        b=construction.construct([f],self.inventory,changed,cache)
        self.assertEqual(a,b)
    def test_earlier_outcomes_legitimately_change_training_signature(self):
        f=next(f for f in self.folds if f['branch']=='primary' and f['targetYear']==2023);changed=deepcopy(self.elections)
        seat=next(s for s in changed[2011]['electorates'] if s['id'] in f['trainingIds']);seat['candidates'][0]['votes']+=1;seat['candidates'][1]['votes']-=1
        a=adapters.prepare(f,self.inventory,self.elections,'baseline_plus_R');b=adapters.prepare(f,self.inventory,changed,'baseline_plus_R')
        self.assertNotEqual(a['signature'],b['signature'])
        with self.assertRaises(ValueError):numerics.checked_saved(b,local('fit-cache.json')[a['signature']])
    def test_independent_restrictions_and_no_fit_cases(self):
        fs=local('construction.json')['folds'];cache=local('fit-cache.json')
        for f in fs:
            self.assertEqual(set(f['fits']),set(METHODS))
            if f['targetYear']==2011 or f['branch']=='separated' and f['targetYear']==2014:
                self.assertTrue(all(not p for p in f['predictions'].values()));continue
            self.assertEqual(len({v['fitId'] for v in f['fits'].values()}),4)
            for method,v in f['fits'].items():
                if v['parameters']['status']=='fitted':self.assertEqual(set(v['parameters']['coefficients']),set(METHODS[method]))
        for year in (2014,2017,2020,2023):
            primary=next(f for f in fs if f['branch']=='primary' and f['targetYear']==year)
            fixed=next(f for f in fs if f['branch']=='primary_fixed_to_observed' and f['targetYear']==year)
            self.assertEqual(primary['fits'],fixed['fits']);self.assertEqual(primary['trainingOnlyMeans'],fixed['trainingOnlyMeans'])
    def test_provenance_and_preservation(self):
        verify_inputs();self.assertEqual(preserve(),1434)
        with patch('scripts.models.joint_candidate_share.common.digest',return_value='corrupt'):
            with self.assertRaises(ValueError):verify_inputs()
    def test_neutral_fallback_complete_prediction(self):
        f=next(f for f in self.folds if f['branch']=='primary' and f['targetYear']==2023)
        train,rows=adapters.fold_rows(f,self.inventory);m='baseline_plus_S_plus_R'
        p=next(c for c in local('construction.json')['folds'] if c['id']==f['id'])['fits'][m]['parameters']
        if p['status']!='fitted':self.skipTest('Explicit numerical abstention')
        predictions=numerics.predict(rows,f,m,p)
        for r,q in zip(rows,predictions):self.assertEqual(set(q['candidateShares']),{c['targetOccurrenceId'] for c in r['candidates']});self.assertAlmostEqual(sum(q['candidateShares'].values()),1,places=12)

class PrecisionStatusTests(unittest.TestCase):
    def test_unsuccessful_status_is_never_overridden_by_small_gradient(self):
        from scripts.tests.test_stage33_numerics import fixture
        p=fixture('baseline_plus_R');p['features']=[[r[1]] for r in p['features']];profile=numerics.Profile(p)
        failure=SimpleNamespace(success=False,fun=1.,message='synthetic unsuccessful',x=np.array([0.]))
        with patch('scripts.models.joint_candidate_share.numerics.minimize',return_value=failure) as solve:
            with self.assertRaisesRegex(ValueError,'unsuccessful'):profile.theta_optimum(.01)
            self.assertEqual(solve.call_count,2)
    def test_precise_same_objective_and_gradient(self):
        from scripts.tests.test_stage33_numerics import fixture
        p=numerics.Profile(fixture('baseline_plus_S_plus_R'));theta=np.array([.3,-.8])
        a,g=p.stable_objective(.01,theta,relative=True);b,h=p.decimal_objective(.01,theta)
        self.assertLess(abs(a-b),1e-13);self.assertLess(max(abs(g-h)),1e-13)

class AdditionalArithmeticTests(unittest.TestCase):
    def test_contest_equal_is_not_candidate_equal(self):
        row=synthetic_row();actual={'candidateShares':{'a':.7,'b':.2,'c':.1},'winnerCandidateId':'a'}
        s1=metrics.score({'a':.5,'b':.3,'c':.2},actual,row,'broad')
        row2={'candidates':row['candidates'][:2]};s2=metrics.score({'a':.6,'b':.4},{'candidateShares':{'a':.7,'b':.3},'winnerCandidateId':'a'},row2,'broad')
        a=metrics.aggregate([s1,s2]);self.assertAlmostEqual(a['contestEqualMaePP'],(40/3+10)/2)
        self.assertAlmostEqual(a['candidateEqualMaePP'],12)
        self.assertAlmostEqual(a['contestEqualRmsePP'],(150)**.5)
    def test_actual_predictor_four_restrictions_nest(self):
        fs,inv=adapters.folds_inventory();f=next(f for f in fs if f['branch']=='primary' and f['targetYear']==2014)
        rows=adapters.fold_rows(f,inv)[1][:1];base=numerics.predict(rows,f,'baseline',{'status':'fitted','kappa':.01,'theta':[]})
        for method in METHODS:
            self.assertEqual(base,numerics.predict(rows,f,method,{'status':'fitted','kappa':.01,'theta':[0.]*len(METHODS[method])}))
    def test_holdout_training_injection_rejected(self):
        fs,inv=adapters.folds_inventory();f=deepcopy(next(f for f in fs if f['branch']=='primary' and f['targetYear']==2023))
        f['trainingIds'].append(f['evaluationIds'][0])
        with self.assertRaises(ValueError):adapters.fold_rows(f,inv)
    def test_earlier_training_actuals_change_numerical_fit(self):
        from scripts.tests.test_stage33_numerics import fixture
        a=fixture('baseline');a['features']=[[] for r in a['features']];b=deepcopy(a)
        b['actual']=[.4,.25,.35,.25,.4,.35]
        first=numerics.calculate({'payload':a,'signature':'synthetic:low'})['fit']
        second=numerics.calculate({'payload':b,'signature':'synthetic:high'})['fit']
        self.assertEqual(first['status'],'fitted');self.assertEqual(second['status'],'fitted');self.assertNotEqual(first['kappa'],second['kappa'])
