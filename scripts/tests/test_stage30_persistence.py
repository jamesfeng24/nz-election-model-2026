"""Stage30 real adapters, paired arithmetic and frozen dependencies."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from math import sqrt
from scripts.models.expanded_candidate_persistence import inventory,construction,evaluation
from scripts.models.expanded_candidate_persistence.common import local,read,unique,RES,LINK,GEO,verify_inputs,preservation,verify_prefit

class PersistenceAdapters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory=local('inventory.json');cls.plan=local('fold-plan.json')
        cls.actuals=unique(read(RES+'occurrences.json')['records'],'candidateOccurrenceId')
        cls.constructed=local('construction.json')
    def one_fold(self,year=2023,protocol='expanding_window'):
        return deepcopy(next(f for f in self.plan['folds'] if (f['view'],f['scope'],f['scale'],f['protocol'],f['targetYear'])==('broad','general','additive',protocol,year)))
    def test_frozen_counts_and_strict_subset(self):
        pairs=self.inventory['pairs'];b={r['id'] for r in pairs if r['scaleEligibility']['additive']['broad']};s={r['id'] for r in pairs if r['scaleEligibility']['additive']['strict']}
        self.assertEqual(len(b),482);self.assertEqual(len(s),413);self.assertTrue(s<=b)
        self.assertEqual(sum(r['scope']=='maori' and r['id'] in b for r in pairs),30)
    def test_exact_geography_and_separate_contest_status(self):
        i=inventory.build();self.assertEqual(i,self.inventory)
        g=deepcopy(i['fullGeographicFrame'])
        valid=next(r for r in g if r['certifiedTwoSidedExact'] and r['contestStatus']=='not_adjudicated_in_geography_layer')
        valid['certifiedTwoSidedExact']=False
        with self.assertRaisesRegex(ValueError,'geography disagreement'):inventory.build(geography=g)
    def test_actual_inventory_outcome_fields_cannot_select(self):
        rs=deepcopy(list(self.actuals.values()))
        for r in rs:
            r.update(winner=True,identityConfidence='confirmed',residual=999,sourcePublishedCandidateVotes=-12)
            if r['year']==2023 and r['normalizedPremium'] is not None:
                r['normalizedPremium']+=2
                for m in r['methods'].values():
                    if m['residual'] is not None:m['residual']+=2
        changed=inventory.build(residuals=rs)
        self.assertEqual(changed,self.inventory)
    def test_no_inherited_winner_anchor_requirement(self):
        edges=deepcopy(read(LINK+'proposed-links.json')['records'])
        for r in edges:r.update(sourceWinner=False,targetWinner=False,identityConfidence='unresolved',laterSuccess=False)
        self.assertEqual(inventory.build(edges=edges),self.inventory)
    def test_missing_residual_is_not_zero(self):
        rs=deepcopy(list(self.actuals.values()));pair=next(r for r in self.inventory['pairs'] if r['scaleEligibility']['additive']['broad'])
        next(r for r in rs if r['candidateOccurrenceId']==pair['sourceOccurrenceId'])['normalizedPremium']=None
        result=next(r for r in inventory.build(residuals=rs)['pairs'] if r['id']==pair['id'])
        self.assertFalse(result['scaleEligibility']['additive']['broad']);self.assertIn('missing_source_residual',result['scaleEligibility']['additive']['exclusionReasons'])
    def test_dedup_and_joins_reject_corruption(self):
        rs=list(self.actuals.values())
        with self.assertRaisesRegex(ValueError,'Duplicate'):inventory.build(residuals=rs+[rs[0]])
        edges=deepcopy(read(LINK+'proposed-links.json')['records']);edges[0]['targetYear']=9999
        with self.assertRaisesRegex(ValueError,'join mismatch'):inventory.build(edges=edges)
    def test_actual_holdout_outcomes_change_scoring_only(self):
        f=self.one_fold();plan={'folds':[f]};changed=deepcopy(self.actuals)
        for r in changed.values():
            r.update(winner=False,identityConfidence='unresolved')
            if r['year']==2023 and r['normalizedPremium'] is not None:r['normalizedPremium']+=0.1
        a=construction.build(self.inventory,plan,self.actuals);b=construction.build(self.inventory,plan,changed)
        self.assertEqual(a['folds'],b['folds'])
        self.assertNotEqual(a['descriptive'],b['descriptive'])
        index=unique(self.inventory['pairs'],'id');af=a['folds'][0]
        self.assertNotEqual(evaluation.evaluate(af['predictions'],f['evaluationIds'],index,self.actuals,'additive'),evaluation.evaluate(af['predictions'],f['evaluationIds'],index,changed,'additive'))
    def test_earlier_response_legitimately_changes_later_fit(self):
        f=self.one_fold(2014);changed=deepcopy(self.actuals)
        for r in changed.values():
            if r['year']==2011 and r['normalizedPremium'] is not None:r['normalizedPremium']+=0.1
        a=construction.build(self.inventory,{'folds':[f]},self.actuals)['folds'][0]
        b=construction.build(self.inventory,{'folds':[f]},changed)['folds'][0]
        self.assertAlmostEqual(b['fits']['regression']['alpha']-a['fits']['regression']['alpha'],0.1)
    def test_target_and_future_training_rejected(self):
        f=self.one_fold();f['trainingIds']+=f['evaluationIds'][:1]
        with self.assertRaisesRegex(ValueError,'Forbidden'):construction.build(self.inventory,{'folds':[f]},self.actuals)
    def test_chronology_overlap_and_earliest(self):
        primary=self.one_fold(2014);separated=self.one_fold(2014,'more_separated')
        self.assertEqual(len(primary['trainingIds']),120);self.assertEqual(separated['trainingIds'],[])
        first=next(f for f in self.constructed['folds'] if f['id']==self.one_fold(2011)['id'])
        self.assertEqual(first['fits']['regression']['status'],'abstain');self.assertEqual(first['predictions']['carry_forward']['status'],'available')
    def test_source_not_target_reference_predictor(self):
        f=self.one_fold();changed=deepcopy(self.actuals)
        for r in changed.values():
            if r['year']==2023:r['leaveOneOutReference']={'offset':100};r['referenceId']='corrupt_evaluation_reference'
        a=construction.build(self.inventory,{'folds':[f]},self.actuals)
        b=construction.build(self.inventory,{'folds':[f]},changed)
        self.assertEqual(a,b)
    def test_fixed_deleted_transition_not_scored(self):
        for r in local('evaluation.json')['descriptive']:self.assertFalse(r['deletedTransitionScored'])
    def test_common_strict_identical_ids(self):
        for r in local('evaluation.json')['commonStrictEvaluation']:
            self.assertEqual(r['broadTrainedOnStrictEvaluation']['eligiblePairs'],len(r['evaluationIds']))
            self.assertEqual(r['strictTrainedOnStrictEvaluation']['eligiblePairs'],len(r['evaluationIds']))
    def test_source_contract_and_prior_bytes(self):
        verify_inputs();verify_prefit();self.assertGreater(preservation(),1400)
    def test_mutated_pinned_input_rejected(self):
        from scripts.models.expanded_candidate_persistence import common
        with patch.object(common,'digest',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'pinned input'):verify_inputs()

class PairedArithmetic(unittest.TestCase):
    def test_metric_units_and_root_after_averaging(self):
        m=evaluation.metrics([0.03,-0.04]);self.assertAlmostEqual(m['MAEpp'],3.5);self.assertAlmostEqual(m['RMSEpp'],sqrt(12.5));self.assertAlmostEqual(m['biasPp'],-0.5)
    def test_same_id_gains_and_abstentions(self):
        rows=[{'id':'a','errors':{'regression':0.01,'zero':0.03,'carry_forward':0.02,'historical_mean':0.04}}, {'id':'b','errors':{'regression':-0.02,'zero':-0.05,'carry_forward':-0.01,'historical_mean':0.04}}]
        s=evaluation.summary(rows);self.assertAlmostEqual(s['pairedGains']['zero']['MAEgainPp'],2.5)
        self.assertEqual(s['pairedGains']['zero']['ids'],['a','b']);self.assertAlmostEqual(s['pairedGains']['carry_forward']['MAEgainPp'],0)
    def test_mismatched_method_sample_rejected(self):
        p={m:{'status':'available','values':[]} for m in evaluation.METHODS}
        with self.assertRaisesRegex(ValueError,'Different evaluation IDs'):evaluation.evaluate(p,['a'],{}, {},'additive')

class UpstreamLinkageIndependence(unittest.TestCase):
    def test_actual_stage26_proposals_ignore_candidate_outcomes(self):
        from scripts.evidence.practical_candidate_linkage.run import construct
        from scripts.evidence.practical_candidate_linkage.common import OCCURRENCES
        original=read(OCCURRENCES)['records'];changed=deepcopy(original)
        for r in changed:r.update(winner=True,candidateShare=999,residual=-100,identityConfidence='confirmed',sourcePublishedCandidateVotes=-1)
        a=construct(occurrences=original);b=construct(occurrences=changed)
        for name in ('proposed-links.json','accepted-relationships.json','persons.json','review-queue.json'):
            self.assertEqual(a[name],b[name])
