"""The forecast cutoff (`seatPolls.pollCutoff`): the date the seat polls are read up to and aged from, which an electorate-only refresh moves
past the national data cutoff (D133, provisional)."""
import copy
import json
import unittest
from pathlib import Path

from scripts.polling import electorate_live
from scripts.seat_polls import live

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / 'config/nowcast-2026.json').read_text(encoding='utf-8'))


class ForecastCutoffTests(unittest.TestCase):
    def test_it_is_the_poll_cutoff_and_falls_back_to_the_national_cutoff(self):
        self.assertEqual(electorate_live.forecast_cutoff(CONFIG), CONFIG['seatPolls']['pollCutoff'])
        bare = copy.deepcopy(CONFIG)
        bare['seatPolls'].pop('pollCutoff')
        self.assertEqual(electorate_live.forecast_cutoff(bare), CONFIG['national']['dataCutoff'])
        bare.pop('seatPolls')
        self.assertEqual(electorate_live.forecast_cutoff(bare), CONFIG['national']['dataCutoff'])

    def test_seat_polls_are_aged_from_the_forecast_cutoff_not_the_national_one(self):
        run, sha = electorate_live.pinned(CONFIG)
        rows = live.live_rows(run, sha)
        early, late = live.inputs('2026-10-10', rows=rows), live.inputs('2026-10-24', rows=rows)     # two weeks later, the national state unchanged
        self.assertTrue(early)
        self.assertEqual(set(early), set(late))
        for seat in early:
            self.assertAlmostEqual(late[seat]['ageWeeks'] - early[seat]['ageWeeks'], 2.0, places=9, msg=seat)

    def test_a_poll_that_ended_after_the_cutoff_is_not_used_until_the_cutoff_moves(self):
        run, sha = electorate_live.pinned(CONFIG)
        rows = live.live_rows(run, sha)
        ends = sorted(p['fieldwork']['end'] for p in electorate_live.polls(run, sha) if p['type'] != 'maori')
        self.assertTrue(ends)
        self.assertEqual(live.inputs('2000-01-01', rows=rows), {})                     # every poll ended after this cutoff
        self.assertTrue(live.inputs(ends[-1], rows=rows))                               # the cutoff that reaches the newest poll uses it


if __name__ == '__main__':
    unittest.main()
