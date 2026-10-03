"""Synthetic-only numerical tests for the frozen S/R family."""
import unittest
from unittest.mock import patch
from math import log
import numpy as np
from scripts.models.joint_candidate_share.numerics import Profile,calculate,predict,rank_at
from scripts.models.joint_candidate_share.common import METHODS
from scripts.checkpoints.joint_candidate_share.kernel import centered


def fixture(method):
    return {'method':method,'trainingIds':['synthetic:1','synthetic:2'],'base':[.5,.2,0,.3,.6,0],
            'features':[[.2,.1],[-.1,-.03],[0,0],[-.3,.07],[.15,-.1],[0,0]],'starts':[0,3],
            'actual':[.55,.35,.1,.35,.6,.05]}


class NumericalTests(unittest.TestCase):
    def test_synthetic_gradient_at_frozen_tolerance(self):
        p=fixture('baseline_plus_S_plus_R');profile=Profile(p);theta=np.array([.3,-.8]);loss,g=profile.value_gradient(.01,theta)
        for i in range(2):
            plus=theta.copy();minus=theta.copy();plus[i]+=1e-6;minus[i]-=1e-6
            finite=(profile.value_gradient(.01,plus)[0]-profile.value_gradient(.01,minus)[0])/2e-6
            self.assertLess(abs(finite-g[i]),1e-8)
    def test_explicit_R_never_uses_V_semantics(self):
        p=fixture('baseline_plus_R');p['features']=[[r[1]] for r in p['features']]
        profile=Profile(p);self.assertEqual(profile.features.shape,(6,1));self.assertEqual(METHODS['baseline_plus_R'],('R',))
    def test_generic_equal_contest_objective(self):
        p=fixture('baseline');p['features']=[[] for r in p['features']];profile=Profile(p)
        direct=0
        for lo,hi in ((0,3),(3,6)):
            w=np.array(p['base'][lo:hi])+.01;q=w/sum(w)
            direct+=-sum(y*log(x) for y,x in zip(p['actual'][lo:hi],q))/2
        self.assertAlmostEqual(profile.value_gradient(.01,np.empty(0))[0],direct,places=14)
    def test_constant_column_abstains_without_pseudoinverse(self):
        p=fixture('baseline_plus_R');p['features']=[[0] for r in p['features']]
        result=calculate({'payload':p,'signature':'synthetic'})
        self.assertEqual(result['fit']['status'],'abstain');self.assertIn('Unidentified',result['fit']['detail'])
    def test_optimizer_failure_is_numerical_abstention(self):
        p=fixture('baseline');p['features']=[[] for r in p['features']]
        with patch('scripts.models.joint_candidate_share.numerics.fit',side_effect=ValueError('independent disagreement')):
            result=calculate({'payload':p,'signature':'synthetic'})
        self.assertEqual(result['fit']['reason'],'numerical_or_rank_failure')

class StableEvaluation(unittest.TestCase):
    def test_same_absolute_objective_and_gradient_as_generic(self):
        from scripts.checkpoints.stage22_fit import Profile as Generic
        p=Profile(fixture('baseline_plus_S_plus_R'))
        for k in (.0001,.01,.1):
            for theta in ([0.,0.],[2.,-4.],[-4.,4.]):
                old,g0=Generic.value_gradient(p,k,np.array(theta));new,g1=p.value_gradient(k,np.array(theta))
                self.assertLess(abs(old-new),1e-13);self.assertLess(max(abs(g0-g1)),1e-13)
                relative,g=p.stable_objective(k,np.array(theta),relative=True)
                self.assertLess(abs(relative-(new-p.value_gradient(k,np.array([0.,0.]))[0])),1e-13)
                self.assertLess(max(abs(g-g1)),1e-13)
