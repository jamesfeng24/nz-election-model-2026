"""Continuous transport logic, actual adapters and unchanged historical contracts."""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from math import fsum, sqrt
import unittest
from unittest.mock import patch

from scripts.transport.geography import all_rows
from scripts.transport.continuous.common import read, PREFIX, METHOD, SNAPSHOT, verify
from scripts.transport.continuous.features import (
    context, flow_index, weighted, candidate_features, selected_link,
    links_for_geography, source_s, source_r,
)
from scripts.transport.continuous.inventory import inventory
from scripts.transport.continuous.construction import build, columns, shares
from scripts.transport.continuous.evaluation import build as evaluate
from scripts.transport.continuous.readiness import build as readiness, features as ready_features
from scripts.evidence.practical_candidate_linkage.names import parse_name


def component(mass, value):
    return {'sourceElectorateId':'source', 'partyMassExact':str(mass),
            'valueFraction':value, 'reason':None}


def link(source='s2', target='target', flags=None):
    return {'sourceOccurrenceId':source+'-candidate', 'targetOccurrenceId':target,
            'sourceYear':2017, 'targetYear':2020, 'sourceElectorateId':source,
            'targetElectorateId':'target-seat', 'label':'accepted_algorithmic_same_person',
            'ruleFlags':['exact_name'] if flags is None else flags, 'edgeId':source+'->'+target}


def synthetic_context():
    return {'continuity':{(2017,2020,'national'):{'status':'eligible',
                'source':{'sourceKey':'national'}}},
            'residuals':{'s2-candidate':{'candidateOccurrenceId':'s2-candidate',
                'electorateId':'s2', 'year':2017, 'normalizedPremium':0.3,
                'candidateContestStatus':'held', 'referenceId':'source-reference'}}}


class WeightedFeatureTests(unittest.TestCase):
    def test_exact_single_predecessor_is_saved_centered_feature(self):
        value=weighted([component('37',0.72)],0.6)
        self.assertAlmostEqual(value['contribution'],0.12)
        self.assertEqual(value['supportedWeight'],1)
        self.assertEqual(value['unsupportedWeight'],0)
        self.assertEqual(value['components'][0]['weightExact'],'1')

    def test_center_before_weighting_with_unsupported_mass(self):
        value=weighted([component('10',0.8),component('30',None)],0.6)
        self.assertAlmostEqual(value['contribution'],0.05)
        self.assertEqual(value['supportedWeight'],0.25)
        self.assertEqual(value['unsupportedWeight'],0.75)
        self.assertNotAlmostEqual(value['contribution'],0.8-0.6)
        self.assertNotAlmostEqual(value['contribution'],0.25*0.8-0.6)

    def test_all_unsupported_is_neutral_even_with_missing_mean(self):
        value=weighted([component('1',None),component('2',None)],None)
        self.assertEqual(value['contribution'],0)
        self.assertEqual(value['unsupportedWeight'],1)
        self.assertEqual(value['reason'],'all_predecessor_features_unsupported')

    def test_zero_mass_is_undefined_not_observed_strength(self):
        value=weighted([component('0',0.9)],0.4)
        self.assertEqual(value['contribution'],0)
        self.assertEqual(value['supportedWeight'],0)
        self.assertEqual(value['reason'],'zero_or_undefined_transported_party_mass')

    def test_corrupt_negative_mass_and_nonfinite_features_rejected(self):
        for components in ([component('-1',None)], [component('-1',0.4),component('2',0.5)]):
            with self.assertRaises(ValueError):weighted(components,0.4)
        with self.assertRaises(ValueError):weighted([component('1',float('nan'))],0.4)
        with self.assertRaises(ValueError):weighted([component('1',0.5)],None)

    def test_nonfinite_saved_center_rejected(self):
        for center in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):weighted([component('1',0.5)],center)

    def test_population_and_known_fragment_party_weights_are_distinct_synthetic(self):
        # Explicitly synthetic: equal population fragments need not carry equal party votes.
        uniform=weighted([component('50',0.9),component('50',0.1)],0.5)
        known_fragment=weighted([component('80',0.9),component('20',0.1)],0.5)
        self.assertAlmostEqual(uniform['contribution'],0)
        self.assertAlmostEqual(known_fragment['contribution'],0.24)
        self.assertNotEqual(uniform['contribution'],known_fragment['contribution'])


