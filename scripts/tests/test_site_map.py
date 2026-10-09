"""Stage84 site map: the saved land-only electorate outlines for the public site's clickable map.

Re-deriving the file reads 280 MB of meshblocks and needs shapely, so that is `python3 -m scripts.site_map.build --check`
(run by hand after a change to the builder or the boundary inputs); these tests check the saved file and its recorded inputs.
"""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAVED = ROOT / 'data/processed/site-map/2026/map.json'


class SiteMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = json.loads(SAVED.read_text(encoding='utf-8'))

    def test_recorded_inputs_are_the_preserved_meshblock_files(self):
        self.assertEqual(len(self.map['inputs']), 5)
        for path, digest in self.map['inputs'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)

    def test_every_2026_seat_has_one_outline(self):
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
        self.assertLess(SAVED.stat().st_size, 400_000)

    def test_the_frame_is_the_mainland_only(self):
        self.assertLess(self.map['width'], 22_000)
        self.assertLess(self.map['height'], 30_000)

    def test_a_seat_on_several_islands_is_one_shape_with_several_parts(self):
        auckland_central = next(s for s in self.map['seats'] if s['name'] == 'Auckland Central')
        self.assertGreater(auckland_central['path'].count('M'), 3)   # Waiheke, Great Barrier and the isthmus

    def test_insets_sit_inside_the_frame(self):
        for inset in self.map['insets']:
            x, y, w, h = inset['box']
            self.assertTrue(x >= 0 and y >= 0 and x + w <= self.map['width'] and y + h <= self.map['height'], inset['name'])


if __name__ == '__main__':
    unittest.main()
