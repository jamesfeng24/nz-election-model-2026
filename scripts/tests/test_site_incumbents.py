"""The sitting-MP flags are reproducible, come only from the preserved MP index, and never mark list MPs."""
import json
import unittest

from scripts.site_incumbents import build as incumbents


class SiteIncumbentsTests(unittest.TestCase):
    def test_saved_file_is_reproduced_from_its_inputs(self):
        self.assertEqual(incumbents.OUT.read_text(encoding='utf-8'), incumbents.render(incumbents.build()))

    def test_every_match_is_an_electorate_mp_standing_under_the_same_name(self):
        data = json.loads(incumbents.OUT.read_text(encoding='utf-8'))
        self.assertGreater(len(data['incumbents']), 50)
        seats = [r['targetElectorateId'] for r in data['incumbents']]
        self.assertEqual(len(seats), len(set(seats)), 'a seat has at most one incumbent')
        mps = {m['name'] for m in incumbents.current_electorate_mps()}
        for r in data['incumbents']:
            self.assertIn(r['mp'], mps)
        self.assertEqual({r['mp'] for r in data['incumbents']} | {r['mp'] for r in data['unmatchedElectorateMps']}, mps)

    def test_name_matching_ignores_case_macrons_and_short_first_names(self):
        mp = {'surname': 'maipi clarke', 'given': 'hana rawhiti'}
        self.assertTrue(incumbents.same_person(mp, 'Hana-Rawhiti MAIPI-CLARKE'))
        self.assertTrue(incumbents.same_person({'surname': 'bishop', 'given': 'chris'}, 'Christopher BISHOP'))
        self.assertFalse(incumbents.same_person({'surname': 'bishop', 'given': 'chris'}, 'Anna BISHOP'))
        self.assertTrue(incumbents.same_person({'surname': 'van de molen', 'given': 'tim'}, 'Tim VAN DE MOLEN'))
        self.assertTrue(incumbents.same_person({'surname': 'macleod', 'given': 'david'}, 'David MacLEOD'))


if __name__ == '__main__':
    unittest.main()
