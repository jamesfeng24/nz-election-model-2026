"""Synthetic fixtures and actual preserved-adapter boundary tests; no new models."""
from copy import deepcopy
from fractions import Fraction
from unittest import TestCase
from unittest.mock import patch

import numpy as np
from scripts.models.asymmetric_response.design import initial_direction, regime_rank_guard
from scripts.models.asymmetric_response.inputs import election_inputs
from scripts.models.asymmetric_response_test import construction as runner
from scripts.models.asymmetric_response_test.common import ROOT, DEST, DESIGN, read, verify_inputs, preserve, prefit
from scripts.models.asymmetric_response_test.numerics import estimate_anchor, fit_restrictions, prediction, checked_ols
from scripts.models.asymmetric_response_test.evaluation import metrics, score_case, evaluate
from scripts.models.asymmetric_response_test.verification import verify_prefit, build as independent


def synthetic_snapshots():
    return [{'id':str(y),'year':y,'nationalSupport':str(Fraction(n,100)),
             'generalPremium':str(Fraction(50-n,100))} for y,n in enumerate((20,30,40,60,70,80))]


def synthetic_responses():
    rows=[]
    for env,t in enumerate((0,0,1,1,1)):
        for i,x in enumerate((-.2,-.1,.05,.1,.2)):
            rows.append({'id':f'{env}:{i}','environmentId':str(env),'T':t,'x':x,
                         'c0':.4,'y':.02+1.2*x-.6*x*t})
    return rows


