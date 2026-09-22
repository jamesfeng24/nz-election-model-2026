"""2013 disclosure and imputation bounds, with no national-ratio substitution."""
import itertools
import unittest
from scripts.boundaries.census_2013 import count_bounds, descent_bounds, PREFIX, UR, FIELDS
from scripts.boundaries.inputs_2014 import load


class Census2013Tests(unittest.TestCase):
    def test_suppression_and_invalid_values(self):
        self.assertEqual(count_bounds('..C',99),(0,99))
        self.assertEqual(count_bounds('0'),(0,2))
        self.assertEqual(count_bounds('3'),(1,5))
        for value in ['', '*', '-999', '-1','1.5','4']:
            with self.assertRaises(ValueError):count_bounds(value,100)

    def test_partition_bounds_match_exhaustive_unknown_imputation(self):
        row={UR:'9',**{PREFIX+k:v for k,v in zip(FIELDS,['3','3','0','3','6','9'])}}
        result=descent_bounds(row)
        feasible=[]
        for y,n,k,r in itertools.product(range(1,6),range(1,6),range(3),range(1,6)):
            if 7<=y+n+k+r<=11 and 4<=y+n+k<=8:
                for q in range(k+r+1):feasible.append((y+n+k+r,y+q,n))
        self.assertEqual(result['electoralDescentLower'],min(x[1] for x in feasible))
        self.assertEqual(result['electoralDescentUpper'],max(x[1] for x in feasible))
        self.assertEqual(result['nonMaoriDescentLower'],min(x[2] for x in feasible))
        row[PREFIX+'Total_people_stated']='99'
        with self.assertRaises(ValueError):descent_bounds(row)

    def test_real_source_lineage_coverage_and_split_conservation(self):
        v=load()
        self.assertEqual(v['censusMeshblocks'],46629)
        self.assertEqual(len(v['splitEvidence']),22)
        self.assertEqual(v['splitPublishedResidentTotal'],1827)
        self.assertEqual(len(v['outsideWithoutCensus']),8)
        self.assertEqual({r['predecessor'] for r in v['outsideTargetRecords']},{'3166710','3166711'})
        for kind,s in v['scopes'].items():
            self.assertEqual(len(s['controls']),64 if kind=='general' else 7)
            split=[g for g in s['groups'] if len(g['targets'])>1]
            self.assertEqual(len(split),22 if kind=='general' else 0)
