"""Rounding checks admit independent rounding, not impossible published cells."""
import unittest
from fractions import Fraction as F
from scripts.transform.split_intervals import envelope, add_intervals, SourceDiscrepancies


class SplitIntervalTests(unittest.TestCase):
    def test_exact_bounds_and_clipping(self):
        self.assertEqual(envelope(29607,6.69),(F('1979.22795'),F('1982.18865')))
        self.assertEqual(envelope(100,0),(F(0),F('.005')))
        self.assertEqual(envelope(100,100),(F('99.995'),F(100)))

    def test_independent_rounding_not_midpoint_equality(self):
        audit=SourceDiscrepancies([])
        audit.compare('rounding',envelope(100,1.00),envelope(100,1.01),[])
        audit.finish()

    def test_disjoint_interval_fails(self):
        with self.assertRaisesRegex(ValueError,'Unreviewed'):
            SourceDiscrepancies([]).compare('impossible',(F('1937.4629'),F('1940.3855')),envelope(29607,6.69),[])

    def test_missing_or_invalid_percent_fails(self):
        for value in (None,-1,101):
            with self.subTest(value=value), self.assertRaises(ValueError):envelope(100,value)

    def test_sum_is_exact(self):
        self.assertEqual(add_intervals([envelope(100,1),envelope(100,2)]),(F('2.99'),F('3.01')))
