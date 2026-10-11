"""Stage84 site evidence: the polls the forecast rests on and the weekly trend, exported for the public site."""
import json
import unittest
from pathlib import Path

from scripts.site_evidence import build

ROOT = Path(__file__).resolve().parents[2]
REFRESH = ROOT / 'data/processed/polling/weekly-refresh/2026-10-07'
SAVED = ROOT / 'data/processed/site-evidence/2026-10-07/evidence.json'


class SiteEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = build.build(REFRESH)

    def test_saved_file_is_reproduced_byte_for_byte(self):
        self.assertEqual(SAVED.read_text(encoding='utf-8'), build.render(self.evidence))

    def test_polls_carry_the_name_wikipedia_prints_for_them(self):
        names = {p['pollster'] for p in self.evidence['nationalPolls']}
        self.assertTrue({"Taxpayers' Union–Curia", 'RNZ–Reid Research', 'Roy Morgan'} <= names)
        self.assertFalse(names & {'Verian lineage', 'Talbot Mills/UMR'})
        self.assertTrue(all(p['commissioner'] is None for p in self.evidence['nationalPolls']))

    def test_every_2026_cycle_poll_is_listed_and_the_used_ones_match_the_fit(self):
        panel = json.loads((REFRESH / 'panel.json').read_text(encoding='utf-8'))
        estimate = json.loads((REFRESH / 'estimate.json').read_text(encoding='utf-8'))
        listed = self.evidence['nationalPolls']
        self.assertEqual(len(listed), sum(1 for r in panel['records'] if r['cycle'] == 2026))
        self.assertEqual(sum(p['usedInModel'] for p in listed), estimate['polls2026'])
        self.assertEqual(len({p['id'] for p in listed}), len(listed))
        for p in listed:
            if not p['usedInModel']:
                self.assertTrue(p['note'])

    def test_poll_figures_are_copied_as_published_and_missing_is_null_not_zero(self):
        panel = json.loads((REFRESH / 'panel.json').read_text(encoding='utf-8'))
        records = {r['id']: r for r in panel['records']}
        for poll in self.evidence['nationalPolls']:
            record = records[poll['id']]
            for share in poll['shares'][:-1]:
                code = next(c for c, party in build.PARTY_IDS.items() if party == share['partyId'] and c in record['estimates'])
                est = record['estimates'][code]
                if est['status'] == 'not_reported':
                    self.assertIsNone(share['percent'])
                else:
                    self.assertAlmostEqual(share['percent'], 100 * est['share'], places=2)

    def test_trend_ends_at_the_last_data_week_and_starts_at_the_previous_election(self):
        trend = self.evidence['trend']
        self.assertEqual(trend['weeks'][-1], '2026-09-27')
        self.assertEqual(len(trend['weeks']), len(trend['parties'][0]['mean']))
        nat = next(p for p in trend['parties'] if p['partyId'] == 'nationalparty')
        self.assertAlmostEqual(nat['mean'][0], 38.08, places=1)  # the 2023 National party vote
        for p in trend['parties']:
            for lo, mid, hi in zip(p['lower90'][1:], p['mean'][1:], p['upper90'][1:]):
                self.assertLessEqual(lo, mid + 1e-9)
                self.assertLessEqual(mid, hi + 1e-9)

    def test_no_poll_or_trend_week_postdates_the_data_cutoff(self):
        cutoff = self.evidence['dataCutoff']
        self.assertLessEqual(max(p['fieldworkEnd'] for p in self.evidence['nationalPolls']), cutoff)
        self.assertLessEqual(self.evidence['trend']['weeks'][-1], self.evidence['modelStateAsOf'])

    def test_every_poll_of_the_pinned_electorate_run_is_listed(self):
        from scripts.polling import electorate_live
        config = json.loads((ROOT / 'config/nowcast-2026.json').read_text(encoding='utf-8'))
        run = electorate_live.polls(*electorate_live.pinned(config))
        listed = self.evidence['seatPolls']
        self.assertEqual(len(listed), len(run))
        self.assertEqual(sorted((p['electorateName'], p['fieldworkEnd']) for p in listed), sorted((p['seat'], p['fieldwork']['end']) for p in run))
        for poll in listed:
            self.assertTrue(poll['fieldworkEnd'])
            self.assertEqual(poll['usedInModel'], poll['note'] is None)
            for source in poll['sources']:
                self.assertTrue(source['url'].startswith('https://') and source['label'])

    def test_general_seat_polls_are_marked_used_exactly_where_the_forecast_reads_them(self):
        from scripts.polling import electorate_live
        from scripts.seat_polls import live
        config = json.loads((ROOT / 'config/nowcast-2026.json').read_text(encoding='utf-8'))
        run, sha = electorate_live.pinned(config)
        rows = live.live_rows(run, sha)
        model_used = {pid for seat in live.inputs(self.evidence['dataCutoff'], rows=rows).values() for pid in seat['pollIds']}
        ids = {(r['electorate'], r['fieldworkEnd']): r['id'] for r in rows}
        general = [p for p in self.evidence['seatPolls'] if (p['electorateName'], p['fieldworkEnd']) in ids]
        self.assertEqual(len(general), len(rows))
        self.assertEqual({ids[(p['electorateName'], p['fieldworkEnd'])] for p in general if p['usedInModel']}, model_used)

    def test_each_maori_seat_uses_only_its_latest_poll_by_the_cutoff(self):
        maori = [p for p in self.evidence['seatPolls'] if p['electorateName'] in ('Hauraki-Waikato', 'Te Tai Hauāuru', 'Te Tai Tonga', 'Waiariki')]
        self.assertTrue(maori)
        for seat in {p['electorateName'] for p in maori}:
            polls = sorted((p for p in maori if p['electorateName'] == seat), key=lambda p: p['fieldworkEnd'])
            self.assertEqual([p['usedInModel'] for p in polls], [False] * (len(polls) - 1) + [True])

    def test_poll_results_name_the_seats_own_candidates_where_one_matches(self):
        mt_albert = next(p for p in self.evidence['seatPolls'] if p['electorateName'] == 'Mt Albert')
        self.assertEqual([r['name'] for r in mt_albert['results'][:2]], ['Helen WHITE', 'Melissa LEE'])
        self.assertEqual({r['party'] for r in mt_albert['results']} <= {'LAB', 'NAT', 'GRN', 'TOP', 'NZF', 'ACT', 'TPM', None}, True)

    def test_the_output_names_no_tooling(self):
        text = SAVED.read_text(encoding='utf-8').lower()
        for word in ('claude', 'anthropic', 'generated by'):
            self.assertNotIn(word, text)


if __name__ == '__main__':
    unittest.main()
