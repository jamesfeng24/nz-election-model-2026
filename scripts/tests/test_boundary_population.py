import unittest
from scripts.boundaries.population import population_interval


class PopulationTests(unittest.TestCase):
    def test_suppressed_is_unavailable_not_zero(self):
        cell = population_interval('-999')
        self.assertIsNone(cell['value'])
        self.assertEqual((cell['lower'], cell['upper']), (0, 5))
        self.assertEqual(cell['published'], -999)

    def test_random_rounding_is_not_nearest_rounding(self):
        cell = population_interval('12')
        self.assertEqual((cell['lower'], cell['upper']), (10, 14))
        self.assertEqual(population_interval('6')['lower'], 6)

    def test_malformed_and_impossible_release_fail(self):
        for value in ('', None, '-1', '0', '3', '7', '12.0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                population_interval(value)

    def test_real_geometry_population_and_controls_regenerate(self):
        import json
        from scripts.boundaries.audit_population import build, OUTPUT
        result = build()
        self.assertEqual(result['meshblockCount'], 57553)
        self.assertEqual(len(result['targetControls']), 71)
        self.assertTrue(all(r['withinDisclosureBounds'] for r in result['targetControls']))
        self.assertEqual((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode(),
                         OUTPUT.read_bytes())
