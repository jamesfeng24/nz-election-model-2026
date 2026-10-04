"""Stage36 synthetic contracts and actual cutoff adapters; no historical MCMC."""
import copy
import importlib.util
import unittest
import numpy as np
from scipy.integrate import quad
from scipy.special import log_ndtr
from scripts.polling.national_model.common import FOUNDATION,read,COARSE
from scripts.polling.national_model.prepare import prepare,interval_rows,initial_shares,cycle_data
from scripts.polling.national_model.transforms import helmert,bridge_factor,softmax,project_box
from scripts.polling.national_model.inventory import semantic,preserved
from scripts.polling.national_model.benchmark import poll_vector,benchmark
from scripts.polling.national_foundation.records import record


def synthetic_poll(org='COL'):
    return record(2014,{'date':['2011-12-04','2011-12-07'],'org':org,'n':1000,
                       'NAT':'45','LAB':'30','GRN':'10','ACT':'2','NZF':'8','MRI':'1','NCP':'0.5'},
                  {'sourceId':'synthetic_not_historical'})


def synthetic_case():
    prev={'year':2011,'shares':dict(zip(['NAT','LAB','GRN','ACT','NZF','MRI','TOP','OTH'],[.45,.3,.1,.02,.08,.01,0,.04]))}
    c=cycle_data(2014,'2011-12-17T23:59:59+13:00',[synthetic_poll(),synthetic_poll('REI')],prev,None,750)
    return {'cycles':[c],'pollsterRoster':['COL','REI'],'year':2014,'schema':c['categories'],'horizonDays':14}


