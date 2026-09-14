import itertools
import unittest
from fractions import Fraction
from scripts.boundaries.composition import summarize


class CompositionTests(unittest.TestCase):
    def test_metrics_match_exhaustive_integer_partitions(self):
        for bounds,total in [([(0,3),(2,5),(0,4)],6), ([(4,5)],5), ([(0,2),(0,2)],1)]:
            feasible = [x for x in itertools.product(*(range(a,b+1) for a,b in bounds)) if sum(x)==total]
            edges = [{'source':str(i),'lower':a,'upper':b} for i,(a,b) in enumerate(bounds)]
            # Summarizer expects sharp marginal bounds from destination tightening.
            from scripts.boundaries.feasible import tighten_destinations
            edges = tighten_destinations([{**e,'target':'x'} for e in edges],{'x':total})
            result = summarize(edges,total)
            metrics = {'dominantPredecessorShare': [Fraction(max(x),total) for x in feasible],
                       'effectivePredecessorCount': [Fraction(total*total,sum(v*v for v in x)) for x in feasible]}
            for key,values in metrics.items():
                self.assertEqual(Fraction(**result[key+'Lower']),min(values))
                self.assertEqual(Fraction(**result[key+'Upper']),max(values))
            counts=[sum(v>0 for v in x) for x in feasible]
            self.assertEqual(result['positivePredecessorCountLower'],min(counts))
            self.assertEqual(result['positivePredecessorCountUpper'],max(counts))
