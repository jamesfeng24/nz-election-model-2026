"""Frozen Stage31 construction checks, using real adapters and synthetic failures."""
import unittest
from copy import deepcopy
from unittest.mock import patch
from scripts.models.expanded_party_substitution import inventory,parties,candidates,construction
from scripts.models.expanded_party_substitution.common import local,read,keyed,S27,SCENARIOS,verify_inputs,preserve

class ExpandedSubstitutionConstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv=local('input-inventory.json');cls.party=local('party-vectors.json');cls.pred=local('candidate-predictions.json')
    def test_canonical_coverage_and_cancelled_separation(self):
        self.assertEqual([r['heldGeneralContests'] for r in self.inv['coverage']],[63,20,64,34,64])
        self.assertEqual(len(self.inv['partyFrame']),356);self.assertEqual(len(self.party['records']),246)
        self.assertEqual(sum(r['contestStatus']=='cancelled_or_unheld' for r in self.party['records']),1)
        self.assertEqual(len(self.inv['candidateRecords']),245)
    def test_vector_roster_and_conservation(self):
        for r in self.party['records']:
            self.assertEqual(set(r['localPartyShares']),set(r['targetPartyGroupKeys']))
            self.assertAlmostEqual(sum(r['localPartyShares'].values()),1,places=12)
            self.assertTrue(all(v>=0 for v in r['localPartyShares'].values()))
            for s in r['sourceAffinityStatus'].values():
                if s['relationship']=='entrant':self.assertEqual(s['affinity'],1)
                if s['sourceLocalStatus']=='observed_zero':self.assertEqual(s['affinity'],0)
    def test_original_reproductions(self):
        self.assertEqual(len(self.party['stage23Reproduction']),192)
        self.assertTrue(all(r['maximumAbsoluteShareDifference']<=1e-12 for r in self.party['stage23Reproduction']))
        self.assertTrue(all(c['passed'] for f in self.pred['folds'] for c in f['observedReproduction']))
        self.assertTrue(all(c['passed'] for c in local('compatibility.json')['checks']))
    def test_no_fits_manufactured(self):
        for f in self.pred['folds']:
            for s in SCENARIOS:
                nofit=f['targetYear']==2011 or (f['targetYear']==2014 and f['protocol']=='more_separated')
                self.assertEqual(f['scenarios'][s]['status']=='abstain',nofit)
    def test_saved_coefficients_and_means(self):
        saved=keyed([r for r in read(S27+'predictions.json')['candidateCases'] if r['trainingVariant']=='expanded'],'foldId')
        for f in self.inv['folds']:
            for s in SCENARIOS:
                self.assertEqual(f['scenarios'][s],{k:saved[f['foldId']]['scenarios'][s][k] for k in ('fits','trainingOnlyMeans')})
        with patch('scripts.checkpoints.stage22_fit.fit',side_effect=AssertionError('No fitting authorized')):
            self.assertEqual(construction.build()[1],self.pred)
    def test_candidate_simplex_same_four_samples(self):
        for f in self.pred['folds']:
            for s in SCENARIOS:
                block=f['scenarios'][s]
                if block['status']!='constructed':continue
                ids={r['targetElectorateId'] for r in block['cells']['A']}
                for rows in block['cells'].values():
                    self.assertEqual({r['targetElectorateId'] for r in rows},ids)
                    for r in rows:self.assertAlmostEqual(sum(r['candidateShares'].values()),1,places=12)
    def test_missing_and_duplicate_groups_rejected(self):
        v=deepcopy(self.party['records'][0]);v['localPartyShares'].pop(next(iter(v['localPartyShares'])))
        with self.assertRaises(ValueError):parties.ballot_vector(v)
        v=deepcopy(self.party['records'][0]);keys=list(v['targetPartyGroupKeys']);v['targetPartyGroupKeys'][keys[1]]=v['targetPartyGroupKeys'][keys[0]]
        with self.assertRaises(ValueError):parties.ballot_vector(v)
        r=deepcopy(self.inv['candidateRecords'][0]);r['candidates'].append(deepcopy(r['candidates'][0]))
        with self.assertRaises(ValueError):candidates.attach_inputs(r,self.party['records'][0])
    def test_one_shared_group_support_without_duplicate_mass(self):
        rows=[r for r in self.inv['candidateRecords'] if any(c['targetPartyKey']=='freedomsnz' for c in r['candidates'])]
        self.assertTrue(rows)
        vectors=keyed(self.party['records'],'targetElectorateId')
        for r in rows:
            selected=candidates.attach_inputs(r,vectors[r['targetElectorateId']])
            shared=[c for c in selected['candidates'] if c['partyBallotGroupKey']=='freedomsnz']
            self.assertEqual(len(shared),1)
            self.assertEqual(shared[0]['predictedTargetPartySupport'],selected['partyBallotGroupShares']['freedomsnz'])
    def test_supplied_national_scenario_can_change_vector(self):
        inv=deepcopy(self.inv);block=next(r for r in inv['categoryRelationships'] if r['targetYear']==2023)
        cats=[r for r in block['categories'] if r['relationship']!='exit'];a,b=cats[:2]
        delta=min(a['suppliedTargetNationalShare']/2,0.001);a['suppliedTargetNationalShare']-=delta;b['suppliedTargetNationalShare']+=delta
        r=next(r for r in inv['partyFrame'] if r['targetYear']==2023 and r['partyInputStatus']=='available')
        self.assertNotEqual(parties.one(r,block['categories'])['localPartyShares'],next(x for x in self.party['records'] if x['targetElectorateId']==r['targetElectorateId'])['localPartyShares'])
    def test_pinned_input_integrity_and_prior_preservation(self):
        verify_inputs();self.assertEqual(preserve(),1414)
        with patch('scripts.models.expanded_party_substitution.common.digest',return_value='corrupt'):
            with self.assertRaisesRegex(ValueError,'required input'):verify_inputs()
