"""Dated real-slate readiness, source-only features and refresh safeguards."""
import copy
from fractions import Fraction
import unittest
from scripts.readiness.common import load, verify_preservation, verify_sources
from scripts.readiness.geography import exact_source, official_roster
from scripts.readiness.registry import build_registry, claim_available, mapping_readiness, occurrence_id, snapshot_changes, verify_register
from scripts.readiness.linkage import build_links, parsed_target
from scripts.readiness.features import r_feature, s_feature
from scripts.readiness.run import build, INPUTS
from scripts.evidence.practical_candidate_linkage.names import alias_pairs, name_match

BASE='data/processed/forecast-readiness/'


class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=load(BASE+'acquisition-manifest.json')
        cls.results=build(cls.manifest)
        cls.frame=cls.results['target-frame.json']['records']
        cls.snapshot=cls.results['snapshot.json']
        cls.occ=load(INPUTS[2])['records']
        cls.aliases=alias_pairs(load(INPUTS[3]))

    def claims(self, status='party_announced', name='Chris Example', **extra):
        return dict(sourceKey='test',displayName=name,sourceElectorateLabel='Coromandel',
            affiliationKey='nationalparty',status=status,publicationDate=None,factDate=None,**extra)

    def sources(self, official=False):
        return {'test':{'id':'synthetic-source','key':'test','url':'https://vote.nz/synthetic' if official else 'https://www.national.org.nz/synthetic',
                       'retrievedAt':'2026-10-04T18:00:00Z','rawPath':'synthetic','sha256':'synthetic'}}

    def registry(self, claims, *, cutoff=None, complete=(), official=False):
        return build_registry(claims,self.frame,self.sources(official),cutoff or self.manifest['acquisitionCutoffUTC'],complete)

    def test_all_seats_and_no_complete_slates(self):
        self.assertEqual(len(self.frame),71)
        self.assertEqual(len({s['targetElectorateId'] for s in self.frame}),71)
        self.assertEqual(self.results['coverage.json']['exactSeatsByScope'],{'general':14,'maori':2})
        self.assertFalse(any(s['slateComplete'] for s in self.results['seat-readiness.json']['records']))
        self.assertFalse(self.snapshot['forecastProduced'])
        self.assertIsNone(self.snapshot['operationalSelection'])

    def test_current_official_roster_names_populations(self):
        roster=official_roster(load('data/raw/forecast-readiness/2026-10-05/schedule-c-readable.json'))
        self.assertEqual(len(roster),71)
        self.assertEqual(sum(r['scope']=='maori' for r in roster),7)
        broken=load('data/raw/forecast-readiness/2026-10-05/schedule-c-readable.json').replace('N01 033','N01 034')
        with self.assertRaises(ValueError):official_roster(broken)

    def test_incoming_identity_is_not_source_retention(self):
        cross=load(INPUTS[0])['scopes']['maori']
        target=next(t for t in cross['targets'] if t['name']=='Te Tai Tokerau')
        self.assertEqual(target['unchangedMembershipStatus'],'identity')
        self.assertIsNone(exact_source(target,cross['edges']))
        self.assertEqual(exact_source(next(t for t in cross['targets'] if t['name']=='Waiariki'),cross['edges']),'7')

    def test_extra_suppressed_predecessor_is_not_exact(self):
        c=load(INPUTS[0])['scopes']['general']
        self.assertIsNone(exact_source(next(t for t in c['targets'] if t['name']=='East Cape'),c['edges']))

    def test_maori_ids_not_reinvented(self):
        m=next(s for s in self.frame if s['canonicalName']=='Waiariki')
        self.assertEqual(m['exactSourceElectorateId'],'nz-general-2023-electorate-72')
        ready=next(s for s in self.results['seat-readiness.json']['records'] if s['targetElectorateId']==m['targetElectorateId'])
        self.assertIsNotNone(ready['maoriPollingInterface'])
        self.assertFalse(ready['maoriPollingInterface']['nationalTPMIsCandidateSupport'])

    def test_duplicate_representation_deduplicates(self):
        c=self.claims();r=self.registry([c,c])
        self.assertEqual(len(r['occurrences']),1)
        self.assertEqual(len(r['claimHistory']),2)
        self.assertEqual(r['deduplicatedRepresentations'],1)

    def test_unknown_does_not_become_no_group(self):
        c=self.claims();c['affiliationKey']='unverified_affiliation'
        row=self.registry([c])['occurrences'][0]
        self.assertIsNone(row['ballotGroupKey'])
        self.assertEqual(mapping_readiness([row]),'abstain_mapping_conflict_or_missing')

    def test_multiple_group_destinations_reject(self):
        r=self.registry([self.claims(),self.claims(name='Jane Example')])
        self.assertTrue(all(c['conflict'] for c in r['occurrences']))
        self.assertEqual(mapping_readiness(r['occurrences']),'abstain_mapping_conflict_or_missing')
        c=copy.deepcopy(r['occurrences'][0]);c.update(sharedGroup=True,conflict=False)
        self.assertEqual(mapping_readiness([c]),'known_destinations_unique; unknown_slate_members_pending')

    def test_withdrawal_and_unordered_conflict(self):
        a=self.claims();w=self.claims(status='withdrawn')
        r=self.registry([a,w]);row=r['occurrences'][0]
        self.assertTrue(row['conflict']);self.assertFalse(row['active'])
        self.assertEqual(mapping_readiness([row]),'abstain_mapping_conflict_or_missing')
        a['factDate']='2026-09-01';w['factDate']='2026-09-02'
        row=self.registry([a,w])['occurrences'][0]
        self.assertEqual(row['status'],'withdrawn');self.assertFalse(row['active'])

    def test_same_day_conflicting_date_only_events_remain_conflicted(self):
        a=self.claims();w=self.claims(status='withdrawn')
        a['factDate']=w['factDate']='2026-09-01'
        self.assertTrue(self.registry([a,w])['occurrences'][0]['conflict'])

    def test_future_fact_publication_and_timezone_boundary(self):
        c=self.claims();source=self.sources()['test'];cut='2026-10-04T19:00:00Z'
        c['publicationDate']='2026-10-05T09:00:00+13:00'
        self.assertFalse(claim_available(c,source,cut))
        c['publicationDate']='2026-10-05T07:59:00+13:00'
        self.assertTrue(claim_available(c,source,cut))
        c['factDate']='2026-10-06';self.assertFalse(claim_available(c,source,cut))
        c['factDate']=None;c['publicationDate']='2026-10-05'
        self.assertTrue(claim_available(c,source,cut)) # explicitly date-only, retrieved before cutoff

    def test_party_sources_cannot_assert_official_nominations(self):
        with self.assertRaises(ValueError):self.registry([self.claims(status='official_nomination')])

    def test_complete_requires_official_membership_and_no_conflicts(self):
        c=self.claims(status='official_nomination')
        seat=next(s['targetElectorateId'] for s in self.frame if s['canonicalName']=='Coromandel')
        oid=occurrence_id(seat,'nationalparty','Chris Example')
        decl={'targetElectorateId':seat,'status':'official_complete_nominations','sourceId':'synthetic-source',
              'publishedAt':'2026-10-08T00:00:00Z','candidateOccurrenceIds':[oid]}
        r=self.registry([c],official=True,cutoff='2026-10-09T00:00:00Z',complete=[decl])
        self.assertIn(seat,r['completeSlateDeclarations'])
        bad=dict(decl,candidateOccurrenceIds=[])
        with self.assertRaises(ValueError):self.registry([c],official=True,cutoff='2026-10-09T00:00:00Z',complete=[bad])
        with self.assertRaises(ValueError):self.registry([c],official=True,complete=[decl])
        with self.assertRaises(ValueError):self.registry([c,self.claims(status='withdrawn')],official=True,cutoff='2026-10-09T00:00:00Z',complete=[decl])

    def test_register_changes_require_explicit_overlay(self):
        text=load('data/raw/forecast-readiness/2026-10-05/party-register-readable.json')
        verify_register(text)
        with self.assertRaises(ValueError):verify_register(text+'\nL2000: ## Synthetic New Party\n')
        with self.assertRaises(ValueError):verify_register(text.replace('L136: None','L136: Synthetic component'))

    def test_explicit_link_rules_and_middle_conflict(self):
        old={'status':'parsed','surname':'smith','given':'william','middle':['james'],'givenSubstantive':True}
        a=parsed_target('Bill Smith',[])
        self.assertTrue(name_match(old,a,self.aliases)['compatible'])
        b=parsed_target('William John Smith',[{'parsedName':old}])
        self.assertFalse(name_match(old,b,self.aliases)['compatible'])
        self.assertEqual(parsed_target('J Smith',[])['givenSubstantive'],False)

    def test_compound_surname_preserved(self):
        h=[{'parsedName':{'status':'parsed','surname':'van velden'}}]
        self.assertEqual(parsed_target('Brooke van Velden',h)['surname'],'van velden')
        self.assertEqual(parsed_target('Unknown Alpha Beta',[])['status'],'unresolved')

    def test_competing_same_name_elsewhere_cannot_hide(self):
        tid=next(e['targetOccurrenceId'] for e in self.results['identity-links.json']['records'] if e['broadAccepted'])
        target=next(c for c in self.snapshot['occurrences'] if c['targetOccurrenceId']==tid)
        clone=copy.deepcopy(target);clone['targetOccurrenceId']='synthetic-other-seat';clone['targetElectorateId']=self.frame[0]['targetElectorateId']
        rows=self.snapshot['occurrences']+[clone]
        p=self.results['party-relationships.json']['records']
        links=build_links(rows,self.occ,self.aliases,self.frame,p)
        edge=next(e for e in links if e['targetOccurrenceId']==target['targetOccurrenceId'])
        self.assertFalse(edge['broadAccepted']);self.assertIn('competing_target_occurrences',edge['exceptionReasons'])

    def test_shared_group_is_not_constituent_party_continuity(self):
        p=self.results['party-relationships.json']['records']
        self.assertIsNone(next(x['sourceBallotGroupKey'] for x in p if x['targetGroupKey']=='visionnewzealand'))
        self.assertIsNone(next(x['sourceBallotGroupKey'] for x in p if x['targetGroupKey']=='nzoutdoorsfreedomparty'))

    def test_source_only_residual_and_no_outgoing_transfer(self):
        seat=next(s for s in self.frame if s['canonicalName']=='Coromandel')
        e={'broadAccepted':False,'strictAccepted':False,'geographyCompatible':True,'sourceOccurrenceId':None,'label':'accepted_algorithmic_same_person'}
        self.assertIsNone(r_feature(e,seat,{})['valueFraction'])
        e.update(broadAccepted=True,sourceOccurrenceId='synthetic',geographyCompatible=False)
        r={'synthetic':{'year':2023,'electorateId':seat['exactSourceElectorateId'],'normalizedPremium':.12,'candidateContestStatus':'held','candidateOccurrenceId':'synthetic','referenceId':'source-ref'}}
        self.assertIsNone(r_feature(e,seat,r)['valueFraction'])
        e['geographyCompatible']=True;self.assertEqual(r_feature(e,seat,r)['valueFraction'],.12)
        self.assertIsNone(r_feature(e,seat,r,True)['valueFraction'])

    def test_cancelled_port_waikato_s_is_not_zero_behaviour(self):
        seat=next(s for s in self.frame if s['canonicalName']=='Port Waikato')
        p={p['targetGroupKey']:p for p in self.results['party-relationships.json']['records']}
        s=s_feature({'originalAffiliation':'nationalparty'},seat,p,self.occ,load(INPUTS[5])['matrices'])
        self.assertIsNone(s['valueFraction']);self.assertEqual(s['reason'],'cancelled_source_candidate_contest')

    def test_rounded_source_rows_remain_coupled(self):
        rows=self.results['party-seat-feature-readiness.json']['records']
        supported=[r['S'] for r in rows if r['S']['status']=='supported']
        self.assertEqual(len(supported),70)
        for s in supported:
            for witness in s['completeRowWitnesses'].values():
                self.assertEqual(sum(Fraction(v) for v in witness),100)
        self.assertFalse(any(r['S']['status']=='requires_explicit_abstention' for r in rows))

    def test_actual_pipeline_outcomes_do_not_control_readiness(self):
        claims=copy.deepcopy([c for row in self.snapshot['occurrences'] for c in row['claims']])
        for c in claims:c.update(winner=True,targetCandidateVotes=999999,residual=-99)
        occ=copy.deepcopy(self.occ)
        occ.extend([{'year':2026,'electorateId':'synthetic-target','candidateOccurrenceId':'synthetic','winner':True,'votes':99999}])
        # Real source residuals remain frozen; target normalization never joins.
        res=load(INPUTS[4])['records']+[{'year':2026,'candidateOccurrenceId':'synthetic','normalizedPremium':999,'winner':True}]
        new=build(self.manifest,claims=claims,occurrences=occ,residuals=res)
        for path in ('target-frame.json','identity-links.json','candidate-feature-readiness.json','party-seat-feature-readiness.json','seat-readiness.json'):
            self.assertEqual(new[path],self.results[path],path)

    def test_deterministic_refresh_changes_and_invalidation(self):
        unchanged=snapshot_changes(self.snapshot,self.snapshot)
        self.assertEqual(unchanged,[])
        new=copy.deepcopy(self.snapshot);new['occurrences'][0]['status']='withdrawn'
        change=snapshot_changes(self.snapshot,new)
        self.assertEqual(len(change),1);self.assertIn('downstream_candidate_outputs',change[0]['invalidate'])
        self.assertEqual(build(self.manifest),self.results)

    def test_refresh_keeps_omitted_assertions_without_inventing_withdrawal(self):
        # A later directory omission is not evidence that a prior real candidate withdrew.
        refreshed=build(self.manifest,claims=[],previous=self.snapshot)
        self.assertEqual(len(refreshed['snapshot.json']['occurrences']),206)
        self.assertTrue(all(c['active'] for c in refreshed['snapshot.json']['occurrences']))
        self.assertEqual(refreshed['candidate-feature-readiness.json'],self.results['candidate-feature-readiness.json'])
        same=build(self.manifest,previous=self.snapshot)
        self.assertEqual(same['changes.json']['records'],[])
        self.assertEqual(same['snapshot.json'],self.snapshot)

    def test_source_occurrence_corruption_rejected(self):
        seat=next(s for s in self.frame if s['canonicalName']=='Coromandel')
        e={'broadAccepted':True,'strictAccepted':True,'geographyCompatible':True,'sourceOccurrenceId':'synthetic','label':'accepted_algorithmic_same_person'}
        r={'synthetic':{'year':2026,'electorateId':seat['exactSourceElectorateId'],'candidateOccurrenceId':'synthetic','normalizedPremium':.1,'candidateContestStatus':'held'}}
        with self.assertRaises(ValueError):r_feature(e,seat,r)

    def test_budget_provenance_and_preservation(self):
        verify_sources(self.manifest)
        broken=copy.deepcopy(self.manifest);broken['resourceCap']=23
        with self.assertRaises(ValueError):verify_sources(broken)
        report=verify_preservation();self.assertEqual(report['priorSourceRecordsUnchanged'],926)
        self.assertGreater(report['priorDataFilesUnchanged'],1600)


if __name__=='__main__':unittest.main()
