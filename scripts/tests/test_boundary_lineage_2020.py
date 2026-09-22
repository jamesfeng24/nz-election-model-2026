"""Official final-2020 lineage and population-allocation safeguards."""
import copy
import json
import unittest
from scripts.boundaries.lineage_2020 import build, reconcile, OUTPUT


class Lineage2020Tests(unittest.TestCase):
    def fixture(self):
        pop = {c: {'GED2020_V1_00': '001', 'GED2020_V1_00_NAME': 'Target',
                   'MED2020_V1_00': '1', 'MED2020_V1_00_NAME': 'Māori',
                   'General_Electoral_Population': v, 'Maori_Electoral_Population': '-999'}
               for c, v in [('child1', '12'), ('child2', '-999')]}
        old = {'parent': {'GED2014_code': '001', 'GED2014_name': 'Source',
                          'MED2014_code': '1', 'MED2014_name': 'Māori'}}
        links = {c: {'MB2020_code': 'parent', 'GED2020_code': '001', 'GED2020_name': 'Target',
                     'MED2020_code': '1', 'MED2020_name': 'Māori'} for c in pop}
        return pop, old, links

    def test_split_uses_children_once_and_preserves_suppression(self):
        cells, _, splits, _ = reconcile(*self.fixture())
        self.assertEqual(len(cells['general']), 2)
        self.assertEqual(splits[0]['descendants'], ['child1', 'child2'])
        self.assertIsNone(cells['general'][1]['population']['value'])
        self.assertEqual(sum(c['population']['upper'] for c in cells['general']), 19)

    def test_wrong_target_missing_parent_and_parent_double_count_fail(self):
        for mutation in ('target', 'parent', 'double'):
            p, s, l = self.fixture()
            if mutation == 'target': l['child1']['GED2020_code'] = '999'
            if mutation == 'parent': s.clear()
            if mutation == 'double':
                p['parent'] = copy.deepcopy(p['child1'])
                l['parent'] = copy.deepcopy(l['child1'])
            with self.assertRaises(ValueError): reconcile(p, s, l)

    def test_in_electorate_source_cannot_disappear(self):
        p, s, l = self.fixture()
        s['lost'] = copy.deepcopy(s['parent'])
        with self.assertRaises(ValueError): reconcile(p, s, l)

    def test_real_memberships_and_determinism(self):
        result = build()
        self.assertEqual(result['directLineageCount'], 53578)
        self.assertEqual(result['populationMeshblocks'], 53582)
        self.assertEqual(len(result['outsideElectorateSourceRecords']), 16)
        self.assertEqual([s['predecessor'] for s in result['splitLineage']], ['2909110', '4011907'])
        self.assertEqual((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode(), OUTPUT.read_bytes())
