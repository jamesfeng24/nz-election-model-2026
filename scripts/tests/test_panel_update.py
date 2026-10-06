"""Stage59 derived 2026 poll panel: additions, the collapsed duplicate and byte-level reproducibility (no fitting)."""
import hashlib
import itertools
import json
import unittest

from scripts.polling.panel_update import build as pu

BASE = json.loads(pu.BASE_PANEL.read_text())['records']
PANEL = json.loads((pu.OUT / 'panel.json').read_text())
CHANGES = json.loads((pu.OUT / 'changes.json').read_text())


def by_id(records):
    return {r['id']: r for r in records}


class PanelUpdateTests(unittest.TestCase):
    def test_committed_outputs_reproduce_byte_for_byte(self):
        for name, value in pu.build().items():
            self.assertEqual((pu.OUT / name).read_bytes(), pu.encode(value), name)

    def test_stage35_panel_is_pinned_and_untouched(self):
        self.assertEqual(PANEL['basePanelSha256'], hashlib.sha256(pu.BASE_PANEL.read_bytes()).hexdigest())
        self.assertEqual(len(BASE), 496)

    def test_exactly_three_added_and_one_removed(self):
        old, new = by_id(BASE), by_id(PANEL['records'])
        self.assertEqual(len(new), 498)
        self.assertEqual(sorted(set(old) - set(new)), [pu.DUPLICATE_DROPPED])
        added = sorted(set(new) - set(old))
        self.assertEqual(added, sorted(a['id'] for a in CHANGES['added']))
        self.assertEqual(len(added), 3)
        # every surviving base wave is byte-identical except the one that absorbed the duplicate
        changed = [i for i in set(old) & set(new) if old[i] != new[i]]
        self.assertEqual(changed, [pu.DUPLICATE_KEPT])

    def test_rnz_reid_6_october_poll(self):
        r = next(x for x in PANEL['records'] if x['pollsterCode'] == 'REI' and x['fieldworkRaw'] == ['2026-09-24', '2026-10-01'])
        self.assertEqual((r['sampleSize'], r['publicationConfidence'], r['evidenceGrade']), (1000, 'verified', 'primary_verified'))
        self.assertEqual(r['publication'], '2026-10-06T06:27:00+13:00')
        shares = {k: v['published'] for k, v in r['estimates'].items()}
        self.assertEqual(shares, {'NAT': '25.9', 'LAB': '30.8', 'GRN': '14.8', 'ACT': '9', 'NZF': '10.6', 'MRI': '2', 'TOP': '5.5'})
        self.assertEqual(r['publishedOther']['share'], 0.007)
        self.assertEqual(r['status'], 'usable_partial')
        self.assertIn('sha256', r['provenance'][0])
        # Stage35 stopped at fieldwork end 2026-09-27; this is the only newer wave
        newer = [x for x in PANEL['records'] if x['cycle'] == 2026 and x['fieldworkEndBounds'][1] > '2026-09-27']
        self.assertEqual([x['id'] for x in newer], [r['id']])

    def test_talbot_mills_2024_rows(self):
        waves = {tuple(r['fieldworkRaw']): r for r in PANEL['records'] if r['pollsterCode'] == 'TBM' and r['fieldworkRaw'][0].startswith('2024')}
        nov, may = waves[('2024-11-01', '2024-11-10')], waves[('2024-05-01', '2024-05-10')]
        self.assertEqual(nov['evidenceGrade'], 'primary_verified')
        self.assertEqual({k: v['published'] for k, v in nov['estimates'].items() if v['status'] != 'not_reported'},
                         {'NAT': '34', 'LAB': '33', 'GRN': '10', 'ACT': '10', 'NZF': '7', 'MRI': '3.3'})
        self.assertTrue(any(p.get('sha256') and p['sourceId'].endswith('talbot-herald-2024-11.html') for p in nov['provenance']))
        self.assertEqual(may['evidenceGrade'], 'aggregator_only')
        self.assertEqual({k for k, v in may['estimates'].items() if v['status'] != 'not_reported'}, {'NAT', 'LAB'})
        # missing is not zero
        self.assertTrue(all(may['estimates'][k]['share'] is None for k in ('GRN', 'ACT', 'NZF', 'MRI', 'TOP')))
        self.assertEqual(len(waves), 7)

    def test_april_2026_duplicate_collapsed_into_the_interval_row(self):
        new = by_id(PANEL['records'])
        self.assertNotIn(pu.DUPLICATE_DROPPED, new)
        kept = new[pu.DUPLICATE_KEPT]
        self.assertEqual(kept['fieldworkRaw'], ['2026-04-00', '2026-04-16'])
        self.assertEqual({p['sourceId'] for p in kept['provenance']}, {'polling35-nixinova-data.yml', 'polling35-wiki2026.html'})
        april = [r for r in PANEL['records'] if r['pollsterCode'] == 'TBM' and r['fieldworkEndBounds'][1] == '2026-04-16']
        self.assertEqual(len(april), 1)

    def test_no_remaining_duplicates_or_same_pollster_overlap_in_the_2026_cycle(self):
        cur = [r for r in PANEL['records'] if r['cycle'] == 2026]
        for a, b in itertools.combinations(cur, 2):
            if a['pollsterCode'] != b['pollsterCode']:
                continue
            overlap = a['fieldworkStartBounds'][0] <= b['fieldworkEndBounds'][1] and b['fieldworkStartBounds'][0] <= a['fieldworkEndBounds'][1]
            self.assertFalse(overlap, (a['fieldworkRaw'], b['fieldworkRaw']))

    def test_stage52_talbot_snapshots_fully_match_the_updated_panel(self):
        for snap in ('labo49', 'danylmc'):
            self.assertEqual(CHANGES['stage52TalbotMillsCheck'][snap]['unmatched'], [])
            self.assertEqual(len(CHANGES['stage52TalbotMillsCheckAgainstStage35Panel'][snap]['unmatched']), 2)
            self.assertEqual(CHANGES['stage52TalbotMillsCheck'][snap]['panelWavesMatchedByMoreThanOneSnapshotRow'], {})

    def test_gap_detection_fails_loudly_if_the_source_changes(self):
        rows = pu.wikipedia_rows()
        base_ids = {r['id'] for r in BASE}
        with self.assertRaises(ValueError):
            pu.build_gap_rows(base_ids | {r['id'] for r in rows if r['pollsterCode'] == 'TBM' and r['fieldworkRaw'][0] == '2024-05-01'}, rows)


if __name__ == '__main__':
    unittest.main()
