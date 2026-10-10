"""Stage82 electorate poll refresh: header-driven alignment, blockers, append-only chain and the committed first run (stdlib only; no network)."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.polling.electorate_refresh import parse, rules, run
from scripts.polling.weekly_refresh import capture, common
from scripts.polling.weekly_refresh.common import CAPTURE, ROOT

FIRST = run.load_index()['runs'][0]['date']
PAGE = (ROOT / 'data/raw/polling/electorate-live' / FIRST / CAPTURE).read_text(encoding='utf-8')
LABELS = json.loads((ROOT / 'data/processed/polling/electorate-live' / FIRST / 'seats.json').read_text())['labels']
SEATS = rules.resolve_seats(LABELS)
DAY = '2026-10-17'

MINI = """<h2>Electorate polling</h2><h3>General electorates</h3><h4>Mount Albert</h4>
<table><tr><th>Date</th><th>Polling organisation</th><th>Sample size</th><th></th><th>LAB</th><th>NAT</th><th>GRN</th><th>OPP</th><th>Lead</th></tr>
<tr><td rowspan="2">1–5 Oct 2026</td><td rowspan="2">Curia<sup><a href="#cite_note-9">[9]</a></sup></td><td rowspan="2">400</td><td><b>Party Vote</b></td><td>31</td><td>28</td><td>17</td><td>6</td><td>3</td></tr>
<tr><td><b>Electorate Vote</b></td><td>33</td><td>~32</td><td>-</td><td>10</td><td>1</td></tr></table>
<h2>Demographic polling</h2>"""


def edit_section(page, old, new):
    """Replace the first `old` inside the electorate section only (the national table above it has many equal cells)."""
    i = page.index('Electorate polling')
    j = page.index(old, i)
    return page[:j] + new + page[j + len(old):]


def poll_with(page, seat, pollster_part):
    return [p for p in parse.parse_page(page) if p['seatName'] == seat and pollster_part in p['pollster']]


class AlignmentTests(unittest.TestCase):
    def test_merged_cells_do_not_shift_the_electorate_row(self):
        (p,) = parse.parse_page(MINI)
        self.assertEqual(p['electorate'], {'LAB': 33.0, 'NAT': 32.0, 'TOP': 10.0})        # GRN "-" is missing, not zero; OPP is stored as TOP
        self.assertEqual(p['flags']['electorate'], {'NAT': 'approx'})
        self.assertEqual(p['partyVote'], {'LAB': 31.0, 'NAT': 28.0, 'GRN': 17.0, 'TOP': 6.0})
        self.assertEqual(p['fieldwork'], {'raw': '1–5 Oct 2026', 'start': '2026-10-01', 'end': '2026-10-05'})

    def test_real_page_reads_twelve_polls_and_matches_the_press_transcriptions(self):
        polls = parse.parse_page(PAGE)
        self.assertEqual(len(polls), 12)
        self.assertEqual((sum(p['kind'] == 'general' for p in polls), sum(p['kind'] == 'maori' for p in polls)), (8, 4))
        (alb,) = [p for p in polls if p['seatName'] == 'Mount Albert' and p['fieldwork']['raw'] == '21–28 Sep 2026']
        self.assertEqual(alb['electorate'], {'LAB': 33.0, 'NAT': 32.0, 'GRN': 14.0, 'TOP': 10.0, 'NZF': 5.0, 'ACT': 3.0, 'TPM': 2.0})   # Stage70 Part C (The Spinoff)
        (bays,) = poll_with(PAGE, 'Wellington Bays', 'Curia')
        self.assertEqual(bays['electorate'], {'GRN': 29.0, 'LAB': 29.0, 'NAT': 15.0, 'ACT': 5.0, 'NZF': 5.0, 'TOP': 3.0})          # Stage70 Part C (Newsroom)
        self.assertEqual(bays['partyVote']['GRN'], 31.0)
        (hutt,) = poll_with(PAGE, 'Hutt South', '')
        self.assertEqual(hutt['flags']['electorate'], {'NAT': 'approx'}); self.assertEqual(hutt['electorate']['NAT'], 30.0)
        (tonga,) = poll_with(PAGE, 'Te Tai Tonga', '')
        self.assertEqual(tonga['electorate'], {'LAB': 36.0, 'TPM': 21.0, 'GRN': 19.0, 'IND': 18.0})

    def test_every_page_seat_resolves_to_an_official_label(self):
        for p in parse.parse_page(PAGE):
            self.assertIn(rules.seat_key(p['seatName']), SEATS, p['seatName'])
        self.assertEqual(SEATS[rules.seat_key('Mount Albert')], 'Mt Albert')
        self.assertEqual(SEATS[rules.seat_key('Kāpiti')], 'Kapiti')
        self.assertEqual(SEATS[rules.seat_key('Te Tai Hauāuru')], 'Te Tai Hauāuru')

    def test_cells_and_dates(self):
        self.assertEqual(parse.cell_number('~30'), (30.0, 'approx'))
        self.assertEqual(parse.cell_number('37.5'), (37.5, None))
        for blank in ('', '-', '—', '—N/a', ' '):
            self.assertEqual(parse.cell_number(blank), (None, None), blank)
        for bad in ('Tie', '3 or 4', '12x', '1e3'):
            with self.assertRaises(parse.Block):
                parse.cell_number(bad)
        self.assertEqual(parse.parse_fieldwork('21 Sep – 1 Oct 2026'), ('2026-09-21', '2026-10-01'))
        self.assertEqual(parse.parse_fieldwork('17 Sep 2026'), ('2026-09-17', '2026-09-17'))
        for bad in ('Sep 2026', '5–1 Oct 2026', '31–32 Oct 2026', 'about September'):
            with self.assertRaises(parse.Block):
                parse.parse_fieldwork(bad)


class BlockTests(unittest.TestCase):
    def blocks(self, html):
        with self.assertRaises(parse.Block) as cm:
            parse.parse_page(html)
        return cm.exception.kind

    def test_unexpected_structure_stops_the_run(self):
        self.assertEqual(self.blocks(MINI.replace('<th>OPP</th>', '<th>XYZ</th>')), 'unknown_party_column')
        self.assertEqual(self.blocks(MINI.replace('<th>Lead</th>', '<th>Margin</th>')), 'unexpected_header')
        self.assertEqual(self.blocks(MINI.replace('<td>33</td>', '<td>Tie</td>')), 'unreadable_cell')
        self.assertEqual(self.blocks(MINI.replace('<b>Electorate Vote</b>', '<b>Candidate</b>')), 'row_pair_labels')
        self.assertEqual(self.blocks(MINI.replace('<td>33</td><td>~32</td>', '<td>33</td>')), 'ragged_table')
        self.assertEqual(self.blocks(MINI.replace('<td>33</td>', '<td>93</td>')), 'shares_exceed_100')
        self.assertEqual(self.blocks(MINI.replace('Electorate polling', 'Seat polling')), 'electorate_section_missing')
        self.assertEqual(self.blocks(MINI.replace('General electorates', 'Other electorates')), 'unknown_subsection')
        self.assertEqual(self.blocks(MINI.replace('<h4>Mount Albert</h4>', '')), 'table_without_seat')
        self.assertEqual(self.blocks(MINI.replace('1–5 Oct 2026', 'early October')), 'unreadable_fieldwork')
        self.assertEqual(self.blocks(MINI.replace('<td rowspan="2">400</td>', '<td rowspan="2">lots</td>')), 'unreadable_sample')

    def test_a_dropped_row_cannot_pair_the_wrong_rows(self):
        rows = list(re.finditer(r'<tr[^>]*>.*?</tr>', PAGE, re.S))
        victim = [m for m in rows if 'Electorate' in m.group(0) and 'Vote' in m.group(0)][2]      # an electorate-vote row in the section
        self.assertGreater(victim.start(), PAGE.index('Electorate polling'))
        with self.assertRaises(parse.Block):
            parse.parse_page(PAGE[:victim.start()] + PAGE[victim.end():])


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.base = [rules.build_record(r, SEATS, DAY)[0] for r in parse.parse_page(PAGE)]

    def ev(self, base, html):
        return run.process(base, html, DAY, LABELS)

    def test_same_page_is_unchanged_and_an_empty_base_adds_everything(self):
        self.assertEqual(self.ev(self.base, PAGE)[0], 'unchanged')
        status, added, blockers, _, _ = self.ev([], PAGE)
        self.assertEqual((status, len(added), blockers), ('updated', 12, []))

    def test_edit_of_a_published_share_blocks(self):
        edited = edit_section(PAGE, '>28</td>', '>27</td>')
        status, _, blockers, _, _ = self.ev(self.base, edited)
        self.assertEqual((status, [b['kind'] for b in blockers]), ('blocked', ['revised_row']))

    def test_removed_unknown_seat_future_fieldwork_and_wrong_kind_block(self):
        status, _, blockers, _, _ = self.ev(self.base + [{**self.base[0], 'id': 'nz-seatpoll-gone'}], PAGE)
        self.assertEqual((status, [b['kind'] for b in blockers]), ('blocked', ['removed_row']))
        raw = parse.parse_page(PAGE)[0]
        self.assertEqual([b['kind'] for b in rules.build_record({**raw, 'seatName': 'Nowhere'}, SEATS, DAY)[1]], ['unknown_seat'])
        late = copy.deepcopy(raw); late['fieldwork'] = {'raw': 'x', 'start': '2026-10-16', 'end': '2026-10-20'}
        self.assertEqual([b['kind'] for b in rules.build_record(late, SEATS, DAY)[1]], ['fieldwork_ends_after_run_date'])
        self.assertEqual([b['kind'] for b in rules.build_record({**raw, 'kind': 'maori'}, SEATS, DAY)[1]], ['seat_kind_mismatch'])

    def test_pollster_spacing_does_not_change_identity(self):
        a, b = copy.deepcopy(parse.parse_page(PAGE)[0]), copy.deepcopy(parse.parse_page(PAGE)[0])
        b['pollster'] = b['pollster'].replace('–', ' – ')
        self.assertEqual(rules.build_record(a, SEATS, DAY)[0]['id'], rules.build_record(b, SEATS, DAY)[0]['id'])

    def test_flags_on_the_real_page(self):
        status, added, blockers, reviews, infos = self.ev([], PAGE)
        self.assertEqual(sorted(r['kind'] for r in reviews), ['approximate_value', 'independent_column', 'sponsored_source'])
        self.assertEqual({i['kind'] for i in infos} - {'late_addition'}, {'primary_verification_pending'})
        new_pollster = parse.parse_page(PAGE)[0]; new_pollster['pollster'] = 'Mystery Polls'
        _, _, reviews, _ = rules.evaluate(self.base[1:], [new_pollster], SEATS, DAY)
        self.assertIn('new_pollster', [r['kind'] for r in reviews])


class RunTests(unittest.TestCase):
    """End to end in a scratch tree below the repository (so relative paths resolve), with the committed capture standing in for a fetch."""

    def scratch(self):
        tmp = tempfile.TemporaryDirectory(dir=ROOT, prefix='.scratch-electorate-')
        base = Path(tmp.name)
        self.addCleanup(tmp.cleanup)
        return base

    def patches(self, base):
        rel_base = base
        national_raw, raw, out, frag = base / 'nat-raw', base / 'raw', base / 'out', base / 'handoff.d'
        return [mock.patch.object(run, 'RAW', raw), mock.patch.object(run, 'OUT', out), mock.patch.object(run, 'INDEX', out / 'index.json'),
                mock.patch.object(run, 'NATIONAL_RAW', national_raw), mock.patch.object(run, 'FRAGMENTS', frag), mock.patch.object(capture, 'RAW', national_raw)], national_raw

    def put_capture(self, national_raw, day, html):
        d = national_raw / day; d.mkdir(parents=True)
        (d / CAPTURE).write_text(html, encoding='utf-8')
        (d / (CAPTURE + '.headers')).write_text('HTTP/2 200\ncontent-revision-id: 111\nlast-modified: Fri, 09 Oct 2026 00:00:00 GMT\n')
        (d / 'fetch-log.tsv').write_text(f'{day}T00:00:00Z\t200\turl\t1\n')

    def test_chain_is_append_only_and_checkable(self):
        base = self.scratch(); patches, nat = self.patches(base)
        for p in patches:
            p.start(); self.addCleanup(p.stop)
        self.put_capture(nat, '2026-10-12', PAGE)
        self.assertEqual(run.run('2026-10-12', use_existing=True), 0)
        first = json.loads((run.OUT / '2026-10-12/polls.json').read_text())
        self.assertEqual(len(first['polls']), 12)
        self.assertTrue((run.FRAGMENTS / '2026-10-12-electorate-poll-refresh.md').exists())
        self.assertEqual(run.check(), ['2026-10-12'])
        # same page a week later: nothing to write
        self.put_capture(nat, '2026-10-19', PAGE)
        self.assertEqual(run.run('2026-10-19', use_existing=True), 0)
        self.assertFalse((run.OUT / '2026-10-19').exists())
        self.assertEqual(len(run.load_index()['runs']), 1)
        polls = json.loads((run.OUT / '2026-10-12/polls.json').read_text())['polls']
        self.assertEqual(polls, sorted(polls, key=lambda r: (r['fieldwork']['end'], r['seat'], r['id'])))
        # a revised published share blocks and writes only the reports and the capture copy
        revised = edit_section(PAGE, '>28</td>', '>27</td>')
        self.put_capture(nat, '2026-10-26', revised)
        self.assertEqual(run.run('2026-10-26', use_existing=True), run.EXIT_BLOCKED)
        names = sorted(p.name for p in (run.OUT / '2026-10-26').iterdir())
        self.assertIn('blocked.json', names); self.assertNotIn('polls.json', names)
        self.assertEqual(len(run.load_index()['runs']), 1)
        self.assertEqual(run.check(), ['2026-10-12'])      # the blocked run is not part of the chain

    def test_election_day_blocked_reruns_are_refused_and_published_reruns_are_no_ops(self):
        with self.assertRaises(ValueError):
            run.run('2026-11-07', use_existing=True)
        base = self.scratch(); patches, nat = self.patches(base)
        for p in patches:
            p.start(); self.addCleanup(p.stop)
        self.put_capture(nat, '2026-10-12', PAGE)
        run.run('2026-10-12', use_existing=True)
        before = sorted(p.name for p in (run.OUT / '2026-10-12').iterdir())
        # a same-date rerun of a published run ends cleanly and edits nothing, whether or not the page changed
        self.assertEqual(run.run('2026-10-12', use_existing=True), 0)
        (nat / '2026-10-12' / CAPTURE).write_text(edit_section(PAGE, '>28</td>', '>27</td>'), encoding='utf-8')
        self.assertEqual(run.run('2026-10-12', use_existing=True), 0)
        self.assertEqual(sorted(p.name for p in (run.OUT / '2026-10-12').iterdir()), before)
        self.assertEqual(len(run.load_index()['runs']), 1)
        self.assertEqual(run.check(), ['2026-10-12'])
        # a blocked date is not silently accepted on a rerun
        self.put_capture(nat, '2026-10-26', edit_section(PAGE, '>28</td>', '>27</td>'))
        self.assertEqual(run.run('2026-10-26', use_existing=True), run.EXIT_BLOCKED)
        with self.assertRaises(FileExistsError):
            run.run('2026-10-26', use_existing=True)


class CommittedRunTests(unittest.TestCase):
    def test_committed_runs_reproduce_from_their_captures(self):
        runs = run.check()
        self.assertEqual(runs, [e['date'] for e in run.load_index()['runs']])
        self.assertTrue(runs)

    def test_only_the_authorised_model_layers_read_the_live_file(self):
        # Authorised readers, both James 2026-10-10: the general-seat poll layer (Stage79 follow-up, D123) and the Maori seat layer (Stage86, D125).
        # Since D128 (Stage88) both read the run the configuration pins through one module, scripts/polling/electorate_live.py, and nothing else
        # names the live file; the layers' readers are checked to use it.
        hits = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'scripts').rglob('*.py')
                if 'electorate-live' in p.read_text(errors='ignore') and 'electorate_refresh' not in str(p)
                and 'refresh_workflow' not in str(p) and 'test_electorate_refresh' not in str(p) and 'test_weekly_refresh_workflow' not in str(p)]
        self.assertEqual(sorted(hits), ['scripts/polling/electorate_live.py'])
        users = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'scripts').rglob('*.py')
                 if 'electorate_live' in p.read_text(errors='ignore') and '/tests/' not in p.as_posix() and p.name != 'electorate_live.py']
        self.assertEqual(sorted(users), ['scripts/maori_seat_layer/live.py', 'scripts/nowcast_assembly/assemble.py', 'scripts/nowcast_assembly/evidence.py',
                                         'scripts/nowcast_assembly/maori.py', 'scripts/nowcast_config/validate.py', 'scripts/polling/weekly_refresh/adopt.py',
                                         'scripts/seat_polls/live.py', 'scripts/seat_polls/readout.py'])


if __name__ == '__main__':
    unittest.main()
