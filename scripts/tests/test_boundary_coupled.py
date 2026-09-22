"""Small exhaustive systems certify global rather than independent local bounds."""
import itertools
from fractions import Fraction
import unittest
import numpy as np
from scripts.boundaries.coupled import PopulationSystem


class CoupledTests(unittest.TestCase):
    def system(self):
        return PopulationSystem([
            {'id':'a','source':'A','targets':['X','Y'],'lower':2,'upper':4},
            {'id':'b','source':'B','targets':['X','Y'],'lower':3,'upper':5}],{'X':4,'Y':3})

    def test_global_population_and_fractional_extrema(self):
        p=self.system()
        feasible=[x for x in itertools.product(range(6),repeat=4)
                  if 2<=x[0]+x[1]<=4 and 3<=x[2]+x[3]<=5
                  and x[0]+x[2]==4 and x[1]+x[3]==3]
        for s,t in p.edge_inventory():
            a,b=p.vector(s,t),p.vector(s)
            values=[int(sum(a*x)) for x in feasible]
            ratios=[Fraction(int(sum(a*x)),int(sum(b*x))) for x in feasible]
            self.assertEqual(p.bounds(a),(min(values),max(values)))
            self.assertEqual(p.ratio(a,b),min(ratios))
            self.assertEqual(p.ratio(a,b,True),max(ratios))
        # Independently selecting each maximum would violate the target control.
        with self.assertRaises(ValueError):p.verify(np.array([4,3,4,3]))

    def test_infeasible_controls_and_duplicate_groups_fail(self):
        g={'id':'a','source':'A','targets':['X'],'lower':2,'upper':4}
        with self.assertRaises(ValueError):PopulationSystem([g],{'X':5})
        with self.assertRaises(ValueError):PopulationSystem([g,g],{'X':4})

    def test_undefined_source_ratio_fails(self):
        p=PopulationSystem([{'id':'a','source':'A','targets':['X'],'lower':0,'upper':2},
                            {'id':'b','source':'B','targets':['X'],'lower':0,'upper':2}],{'X':1})
        with self.assertRaises(ValueError):p.ratio(p.vector('A','X'),p.vector('A'))