class RelationshipAndSourceTests(unittest.TestCase):
    def test_nondominant_unique_same_person_source_is_allowed(self):
        edge=link()
        accepted,reason=selected_link('target',2017,2020,[edge],{'s1','s2'},'broad')
        self.assertEqual(accepted,edge);self.assertIsNone(reason)
        value,reason,evidence=source_r(synthetic_context(),'s2',accepted)
        self.assertEqual(value,0.3);self.assertIsNone(reason)
        self.assertEqual(evidence['sourceOccurrenceId'],'s2-candidate')

    def test_competing_links_are_not_resolved_by_predecessor_filter(self):
        edge=link();competing=link('outside')
        accepted,reason=selected_link('target',2017,2020,[edge,competing],{'s2'},'broad')
        self.assertIsNone(accepted);self.assertIn('no_unique',reason)
        accepted,reason=selected_link('target',2017,2020,[competing],{'s2'},'broad')
        self.assertIsNone(accepted);self.assertIn('outside_genuine',reason)

    def test_outgoing_person_and_nonmatch_do_not_transfer_residual(self):
        value,reason,_=source_r(synthetic_context(),'s1',link())
        self.assertIsNone(value);self.assertEqual(reason,'no_same_person_in_this_predecessor')
        accepted,reason=selected_link('replacement',2017,2020,[link()],{'s2'},'broad')
        self.assertIsNone(accepted);self.assertIn('not_replacement',reason)

    def test_strict_sensitivity_excludes_nickname_but_keeps_documentary(self):
        edge=link(flags=['frozen_nickname'])
        self.assertIsNotNone(selected_link('target',2017,2020,[edge],{'s2'},'broad')[0])
        self.assertIsNone(selected_link('target',2017,2020,[edge],{'s2'},'strict')[0])
        edge['label']='documentary_same_person'
        self.assertIsNotNone(selected_link('target',2017,2020,[edge],{'s2'},'strict')[0])

    def test_cancelled_or_missing_source_residual_is_neutral(self):
        ctx=synthetic_context();ctx['residuals']['s2-candidate']['candidateContestStatus']='cancelled'
        self.assertIsNone(source_r(ctx,'s2',link())[0])
        ctx['residuals'].clear();self.assertIsNone(source_r(ctx,'s2',link())[0])

    def test_source_split_table_missing_and_cancelled_keep_explicit_reasons(self):
        ctx={'seats':{2017:{'s':{'validCandidateVotes':100}}},'splits':{2017:{}}}
        self.assertEqual(source_s(ctx,'s',{}, {},2017,2020)[1],'missing_source_split_table')
        ctx['seats'][2017]['s']['validCandidateVotes']=0
        self.assertEqual(source_s(ctx,'s',{}, {},2017,2020)[1],'cancelled_source_candidate_contest')

    def test_continuous_components_keep_every_predecessor_mass(self):
        ctx=synthetic_context();g={'sourceYear':2017,'targetYear':2020}
        candidate={'partyKey':'national','candidateOccurrenceId':'target'}
        flows=[{'sourceElectorateId':'s1','partyMassExact':{'national':'30'}},
               {'sourceElectorateId':'s2','partyMassExact':{'national':'10'}}]
        def split(_,sid,*unused):return (0.8,None,{}) if sid=='s1' else (None,'missing_table',None)
        with patch('scripts.transport.continuous.features.source_s',side_effect=split):
            f=candidate_features(ctx,g,candidate,{},flows,[link()],{'S':0.6,'R':0.1})
        self.assertAlmostEqual(f['S']['contribution'],0.15)
        self.assertEqual(f['S']['supportedWeight'],0.75)
        self.assertAlmostEqual(f['R']['contribution'],0.05)
        self.assertEqual(f['R']['supportedWeight'],0.25)
        self.assertEqual(len(f['S']['components']),2)
        self.assertEqual(sum(Fraction(c['weightExact']) for c in f['R']['components']),1)

    def test_duplicate_predecessor_party_mass_rejected(self):
        flow={'sourceElectorateId':'s2','partyMassExact':{'national':'10'}}
        with self.assertRaisesRegex(ValueError,'Duplicate predecessor'):
            candidate_features(synthetic_context(),{'sourceYear':2017,'targetYear':2020},
                {'partyKey':'national','candidateOccurrenceId':'target'},{},[flow,flow],[],{'S':0.6,'R':0.1})

    def test_no_group_entry_and_missing_continuity_are_neutral(self):
        ctx=synthetic_context();g={'sourceYear':2017,'targetYear':2020}
        ctx['continuity'][(2017,2020,'shared-alliance')]={'status':'entrant','source':None}
        for group in (None,'shared-alliance','unknown'):
            f=candidate_features(ctx,g,{'partyKey':group,'candidateOccurrenceId':'target'}, {},[],[link()],{'S':0.6,'R':0.1})
            self.assertTrue(all(x['contribution']==0 and x['supportedWeight']==0 for x in f.values()))
        # Whole shared-group mass must not be replaced by a constituent's arbitrary share.
        ctx['continuity'][(2017,2020,'shared-alliance')]={'status':'eligible','source':{'sourceKey':'whole-group'}}
        with self.assertRaisesRegex(ValueError,'mass missing'):
            candidate_features(ctx,g,{'partyKey':'shared-alliance','candidateOccurrenceId':'target'}, {},
                [{'sourceElectorateId':'s1','partyMassExact':{'constituent':'12'}}],[],{'S':0.6,'R':0.1})

    def test_geographic_only_reassessment_respects_cancelled_and_conflicts(self):
        def row(cid,year,held=True):return {'candidateOccurrenceId':cid,'year':year,
            'candidateContestStatus':'held' if held else 'cancelled',
            'parsedName':parse_name('Smith, Robert')}
        original=link();original.update(sourceOccurrenceId='source',targetOccurrenceId='target',
            label='unresolved_ambiguous',ambiguityType='seat_change_or_nonexact_geography',
            nameAssessment={'compatible':True},competingOccurrenceIds=[],
            contextAssessment='documented_party_continuity_same_original_affiliation')
        geo=[{'targetElectorateId':'target-seat','predecessors':[{'sourceElectorateId':'s2'}]}]
        aliases={'pairs':[['Bob','Robert']]}
        for held,competing in ((True,False),(False,False),(True,True)):
            edge=deepcopy(original)
            if competing:edge['competingOccurrenceIds']=['other']
            with patch('scripts.transport.continuous.features.read',side_effect=lambda p:
                    aliases if p.endswith('aliases.json') else {'records':[edge]}):
                assessed,_=links_for_geography(geo,[row('source',2017,held),row('target',2020)])
            accepted=assessed[0]['label']=='accepted_algorithmic_same_person'
            self.assertEqual(accepted,held and not competing)
            self.assertEqual(edge,original if not competing else dict(original,competingOccurrenceIds=['other']))


class ActualAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo=all_rows();cls.ctx=context()
        cls.edges,cls.links=links_for_geography(cls.geo,cls.ctx['occurrences'])
        cls.flows=flow_index(cls.geo,cls.ctx['occurrences'])
        cls.inv=inventory(cls.geo,cls.ctx,cls.flows,cls.edges)
        cls.samples=read(PREFIX+'/sample-manifest.json')['folds']
        cls.saved=read('data/processed/models/joint-candidate-share/construction.json')
        cls.old=read('data/processed/forecast-transport/construction.json')
        cls.predictions=build(cls.inv,cls.samples,cls.saved,cls.old)

    def test_full_frame_identical_complete_slates_and_stage41_reproduction(self):
        for fold,n in zip(self.predictions['folds'],(64,65)):
            self.assertTrue(fold['stage41ReproductionWithin1eMinus12'])
            self.assertFalse(fold['fittingPerformed'])
            ids=[p['targetElectorateId'] for p in fold['predictions']['continuous']]
            self.assertEqual(len(ids),n)
            for predictions in fold['predictions'].values():
                self.assertEqual(ids,[p['targetElectorateId'] for p in predictions])
                for p in predictions:
                    self.assertAlmostEqual(sum(p['candidateShares'].values()),1,places=12)
                    self.assertTrue(all(q>=0 for q in p['candidateShares'].values()))
        self.assertTrue(any(r['transportTier']=='fallback' for r in self.inv['records']))
        self.assertEqual(len(self.inv['fullFrame']),143)

    def test_exact_feature_and_prediction_equivalence_under_both_views(self):
        for row in self.inv['records']:
            if row['transportTier']!='exact':continue
            for candidate in row['candidates']:
                for view in ('broad','strict'):
                    for a,b in zip(columns(candidate,'exact','continuous',view),columns(candidate,'exact','exact',view)):
                        self.assertAlmostEqual(a,b,places=12)

    def test_actual_heldout_outcomes_and_target_normalization_independence(self):
        ctx=deepcopy(self.ctx)
        for year in (2014,2020):
            for seat in ctx['elections'][year]['electorates']:
                seat['winnerCandidateId']='counterfactual'
                for candidate in seat['candidates']:candidate.update(votes=123,winner=True,residual=999,modelError=-999)
        for occurrence in ctx['occurrences']:
            if occurrence['year'] in (2014,2020):occurrence.update(winner=True,votes=999999,residual=999)
        for r in ctx['residuals'].values():
            if r['year'] in (2014,2020):r.update(normalizedPremium=999,referenceId='counterfactual-target-reference')
        changed_edges,changed_links=links_for_geography(self.geo,ctx['occurrences'])
        self.assertEqual(changed_edges,self.edges);self.assertEqual(changed_links,self.links)
        changed=inventory(self.geo,ctx,self.flows,changed_edges)
        self.assertTrue(changed==self.inv)
        self.assertTrue(build(changed,self.samples,self.saved,self.old)==self.predictions)

    def test_party_flows_conserve_each_source_party_and_use_all_predecessors(self):
        totals=defaultdict(Fraction);votes={}
        for tid,flows in self.flows.items():
            g=next(g for g in self.geo if g['targetElectorateId']==tid)
            self.assertEqual({f['sourceElectorateId'] for f in flows},{p['sourceElectorateId'] for p in g['predecessors']})
            for flow in flows:
                for party,mass in flow['partyMassExact'].items():
                    key=(flow['sourceElectorateId'],party)
                    totals[key]+=Fraction(mass);votes[key]=flow['sourceVotes'][party]
        self.assertTrue(totals)
        for key,total in totals.items():self.assertEqual(total,votes[key])
        for row in self.inv['records']:
            for candidate in row['candidates']:
                for feature in candidate['continuous'].values():
                    if feature['totalMassExact'] is not None and Fraction(feature['totalMassExact'])>0:
                        self.assertEqual(sum(Fraction(c['weightExact']) for c in feature['components']),1)
                        self.assertAlmostEqual(feature['supportedWeight']+feature['unsupportedWeight'],1,places=12)

    def test_target_local_party_inputs_are_distinct_from_flow_features(self):
        ctx=deepcopy(self.ctx)
        for seat in ctx['elections'][2014]['electorates']:
            for party in seat['parties']:
                if party['partyKey']=='nationalparty':party['votes']+=1
        changed=inventory(self.geo,ctx,self.flows,self.edges)
        continuous_before=[c['continuous'] for r in self.inv['records'] for c in r['candidates']]
        continuous_after=[c['continuous'] for r in changed['records'] for c in r['candidates']]
        self.assertTrue(continuous_before==continuous_after)
        # The historical compatibility guard correctly notices changed permitted input.
        with self.assertRaisesRegex(ValueError,'Stage41 prediction reproduction failed'):
            build(changed,self.samples,self.saved,self.old)
        parameters=self.samples[0]['savedFit']['parameters']
        def candidate_vectors(inv):
            return [shares([c['observedPartySupport'] for c in row['candidates']],
                [columns(c,row['transportTier'],'continuous','broad') for c in row['candidates']],parameters)
                for row in inv['records'] if row['targetYear']==2014]
        self.assertNotEqual(candidate_vectors(changed),candidate_vectors(self.inv))

    def test_metrics_and_paired_gains_have_independent_arithmetic(self):
        evaluation=evaluate(self.predictions,self.inv)
        for fold in evaluation['folds']:
            rows=fold['records'];mae={}
            for branch in fold['samples']['full']['metrics']:
                contest_errors=[];contest_mses=[]
                for row in rows:
                    error=list(row['errors'][branch]['candidateErrorsPP'].values())
                    contest_errors.append(fsum(abs(e) for e in error)/len(error))
                    contest_mses.append(fsum(e*e for e in error)/len(error))
                mae[branch]=fsum(contest_errors)/len(rows)
                published=fold['samples']['full']['metrics'][branch]
                self.assertAlmostEqual(published['maePP'],mae[branch],places=12)
                self.assertAlmostEqual(published['rmsePP'],sqrt(fsum(contest_mses)/len(rows)),places=12)
            for pair in fold['samples']['full']['pairs'].values():
                self.assertAlmostEqual(pair['maeGainPP'],mae[pair['comparator']]-mae[pair['model']],places=12)
            self.assertEqual(sum(len(fold['samples'][tier]['pairs']['continuous_versus_exact_fallback']['pairedContests'])
                for tier in ('exact','approximate_95','approximate_90','fallback')),len(rows))

    def test_target_outcomes_affect_evaluation_only(self):
        elections={y:read(f'data/processed/elections/{y}.json') for y in (2014,2020)}
        before=evaluate(self.predictions,self.inv,elections)
        tid=self.predictions['folds'][0]['predictions']['continuous'][0]['targetElectorateId']
        seat=next(s for s in elections[2014]['electorates'] if s['id']==tid)
        values=[c['votes'] for c in seat['candidates']]
        for candidate,votes in zip(seat['candidates'],reversed(values)):candidate['votes']=votes
        self.assertTrue(evaluate(self.predictions,self.inv,elections)!=before)
        self.assertTrue(build(self.inv,self.samples,self.saved,self.old)==self.predictions)

    def test_parameter_center_and_chronology_changes_are_rejected(self):
        for mutate in ('mean','parameters','training'):
            saved=deepcopy(self.saved);sample=self.samples[0]
            fold=next(f for f in saved['folds'] if f['id']==sample['savedFoldId'])
            if mutate=='mean':fold['trainingOnlyMeans']['S']+=0.01
            elif mutate=='parameters':fold['fits'][METHOD]['parameters']['theta'][0]+=0.01
            else:fold['trainingIds'].append('nz-general-2023-electorate-01')
            with self.assertRaisesRegex(ValueError,'parameters/preprocessing changed'):
                build(self.inv,self.samples,saved,self.old)
        samples=deepcopy(self.samples);saved=deepcopy(self.saved)
        injected='nz-general-2023-electorate-01'
        samples[0]['trainingIds'].append(injected)
        fold=next(f for f in saved['folds'] if f['id']==samples[0]['savedFoldId'])
        fold['trainingIds'].append(injected)
        with self.assertRaisesRegex(ValueError,'Target/later fit'):build(self.inv,samples,saved,self.old)

    def test_broad_strict_support_is_reproducible_and_no_prior_links_changed(self):
        for row in self.inv['records']:
            for candidate in row['candidates']:
                f=candidate['continuous']
                self.assertLessEqual(f['RStrict']['supportedWeight'],f['R']['supportedWeight'])
        original=read('data/processed/evidence/practical-candidate-linkage/proposed-links.json')['records']
        baseline={e['edgeId']:e for e in original}
        for edge in self.links['records']:
            self.assertEqual(edge['originalReason'],'seat_change_or_nonexact_geography')
            self.assertEqual(baseline[edge['edgeId']]['label'],edge['originalLabel'])
        self.assertFalse(self.links['priorAdjudicationsChanged'])

    def test_deterministic_inventory_and_consumed_source_preservation(self):
        self.assertTrue(inventory(self.geo,self.ctx,self.flows,self.edges)==self.inv)
        self.assertTrue(verify()>1731)


