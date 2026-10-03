"""Outcome boundaries and paired arithmetic through Stage31's real dependency path."""
from copy import deepcopy
import unittest
from math import sqrt
from scripts.models.expanded_party_substitution import inventory,parties,candidates,evaluation
from scripts.models.expanded_party_substitution.common import local,read,keyed,GEO,S27
from scripts.models.exact_geography_retests import adapters
from scripts.checkpoints import stage25_availability as a
from scripts.models.complete_party_vector.inventory import evidence
from scripts.checkpoints import stage24_evaluation as metric

class ActualDependencyPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv=local('input-inventory.json');cls.party=local('party-vectors.json');cls.pred=local('candidate-predictions.json')
        cls.elections,cls.splits=adapters.datasets();cls.party_elections=evidence()[0]
    def adapt(self,elections):
        return adapters.inventory(elections,self.splits,read(GEO+'geography.json'),read(GEO+'availability.json'),read(a.MAPPING),read(a.CONTINUITY)['records'])
    def test_candidate_outcomes_leave_inputs_and_predictions_fixed(self):
        changed=deepcopy(self.elections)
        for seat in changed[2023]['electorates']:
            seat['winnerCandidateId']=seat['candidates'][-1]['id']
            for c in seat['candidates']:c['votes']=c['votes']+101;c['winner']=False;c['identityConfidence']='unresolved';c['residual']=999
            seat['validCandidateVotes']=sum(c['votes'] for c in seat['candidates'])
        data=self.adapt(changed);new=inventory.build(elections=self.party_elections,data=data)
        self.assertEqual(new,self.inv);self.assertEqual(candidates.build(new,parties.build(new)),self.pred)
        self.assertNotEqual(evaluation.candidate_actuals(changed,self.inv),evaluation.candidate_actuals(self.elections,self.inv))
    def test_local_party_outcomes_cannot_change_constructed_branch(self):
        changed=deepcopy(self.elections);party_elections=deepcopy(self.party_elections)
        for seat in changed[2023]['electorates']:
            nat=next(p for p in seat['parties'] if p['partyKey']=='nationalparty');lab=next(p for p in seat['parties'] if p['partyKey']=='labourparty')
            d=min(100,lab['votes']);nat['votes']+=d;lab['votes']-=d
        for seat in party_elections[2023]['scopes']['general'].values():
            nat=next(p for p in seat['parties'].values() if p['partyKey']=='nationalparty');lab=next(p for p in seat['parties'].values() if p['partyKey']=='labourparty')
            d=min(100,lab['votes']);nat['votes']+=d;lab['votes']-=d;nat['share']=nat['votes']/seat['validVotes'];lab['share']=lab['votes']/seat['validVotes']
        new=inventory.build(elections=party_elections,data=self.adapt(changed));new_party=parties.build(new)
        self.assertEqual(new_party,self.party)
        f=next(f for f in self.inv['folds'] if f['targetYear']==2023 and f['protocol']=='expanding_window')
        v=keyed(self.party['records'],'targetElectorateId');old_rows=keyed(self.inv['candidateRecords'],'targetElectorateId');new_rows=keyed(new['candidateRecords'],'targetElectorateId')
        old=[candidates.attach_inputs(old_rows[c],v[c]) for c in f['evaluationIds']];updated=[candidates.attach_inputs(new_rows[c],v[c]) for c in f['evaluationIds']]
        for s in f['scenarios']:
            self.assertEqual(candidates.apply_saved(old,f['scenarios'][s],s,'predicted'),candidates.apply_saved(updated,f['scenarios'][s],s,'predicted'))
            self.assertNotEqual(candidates.apply_saved(old,f['scenarios'][s],s,'observed'),candidates.apply_saved(updated,f['scenarios'][s],s,'observed'))
        self.assertEqual(new['folds'],self.inv['folds'])
    def test_saved_fit_changes_are_rejected(self):
        altered=deepcopy(self.inv);altered['folds'][1]['scenarios']['printed']['fits']['baseline']['kappa']+=0.01
        with self.assertRaisesRegex(ValueError,'parameters/means'):candidates.build(altered,self.party)
    def test_all_cells_abstain_when_party_group_missing(self):
        folded=deepcopy(self.party);f=next(f for f in self.inv['folds'] if f['targetYear']==2014 and f['protocol']=='expanding_window');cid=f['evaluationIds'][0]
        r=next(r for r in folded['records'] if r['targetElectorateId']==cid);r['targetPartyGroupKeys'].pop(next(iter(r['targetPartyGroupKeys'])))
        case=next(x for x in candidates.build(self.inv,folded)['folds'] if x['foldId']==f['foldId'])
        self.assertEqual(len(case['abstentions']),1)
        for s in case['scenarios'].values():
            for rows in s['cells'].values():self.assertNotIn(cid,[r['targetElectorateId'] for r in rows])
    def test_no_group_support_fixed_zero_but_share_can_move(self):
        f=next(f for f in self.pred['folds'] if f['targetYear']==2023 and f['protocol']=='expanding_window')
        no_group={c['candidateOccurrenceId'] for r in f['contests'] for c in r['candidates'] if c['partyBallotGroupKey'] is None}
        block=f['scenarios']['printed']['cells'];b={c:v for r in block['B'] for c,v in r['candidateShares'].items()};d={c:v for r in block['D'] for c,v in r['candidateShares'].items()}
        self.assertTrue(any(abs(b[c]-d[c])>1e-12 for c in no_group))
        self.assertTrue(all(c['predictedTargetPartySupport']==0 for r in f['contests'] for c in r['candidates'] if c['candidateOccurrenceId'] in no_group))