class Stage29Tests(TestCase):
    def test_centered_anchor_and_snapshot_deletions(self):
        result=estimate_anchor(synthetic_snapshots())
        self.assertEqual(result['status'],'available')
        self.assertEqual(len(result['estimates']),7)
        for row in result['estimates']:
            self.assertAlmostEqual(row['anchor'],.5)
            self.assertAlmostEqual(row['slope'],-1)

    def test_anchor_counts_sign_bracket_and_stability_failure(self):
        snaps=synthetic_snapshots()
        self.assertEqual(estimate_anchor(snaps[:3])['reason'],'fewer_than_four_completed_elections')
        for r in snaps:r['generalPremium']='1/10'
        self.assertNotEqual(estimate_anchor(snaps)['status'],'available')
        actual=read(str((DEST/'descriptive-construction.json').relative_to(ROOT)))
        self.assertEqual([c['anchor']['reason'] for c in actual['cases']],['extrapolated_crossing']*2)

    def test_synthetic_classifier_zero_tie_overshoot_disagreement(self):
        self.assertIsNone(initial_direction('.4','.4','.5')['T'])
        self.assertEqual(initial_direction('.5','.6','.5')['T'],0)
        self.assertEqual(initial_direction('.4','.8','.5')['T'],1)
        self.assertTrue(initial_direction('.4','.8','.5')['crossesAnchor'])
        snaps=[{'id':'a','year':1,'nationalSupport':'.4','generalPremium':'.1'},
               {'id':'b','year':2,'nationalSupport':'.6','generalPremium':'-.1'}]
        anchor={'status':'available','stabilityAnchors':[.5]}
        row={'id':'r','party':'p','sourceYear':1,'targetYear':2,'p0':.4,'x':-.1,
             'partyInputs':{'actual_observed_local_party':[.3,.3]}}
        snaps=[{**r,'id':f'{r["year"]}:p','party':'p'} for r in snaps]
        r=runner.classification([row],snaps,anchor)['rows'][0]
        self.assertEqual(r['T'],1)
        self.assertTrue(r['classification']['nationalLocalOppose'])

    def test_unstable_classifier_abstains_whole_case_not_trimming(self):
        row={'id':'r','party':'p','sourceYear':1,'targetYear':2,'p0':.4,
             'partyInputs':{'actual_observed_local_party':[.5,.5]}}
        snaps=[{'id':'1:p','nationalSupport':'.4'},{'id':'2:p','nationalSupport':'.6'}]
        result=runner.classification([row],snaps,{'status':'available','stabilityAnchors':[.3,.5]})
        self.assertEqual(result['status'],'abstain')
        self.assertEqual(result['failedRecords'][0]['reason'],'anchor_stability_disagreement')

    def test_unrestricted_slopes_and_refitted_intercepts(self):
        rows=synthetic_responses();result=fit_restrictions(rows)
        self.assertEqual(result['status'],'available')
        fit=result['fits']['asymmetric']
        self.assertAlmostEqual(fit['alpha'],.02)
        self.assertAlmostEqual(fit['betaAway'],1.2)
        self.assertAlmostEqual(fit['betaToward'],.6)
        self.assertFalse(fit['hypothesizedOrdering'])
        self.assertNotEqual(result['fits']['beta_one']['alpha'],fit['alpha'])
        x=np.array([[1,r['x'],r['x']*r['T']] for r in rows])
        expected=np.linalg.lstsq(x,[r['y'] for r in rows],rcond=None)[0]
        np.testing.assert_allclose([fit['alpha'],fit['betaAway'],fit['delta']],expected,atol=1e-12)

    def test_regime_replication_and_rank_failures(self):
        rows=synthetic_responses()
        deficient=[r for r in rows if r['environmentId']!='0']
        self.assertEqual(fit_restrictions(deficient)['reason'],'fewer_than_two_transition_environments_per_regime')
        for r in rows:r['x']=.1
        self.assertEqual(regime_rank_guard(rows)['reason'],'rank_deficient_or_weak_condition')

    def test_solver_failure_and_disagreement_are_abstentions(self):
        self.assertEqual(checked_ols([[1,1],[1,1]],[1,2])['status'],'abstain')
        with patch('scripts.models.asymmetric_response_test.numerics.np.linalg.lstsq',return_value=(np.array([99.]),)):
            self.assertEqual(checked_ols([[1],[1]],[1,2])['reason'],'independent_solver_disagreement')

    def test_solver_exception_is_explicit_abstention(self):
        with patch('scripts.models.asymmetric_response_test.numerics.np.linalg.lstsq',side_effect=np.linalg.LinAlgError('synthetic failure')):
            self.assertEqual(checked_ols([[1],[1]],[1,2])['reason'],'independent_solver_numerical_failure')
        self.assertEqual(checked_ols([[float('nan')]],[1])['reason'],'nonfinite_or_empty_solver_input')

    def test_unclipped_prediction_and_metric_arithmetic(self):
        f={'alpha':.8,'betaAway':2,'delta':1}
        self.assertGreater(prediction({'c0':.4,'x':.2,'T':1},f),1)
        p=[{'id':'a','candidateShare':.5,'outOfRange':False},
           {'id':'b','candidateShare':.4,'outOfRange':False}]
        m=metrics(p,{'a':.4,'b':.6})
        self.assertAlmostEqual(m['maePP'],15)
        self.assertAlmostEqual(m['rmsePP'],100*(.025**.5))
        self.assertAlmostEqual(m['biasPP'],-5)
        with self.assertRaises(ValueError):metrics(p,{'a':.4})

    def test_actual_inventory_and_both_chronology_windows(self):
        data=prefit()
        self.assertEqual(len(data['chronologicalFolds']),20)
        rows={r['id']:r for r in read('data/processed/models/exact-geography-retests/inventory.json')['responseRecords']}
        for f in data['chronologicalFolds']:
            for i in f['trainingIds']:
                self.assertLess(rows[i]['targetYear'],f['targetYear'])
                self.assertLessEqual(rows[i]['targetYear'],f['sourceYear'])
                if f['protocol']=='more_separated':self.assertLess(rows[i]['targetYear'],f['sourceYear'])
        self.assertEqual(sum(f['countGatesPotentiallyFeasible'] for f in data['chronologicalFolds']),2)

    def test_full_adapter_holdout_candidate_outcomes_only_change_descriptive_anchor(self):
        elections={y:read(f'data/processed/elections/{y}.json') for y in (2008,2011,2014,2017,2020,2023)}
        original_chrono,original_full=runner.build(elections=elections)
        changed=deepcopy(elections)
        for seat in changed[2023]['electorates']:
            seat['winnerCandidateId']='changed'; seat['residual']=999
            for c in seat['candidates']:
                c['identityConfidence']='mutated'
                if c['partyKey']=='nationalparty':c['votes']+=10
        mutated_chrono,mutated_full=runner.build(elections=changed)
        self.assertEqual(original_chrono,mutated_chrono)
        self.assertNotEqual(original_full,mutated_full)
        earlier=deepcopy(elections)
        for seat in earlier[2020]['electorates']:
            for c in seat['candidates']:
                if c['partyKey']=='nationalparty':c['votes']+=10
        later,_=runner.build(elections=earlier)
        for a,b in zip(original_chrono['cases'],later['cases']):
            if a['targetYear']<=2020:self.assertEqual(a,b)
        key=lambda c: c['targetYear']==2023 and c['protocol']=='expanding_window' and c['party']=='nationalparty'
        original_case=next(c for c in original_chrono['cases'] if key(c))
        changed_case=next(c for c in later['cases'] if key(c))
        self.assertNotEqual(original_case['anchor'],changed_case['anchor'])

    def test_inherited_identity_labels_cannot_confirm_or_change_fit(self):
        rows=synthetic_responses();base=fit_restrictions(rows)
        for r in rows:r.update(identityConfidence='confirmed',winner=True,residual=999)
        self.assertEqual(base,fit_restrictions(rows))

    def test_fixed_anchor_transition_deletion_and_no_deleted_scoring(self):
        rows=synthetic_responses()
        for r in rows:r['classification']={'nationalLocalOppose':False}
        parent={'status':'available','classifiedTraining':rows,'anchor':{'stabilityAnchors':[.5]}}
        deletions=[{'deletedEnvironment':str(e),'retainedIds':[r['id'] for r in rows if r['environmentId']!=str(e)]} for e in range(5)]
        def prepared(retained,_):return retained
        with patch.object(runner,'response_training',side_effect=prepared),patch.object(runner,'estimate_anchor',side_effect=AssertionError('anchor refit forbidden')):
            children=runner.transition_deletions(parent,deletions,{})
        self.assertEqual([c['status'] for c in children],['abstain','abstain','available','available','available'])
        self.assertTrue(all(not c['deletedTransitionScored'] for c in children))
        self.assertEqual(parent['anchor']['stabilityAnchors'],[.5])
        for child in children:
            self.assertEqual(child['trainingIds'],child['retainedIds'])
            if child['status']=='available':self.assertEqual(child['evaluationIds'],child['retainedIds'])

    def test_parent_failure_leaves_all_children_visible(self):
        doc=read(str((DEST/'descriptive-construction.json').relative_to(ROOT)))
        self.assertEqual(sum(len(c['deletions']) for c in doc['cases']),10)
        self.assertTrue(all(d['status']=='not_attempted' for c in doc['cases'] for d in c['deletions']))

    def test_snapshot_deletion_distinct_from_response_transition_deletion(self):
        data=prefit()['fullPanelDescriptive']
        for case in data:
            self.assertEqual(len(case['snapshotIds']),6)
            self.assertEqual(len(case['transitionDeletions']),5)
            self.assertEqual(len(case['responseIds']),245)
            for d in case['transitionDeletions']:
                self.assertGreater(len(d['retainedIds']),0)
                self.assertEqual(len(case['snapshotIds']),6)

    def test_independent_arithmetic_and_null_selection(self):
        self.assertEqual(independent()['independentAnchorChecks'],46)
        c=read(str((DEST/'chronological-construction.json').relative_to(ROOT)))
        d=read(str((DEST/'descriptive-construction.json').relative_to(ROOT)))
        result=evaluate(c,d)
        self.assertIsNone(result['selectedOperationalEffect'])
        self.assertFalse(any(s['passes'] for s in result['developmentScreen'].values()))
        self.assertEqual(sum(r['status']=='available' for r in result['chronological']),0)

    def test_provenance_prefit_and_preservation(self):
        verify_inputs();verify_prefit()
        self.assertEqual(preserve(include_registry=False),1382)


