"""Synthetic linkage safeguards and preserved-input adapter counterfactuals."""
import copy
import unittest
from collections import Counter

from scripts.evidence.practical_candidate_linkage.common import (
    ROOT, DEST, OCCURRENCES, LINKS, read, unique, verify_inputs)
from scripts.evidence.practical_candidate_linkage.names import (
    alias_pairs, parse_name, name_match, strict_member)
from scripts.evidence.practical_candidate_linkage.proposals import (
    adapt_occurrences, generate, party_context, claim_index)
from scripts.evidence.practical_candidate_linkage.components import (
    validate_components, person_groups)
from scripts.evidence.practical_candidate_linkage.run import (
    construct, review_queue, apply_review, ballot_groups)

ALIASES = alias_pairs(read(str((DEST / 'aliases.json').relative_to(ROOT))))


def occurrence(cid, year, name='SMITH, William John', seat=None, party='national'):
    return {'candidateOccurrenceId': cid, 'year': year,
            'electorateId': seat or str(year), 'electorateName': 'Synthetic seat',
            'electorateType': 'general', 'sourceCandidateName': name,
            'sourceAffiliation': party, 'candidateAffiliationKey': party,
            'partyKey': party, 'candidateContestStatus': 'held', 'eligible': True,
            'provenance': {'sourceIds': ['synthetic-only']}}


def geography():
    return [{'sourceYear': 2008, 'targetYear': 2011, 'certifiedTwoSidedExact': True,
             'dominantPredecessorId': '2008', 'targetElectorateId': '2011',
             'geographyId': 'synthetic-only'}]


def continuity():
    return [{'sourceYear': 2008, 'targetYear': 2011, 'status': 'eligible',
             'source': {'sourceKey': 'national'}, 'target': {'sourceKey': 'national'}}]


def proposals(records, links=None):
    rows, _ = adapt_occurrences(records)
    return rows, generate(rows, geography(), continuity(), links or [], [], ALIASES)


class Names(unittest.TestCase):
    def match(self, left, right):
        return name_match(parse_name(left), parse_name(right), ALIASES)

    def test_every_frozen_nickname_without_biography(self):
        self.assertEqual(len(ALIASES), 12)
        for a, b in sorted(ALIASES):
            with self.subTest(a=a, b=b):
                result = self.match('COMMON, '+a, 'COMMON, '+b)
                self.assertTrue(result['compatible'])
                self.assertEqual(result['flags'], ['frozen_nickname'])
        self.assertFalse(self.match('SMITH, Will', 'SMITH, William')['compatible'])

    def test_exact_unicode_compound_and_name_order(self):
        self.assertTrue(self.match('VAN DEN HEUVEL, Anthony', 'van den heuvel, ANTHONY')['compatible'])
        self.assertTrue(self.match('O’CONNOR-JONES, Elizabeth', "O'CONNOR-JONES, Elizabeth")['compatible'])
        self.assertFalse(self.match('MĀORI, William', 'MAORI, William')['compatible'])
        self.assertEqual(parse_name('William van den Heuvel', 'given_surname')['status'], 'unresolved')
        self.assertEqual(parse_name('William van den Heuvel', 'given_surname', 'van den Heuvel')['surname'], 'van den heuvel')
        self.assertEqual(parse_name('William Smith', 'given_surname')['given'], 'william')
        self.assertEqual(parse_name('SMITH William')['status'], 'unresolved')

    def test_middle_omission_initial_and_conflicts(self):
        self.assertEqual(self.match('SMITH, William John', 'SMITH, William')['flags'], ['middle_omission'])
        self.assertEqual(self.match('SMITH, William J.', 'SMITH, William John')['flags'], ['middle_initial'])
        self.assertFalse(self.match('SMITH, William John', 'SMITH, William James')['compatible'])
        self.assertFalse(self.match('SMITH, William John Peter', 'SMITH, William Peter')['compatible'])
        self.assertFalse(self.match('SMITH, W.', 'SMITH, William')['compatible'])
        self.assertFalse(self.match('SMITH, Celeste Mojo', 'SMITH, Mojo Celeste')['compatible'])
        self.assertEqual(self.match('SMITH, Bill J.', 'SMITH, William John Peter')['flags'],
                         ['frozen_nickname', 'middle_initial', 'middle_omission'])

    def test_strict_is_reproducible_from_all_flags(self):
        for flags, expected in [(['exact_name'], True), (['middle_initial'], False),
                                (['frozen_nickname', 'middle_omission'], False)]:
            self.assertEqual(strict_member({'label': 'accepted_algorithmic_same_person', 'ruleFlags': flags}), expected)
        self.assertFalse(strict_member({'label': 'unresolved_ambiguous', 'ruleFlags': ['exact_name']}))
        self.assertTrue(strict_member({'label': 'documentary_same_person', 'ruleFlags': []}))