class SubstitutionArithmetic(unittest.TestCase):
    def test_interaction_sign_and_algebra(self):
        cells={c:{'contestMaePP':v,'contestMsePP2':v*v} for c,v in zip('ABCD',[3,2,5,4.5])}
        r=metric.paired_row({'targetElectorateId':'synthetic','cells':cells})
        self.assertEqual(r['interactionPP'],0.5);self.assertEqual(r['baselineSubstitutionDamagePP'],2);self.assertEqual(r['sSubstitutionDamagePP'],2.5)
    def test_slate_equal_rmse_and_ties(self):
        candidates=[{'candidateOccurrenceId':'a','partyBallotGroupKey':'nationalparty'},{'candidateOccurrenceId':'b','partyBallotGroupKey':None}]
        score=evaluation.score_cell({'a':0.5,'b':0.5},{'candidateShares':{'a':0.6,'b':0.4},'winnerCandidateId':'a'},candidates)
        self.assertEqual(score['predictedWinnerSet'],['a','b']);self.assertTrue(score['tieContainsWinner']);self.assertFalse(score['uniqueCorrect']);self.assertAlmostEqual(score['contestMaePP'],10);self.assertAlmostEqual(sqrt(score['contestMsePP2']),10)
    def test_pooled_weights_count_contests_not_elections(self):
        r=local('evaluation.json');p=next(f for f in r['pooled'] if f['protocol']=='expanding_window' and f['scenario']=='printed')
        self.assertEqual(p['contests'],182);self.assertEqual(p['candidates'],1319)
        self.assertEqual(p['noFitTargetYears'],[2011]);self.assertEqual(p['new2014_2020']['contests'],54);self.assertEqual(p['originalCommon']['contests'],128)
    def test_group_denominators_and_bias_accounting(self):
        for f in local('evaluation.json')['folds']:
            if f['status']!='evaluated':continue
            for c in f['cells'].values():self.assertLess(abs(c['fullSlateSignedBiasPPAccountingCheck']),1e-8)
            for g in f['groups'].values():self.assertLessEqual(g['contestsContainingGroup'],f['contests'])

class PhaseIntegrity(unittest.TestCase):
    def test_altered_committed_prediction_fails_before_evaluation(self):
        from unittest.mock import patch
        from scripts.models.expanded_party_substitution.integrity import verify_phase
        verify_phase('construction')
        with patch('scripts.models.expanded_party_substitution.integrity.sha256') as hashed:
            hashed.return_value.hexdigest.return_value='corrupt'
            with self.assertRaisesRegex(ValueError,'Changed construction artifact'):
                verify_phase('construction')
    def test_evaluation_and_independent_check_manifests(self):
        from scripts.models.expanded_party_substitution.integrity import verify_phase
        verify_phase('evaluation'); verify_phase('verification')
    def test_report_is_generated_from_fixed_scores(self):
        from scripts.models.expanded_party_substitution.report import build, PATH
        self.assertEqual(build(),PATH.read_text())
