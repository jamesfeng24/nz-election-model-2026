"""Independent frozen baseline captured before authorized panel expansion."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]


class PanelBaselineTests(unittest.TestCase):
    def test_pinned_per_election_inputs(self):
        contract=json.loads((ROOT/'data/source-plans/historical-panel.json').read_text())
        self.assertEqual(contract['years'],[2008,2011,2014,2017,2020,2023])
        self.assertEqual(len(contract['inputSha256']),18)
        for path,digest in contract['inputSha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
        self.assertEqual(len(contract['legacyPanel']),6)
