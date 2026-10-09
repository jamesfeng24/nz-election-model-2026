import hashlib
import json
import unittest
from scripts.polling import waiariki_poll_2026_10 as W
from scripts.polling.weekly_refresh.common import ROOT, read


class WaiarikiPoll(unittest.TestCase):
    def test_saved_registry_and_transcription_reproduce_from_the_preserved_bytes(self):
        for name, value in W.build().items():
            self.assertEqual(read(W.OUT / name), value)

    def test_registry_checksum_matches_the_page_bytes(self):
        entry = read(W.OUT / 'source-registry.json')['sources'][0]
        self.assertEqual(entry['sha256'], hashlib.sha256((ROOT / entry['rawPath']).read_bytes()).hexdigest())

    def test_transcription_is_internally_consistent(self):
        poll = read(W.OUT / 'polls.json')['polls'][0]
        named = sum(c['pollPercent'] for c in poll['candidates'])
        self.assertEqual(named + poll['undecidedPercent'] + poll['otherPercent'], 99)  # published whole numbers; rounding leaves 1 point
        self.assertEqual(poll['candidates'][0]['party'], 'MP')

    def test_pinned_inputs_are_untouched_and_waiariki_remains_unpolled(self):
        pinned = json.loads((ROOT / 'data/source-plans/maori-seat-layer/polls-2026.json').read_text())
        self.assertNotIn('Waiariki', {p['seat'] for p in pinned['polls']})
        self.assertEqual(hashlib.sha256((ROOT / 'data/source-plans/maori-seat-layer/polls-2026.json').read_bytes()).hexdigest(),
                         '5e613db83309d7b77cae0f3b5066e4bee9411a797ce5505c95427d91a14e8559')


if __name__ == '__main__':
    unittest.main()
