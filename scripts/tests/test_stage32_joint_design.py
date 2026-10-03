"""Stage32 design contracts; every share calculation here is explicitly synthetic."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from scripts.checkpoints.joint_candidate_share import inventory, folds, kernel, residuals
from scripts.checkpoints.joint_candidate_share.common import local, read, keyed, LINK, RES, GEO, PARTY, verify_inputs, preserve
from scripts.models.exact_geography_retests import adapters
from scripts.models.expanded_party_substitution.inventory import candidate_frame
from scripts.checkpoints import stage25_availability as a


def synthetic_candidate(p, s=None, r=None):
    return {'constructedPartySupport':p,'observedPartySupport':p,'s0Reported':s,
            'coupledSamePartyPercent':['20','40'] if s is not None else None,
            'R':{v:{'valueFraction':r} for v in ('broad','strict')}}


class SyntheticFamily(unittest.TestCase):
    def setUp(self):
        self.cs=[synthetic_candidate(.6,.8,.1),synthetic_candidate(.3,.2,-.04),synthetic_candidate(0)]
        self.center={'S':.5,'R':.02}
    def test_nesting_all_four_and_conservation(self):
        base=kernel.synthetic_shares(self.cs,self.center,.01,{})
        for m,names in kernel.METHODS.items():
            q=kernel.synthetic_shares(self.cs,self.center,.01,{n:0 for n in names})
            self.assertEqual(q,base);self.assertAlmostEqual(sum(q),1);self.assertTrue(all(v>=0 for v in q))
        s=kernel.synthetic_shares(self.cs,self.center,.01,{'S':1})
        self.assertEqual(s,kernel.synthetic_shares(self.cs,self.center,.01,{'S':1,'R':0}))
        self.assertEqual(kernel.synthetic_shares(self.cs,self.center,.01,{'R':1}),kernel.synthetic_shares(self.cs,self.center,.01,{'S':0,'R':1}))
    def test_missing_feature_neutral_before_normalization(self):
        c=self.cs[-1]
        self.assertEqual(kernel.centered(c,'S',self.center,'broad','printed'),0)
        self.assertEqual(kernel.centered(c,'R',self.center,'broad','printed'),0)
        q=kernel.synthetic_shares(self.cs,self.center,.01,{'R':2})
        self.assertGreater(q[-1],0);self.assertNotEqual(q[-1],kernel.synthetic_shares(self.cs,self.center,.01,{})[-1])
    def test_r_only_feature_and_training_center(self):
        rows=[{'candidates':[synthetic_candidate(.5,None,.1),synthetic_candidate(.5,None,None)]},
              {'candidates':[synthetic_candidate(.5,None,.3)]}]
        center=kernel.means(rows);self.assertAlmostEqual(center['R'],(.5*.1+1*.3)/1.5);self.assertIsNone(center['S'])
        self.assertNotEqual(kernel.synthetic_shares(rows[0]['candidates'],center,.01,{'R':2}),[.5,.5])
    def test_extreme_valid_inputs_stable(self):
        cs=[synthetic_candidate(1,1,2),synthetic_candidate(0,0,-2),synthetic_candidate(0)]
        q=kernel.synthetic_shares(cs,{'S':0,'R':0},.0001,{'S':4,'R':4})
        self.assertAlmostEqual(sum(q),1);self.assertTrue(all(v>0 for v in q))
        with self.assertRaises(ValueError):kernel.synthetic_shares(cs,self.center,0,{'R':1})
    def test_rank_constant_and_collinear_fail_without_pseudoinverse(self):
        rows=[{'candidates':[synthetic_candidate(.8,.5,.1),synthetic_candidate(.2,.5,.1)]}]
        result=kernel.rank_audit(rows,kernel.means(rows),'broad','printed','constructed')
        self.assertTrue(result['methods']['baseline']['estimable']);self.assertFalse(result['methods']['baseline_plus_R']['estimable'])
        rows=[{'candidates':[synthetic_candidate(.8,.8,.8),synthetic_candidate(.2,.2,.2)]}]
        result=kernel.rank_audit(rows,kernel.means(rows),'broad','printed','constructed')
        self.assertFalse(result['methods']['baseline_plus_S_plus_R']['estimable'])
    def test_rounding_and_strict_use_declared_measurements(self):
        c=self.cs[0];c['R']['strict']['valueFraction']=None
        self.assertEqual(kernel.feature(c,'S','broad','selected_lower'),.2)
        self.assertEqual(kernel.feature(c,'S','broad','selected_upper'),.4)
        self.assertEqual(kernel.centered(c,'R',self.center,'strict','printed'),0)


class Applicability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv=local('inventory.json');cls.base=read(PARTY+'input-inventory.json')
        cls.occ=read(LINK+'occurrences.json')['records'];cls.rs=read(RES+'occurrences.json')['records']
        cls.edges=read(LINK+'proposed-links.json')['records'];cls.accepted=read(LINK+'accepted-relationships.json')
    def test_complete_frame_not_stage30_pair_sample(self):
        self.assertEqual(len(self.inv['fullFrame']),356);self.assertEqual(len(self.inv['contestRecords']),245)
        self.assertEqual(sum(len(r['candidates']) for r in self.inv['contestRecords']),1742)
        for view,n in [('broad',452),('strict',386)]:
            self.assertEqual(sum(c['R'][view]['valueFraction'] is not None for r in self.inv['contestRecords'] for c in r['candidates']),n)
        self.assertTrue(any(c['R']['broad']['valueFraction'] is None for r in self.inv['contestRecords'] for c in r['candidates']))
    def test_no_target_residual_requirement(self):
        changed=deepcopy(self.rs)
        for r in changed:
            if r['year']==2023:
                r['normalizedPremium']=None;r['methods']={};r['referenceId']=None;r['normalizationReason']='synthetic_missing_target_outcome'
                r['sourcePublishedCandidateVotes']=0;r['winner']=not r.get('winner',False)
        self.assertEqual(inventory.build(residuals=changed),self.inv)
    def test_no_outgoing_residual_transfer(self):
        row=next(r for r in self.inv['contestRecords'] if r['targetYear']==2023)
        candidate=next(c for c in row['candidates'] if c['R']['broad']['valueFraction'] is None)
        changed=deepcopy(self.rs)
        for r in changed:
            if r['electorateId']==row['sourceElectorateId']:r['normalizedPremium']=.99
        output=inventory.build(residuals=changed);selected=next(r for r in output['contestRecords'] if r['targetElectorateId']==row['targetElectorateId'])
        self.assertIsNone(next(c for c in selected['candidates'] if c['targetOccurrenceId']==candidate['targetOccurrenceId'])['R']['broad']['valueFraction'])
    def test_duplicate_direct_relations_become_neutral_conflict(self):
        edges=deepcopy(self.edges);accepted=deepcopy(self.accepted)
        old=next(e for e in edges if e['edgeId'] in accepted['broadEdgeIds'] and e['targetYear']==2023)
        extra=deepcopy(old);extra['edgeId']+=':synthetic_conflict';edges.append(extra);accepted['broadEdgeIds'].append(extra['edgeId'])
        if old['edgeId'] in accepted['strictEdgeIds']:accepted['strictEdgeIds'].append(extra['edgeId'])
        result=inventory.build(edges=edges,accepted=accepted)
        c=next(c for r in result['contestRecords'] for c in r['candidates'] if c['targetOccurrenceId']==old['targetOccurrenceId'])
        self.assertEqual(c['R']['broad']['reason'],'conflicting_multiple_direct_sources');self.assertIsNone(c['R']['broad']['valueFraction'])
    def test_documented_label_continuity_not_equal_party_strings(self):
        source=keyed(self.occ,'candidateOccurrenceId');edges=keyed(self.edges,'edgeId');n=0
        for row in self.inv['contestRecords']:
            for c in row['candidates']:
                r=c['R']['broad']
                if r['valueFraction'] is not None and edges[r['edgeId']]['contextAssessment']=='documented_single_party_label_continuity':
                    self.assertNotEqual(source[r['sourceOccurrenceId']]['candidateAffiliationKey'],source[c['targetOccurrenceId']]['candidateAffiliationKey']);n+=1
        self.assertEqual(n,13)
    def test_shared_group_once_and_missing_group_abstention(self):
        row=next(r for r in self.inv['contestRecords'] if any(c['partyBallotGroupKey']=='freedomsnz' for c in r['candidates']))
        self.assertEqual(sum(c['partyBallotGroupKey']=='freedomsnz' for c in row['candidates']),1)
        changed=deepcopy(read(PARTY+'party-vectors.json'));vec=next(v for v in changed['records'] if v['targetElectorateId']==row['targetElectorateId']);vec['targetPartyGroupKeys'].pop(next(iter(vec['targetPartyGroupKeys'])))
        output=inventory.build(party=changed);r=next(r for r in output['contestRecords'] if r['targetElectorateId']==row['targetElectorateId'])
        self.assertEqual(r['status'],'abstain');self.assertEqual(len(r['candidates']),len(row['candidates']))
    def test_no_historical_fit_or_shares_called(self):
        with patch('scripts.checkpoints.stage22_fit.fit',side_effect=AssertionError('No fitting')),patch.object(kernel,'synthetic_shares',side_effect=AssertionError('No historical predictions')):
            self.assertEqual(inventory.build(),self.inv);folds.build(self.inv)
    def test_provenance_and_preservation(self):
        verify_inputs();self.assertEqual(preserve(),1427)
        with patch('scripts.checkpoints.joint_candidate_share.common.digest',return_value='corrupt'):
            with self.assertRaisesRegex(ValueError,'consumed input'):verify_inputs()


class ChronologicalPaths(unittest.TestCase):
    def test_canonical_fold_counts_and_earliest_abstentions(self):
        fs=local('fold-plan.json')['folds']
        self.assertEqual([len(f['trainingIds']) for f in fs if f['branch']=='primary'],[0,63,83,147,181])
        self.assertEqual([len(f['evaluationIds']) for f in fs if f['branch']=='primary'],[63,20,64,34,64])
        self.assertEqual([len(f['trainingIds']) for f in fs if f['branch']=='separated'],[0,0,63,83,147])
        self.assertFalse(next(f for f in fs if f['branch']=='primary' and f['targetYear']==2011)['fourModelFitReady'])
    def test_actual_adapter_candidate_outcomes_and_winners_independent(self):
        elections,splits=adapters.datasets();changed=deepcopy(elections)
        for s in changed[2023]['electorates']:
            s['winnerCandidateId']=s['candidates'][-1]['id']
            for c in s['candidates']:c['votes']+=13;c['winner']=False;c['residual']=777
            s['validCandidateVotes']=sum(c['votes'] for c in s['candidates'])
        data=adapters.inventory(changed,splits,read(GEO+'geography.json'),read(GEO+'availability.json'),read(a.MAPPING),read(a.CONTINUITY)['records'])
        base=deepcopy(read(PARTY+'input-inventory.json'));base['candidateRecords']=candidate_frame(data,read(a.MAPPING))
        self.assertEqual(inventory.build(base=base),local('inventory.json'))
    def test_target_and_future_training_rejected(self):
        canonical=deepcopy(read(GEO+'fold-plan.json')['folds']);f=next(f for f in canonical if f['family']=='complete_share_baseline_s' and f['chronologyProtocol']=='expanding_window' and f['targetYear']==2017)
        f['trainingIds'].append(f['evaluationIds'][0])
        with self.assertRaisesRegex(ValueError,'overlap'):folds.build(local('inventory.json'),canonical)
    def test_training_centers_never_use_heldout_features(self):
        inv=deepcopy(local('inventory.json'));original=folds.build(inv)
        for r in inv['contestRecords']:
            if r['targetYear']==2023:
                for c in r['candidates']:
                    if c['s0Reported'] is not None:
                        c['s0Reported']=.99;c['coupledSamePartyPercent']=['99','99']
                    for v in ('broad','strict'):c['R'][v]['valueFraction']=.5
        changed=folds.build(inv)
        self.assertEqual([f['trainingOnlyMeans'] for f in original['folds']],[f['trainingOnlyMeans'] for f in changed['folds']])
        self.assertEqual([f['evaluationIds'] for f in original['folds']],[f['evaluationIds'] for f in changed['folds']])
    def test_all_four_and_strict_keep_complete_slates(self):
        fs=local('fold-plan.json')['folds']
        for year in (2011,2014,2017,2020,2023):
            primary=next(f for f in fs if f['branch']=='primary' and f['targetYear']==year)
            strict=next(f for f in fs if f['branch']=='strict' and f['targetYear']==year)
            self.assertEqual(primary['evaluationCandidateIds'],strict['evaluationCandidateIds']);self.assertEqual(primary['trainingCandidateIds'],strict['trainingCandidateIds'])
            fixed=next(f for f in fs if f['branch']=='primary_fixed_to_observed' and f['targetYear']==year)
            self.assertEqual(primary['trainingOnlyMeans'],fixed['trainingOnlyMeans']);self.assertEqual(primary['numericalAudit'],fixed['numericalAudit'])

class SupplementalContracts(unittest.TestCase):
    def test_linkage_dependency_ignores_outcomes_and_inherited_confidence(self):
        from scripts.evidence.practical_candidate_linkage.run import construct
        rows=deepcopy(read(RES+'occurrences.json')['records'])
        for r in rows:
            r['sourcePublishedCandidateVotes']=0;r['normalizedPremium']=999
            r['winner']=not r.get('winner',False);r['identityConfidence']='confirmed'
        outputs=construct(occurrences=rows)
        self.assertEqual(outputs['accepted-relationships.json']['broadEdgeIds'],read(LINK+'accepted-relationships.json')['broadEdgeIds'])
        self.assertEqual(outputs['accepted-relationships.json']['strictEdgeIds'],read(LINK+'accepted-relationships.json')['strictEdgeIds'])
    def test_full_candidate_coverage_includes_excluded_and_maori_evidence_only(self):
        inv=local('inventory.json');cs=inv['candidateCoverageFrame']
        self.assertEqual(len(cs),2485);self.assertEqual(len({c['targetOccurrenceId'] for c in cs}),2485)
        self.assertEqual(sum(c['modelEligibility'] for c in cs),1742)
        for c in cs:
            if c['scope']=='maori':self.assertFalse(c['modelEligibility'])
    def test_independent_training_mean_arithmetic(self):
        from fractions import Fraction
        inv=local('inventory.json');records=keyed(inv['contestRecords'],'targetElectorateId')
        f=next(f for f in local('fold-plan.json')['folds'] if f['branch']=='primary' and f['targetYear']==2023)
        for name in ('S','R'):
            numerator=Fraction(0);denominator=Fraction(0)
            for cid in f['trainingIds']:
                cs=records[cid]['candidates'];weight=Fraction(1,len(cs))
                for c in cs:
                    value=c['s0Reported'] if name=='S' else c['R']['broad']['valueFraction']
                    if value is not None:numerator+=Fraction(str(value))*weight;denominator+=weight
            self.assertAlmostEqual(float(numerator/denominator),f['trainingOnlyMeans'][name],places=14)
