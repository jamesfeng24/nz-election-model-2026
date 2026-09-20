"""2017→2020 real-source crosswalk and conservation regression checks."""
import json
import unittest
from scripts.boundaries.lineage_2020 import ROOT
from scripts.boundaries.transition import build
from scripts.tests import test_boundary_transition as current_tests


class Transition2020Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build(json.loads((ROOT / 'data/controls/boundaries/transitions/2017-2020.json').read_bytes()))

    def test_source_destination_coverage_and_unchanged_controls(self):
        for kind, counts in [('general', (64, 65, 97, 34)), ('maori', (7, 7, 10, 2))]:
            scope = self.result['scopes'][kind]
            self.assertEqual((len(scope['sources']), len(scope['targets']), len(scope['edges']),
                              sum(t['officialChangeStatus'] == 'unchanged' for t in scope['targets'])), counts)
            self.assertEqual(scope['meshblockCount'], 53582)
            self.assertTrue(all(t['unchangedMembershipStatus'] == 'identity' for t in scope['targets']
                                if t['officialChangeStatus'] == 'unchanged'))
        general = self.result['scopes']['general']
        self.assertTrue(next(t for t in general['targets'] if t['name'] == 'Remutaka')['officialRename'])
        self.assertFalse(next(t for t in general['targets'] if t['name'] == 'Māngere')['officialRename'])
        self.assertIn('Mangere', [s['name'] for s in general['sources']])
        self.assertIsNone(self.result['nominalAllocation'])

    def test_all_weight_endpoints_have_conserving_witnesses(self):
        current_tests.TransitionTests.test_every_sharp_weight_endpoint_has_conserving_population_witness(self)

    def test_deterministic_committed_output(self):
        self.assertEqual((json.dumps(self.result, ensure_ascii=False, indent=2) + '\n').encode(),
                         (ROOT / 'data/processed/boundaries/2017-2020/crosswalk.json').read_bytes())