class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.ready=readiness()

    def test_incomplete_slates_and_separate_maori_interface(self):
        self.assertEqual(len(self.ready['seatRecords']),71)
        self.assertEqual(len(self.ready['candidateRecords']),206)
        self.assertEqual(self.ready['coverage']['completeSlates'],0)
        self.assertTrue(all(not s['candidateForecastPermitted'] for s in self.ready['seatRecords']))
        self.assertTrue(all(not c['candidateSharesCalculated'] for c in self.ready['candidateRecords']))
        self.assertTrue(all(c['maoriRequiresSeparateBaseline'] for c in self.ready['candidateRecords'] if c['scope']=='maori'))
        self.assertEqual(self.ready['coverage']['candidateFeatureSupport']['maori']['S'],0)

    def test_2026_target_outcome_mutation_does_not_change_readiness(self):
        snapshot=read(SNAPSHOT+'snapshot.json')
        for candidate in snapshot['occurrences']:candidate.update(votes=999999,winner=True,residual=42)
        self.assertTrue(readiness(snapshot=snapshot)==self.ready)

    def test_party_seat_s_is_independent_of_candidate_announcements(self):
        snapshot=read(SNAPSHOT+'snapshot.json')
        snapshot['occurrences']=[]
        empty=readiness(snapshot=snapshot)
        self.assertEqual(empty['sourcePartySeatRecords'],self.ready['sourcePartySeatRecords'])
        self.assertEqual(empty['candidateRecords'],[])
        self.assertEqual(empty['coverage']['sourcePartySeatSSupport'],self.ready['coverage']['sourcePartySeatSSupport'])

    def test_readiness_weights_preserve_any_predecessor_identity_and_strict(self):
        for candidate in self.ready['candidateRecords']:
            f=candidate['continuous']
            self.assertLessEqual(f['RStrict']['supportedWeight'],f['R']['supportedWeight'])
            for name in ('S','R','RStrict'):
                if f[name]['totalMassExact'] is None or Fraction(f[name]['totalMassExact'])<=0:continue
                self.assertEqual(sum(Fraction(p['weightExact']) for p in f[name]['components']),1)
                supported=[p for p in f[name]['components'] if p['valueFraction'] is not None and Fraction(p['partyMassExact'])>0]
                if name!='S' and supported:
                    self.assertEqual(len(supported),1)
                    self.assertEqual(supported[0]['evidence']['sourceOccurrenceId'],candidate['identityEvidence']['sourceOccurrenceId'])

    def test_synthetic_2026_nondominant_r_and_outside_predecessor_fallback(self):
        candidate={'ballotGroupKey':'national','originalAffiliation':'national'}
        seat={'scope':'general','exactSourceElectorateId':None}
        relations={'national':{'sourceBallotGroupKey':'national'}}
        flows=[{'sourceElectorateId':'s1','partyMassExact':{'national':'30'}},
               {'sourceElectorateId':'s2','partyMassExact':{'national':'10'}}]
        residuals={'returnee':{'year':2023,'electorateId':'s2','normalizedPremium':0.3,
            'candidateContestStatus':'held','candidateOccurrenceId':'returnee','referenceId':'source'}}
        identity={'sourceOccurrenceId':'returnee','broadAccepted':True,'strictAccepted':False,
            'geographyCompatible':False,'label':'accepted_algorithmic_same_person'}
        neutral={'valueFraction':None,'reason':'synthetic_missing_split'}
        with patch('scripts.transport.continuous.readiness.s_feature',return_value=neutral):
            f=ready_features(candidate,seat,flows,relations,[],[],identity,residuals,{'S':0.6,'R':0.1})
            self.assertAlmostEqual(f['R']['contribution'],0.05)
            self.assertEqual(f['R']['supportedWeight'],0.25)
            self.assertEqual(f['RStrict']['contribution'],0)
            residuals['returnee']['electorateId']='outside'
            f=ready_features(candidate,seat,flows,relations,[],[],identity,residuals,{'S':0.6,'R':0.1})
            self.assertEqual(f['R']['contribution'],0)
            self.assertEqual(f['R']['supportedWeight'],0)


class CandidateArithmeticTests(unittest.TestCase):
    def test_extreme_valid_inputs_conserve_complete_slate(self):
        parameters={'status':'fitted','kappa':0.0001,'theta':[4,-4]}
        result=shares([0,1,0],[[1,-1],[-1,1],[0,0]],parameters)
        self.assertAlmostEqual(sum(result),1,places=12)
        self.assertTrue(all(0<=q<=1 for q in result))
        with self.assertRaises(ValueError):shares([0.5,-0.1],[[0,0],[0,0]],parameters)
        with self.assertRaises(ValueError):shares([0.5],[[0,0]],dict(parameters,theta=[4.1,0]))

    def test_fixed_normalization_moves_unsupported_candidates_too(self):
        parameters={'status':'fitted','kappa':0.01,'theta':[1,1]}
        before=shares([0.4,0.4],[[0,0],[0,0]],parameters)
        after=shares([0.4,0.4],[[0.2,0],[0,0]],parameters)
        self.assertLess(after[1],before[1])
        self.assertGreater(after[0],before[0])


if __name__=='__main__':unittest.main()