class Proposals(unittest.TestCase):
    def test_context_unique_complete_names_accepted(self):
        rows, edges = proposals([occurrence('a', 2008), occurrence('b', 2011)])
        self.assertEqual(edges[0]['label'], 'accepted_algorithmic_same_person')
        self.assertEqual(len(person_groups(edges, rows)), 1)
        self.assertFalse(person_groups(edges, rows)[0]['historicalPersonIdsOverwritten'])

    def test_competitor_elsewhere_and_another_party_blocks(self):
        _, edges = proposals([occurrence('a', 2008), occurrence('b', 2011),
                              occurrence('c', 2011, seat='outside-frame', party='labour')])
        edge = next(e for e in edges if e['targetOccurrenceId']=='b')
        self.assertEqual(edge['ambiguityType'], 'competing_matches')
        self.assertIn('c', edge['competingOccurrenceIds'])
        self.assertFalse(any(e['label']=='accepted_algorithmic_same_person' for e in edges))

    def test_duplicate_representation_is_not_competitor_but_conflict_rejected(self):
        a, b = occurrence('a', 2008), occurrence('b', 2011)
        rows, count = adapt_occurrences([a, b, copy.deepcopy(b)])
        self.assertEqual((len(rows), count), (2, 1))
        changed = copy.deepcopy(b); changed['sourceCandidateName']='SMITH, James'
        with self.assertRaises(ValueError):
            adapt_occurrences([a,b,changed])
        self.assertEqual(unique([a,a], 'candidateOccurrenceId'), {'a':a})

    def test_documented_party_label_change_and_shared_group_separation(self):
        source, target = adapt_occurrences([occurrence('a',2008),occurrence('b',2011,party='renamed')])[0]
        target['ballotGroupKey']='new-national'
        relation={(2008,2011,'new-national'):{'status':'eligible','source':{'sourceKey':'national'}}}
        self.assertTrue(party_context(source,target,relation)[0])
        source['sharedBallotGroup']=True
        self.assertEqual(party_context(source,target,relation)[1], 'shared_group_not_constituent_continuity')
        source['sharedBallotGroup']=False
        self.assertFalse(party_context(source,target,{})[0])

    def test_party_and_seat_changes_remain_explicit_exceptions(self):
        for b, reason in [(occurrence('b',2011,party='labour'),'party_change_or_unknown_continuity'),
                          (occurrence('b',2011,seat='outside-frame'),'seat_change_or_nonexact_geography')]:
            _, edges=proposals([occurrence('a',2008),b])
            self.assertEqual(edges[0]['ambiguityType'],reason)
            self.assertEqual(edges[0]['label'],'unresolved_ambiguous')

    def test_inherited_confirmation_never_proves_relationship(self):
        _, edges=proposals([occurrence('a',2008),occurrence('b',2011,'SMITH, Sam')],
                          [{'candidateOccurrenceId':cid,'personId':'old-shared','status':'confirmed'} for cid in ('a','b')])
        self.assertEqual(edges[0]['label'],'unresolved_ambiguous')
        self.assertEqual(edges[0]['relationshipEvidence'],[])
        self.assertIn('inherited_person_ID_lead_not_proof',edges[0]['proposalRoutes'])

    def test_documentary_conflicts_and_missing_bridges_rejected(self):
        c={'sourceOccurrenceId':'a','targetOccurrenceId':'b','label':'documentary_distinct_people',
           'evidenceArtifact':'synthetic-only','evidencePointer':'a->b','evidence':{'passage':'Two explicitly identified people'}}
        self.assertEqual(len(claim_index([c,c])),1)
        changed={**c,'label':'documentary_same_person','evidence':{'relationshipPassage':'Explicit bridge'}}
        with self.assertRaises(ValueError): claim_index([c,changed])
        with self.assertRaises(ValueError): claim_index([{**changed,'evidence':{'profile':'Existence only'}}])


