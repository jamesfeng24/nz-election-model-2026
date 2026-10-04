"""Focused transport fixtures and complete actual-adapter information-flow checks."""
from copy import deepcopy
from fractions import Fraction
import unittest

from scripts.transport.common import read, PREFIX, SNAPSHOT, LINKS, METHOD, preserve, verify_inputs
from scripts.transport.geography import classification, admitted, all_rows, relationship_records
from scripts.transport.history import inventory, defaults, r_source, supplemental_links
from scripts.transport.construction import build as construct, feature_rows
from scripts.transport.evaluation import build as evaluate, errors, aggregate
from scripts.transport.readiness import build as readiness
from scripts.checkpoints.stage25_availability import target_candidates
from scripts.evidence.practical_candidate_linkage.names import alias_pairs


def ratio(n,d=100):return {'numerator':n,'denominator':d}


class GeographicPolicyTests(unittest.TestCase):
    def setUp(self):
        self.g={'certifiedTwoSidedExact':False,'dominantPredecessorId':'s',
                'dominantTargetInheritanceLower':ratio(95),'dominantSourceRetentionLower':ratio(95)}

    def test_rational_threshold_boundaries(self):
        self.assertEqual(classification(self.g),'approximate_95')
        self.g['dominantSourceRetentionLower']=ratio(94999,100000)
        self.assertEqual(classification(self.g),'approximate_90')
        self.assertTrue(admitted(self.g,90));self.assertFalse(admitted(self.g,95))
        self.g['dominantTargetInheritanceLower']=ratio(89999,100000)
        self.assertEqual(classification(self.g),'fallback')

    def test_one_sided_missing_and_ambiguous(self):
        self.g['dominantTargetInheritanceLower']=ratio(100)
        self.g['dominantSourceRetentionLower']=None
        self.assertEqual(classification(self.g),'fallback')
        self.g['dominantSourceRetentionLower']=ratio(100)
        self.g['dominantPredecessorId']=None
        self.assertEqual(classification(self.g),'fallback')

    def test_certification_is_not_rounded_overlap(self):
        self.g['dominantTargetInheritanceLower']=ratio(100)
        self.g['dominantSourceRetentionLower']=ratio(100)
        self.assertEqual(classification(self.g),'approximate_95')
        self.g['certifiedTwoSidedExact']=True
        self.assertEqual(classification(self.g),'exact')

    def test_canonical_nested_counts(self):
        rows=all_rows()
        for y,exact,n95,n90 in ((2014,20,28,37),(2020,34,41,47),(2026,14,29,37)):
            group=[r for r in rows if r['scope']=='general' and r['targetYear']==y]
            self.assertEqual(sum(classification(r)=='exact' for r in group),exact)
            self.assertEqual(sum(admitted(r,95) for r in group),n95)
            self.assertEqual(sum(admitted(r,90) for r in group),n90)

    def test_suppressed_incoming_identity_stays_approximate(self):
        rows=[r for r in all_rows() if r['targetYear']==2026]
        tt=next(r for r in rows if r['targetElectorateName']=='Te Tai Tokerau')
        self.assertFalse(tt['certifiedTwoSidedExact']);self.assertEqual(classification(tt),'approximate_95')

    def test_multiple_predecessors_and_cancelled_sources_remain_visible(self):
        rows=relationship_records(all_rows(),read(LINKS+'occurrences.json')['records'])
        self.assertEqual(len(rows),len({r['relationshipId'] for r in rows}))
        pw=[r for r in rows if r['targetYear']==2026 and r['sourceCandidateContestStatuses']==['cancelled']]
        self.assertTrue(pw)
        self.assertTrue(any(not r['selectedDominantPredecessor'] for r in rows))


class ActualTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo=all_rows();cls.inputs=defaults();cls.inv=inventory(cls.geo,inputs=cls.inputs)
        cls.construction=construct(cls.inv)

    def test_frozen_common_slates_and_saved_fit_reproduction(self):
        for fold,n in zip(self.construction['folds'],(37,47)):
            ids=[p['targetElectorateId'] for p in fold['predictions']['fallback']]
            self.assertEqual(len(ids),n)
            for branch,ps in fold['predictions'].items():
                self.assertEqual(ids,[p['targetElectorateId'] for p in ps])
                for pred in ps:self.assertAlmostEqual(sum(pred['candidateShares'].values()),1,places=12)
            self.assertLessEqual(fold['exactStage33MaximumShareDeviation'],1e-12)

    def test_holdout_candidate_results_and_residuals_cannot_affect_pipeline(self):
        inputs=list(deepcopy(self.inputs))
        for y in (2014,2020):
            for seat in inputs[0][y]['electorates']:
                seat['winnerCandidateId']='counterfactual'
                for c in seat['candidates']:c.update(votes=123,winner=True,modelError=999)
        residuals={r['candidateOccurrenceId']:r for r in read('data/processed/models/candidate-overperformance/occurrences.json')['records']}
        for r in residuals.values():
            if r['year'] in (2014,2020):r['normalizedPremium']=999
        changed=inventory(self.geo,inputs=tuple(inputs),residuals=residuals)
        self.assertEqual(changed,self.inv)
        self.assertEqual(construct(changed),self.construction)

    def test_target_outcomes_change_evaluation_only(self):
        elections={y:read(f'data/processed/elections/{y}.json') for y in (2014,2020)}
        before=evaluate(self.construction,self.inv,elections)
        scored_id=self.construction['folds'][0]['predictions']['fallback'][0]['targetElectorateId']
        seat=next(s for s in elections[2014]['electorates'] if s['id']==scored_id)
        for c,v in zip(seat['candidates'],reversed([c['votes'] for c in seat['candidates']])):c['votes']=v
        after=evaluate(self.construction,self.inv,elections)
        self.assertTrue(before!=after)
        self.assertEqual(construct(self.inv),self.construction)

    def test_neutral_fallback_and_exact_feature_preservation(self):
        for view in ('broad','strict'):
            fallback=feature_rows(self.inv['records'],None,view)
            for old,new in zip(self.inv['records'],fallback):
                for a,b in zip(old['candidates'],new['candidates']):
                    if old['transportTier']=='exact':
                        self.assertEqual(a['s0Reported'],b['s0Reported'])
                        self.assertEqual(a['R'][view]['valueFraction'],b['R'][view]['valueFraction'])
                    else:
                        self.assertIsNone(b['s0Reported']);self.assertIsNone(b['R'][view]['valueFraction'])

    def test_saved_parameter_and_mean_changes_are_rejected(self):
        saved=read('data/processed/models/joint-candidate-share/construction.json')
        f=next(x for x in saved['folds'] if x['branch']=='primary' and x['targetYear']==2014)
        f['trainingOnlyMeans']['S']+=0.01
        with self.assertRaisesRegex(ValueError,'preprocessing changed'):construct(self.inv,saved=saved)

    def test_no_outgoing_or_other_predecessor_residual_transfer(self):
        row=next(r for r in self.inv['records'] if r['transportTier']!='exact')
        residuals={r['candidateOccurrenceId']:r for r in read('data/processed/models/candidate-overperformance/occurrences.json')['records']}
        for c in row['candidates']:
            r=r_source(c['targetOccurrenceId'],row['geography'],'broad',[],residuals)
            self.assertIsNone(r['valueFraction'])
        edge=next(e for e in self.inputs[4] if e['label']=='accepted_algorithmic_same_person')
        wrong=dict(row['geography'],sourceYear=edge['sourceYear'],targetYear=edge['targetYear'],dominantPredecessorId='wrong')
        self.assertIsNone(r_source(edge['targetOccurrenceId'],wrong,'broad',[edge],residuals)['valueFraction'])

    def test_strict_is_subset_and_original_links_unchanged(self):
        original=read(LINKS+'proposed-links.json')['records'];before=deepcopy(original)
        _,supplemental,_=supplemental_links(original,read(LINKS+'occurrences.json')['records'],
            alias_pairs(read(LINKS+'aliases.json')),{(r['geography']['dominantPredecessorId'],r['targetElectorateId']) for r in self.inv['records'] if r['transportTier']!='exact'})
        self.assertEqual(original,before)
        self.assertTrue(all(e['originalReason']=='seat_change_or_nonexact_geography' for e in supplemental))
        for row in self.inv['records']:
            for c in row['candidates']:
                if c['R']['strict']['valueFraction'] is not None:self.assertEqual(c['R']['broad']['valueFraction'],c['R']['strict']['valueFraction'])

    def test_duplicate_ballot_group_rejected(self):
        e=self.inputs[0][2014]['electorates'][0]
        mapping={'status':'complete','candidates':[{'candidateOccurrenceId':c['id'],'partyKey':'nationalparty','noRegisteredPartyGroup':False} for c in e['candidates']]}
        self.assertIsNone(target_candidates(mapping,e,{'nationalparty'})[0])

    def test_provenance_and_prior_preservation(self):
        verify_inputs();self.assertEqual(preserve(),1731)


class ArithmeticTests(unittest.TestCase):
    def test_denominators_metrics_and_gain_sign(self):
        target={'validCandidateVotes':100,'candidates':[{'id':'a','votes':70},{'id':'b','votes':30}]}
        score=errors({'a':0.6,'b':0.4},target)
        self.assertAlmostEqual(score['contestMaePP'],10);self.assertAlmostEqual(aggregate([score])['rmsePP'],10)
        with self.assertRaises(ValueError):errors({'a':1},target)

    def test_candidate_and_contest_equal_weighting_are_distinct(self):
        a={'candidateErrorsPP':{'a':10,'b':-10},'contestMaePP':10,'contestMsePP2':100}
        b={'candidateErrorsPP':{'c':0,'d':0,'e':0,'f':0},'contestMaePP':0,'contestMsePP2':0}
        self.assertEqual(aggregate([a,b])['maePP'],5)
        self.assertAlmostEqual(aggregate([a,b])['candidateEqualMaePP'],20/6)


class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.ready=readiness()

    def test_partial_slates_are_never_forecast(self):
        self.assertEqual(len(self.ready['seatRecords']),71);self.assertEqual(len(self.ready['candidateRecords']),206)
        self.assertTrue(all(not s['candidatePredictionsPermitted'] for s in self.ready['seatRecords']))
        self.assertEqual(self.ready['coverage']['completeCandidateSlates'],0)

    def test_cancelled_source_and_separate_maori_coefficients(self):
        pw=next(s for s in self.ready['seatRecords'] if s['officialName']=='Port Waikato')
        self.assertEqual(pw['dominantSourceContestStatuses'],['cancelled'])
        for c in self.ready['candidateRecords']:
            if c['targetElectorateId']==pw['targetElectorateId']:
                self.assertNotEqual(c['scenarios']['90']['S']['status'],'supported')
                self.assertNotEqual(c['scenarios']['90']['R']['status'],'supported')
        self.assertTrue(all(s['maoriGeneralCoefficientsPermitted'] is False for s in self.ready['seatRecords'] if s['scope']=='maori'))

    def test_2026_outcomes_do_not_change_features_or_readiness(self):
        snapshot=read(SNAPSHOT+'snapshot.json')
        for c in snapshot['occurrences']:c.update(votes=999999,winner=True,normalizedPremium=42)
        self.assertEqual(readiness(snapshot=snapshot),self.ready)


if __name__=='__main__':unittest.main()
