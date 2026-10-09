"""Stage84 site map: simplified electorate outlines for the public site's clickable map."""
import json
import unittest
from pathlib import Path

from scripts.site_map import build

ROOT = Path(__file__).resolve().parents[2]
SAVED = ROOT / 'data/processed/site-map/2026/map.json'


class SiteMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = build.build()

    def test_saved_file_is_reproduced_byte_for_byte(self):
        self.assertEqual(SAVED.read_text(encoding='utf-8'), build.render(self.map))

    def test_every_2026_seat_has_one_outline_and_nothing_is_empty(self):
        seats = self.map['seats']
        self.assertEqual(sum(s['kind'] == 'general' for s in seats), 64)
        self.assertEqual(sum(s['kind'] == 'maori' for s in seats), 7)
        self.assertEqual(len({s['id'] for s in seats}), 71)
        self.assertEqual(len({(s['kind'], s['name']) for s in seats}), 71)
        for s in seats:
            self.assertTrue(s['path'].startswith('M') and s['path'].endswith('z'), s['name'])
            x0, y0, x1, y1 = s['box']
            self.assertTrue(0 <= x0 < x1 <= self.map['width'] and 0 <= y0 < y1 <= self.map['height'], s['name'])

    def test_the_map_stays_light(self):
        self.assertLess(len(build.render(self.map)), 150_000)

    def test_chatham_islands_are_left_out_of_the_frame(self):
        self.assertLess(self.map['width'], 25_000)

    def test_simplification_keeps_endpoints_and_drops_collinear_points(self):
        line = [(0, 0), (1, 0.01), (2, 0), (3, 5), (4, 0)]
        kept = build.douglas_peucker(line, 0.5)
        self.assertEqual(kept[0], (0, 0))
        self.assertEqual(kept[-1], (4, 0))
        self.assertIn((3, 5), kept)
        self.assertNotIn((1, 0.01), kept)

    def test_insets_sit_inside_the_frame(self):
        for inset in self.map['insets']:
            x, y, w, h = inset['box']
            self.assertTrue(x >= 0 and y >= 0 and x + w <= self.map['width'] and y + h <= self.map['height'], inset['name'])


if __name__ == '__main__':
    unittest.main()
