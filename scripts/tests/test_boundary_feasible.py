"""Brute-force small fixtures prove sharpness, not just interval containment."""
import itertools
import unittest
from fractions import Fraction
from scripts.boundaries.feasible import bounded_sum_component, tighten_destinations, outgoing_weight_bounds


class FeasibleTests(unittest.TestCase):
    def test_control_tightens_suppressed_cell_without_imputing(self):
        self.assertEqual(bounded_sum_component(0, 5, 10, 12, 13), (1, 3))
        with self.assertRaises(ValueError):
            bounded_sum_component(0, 5, 10, 12, 18)

    def test_ratio_bounds_attained_under_all_destination_equations(self):
        edges = [{'source': s, 'target': t, 'lower': lo, 'upper': hi}
                 for s,t,lo,hi in [('a','x',1,4),('b','x',2,5),('a','y',3,6),('b','y',1,3)]]
        controls = {'x': 6, 'y': 7}
        tightened = tighten_destinations(edges, controls)
        weights = outgoing_weight_bounds(tightened)
        feasible = [v for v in itertools.product(*(range(e['lower'],e['upper']+1) for e in edges))
                    if v[0]+v[1]==6 and v[2]+v[3]==7]
        for i, edge in enumerate(weights):
            ratios = [Fraction(v[i], sum(v[j] for j,e in enumerate(edges) if e['source']==edge['source'])) for v in feasible]
            self.assertEqual(Fraction(**edge['weightLower']), min(ratios))
            self.assertEqual(Fraction(**edge['weightUpper']), max(ratios))
        for v in feasible:
            for source in ('a','b'):
                ids = [j for j,e in enumerate(edges) if e['source']==source]
                self.assertEqual(sum(Fraction(v[j],sum(v[k] for k in ids)) for j in ids),1)

    def test_reject_missing_controls_duplicates_and_zero_denominator(self):
        edge = {'source':'a','target':'x','lower':0,'upper':5}
        for edges,controls in [([edge],{}),([edge,edge],{'x':2}),([edge],{'x':6})]:
            with self.assertRaises(ValueError): tighten_destinations(edges,controls)
        with self.assertRaises(ValueError): outgoing_weight_bounds([edge])

    def test_real_exceptions_preserve_uncertainty_and_exact_endpoints(self):
        import json
        from scripts.boundaries.suppression_report import build, OUTPUT
        result = build()
        self.assertEqual(result['status'], 'resolved_as_partially_identified')
        for row, denominator in zip(result['exceptions'], (64501, 76207)):
            self.assertIsNone(row['population']['value'])
            self.assertEqual((row['conditionalPopulationLower'],row['conditionalPopulationUpper']), (0,5))
            self.assertIsNone(row['transfer']['weight'])
            self.assertEqual(Fraction(**row['transfer']['weightUpper']), Fraction(5,denominator))
        self.assertEqual((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode(),OUTPUT.read_bytes())
