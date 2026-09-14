"""Real current-transition coverage and feasible endpoint conservation checks."""
import copy
import json
import unittest
from fractions import Fraction
from scripts.boundaries.current_inputs import ROOT
from scripts.boundaries.transition import build, build_scope


class TransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((ROOT/'data/controls/boundaries/transitions/2023-2026.json').read_bytes())
        cls.result=build(cls.config)

    def test_coverage_and_no_nominal_imputation(self):
        self.assertIsNone(self.result['nominalAllocation'])
        for kind,counts in [('general',(65,64,123)),('maori',(7,7,10))]:
            scope=self.result['scopes'][kind]
            self.assertEqual((len(scope['sources']),len(scope['targets']),len(scope['edges'])),counts)
            self.assertEqual(scope['meshblockCount'],57553)
            for edge in scope['edges']:
                self.assertLessEqual(Fraction(**edge['weightLower']),Fraction(**edge['weightUpper']))
                if not edge['uniquelyIdentified']: self.assertIsNone(edge['weight'])

    def test_every_sharp_weight_endpoint_has_conserving_population_witness(self):
        for scope in self.result['scopes'].values():
            edges=scope['edges']
            totals={t['code']:t['populationControl'] for t in scope['targets']}
            for pivot,edge in enumerate(edges):
                for endpoint in ('Lower','Upper'):
                    pinned={i:e['lower' if (i==pivot)==(endpoint=='Lower') else 'upper']
                            for i,e in enumerate(edges) if e['source']==edge['source']}
                    allocation=dict(pinned)
                    for target,total in totals.items():
                        ids=[i for i,e in enumerate(edges) if e['target']==target and i not in pinned]
                        residual=total-sum(v for i,v in pinned.items() if edges[i]['target']==target)
                        for i in ids: allocation[i]=edges[i]['lower']
                        residual-=sum(allocation[i] for i in ids)
                        for i in ids:
                            delta=min(residual,edges[i]['upper']-allocation[i])
                            allocation[i]+=delta;residual-=delta
                        self.assertEqual(residual,0)
                    for i,e in enumerate(edges):
                        self.assertLessEqual(e['lower'],allocation[i]);self.assertLessEqual(allocation[i],e['upper'])
                    denom=sum(allocation[i] for i,e in enumerate(edges) if e['source']==edge['source'])
                    self.assertEqual(Fraction(allocation[pivot],denom),Fraction(**edge['weight'+endpoint]))
                    for source in scope['sources']:
                        ids=[i for i,e in enumerate(edges) if e['source']==source['code']]
                        denom=sum(allocation[i] for i in ids)
                        self.assertEqual(sum(Fraction(allocation[i],denom) for i in ids),1)

    def test_unchanged_and_rename_semantics(self):
        general=self.result['scopes']['general']['targets']
        self.assertEqual(sum(t['officialChangeStatus']=='unchanged' for t in general),15)
        east=next(t for t in general if t['name']=='East Cape')
        self.assertTrue(east['officialRename'])
        self.assertEqual(east['unchangedMembershipStatus'],'suppressed_technical_uncertainty')
        self.assertEqual(next(t for t in general if t['name']=='Port Waikato')['unchangedMembershipStatus'],'identity')

    def test_duplicates_and_missing_source_fail(self):
        cells=[{'meshblockId':'a','source':'s','target':'t','population':{'lower':10,'upper':10,'status':'exact'}}]
        with self.assertRaises(ValueError):build_scope(cells*2,{'t':20},{'s':'S'},{'t':'T'},[],{})
        with self.assertRaises(ValueError):build_scope(cells,{'t':10},{'s':'S','z':'Z'},{'t':'T'},[],{})

    def test_committed_crosswalk_deterministic(self):
        self.assertEqual((json.dumps(self.result,ensure_ascii=False,indent=2)+'\n').encode(),
                         (ROOT/'data/processed/boundaries/2023-2026/crosswalk.json').read_bytes())
