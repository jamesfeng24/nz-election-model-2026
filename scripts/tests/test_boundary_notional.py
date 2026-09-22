"""Notional reconstruction enclosures, input integrity and mass conservation."""
import json
import unittest
import numpy as np
from scripts.boundaries.coupled import PopulationSystem
from scripts.boundaries.feasible import fraction_json
from scripts.boundaries.notional_bounds import TargetEnvelope
from scripts.boundaries.party_inputs import load
from scripts.boundaries.census_2013 import ROOT
from scripts.boundaries.notional import party_inventory


class NotionalTests(unittest.TestCase):
    def fixture(self):
        p=PopulationSystem([
            {'id':'a','source':'A','targets':['X','Y'],'lower':2,'upper':4},
            {'id':'b','source':'B','targets':['X','Y'],'lower':3,'upper':5}],{'X':4,'Y':3})
        edges=[]
        for s,t in p.edge_inventory():
            a,b=p.vector(s,t),p.vector(s)
            edges.append({'source':s,'target':t,'weightLower':fraction_json(p.ratio(a,b)),
                          'weightUpper':fraction_json(p.ratio(a,b,True))})
        sources=[]
        for s in ['A','B']:
            lo,hi=p.bounds(p.vector(s));sources.append({'code':s,'populationLower':lo,'populationUpper':hi})
        return p,{'edges':edges,'sources':sources}

    def test_global_enclosures_cover_dense_feasible_assignments(self):
        p,scope=self.fixture();env=TargetEnvelope(p,scope,'X')
        for denominator in [None,[30,40]]:
            lo=env.bound([10,20],denominator,max_nodes=64)
            hi=env.bound([10,20],denominator,maximize=True,max_nodes=64)
            for total in np.linspace(2,4,31):
                for x in np.linspace(max(0,total-3),min(total,4),31):
                    weights=[x/total,(4-x)/(7-total)]
                    value=10*weights[0]+20*weights[1]
                    if denominator is not None:value/=(30*weights[0]+40*weights[1])
                    self.assertLessEqual(lo['outer'],value+1e-7)
                    self.assertGreaterEqual(hi['outer'],value-1e-7)
            self.assertLessEqual(lo['outer'],lo['attainable'])
            self.assertGreaterEqual(hi['outer'],hi['attainable'])
            self.assertLessEqual(lo['gap'],.25 if denominator is None else .01)
            self.assertLessEqual(hi['gap'],.25 if denominator is None else .01)

    def test_party_inventory_and_negative_votes_fail(self):
        with self.assertRaises(ValueError):party_inventory({'s':{'validVotes':5,'parties':[{'partyKey':'a','partyName':'A','votes':4}]}})
        p,scope=self.fixture()
        with self.assertRaises(ValueError):TargetEnvelope(p,scope,'X').bound([-1,2])

    def test_all_preserved_general_and_supporting_maori_party_totals(self):
        for transition in ['2011-2014','2017-2020','2023-2026']:
            crosswalk=json.loads((ROOT/f'data/processed/boundaries/{transition}/crosswalk.json').read_bytes())
            records,_=load(int(transition[:4]),crosswalk)
            self.assertEqual(len(records['maori']),7)
            for scope in records.values():self.assertTrue(party_inventory(scope))
        pw=next(r for r in records['general'].values() if r['name']=='Port Waikato')
        self.assertGreater(pw['validVotes'],0)
        self.assertTrue(any('opportunities' in p['partyKey'] for p in pw['parties']))
