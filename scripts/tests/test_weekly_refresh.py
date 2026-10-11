"""Stage70 weekly poll refresh: rules, panel chain and committed-artifact checks (stdlib + numpy only; no network, no inference)."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.polling.national_foundation.records import record
from scripts.polling.weekly_refresh import delta, electorate_polls, run, summarize
from scripts.polling.weekly_refresh.common import BASE_PANEL, read

TABLE = """<table><tr><th>Date[a]</th><th>Polling organisation</th><th>Sample size</th><th>NAT</th><th>LAB</th><th>GRN</th><th>ACT</th><th>NZF</th><th>TPM</th><th>OPP</th><th>Others</th><th>Lead</th></tr>
<tr><td>6 Oct 2026</td><td>Leaders debate in TVNZ.</td></tr>
<tr><td>1–5 Oct 2026</td><td>1 News–Verian</td><td>1,001</td><td>29</td><td>28</td><td>16</td><td>9</td><td>10</td><td>0.6</td><td>7</td><td>0.8[b]</td><td>1</td></tr>
<tr><td>2–4 Oct 2026</td><td>Mystery Polls Ltd</td><td>800</td><td>30</td><td>30</td><td>10</td><td>10</td><td>10</td><td>2</td><td>5</td><td>3</td><td>0</td></tr>
<tr><td>14 Oct 2023</td><td>2023 election result</td><td>N/A</td><td>38</td><td>27</td><td>11</td><td>8</td><td>6</td><td>2</td><td>2</td><td>6</td><td>11</td></tr></table>"""


def rec(org, d, nat=30, lab=30, n='1000', **kw):
    fs = {'date': d, 'org': org, 'n': n, 'NAT': str(nat), 'LAB': str(lab), 'GRN': '10', 'ACT': '10', 'NZF': '10', 'MRI': '2', 'TOP': '5', 'OTH': '3', **kw}
    r = record(2026, fs, {'sourceId': 'test'})
    r['commissioner'] = org
    return r


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.base = [rec('COL', ['2026-09-20', '2026-09-27'], 28, 28), rec('REI', ['2026-09-24', '2026-10-01'], 26, 31)]

    def kinds(self, wiki, unmapped=(), day='2026-10-07'):
        added, blockers, reviews, infos = delta.evaluate(self.base, wiki, list(unmapped), day)
        return added, [b['kind'] for b in blockers], [r['kind'] for r in reviews], [i['kind'] for i in infos]

    def test_clean_new_row_has_no_blocker_or_review(self):
        new = rec('COL', ['2026-10-01', '2026-10-05'], 29, 28)
        added, b, r, i = self.kinds(self.base + [new])
        self.assertEqual((len(added), b, r), (1, [], []))
        self.assertIn('primary_verification_pending', i)

    def test_future_fieldwork_is_a_blocker(self):
        self.assertIn('fieldwork_ends_after_run_date', self.kinds(self.base + [rec('COL', ['2026-10-08', '2026-10-12'])])[1])

    def test_revised_and_removed_rows_block(self):
        revised = rec('COL', ['2026-09-20', '2026-09-27'], 29, 28)
        self.assertEqual(self.kinds([revised, self.base[1]])[1], ['revised_row'])
        self.assertEqual(self.kinds([self.base[0]])[1], ['removed_row'])

    def test_unmapped_row_blocks(self):
        self.assertEqual(self.kinds(self.base, [{'row': 3, 'reason': 'Unrecognized pollster', 'cells': []}])[1], ['unmapped_row'])

    def test_new_pollster_and_odd_dates_are_reviews_not_blockers(self):
        added, b, r, i = self.kinds(self.base + [rec('IPS', ['2026-10-01', '2026-10-05']), rec('COL', ['2026-08-01', '2026-09-30'])])
        self.assertEqual(b, [])
        self.assertIn('new_pollster', r); self.assertIn('odd_field_dates', r)

    def test_blank_sample_is_info_and_compatible_with_pinned_default(self):
        base = [rec('TBM', ['2026-03-01', '2026-03-10'], n='1000')]
        wiki = [rec('TBM', ['2026-03-01', '2026-03-10'], n='~')]
        _, blockers, _, _ = delta.evaluate(base, wiki, [], '2026-10-07')
        self.assertEqual(blockers, [])

    def test_known_collapsed_april_pair_is_not_a_change(self):
        dropped = rec('TBM', ['2026-04-16'])
        dropped['id'] = delta.DUPLICATE_DROPPED
        kept = rec('TBM', ['2026-04-00', '2026-04-16'], n='1000')
        kept['id'] = delta.DUPLICATE_KEPT
        _, blockers, _, _ = delta.evaluate([kept], [dropped], [], '2026-10-07')
        self.assertEqual(blockers, [])

    def test_wiki_table_parse_skips_events_and_results_and_reports_unmapped(self):
        rows, unmapped = delta.wiki_rows(TABLE, 'src', 'raw', 'sha')
        self.assertEqual([r['pollsterCode'] for r in rows], ['COL'])
        self.assertEqual(rows[0]['publishedOther']['published'], '0.8')
        self.assertEqual([u['reason'] for u in unmapped], ['Unrecognized pollster'])
        with self.assertRaises(ValueError):
            delta.wiki_rows('<table><tr><th>x</th></tr></table>', 's', 'r', 'h')


class PanelAndRunTests(unittest.TestCase):
    def test_next_panel_is_previous_plus_additions_and_rejects_collisions(self):
        base = read(BASE_PANEL)
        existing = {r['id'] for r in base['records']}
        new = rec('COL', ['2026-10-01', '2026-10-05'], 29, 28)
        self.assertNotIn(new['id'], existing)
        with tempfile.TemporaryDirectory() as d:
            panel, changes = delta.next_panel(BASE_PANEL, [new], '2026-10-07', 'raw/x', 'abc', '123')
        self.assertEqual(len(panel['records']), len(base['records']) + 1)
        self.assertEqual(panel['basePanelSha256'], run.sha(BASE_PANEL))
        self.assertEqual(next(r for r in panel['records'] if r['id'] == new['id'])['evidenceGrade'], 'aggregator_only')
        self.assertEqual([a['id'] for a in changes['added']], [new['id']])
        clash = json.loads(json.dumps(base['records'][0])); clash['estimates']['NAT']['share'] = .99
        with self.assertRaises(ValueError):
            delta.next_panel(BASE_PANEL, [clash], '2026-10-07', 'raw/x', 'abc', '123')

    def test_run_refuses_election_day_and_later(self):
        with self.assertRaises(ValueError):
            run.run('2026-11-07')

    def test_estimate_shift_flag_uses_the_stage62_threshold(self):
        def est(nat, lab):
            return {'codes': ['NAT', 'LAB'], 'lastData': {'NAT': {'mean': nat}, 'LAB': {'mean': lab}}, 'marginNatMinusLabLastData': {'mean': nat - lab}}
        prev = {'lastData': {'NAT': {'mean': 27.5}, 'LAB': {'mean': 28.9}}, 'marginNatMinusLabLastData': {'mean': -1.4}, 'lastDataWeek': 'w', 'polls2026': 119}
        _, flags = summarize.compare(est(27.9, 29.1), prev, 'x')
        self.assertEqual(flags, [])
        _, flags = summarize.compare(est(28.6, 29.1), prev, 'x')
        self.assertEqual([f['category'] for f in flags], ['NAT'])


class AdoptTests(unittest.TestCase):
    def test_next_version(self):
        from scripts.polling.weekly_refresh import adopt
        self.assertEqual(adopt.next_version('2026-10-07.4', '2026-10-07'), '2026-10-07.5')
        self.assertEqual(adopt.next_version('2026-10-07.4', '2026-10-14'), '2026-10-14.1')

    def test_adopting_the_latest_run_points_the_config_at_last_data_draws_only(self):
        from scripts.polling.weekly_refresh import adopt
        runs = run.load_index()['runs']
        if not runs:
            self.skipTest('no published refresh yet')
        date = runs[-1]['date']
        want = adopt.target(date)
        self.assertEqual(want['stateKey'], 'lastDataSupport')
        self.assertIn('electionDay', want['forbiddenStateKeys'])
        self.assertLessEqual(want['modelStateAsOf'], want['dataCutoff'])
        original = adopt.CONFIG
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / 'nowcast.json'
            copy.write_bytes(original.read_bytes())
            adopt.CONFIG = copy
            try:
                adopt.adopt(date)
                adopt.adopt(date, check=True)
                cfg = json.loads(copy.read_text(encoding='utf-8'))
            finally:
                adopt.CONFIG = original
        self.assertEqual(cfg['national']['source'], want['source'])
        self.assertEqual(cfg['national']['stateKey'], 'lastDataSupport')
        # the forecast is as of the later of the adopted national cutoff and the adopted electorate-poll run (an electorate-only refresh moves it)
        self.assertEqual(cfg['seatPolls']['pollCutoff'], adopt.poll_cutoff(want['dataCutoff'], adopt.electorate_target()))
        self.assertGreaterEqual(cfg['seatPolls']['pollCutoff'], cfg['national']['dataCutoff'])

    def test_an_electorate_only_refresh_moves_the_pin_and_the_poll_cutoff_but_not_the_national_input(self):
        from scripts.polling.weekly_refresh import adopt
        runs = run.load_index()['runs']
        if not runs:
            self.skipTest('no published refresh yet')
        date = runs[-1]['date']
        want = adopt.target(date)
        fake = {'date': '2999-01-01', 'pollsSha256': 'a' * 64}                    # a later electorate-poll run; no national run came with it
        saved = adopt.CONFIG, adopt.electorate_target, adopt.check_config
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / 'nowcast.json'
            copy.write_bytes(adopt.CONFIG.read_bytes())
            before = json.loads(copy.read_text(encoding='utf-8'))
            adopt.CONFIG, adopt.electorate_target, adopt.check_config = copy, lambda date=None: fake, lambda config: None     # the real index does not hold the run
            try:
                adopt.adopt(date)
                after = json.loads(copy.read_text(encoding='utf-8'))
            finally:
                adopt.CONFIG, adopt.electorate_target, adopt.check_config = saved
        self.assertEqual(after['seatPolls']['electorateRun'], fake)
        self.assertEqual(after['seatPolls']['pollCutoff'], '2999-01-01')
        self.assertEqual(after['national']['dataCutoff'], want['dataCutoff'])         # the national input is the newest national run, unchanged
        changed = {k for k in after if after[k] != before[k]}
        self.assertEqual(changed, {'national', 'seatPolls', 'configVersion'})

    def test_poll_cutoff_follows_the_later_of_the_national_cutoff_and_the_electorate_run(self):
        from scripts.polling.weekly_refresh import adopt
        self.assertEqual(adopt.poll_cutoff('2026-10-07', {'date': '2026-10-10'}), '2026-10-10')       # electorate polls arrived after the last national run
        self.assertEqual(adopt.poll_cutoff('2026-10-14', {'date': '2026-10-10'}), '2026-10-14')       # national run after the last electorate run
        self.assertEqual(adopt.poll_cutoff('2026-10-14', {'date': '2026-10-14'}), '2026-10-14')
        self.assertEqual(adopt.poll_cutoff('2026-10-14', None), '2026-10-14')


class CommittedArtifactTests(unittest.TestCase):
    def test_committed_runs_are_consistent(self):
        seen = run.check()
        self.assertEqual(seen, [r['date'] for r in run.load_index()['runs']])
        for d in seen:
            est = read(run.OUT / d / 'estimate.json')
            self.assertEqual(est['targetType'], 'nowcast')
            self.assertNotIn('electionWeek', est)
            self.assertNotIn('electionDay', json.dumps(est['nowcastInput']['stateKey']))

    def test_electorate_poll_registry_matches_preserved_bytes(self):
        out = electorate_polls.build()
        for name, value in out.items():
            self.assertEqual(read(electorate_polls.OUT / name), value)
        polls = out['polls.json']['polls']
        self.assertEqual({p['electorate'] for p in polls}, {'Wellington Bays', 'Mt Albert'})
        self.assertTrue(all(p['type'] == 'general' for p in polls))


if __name__ == '__main__':
    unittest.main()