class ComponentsAndReview(unittest.TestCase):
    def test_transitive_middle_conflict_quarantines_component(self):
        rows=adapt_occurrences([occurrence('a',2008,'SMITH, William John'),
                               occurrence('b',2011,'SMITH, William'),
                               occurrence('c',2014,'SMITH, William James')])[0]
        edges=[{'edgeId':a+'->'+b,'sourceOccurrenceId':a,'targetOccurrenceId':b,
                'label':'accepted_algorithmic_same_person','ruleFlags':['middle_omission'],
                'competingOccurrenceIds':[]} for a,b in [('a','b'),('b','c')]]
        audits=validate_components(edges,rows,ALIASES)
        self.assertEqual(audits[0]['status'],'quarantined')
        self.assertTrue(all(e['label']=='unresolved_ambiguous' for e in edges))
        self.assertEqual(person_groups(edges,rows),[])

    def test_rejected_internal_edge_cannot_be_bypassed(self):
        rows=adapt_occurrences([occurrence('a',2008),occurrence('b',2011),occurrence('c',2014)])[0]
        edges=[{'edgeId':a+'->'+b,'sourceOccurrenceId':a,'targetOccurrenceId':b,
                'label':label,'ruleFlags':['exact_name'],'competingOccurrenceIds':[]}
               for a,b,label in [('a','b','accepted_algorithmic_same_person'),('b','c','accepted_algorithmic_same_person'),('a','c','documentary_distinct_people')]]
        validate_components(edges,rows,ALIASES)
        self.assertFalse(any(e['label']=='accepted_algorithmic_same_person' for e in edges))

    def test_cap_order_and_no_replacing_difficult_cases(self):
        edges=[{'edgeId':str(i),'sourceYear':2008,'targetYear':2011,'ambiguityType':'a',
                'sourceOccurrenceId':f'{i:03}','targetOccurrenceId':'target','label':'unresolved_ambiguous'} for i in range(70)]
        queue=review_queue(list(reversed(edges)))
        self.assertEqual(sum(r['reviewState']=='pending_preserved_inspection' for r in queue),60)
        self.assertEqual(queue,review_queue(edges))
        with self.assertRaises(ValueError):review_queue(edges,61)
        with self.assertRaises(ValueError):apply_review(queue,{'records':[{'edgeId':'1'}]})
        self.assertEqual(Counter(r['reviewState'] for r in apply_review(queue,{'records':[]})),
                         {'not_reviewed_stopped':60,'not_reviewed_budget':10})


class RealAdapters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved=construct()

    def test_actual_pipeline_outcomes_confidence_and_votes_do_not_select(self):
        records=copy.deepcopy(read(OCCURRENCES)['records'])
        for r in records:
            for key in ('sourcePublishedCandidateVotes','validCandidateVotes','candidateShare',
                        'localPartyVotes','validPartyVotes','localPartyShare','rawPremium','normalizedPremium'):
                r[key]=999999
            r['winner']=not r.get('winner',False)
            r['personId']='counterfactual_identity_label'
        links=copy.deepcopy(read(LINKS)['links'])
        for r in links:r['status']='counterfactual_confidence'
        changed=construct(occurrences=records,links=links)
        for name in ('occurrences.json','proposed-links.json','accepted-relationships.json','persons.json','review-queue.json','review-table.md'):
            self.assertEqual(self.saved[name],changed[name],name)

    def test_all_saved_occurrences_and_reversible_links(self):
        rows=self.saved['occurrences.json']['records']
        self.assertEqual(len(rows),3007)
        ids={r['candidateOccurrenceId'] for r in rows}
        for edge in self.saved['proposed-links.json']['records']:
            self.assertIn(edge['sourceOccurrenceId'],ids)
            self.assertIn(edge['targetOccurrenceId'],ids)
            self.assertTrue(edge['reversible'])
            self.assertEqual(edge['careerCompleteness'],'not_established_by_linkage')
        self.assertEqual(len(self.saved['accepted-relationships.json']['broadEdgeIds']),496)
        self.assertEqual(len(self.saved['accepted-relationships.json']['strictEdgeIds']),424)
        self.assertEqual(len(self.saved['documentary-claims.json']['records']),10)

    def test_pinned_source_records_and_raw_bytes(self):
        registry=read('data/sources.json')
        added=copy.deepcopy(registry);added['sources'].append({'id':'unrelated-synthetic-test'})
        verify_inputs(registry=added)
        contract=read(str((DEST/'input-contract.json').relative_to(ROOT)))
        required=next(r['record'] for r in contract['requiredSources'] if r['registryPath']=='data/sources.json')
        removed=copy.deepcopy(registry);removed['sources']=[r for r in removed['sources'] if r['id']!=required['id']]
        with self.assertRaises(ValueError):verify_inputs(registry=removed)
        altered=copy.deepcopy(registry)
        next(r for r in altered['sources'] if r['id']==required['id'])['url']='changed'
        with self.assertRaises(ValueError):verify_inputs(registry=altered)
        duplicate=copy.deepcopy(registry);duplicate['sources'].append(copy.deepcopy(duplicate['sources'][0]))
        with self.assertRaises(ValueError):verify_inputs(registry=duplicate)
        with self.assertRaises(ValueError):verify_inputs(raw_reader=lambda path:b'corrupt-required-bytes')

    def test_dates_and_shared_mapping_remain_explicit(self):
        for row in self.saved['occurrences.json']['records']:
            self.assertEqual(row['historicalFactYear'],row['year'])
            self.assertEqual(row['publicationByForecastCutoff'],'unknown')
        for claim in self.saved['documentary-claims.json']['records']:
            self.assertIn('sourceFactDate',claim['evidence'])
            self.assertIn('sourcePublicationDate',claim['evidence'])
            self.assertIn('sourceRetrievalAt',claim['evidence'])
        from scripts.evidence.practical_candidate_linkage.common import MAPPING
        groups=ballot_groups(read(MAPPING))
        self.assertTrue(any(r['shared'] for r in groups.values()))
        self.assertTrue(any(r['partyKey'] is None and not r['shared'] for r in groups.values()))


if __name__=='__main__':
    unittest.main()