class SupplementalDiagnosticTests(TestCase):
    def setUp(self):
        self.construction=read(str((DEST/'supplemental-construction.json').relative_to(ROOT)))
        self.evaluation=read(str((DEST/'supplemental-evaluation.json').relative_to(ROOT)))

    def test_all_anchor_failures_and_classification_changes_are_separate(self):
        by_party={c['party']:c['anchorDiagnostic'] for c in self.construction['cases']}
        self.assertEqual(by_party['nationalparty']['changedTransitionClassifications'],2)
        self.assertEqual(by_party['labourparty']['changedTransitionClassifications'],0)
        for a in by_party.values():
            self.assertEqual(len(a['anchorEstimates']),7)
            self.assertTrue(a['independentlyAssessableSetGates']['anyCrossingOutsideObservedSupport'])
            self.assertFalse(a['independentlyAssessableSetGates']['numericalRankOrConditionFailure'])
            self.assertFalse(a['independentlyAssessableSetGates']['slopeSignInstability'])
            self.assertTrue(all(len(t['labels'])==7 for t in a['transitionLabels']))
            self.assertTrue(any(not l['crossingWithinOwnObservedSupport'] for t in a['transitionLabels'] for l in t['labels']))
            self.assertIn('unavailable',a['independentlyAssessableSetGates']['separateExcessiveWidthGate'])

    def test_all_three_deletion_restrictions_refitted_on_fixed_common_anchor(self):
        gate_failures=0
        for case in self.construction['cases']:
            self.assertEqual(case['status'],'available')
            self.assertEqual(len(case['trainingIds']),245)
            self.assertFalse(case['fits']['asymmetric']['hypothesizedOrdering'])
            for child in case['transitionDeletions']:
                self.assertEqual(child['centralAnchorFixed'],case['centralAnchor'])
                self.assertFalse(child['deletedTransitionScored'])
                self.assertEqual(child['status'],'available')
                self.assertEqual(set(child['fits']),{'beta_one','constant','asymmetric'})
                sample=child['trainingIds']
                for values in child['predictions'].values():self.assertEqual([p['id'] for p in values],sample)
                gate_failures+=child['formalResponseGate']['status']=='abstain'
        self.assertEqual(gate_failures,4)

    def test_disappeared_regime_abstains_no_pseudoinverse(self):
        from scripts.models.asymmetric_response_test.descriptive_diagnostic import diagnostic_response
        rows=[r for r in synthetic_responses() if r['T']==1]
        for r in rows:r['classification']={'nationalLocalOppose':False}
        with patch('scripts.models.asymmetric_response_test.descriptive_diagnostic.response_training',return_value=rows):
            result=diagnostic_response(rows,{})
        self.assertEqual(result['reason'],'regime_disappeared')
        self.assertNotIn('fits',result)

    def test_supplement_metrics_and_independent_coefficients(self):
        from scripts.models.asymmetric_response_test.supplement_evaluation import evaluate
        self.assertEqual(evaluate(),self.evaluation)
        self.assertEqual(self.evaluation['independentResponseChecks'],36)
        for c in self.evaluation['cases']:
            for m in c['metrics'].values():
                self.assertEqual(m['n'],245)
                self.assertAlmostEqual(m['biasPP'],0,places=10)
            self.assertIsNone(self.evaluation['operationalSelection'])

    def test_independent_display_signed_zero_has_one_byte_representation(self):
        import json
        from scripts.models.asymmetric_response_test.supplement_evaluation import display_metric
        self.assertEqual(json.dumps(display_metric(-1e-15)),json.dumps(display_metric(1e-15)))
        self.assertEqual(display_metric(1.23456789),1.234568)

    def test_supplement_cannot_rewrite_formal_result(self):
        from scripts.models.asymmetric_response_test.common import digest
        manifest=read(str((DEST/'supplement-prefit-manifest.json').relative_to(ROOT)))
        for name,original in manifest['formalConstructionSha256'].items():
            self.assertEqual(digest(str((DEST/name).relative_to(ROOT))),original)
        c=read(str((DEST/'chronological-construction.json').relative_to(ROOT)))
        d=read(str((DEST/'descriptive-construction.json').relative_to(ROOT)))
        self.assertTrue(all(row['status']=='abstain' for row in c['cases']+d['cases']))
        self.assertTrue(all(child['status']=='not_attempted' for row in d['cases'] for child in row['deletions']))
        self.assertTrue(all(row['formalGateFirstResultUnchanged'] for row in self.construction['cases']))
