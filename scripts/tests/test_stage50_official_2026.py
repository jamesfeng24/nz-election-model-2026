"""Stage50 part 2: the preserved 2026-10-10 official publications reproduce the official table, roster snapshot,
features and config pointers, and the live config's roster is the official one."""
import json
import unittest
from collections import Counter
from scripts.nominations_2026 import extract, official, refresh
from scripts.uncertainty_revision.common import ROOT, read

ACQUISITION = 'data/processed/nominations-2026/2026-10-10/acquisition.json'


class Publication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = extract.build()
        cls.table = cls.outputs[extract.OUT + 'official-table.json']

    def test_extract_reproduces_the_preserved_tables(self):
        for path, value in self.outputs.items():
            self.assertEqual(read(path), json.loads(json.dumps(value)), path)

    def test_every_published_row_is_transcribed_once(self):
        rows = self.table['rows']
        self.assertEqual(len(rows), 469)
        self.assertEqual(len({r['electorateLabel'] for r in rows}), 71)
        self.assertEqual(len({r['locator'] for r in rows}), 469)
        self.assertEqual(rows[0], {'electorateLabel': 'Auckland Central', 'displayName': 'Johan CHANG',
                                   'affiliationLabel': 'Opportunity Party', 'locator': 'Candidates!A2:C2'})
        official.check_table(self.table)

    def test_published_names_keep_their_letters(self):
        self.assertEqual(extract.display_name('SWARBRICK, Chlöe'), 'Chlöe SWARBRICK')
        self.assertEqual(extract.display_name('McLELLAN, Tracey'), 'Tracey McLELLAN')
        for bad in ('NoComma', 'A, B, C', ', Given'):
            with self.assertRaises(ValueError):
                extract.display_name(bad)

    def test_affiliations_resolve_and_unregistered_parties_have_no_group(self):
        keys = Counter(official.affiliation_key(r['affiliationLabel']) for r in self.table['rows'])
        self.assertEqual(keys['labourparty'], 71)
        self.assertEqual(keys['independent'], 48)
        unregistered = {k: n for k, n in keys.items() if k.startswith('unregistered:')}
        self.assertEqual((len(unregistered), sum(unregistered.values())), (11, 17))
        self.assertEqual(official.affiliation_key('Alliance Party'), 'alliancepartyofaotearoanewzealand')

    def test_party_list_headings_are_exactly_the_register(self):
        lists = self.outputs[extract.OUT + 'party-lists.json']
        self.assertEqual(len(lists['parties']), 17)
        relations = read('data/processed/forecast-readiness/snapshots/2026-10-10/party-relationships.json')['records']
        self.assertEqual({p['targetGroupKey'] for p in lists['parties']}, {r['targetGroupKey'] for r in relations})


class Roster(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acquisition = read(ACQUISITION)
        cls.outputs = refresh.build(cls.acquisition)

    def test_refresh_reproduces_the_committed_outputs(self):
        for path, value in self.outputs.items():
            self.assertEqual(read(path), json.loads(json.dumps(value)), path)

    def test_every_seat_is_a_complete_official_slate(self):
        snapshot = self.outputs[refresh.snapshot_dir(self.acquisition) + 'snapshot.json']
        self.assertEqual(len(snapshot['completeSlateDeclarations']), 71)
        self.assertEqual(len(snapshot['occurrences']), 469)
        self.assertTrue(all(o['status'] == 'official_nomination' and o['active'] and not o['conflict'] for o in snapshot['occurrences']))
        self.assertEqual(snapshot['unmatchedClaims'], [])
        no_group = {o['originalAffiliation'] for o in snapshot['occurrences'] if o['ballotGroupKey'] is None}
        self.assertTrue(all(k == 'independent' or k.startswith('unregistered:') for k in no_group))

    def test_live_config_points_at_the_official_roster(self):
        from scripts.nowcast_assembly import assemble
        config = read('config/nowcast-2026.json')
        self.assertEqual(config['roster']['snapshotId'], 'nz-2026-official-nominations-2026-10-10')
        self.assertNotIn('roster.snapshotId', config['pending'])
        slates, _ = assemble.live_slates(config)
        self.assertEqual(len(slates), 64)
        self.assertEqual(sum(len(s) for s in slates.values()), 469 - sum(
            1 for c in read(config['candidate']['features'])['candidateRecords'] if c['scope'] == 'maori'))
        self.assertTrue(all(sum(c['group'] == 'labourparty' for c in s) == 1 for s in slates.values()))

    def test_apply_config_edits_only_the_roster_values(self):
        text = (ROOT / refresh.CONFIG).read_text(encoding='utf-8')
        self.assertEqual(refresh.apply_config(self.acquisition, self.outputs, text=text), text)
        pending = text.replace('"snapshotId": "nz-2026-official-nominations-2026-10-10"', '"snapshotId": null').replace(
            '  "pending": {\n', '  "pending": {\n    "roster.snapshotId": "Stage50",\n')
        self.assertEqual(refresh.apply_config(self.acquisition, self.outputs, text=pending), text)


if __name__ == '__main__':
    unittest.main()