class Stage36Contracts(unittest.TestCase):
    def test_archive_requires_complete_frame_and_finished_attempts(self):
        from scripts.polling.national_model.archive import validate_completion
        inventory=[{'id':'a'},{'id':'b'}];cases=[{'id':'a','status':'accepted'},{'id':'b','status':'data_abstention'}]
        validate_completion(cases,inventory)
        for changed in (cases[:1],cases+[cases[0]], [{'id':'a','status':'numerical_failure','attempts':['one']},cases[1]]):
            with self.assertRaises(ValueError):validate_completion(changed,inventory)

    def test_independent_interval_and_coarsening_arithmetic(self):
        from scripts.polling.national_model.verification import independent_quantile,verify_intervals
        from scripts.polling.national_model.metrics import probabilities
        values=[0.,.2,.4,.6,.8,1.]
        self.assertAlmostEqual(independent_quantile(values,.25),.25)
        draws=np.array([[x,1-x] for x in values]);result=probabilities(draws,[.3,.7],['a','b'])
        verify_intervals(values,.3,result['parties'][0]['intervals'])
        changed=copy.deepcopy(result['parties'][0]['intervals']);changed['0.5']['covered']=False
        with self.assertRaisesRegex(ValueError,'coverage'):verify_intervals(values,.3,changed)

    def test_helmert_and_category_projection(self):
        for k in (7,8):
            h=helmert(k);np.testing.assert_allclose(h.T@h,np.eye(k-1),atol=1e-15);np.testing.assert_allclose(h.sum(axis=0),0,atol=1e-15)
        indices=[0,1,2,3,4,5,7];project=helmert(7).T@helmert(8)[indices]
        np.testing.assert_allclose(project@project.T,np.eye(6),atol=1e-15)

    def test_bridge_is_same_random_walk_not_result_bridge(self):
        t=np.array([7,14,17]);l=bridge_factor(t)
        np.testing.assert_allclose(l@l.T,np.minimum.outer(t,t)/7,atol=1e-14)
        self.assertGreater(np.linalg.matrix_rank(l),2)

    def test_softmax_extreme_and_conservation(self):
        q=softmax([1000,-1000,999]);self.assertTrue(np.all(np.isfinite(q)));self.assertAlmostEqual(sum(q),1);self.assertTrue(np.all(q>=0))

    def test_actual_heldout_and_later_results_excluded(self):
        r=read(FOUNDATION/'official-results-isolated.json')['records'];a=prepare(2017,14,results=r)
        changed=copy.deepcopy(r)
        for x in changed:
            if x['year']>=2017:x['shares']={'NAT':999};x['winner']='fiction'
        self.assertEqual(semantic(a),semantic(prepare(2017,14,results=changed)))
        self.assertEqual(a['permittedAnchorYears'],[2011,2014]);self.assertIsNone(a['cycles'][-1]['endpointShares'])

    def test_post_cutoff_and_future_revision_excluded(self):
        r=read(FOUNDATION/'polls.json')['records'];a=prepare(2017,56,polls=r);changed=copy.deepcopy(r)
        for x in changed:
            if x['fieldworkEndBounds'][1]>a['cutoff'][:10]:x['estimates']['NAT']['share']=999
        future=copy.deepcopy(synthetic_poll());future.update(cycle=2017,id='future-revision',publication='2023-01-01T00:00:00Z',publicationConfidence='verified',fieldworkStartBounds=['2017-07-01']*2,fieldworkEndBounds=['2017-07-02']*2)
        from scripts.polling.national_model.inference import fit_signature
        self.assertEqual(fit_signature(a)['inputDigest'],fit_signature(prepare(2017,56,polls=changed+[future]))['inputDigest'])

    def test_earlier_anchor_legitimately_changes_start(self):
        r=read(FOUNDATION/'official-results-isolated.json')['records'];a=prepare(2017,14,results=r);b=copy.deepcopy(r)
        x=next(v for v in b if v['year']==2014);x['shares']['NAT']-=.01;x['shares']['LAB']+=.01
        self.assertNotEqual(a['cycles'][-1]['initial']['mean'],prepare(2017,14,results=b)['cycles'][-1]['initial']['mean'])

    def test_schema_entry_no_historical_top_observation(self):
        c=prepare(2017,14);self.assertNotIn('TOP',c['cycles'][0]['categories']);self.assertEqual(c['cycles'][1]['initial']['entrants'],['TOP'])
        self.assertNotIn('TOP',[r['category'] for r in c['cycles'][0]['rows']]);self.assertAlmostEqual(c['cycles'][1]['initial']['shares'][6],.002)

    def test_partial_missing_zero_and_minor_censor(self):
        r=synthetic_poll();r['estimates']['ACT']={'status':'not_reported','bounds':None};r['estimates']['MRI']={'status':'rounded_zero','bounds':[0,.0005]};r['additionalPublishedCategories']={'NCP':{'status':'rounded','bounds':[.0045,.0055]}}
        rows,_=interval_rows(r,COARSE);self.assertNotIn('ACT',[x['category'] for x in rows]);self.assertIn('MRI',[x['category'] for x in rows]);self.assertEqual(rows[-1]['upper'],None);self.assertEqual(rows[-1]['lower'],.0045)

    def test_alliance_not_double_counted(self):
        r=synthetic_poll();r['additionalPublishedCategories']={p:{'bounds':[.01,.02]} for p in ('INM','MNA')}
        rows,reason=interval_rows(r,COARSE);self.assertIn('overlapping_alliance',reason);self.assertNotIn('OTH',[x['category'] for x in rows])

    def test_all_respondent_requires_denominator(self):
        r=synthetic_poll();r['denominator']='all_respondents';self.assertEqual(interval_rows(r,COARSE)[0],[])
        r['nonresponseCombined']=.1
        for p in COARSE[1:-1]:r['estimates'][p]={'status':'not_reported','bounds':None}
        rows,_=interval_rows(r,COARSE);self.assertAlmostEqual(rows[0]['lower'],.445/.9)

    def test_projection_not_independent_renormalization(self):
        q=project_box([.6,.5],[.55,.45],[.65,.55]);np.testing.assert_allclose(q,[.55,.45],atol=1e-14)
        with self.assertRaises(ValueError):project_box([.6,.5],[.59,.49],[.65,.55])

    def test_benchmark_vector_and_missing(self):
        r=synthetic_poll();v=poll_vector(r);np.testing.assert_allclose(v,[.45,.3,.1,.02,.08,.01,.04],atol=1e-14)
        r['estimates']['ACT']['status']='threshold'
        with self.assertRaises(ValueError):poll_vector(r)

    def test_benchmark_other_lower_constraint(self):
        from scripts.polling.national_foundation.records import observation
        from scripts.polling.national_model.benchmark import other_lower
        r=synthetic_poll()
        for p,v in zip(COARSE[:-1],['50','40','5','2','2','1']):r['estimates'][p]=observation(v)
        r['estimates']['TOP']=observation('1');r['additionalPublishedCategories']['NCP']=observation('2')
        v=poll_vector(r);self.assertGreaterEqual(v[-1]+1e-12,other_lower(r));self.assertAlmostEqual(sum(v),1)
        self.assertFalse(np.allclose(v[:6],np.array([.5,.4,.05,.02,.02,.01])))

    def test_score_arithmetic_on_synthetic_draws(self):
        from scripts.polling.national_model.metrics import point,crps,energy,probabilities
        q=np.array([.6,.4]);actual=np.array([.5,.5]);draws=np.tile(q,(8,1))
        p=point(q,actual,['NAT','LAB']);self.assertAlmostEqual(p['MAEpp'],10);self.assertAlmostEqual(p['RMSEpp'],10);self.assertAlmostEqual(p['accountingBiasPP'],0)
        self.assertAlmostEqual(crps(draws[:,0],.5),10);self.assertAlmostEqual(energy(draws,actual)['energyScorePP'],np.sqrt(200))
        result=probabilities(draws,actual,['NAT','LAB']);self.assertEqual(result['coverage90'],0);self.assertEqual(result['width90PP'],0)

    def test_pooled_rmse_uses_squared_errors(self):
        from scripts.polling.national_model.evaluation import pooled
        rows=[]
        for x in (1,3):
            rows.append({'branch':'primary','coarseComparison':{'modelMAEpp':x,'benchmarkMAEpp':4,'MAEImprovementPP':4-x,'modelRMSEpp':x,'benchmarkRMSEpp':4},'model':{'coarsePoint':{'parties':[{'biasPP':x} for _ in COARSE]},'coarseProbability':{k:0 for k in ['meanCRPSpp','coverage50','coverage90','width50PP','width90PP','energyScorePP']}},'benchmark':{'parties':[{'biasPP':4} for _ in COARSE]}})
        p=pooled(rows)[0];self.assertAlmostEqual(p['modelMAEpp'],2);self.assertAlmostEqual(p['modelRMSEpp'],np.sqrt(5));self.assertFalse(p['fullPlannedPoolAvailable']);self.assertEqual(p['plannedWeightPerCase'],.125);self.assertEqual(p['partyMetrics'][0]['modelBiasPP'],2)

    def test_exact_manifest_and_verified_no_data(self):
        inv=read(FOUNDATION.parent/'national-backtest/inventory.json')
        self.assertEqual(len(inv['cases']),32);self.assertEqual(sum(x['status']=='ready' for x in inv['cases']),26)
        self.assertEqual(prepare(2014,14,'verified_only')['status'],'data_abstention');self.assertGreater(preserved(),1500)

    def test_actual_benchmark_no_candidate_or_future_result_use(self):
        c=prepare(2020,14);a=benchmark(c);c['candidateVotes']=-1;c['winner']=999
        self.assertEqual(a,benchmark(c));self.assertEqual(a['status'],'constructed');self.assertAlmostEqual(sum(a['shares']),1)


