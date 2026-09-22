"""Same-boundary contract mutations must fail without altering source data."""
import copy
import json
import unittest
from scripts.boundaries.census_2013 import ROOT
from scripts.boundaries.readiness import build, audit_party, names, verify_hashes

class ReadinessTests(unittest.TestCase):
    def test_five_comparisons_and_deterministic_contract(self):
        a=build();self.assertEqual(a,build())
        self.assertEqual([r['generalElectorates'] for r in a['comparisons']],[63,64,64,65,65])
        self.assertEqual(a['futureBaseline']['generalElectorates'],64)

    def test_mass_and_bracket_corruption_fail(self):
        original=json.loads((ROOT/'data/processed/boundaries/2023-2026/party-votes.json').read_bytes())
        d=copy.deepcopy(original);d['scopes']['general']['partyMassConservation'][0]['sourceVotes']+=1
        with self.assertRaises(ValueError):audit_party(d)
        d=copy.deepcopy(original);d['scopes']['general']['targets'][0]['parties'][0]['shareUpper']=2
        with self.assertRaises(ValueError):audit_party(d)
        d=copy.deepcopy(original);d['nominalAllocation']=0
        with self.assertRaises(ValueError):audit_party(d)

    def test_typography_join_is_number_scoped_and_hashes_fail(self):
        self.assertEqual(names([{'targetName':'Rangit?¢kei','targetCode':'043'}],'targetName'),{'rangitikei'})
        with self.assertRaises(ValueError):names([{'targetName':'Rangit?¢kei','targetCode':'042'}],'targetName')
        with self.assertRaises(ValueError):verify_hashes({'AGENTS.md':'wrong'})

    def test_secondary_missingness_and_discrepancies_preserved(self):
        from scripts.boundaries.secondary import build as secondary
        d=secondary()['transitions']['2023-2026']
        original=json.loads((ROOT/'data/processed/split-votes/2023.json').read_bytes())
        self.assertEqual(d['sourceDiscrepancies'],original['sourceDiscrepancies'])
        self.assertEqual(d['heldGeneralSourceContests'],64)
        self.assertEqual(d['cancelledGeneralSourceContests'],1)
        self.assertIsNone(d['candidateAffiliationBaseline'])
        self.assertIsNone(d['splitJointBaseline'])
        self.assertTrue(any(r['heldContestPredecessorPopulationFractionLower']<1 for r in d['targetCoverage']))
