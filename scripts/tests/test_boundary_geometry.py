"""Synthetic geometry fixtures only; no election observations invented."""
import copy
import json
from pathlib import Path
import unittest
from scripts.boundaries.geometry import decode_layer, decode_polygon

SHELL = [[0,0],[0,10],[10,10],[10,0],[0,0]]
HOLE = [[2,2],[4,2],[4,4],[2,4],[2,2]]
ISLAND = [[20,0],[20,2],[22,2],[22,0],[20,0]]


class GeometryTests(unittest.TestCase):
    def test_holes_and_islands_are_preserved_independent_of_order(self):
        result = decode_polygon([HOLE, ISLAND, SHELL])
        self.assertEqual(result.area, 100)
        self.assertEqual(len(result.geoms), 2)
        self.assertEqual(sum(len(p.interiors) for p in result.geoms), 1)

    def test_bad_rings_fail_without_repair(self):
        for rings in [[SHELL[:-1]], [HOLE], [[[0,0],[2,2],[0,2],[2,0],[0,0]]]]:
            with self.subTest(rings=rings), self.assertRaises(ValueError):
                decode_polygon(rings)

    def test_source_contract_failures(self):
        data = {'spatialReference':{'wkid':2193},'features':[
            {'attributes':{'code':'001','name':'Synthetic'},'geometry':{'rings':[SHELL]}}]}
        self.assertEqual(set(decode_layer(data,'code','name',1)), {'001'})
        for field, value in [('spatialReference',{'wkid':4326}),('exceededTransferLimit',True),('features',data['features']*2)]:
            changed=copy.deepcopy(data);changed[field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):
                decode_layer(changed,'code','name',1)

    def test_duplicate_ids_fail_even_with_expected_count(self):
        data={'spatialReference':{'wkid':2193},'features':[
            {'attributes':{'code':'001','name':'Synthetic'},'geometry':{'rings':[SHELL]}}]*2}
        with self.assertRaises(ValueError):decode_layer(data,'code','name',2)

    def test_preserved_official_layers_have_valid_topology(self):
        root=Path(__file__).resolve().parents[2]
        for year in (2020,2025):
            for kind,prefix,count in [('general','GED',65 if year==2020 else 64),('maori','MED',7)]:
                with self.subTest(year=year,kind=kind):
                    data=json.loads((root/f'data/raw/boundaries/2020-2025/{kind}-{year}-geometry.json').read_bytes())
                    field=f'{prefix}{year}_V1_00'
                    self.assertEqual(len(decode_layer(data,field,field+'_NAME',count)),count)

    def test_saved_audit_is_deterministic_and_not_a_crosswalk(self):
        from scripts.boundaries.audit_geography import build, OUTPUT
        first = build()
        self.assertEqual(first, build())
        self.assertEqual(first, json.loads(OUTPUT.read_bytes()))
        self.assertFalse(first['isVoteTransferOutput'])
        unchanged = first['officialUnchangedGeometryComparisons']
        self.assertEqual(len(unchanged), 19)
        self.assertTrue(all(r['populationMovement'] is None for r in unchanged))
        self.assertEqual(sum(r['renamed'] for r in unchanged), 1)