@unittest.skipUnless(importlib.util.find_spec('jax') and importlib.util.find_spec('numpyro'),'isolated polling inference environment required')
class Stage36Generative(unittest.TestCase):
    def test_all_latent_coordinates_are_gated_not_only_headlines(self):
        from scripts.polling.national_model.inference import diagnostics
        rng=np.random.default_rng(36036)
        latent=rng.normal(size=(4,2000,2));latent[:,:,0]+=np.arange(4)[:,None]*10
        latent[:,:,1]=0
        shares=softmax(rng.normal(size=(4,2000,7)))
        extra={'diverging':np.zeros((4,2000),bool),'num_steps':np.ones((4,2000)),
               'accept_prob':np.ones((4,2000))*.98,'energy':rng.normal(size=(4,2000))}
        d=diagnostics({'poorly_mixed_latent':latent},{'electionDay':shares.reshape(-1,7)},extra,12)
        self.assertFalse(d['passed']);self.assertEqual(d['divergences'],0)
        self.assertEqual(d['failedVariables'],[{'variable':'poorly_mixed_latent','count':1}])
        self.assertEqual(d['constants'][0]['exactConstantCoordinates'],[1])

    def test_interval_values_and_gradients(self):
        import jax
        import jax.numpy as jnp
        from scripts.polling.national_model.model import interval_logprob
        for lo,hi,mu,sd in [(0,.0005,.001,.005),(.2,.200000000001,.21,.02),(.8,.81,.01,.005),(.45,np.inf,.3,.1)]:
            got=float(interval_logprob(jnp.array(lo),jnp.array(hi),jnp.array(mu),jnp.array(sd)))
            if np.isinf(hi):expected=float(log_ndtr((mu-lo)/sd))
            else:
                a=(lo-mu)/sd;b=(hi-mu)/sd;mode=np.clip(0,a,b);scale=-mode**2/2
                integral=quad(lambda t:np.exp(-t*t/2-scale),(lo-mu)/sd,(hi-mu)/sd,epsabs=1e-13)[0]
                expected=np.log(integral)+scale-.5*np.log(2*np.pi)
            self.assertAlmostEqual(got,expected,places=7)
            g=float(jax.grad(lambda m:interval_logprob(jnp.array(lo),jnp.array(hi),m,jnp.array(sd)))(jnp.array(mu)))
            self.assertTrue(np.isfinite(g))

    def test_fieldwork_mean_independent_arithmetic(self):
        from scripts.polling.national_model.model import arrays,poll_expectation
        import jax.numpy as jnp
        case=synthetic_case();c=arrays(case)[0];path=np.tile(c['initialMean'],(4,1));path[-1,0]+=.3
        got=np.asarray(poll_expectation(jnp.array(path),jnp.zeros((2,7)),jnp.zeros(7),jnp.zeros(7),c))
        expected=[]
        for i in range(2):
            days=[d for d in case['cycles'][0]['days'] if d['poll']==i]
            expected.append(sum(softmax((path[d['lo']]*(1-d['fraction'])+path[d['hi']]*d['fraction'])@helmert(7).T)*d['weight'] for d in days))
        np.testing.assert_allclose(got,expected,atol=1e-14)

    def test_prior_predictive_joint_support_and_common_error(self):
        import jax
        from numpyro.infer import Predictive
        from scripts.polling.national_model.model import national_model,arrays
        v=Predictive(national_model,num_samples=500)(jax.random.PRNGKey(36),data=arrays(synthetic_case()),n_pollsters=2)
        q=np.asarray(v['current_2014']);np.testing.assert_allclose(q.sum(axis=1),1,atol=1e-14)
        self.assertTrue(np.all(q>=0));self.assertGreater(np.asarray(v['bias_2014']).std(),.02)
        self.assertGreater(np.asarray(v['sigma']).std(),.01)

    def test_noisier_measurement_has_less_information(self):
        import jax
        import jax.numpy as jnp
        from scripts.polling.national_model.model import interval_logprob
        def curvature(sd):
            fn=lambda mu:interval_logprob(jnp.array(.2995),jnp.array(.3005),mu,jnp.array(sd))
            return -float(jax.grad(jax.grad(fn))(jnp.array(.3)))
        self.assertLess(curvature(.04),curvature(.02))

    def test_complete_joint_gradient(self):
        import jax
        from numpyro.infer.util import initialize_model
        from scripts.polling.national_model.model import national_model,arrays
        setup=initialize_model(jax.random.PRNGKey(360),national_model,model_kwargs={'data':arrays(synthetic_case()),'n_pollsters':2})
        v,g=jax.value_and_grad(setup.potential_fn)(setup.param_info.z)
        self.assertTrue(np.isfinite(v))
        self.assertTrue(all(np.all(np.isfinite(x)) for x in jax.tree_util.tree_leaves(g)))
        z=setup.param_info.z;step=1e-5
        plus={**z,'sigma':z['sigma']+step};minus={**z,'sigma':z['sigma']-step}
        fd=(float(setup.potential_fn(plus))-float(setup.potential_fn(minus)))/(2*step)
        self.assertAlmostEqual(fd/float(g['sigma']),1,places=5)

    def test_four_chain_sampler_runtime_on_synthetic_only(self):
        import jax
        import jax.numpy as jnp
        from numpyro.infer import MCMC,NUTS,init_to_median
        from scripts.polling.national_model.model import national_model,arrays,mass_blocks
        data=arrays(synthetic_case())
        sampler=MCMC(NUTS(national_model,dense_mass=mass_blocks(data),init_strategy=init_to_median(num_samples=15)),num_warmup=30,num_samples=20,num_chains=4,chain_method='parallel',progress_bar=False)
        sampler.run(jnp.stack([jax.random.PRNGKey(x) for x in [13601,13602,13603,13604]]),data=data,n_pollsters=2,extra_fields=('diverging','num_steps','accept_prob','energy'))
        q=np.asarray(sampler.get_samples(group_by_chain=True)['current_2014'])
        self.assertEqual(q.shape,(4,20,7));np.testing.assert_allclose(q.sum(axis=-1),1,atol=1e-14)
        self.assertTrue(np.all(np.isfinite(q)))
        # Short synthetic smoke is not a historical convergence claim.
