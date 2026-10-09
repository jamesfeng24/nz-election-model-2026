"""Stage50: the official-nomination refresh is fail-closed and produces complete official slates through the unchanged
Stage40/42 builders and the Stage75 recentring. The end-to-end run uses a SYNTHETIC TEST FIXTURE official table (the
2026-10-05 party announcements plus invented Labour and independent rows), held in memory and never written."""
import copy
import unittest
from scripts.nominations_2026 import official, refresh, synthetic
from scripts.readiness.registry import occurrence_id
from scripts.uncertainty_revision.common import read

FRAME = read(refresh.PREVIOUS + 'target-frame.json')['records']
NAMES = {s['targetElectorateId']: s['canonicalName'] for s in FRAME}
ACQUISITION = synthetic.ACQUISITION


def synthetic_table():
    return synthetic.table()


def synthetic_registry():
    return synthetic.registry()


class Table(unittest.TestCase):
    def test_affiliations_map_or_fail_closed(self):
        self.assertEqual(official.affiliation_key('The New Zealand National Party'), 'nationalparty')
        self.assertEqual(official.affiliation_key('Labour Party'), 'labourparty')
        self.assertEqual(official.affiliation_key('Independent'), official.INDEPENDENT)
        with self.assertRaises(official.OfficialTableError):
            official.affiliation_key('A Party Registered After The Snapshot')

    def test_table_and_coverage_fail_closed(self):
        table = synthetic_table()
        self.assertEqual(len(official.completeness(table, FRAME)), 71)
        for edit in (lambda t: t['rows'].append(dict(t['rows'][0])),
                     lambda t: t['rows'][0].update(electorateLabel='Nowhere'),
                     lambda t: t['rows'][0].pop('locator'),
                     lambda t: t.update(publishedAt='soon')):
            broken = copy.deepcopy(table); edit(broken)
            with self.assertRaises((official.OfficialTableError, ValueError)):
                official.check_table(broken); official.completeness(broken, FRAME)
        partial = copy.deepcopy(table)
        partial['rows'] = [r for r in partial['rows'] if r['electorateLabel'] != NAMES['nz-general-2026-boundary-001']]
        with self.assertRaises(official.OfficialTableError):
            official.completeness(partial, FRAME)


class Refresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = synthetic_table()
        cls.outputs = refresh.build(ACQUISITION, registry=synthetic_registry(), tables=[('synthetic-official', cls.table)])

    def test_every_seat_is_an_official_complete_slate(self):
        snapshot = self.outputs[refresh.snapshot_dir(ACQUISITION) + 'snapshot.json']
        self.assertEqual(len(snapshot['completeSlateDeclarations']), 71)
        self.assertEqual(len(snapshot['occurrences']), len(self.table['rows']))
        self.assertTrue(all(o['status'] == 'official_nomination' and o['active'] for o in snapshot['occurrences']))
        independents = [o for o in snapshot['occurrences'] if o['originalAffiliation'] == official.INDEPENDENT]
        self.assertTrue(independents and all(o['ballotGroupKey'] is None for o in independents))

    def test_features_cover_every_candidate_and_are_recentred_on_the_live_fit(self):
        features = self.outputs[refresh.output_dir(ACQUISITION) + 'features-raw.json']
        centred = self.outputs[refresh.output_dir(ACQUISITION) + 'features-centred.json']
        self.assertTrue(all(s['slateComplete'] for s in features['seatRecords']))
        self.assertEqual(set(centred['candidates']), {c['targetOccurrenceId'] for c in features['candidateRecords']})
        self.assertEqual(centred['fitId'], read('data/processed/candidate-fit-2026/fit.json')['folds'][0]['fits']['baseline_plus_S_plus_R']['fitId'])

    def test_reconciliation_names_matches_and_new_candidates(self):
        report = self.outputs[refresh.output_dir(ACQUISITION) + 'reconciliation.json']
        self.assertEqual(report['matched'], report['announcedCandidates'])
        self.assertEqual(report['newInOfficialList'], 2 * 71)
        self.assertEqual(report['announcedNotNominatedAsSamePerson'], [])

    def test_refreshed_roster_feeds_the_live_assembly(self):
        from scripts.nowcast_assembly import assemble
        from scripts.tests.test_stage73_nowcast_assembly import synthetic_classification, synthetic_maori, COUNT
        config = read('config/nowcast-2026.json')
        config['roster']['snapshotId'] = 'synthetic-test-roster'; config['pending'].pop('roster.snapshotId', None)
        slates, _ = assemble.live_slates(config, self.outputs[refresh.output_dir(ACQUISITION) + 'features-raw.json'],
                                         self.outputs[refresh.output_dir(ACQUISITION) + 'features-centred.json'])
        self.assertEqual(len(slates), 64)
        bank = assemble.assemble(config, COUNT, slates=slates, classification=synthetic_classification(),
                                 maori_records=synthetic_maori(), workers=2)
        general = [s for s in bank['seats'] if s['scope'] == 'general']
        self.assertTrue(all(s['status'] == 'simulated' and len(s['winners']) == COUNT for s in general))
        self.assertTrue(any(None in s['candidateParty'] for s in general))

    def test_ids_follow_the_stage40_rule(self):
        snapshot = self.outputs[refresh.snapshot_dir(ACQUISITION) + 'snapshot.json']
        o = snapshot['occurrences'][0]
        self.assertEqual(o['targetOccurrenceId'], occurrence_id(o['targetElectorateId'], o['originalAffiliation'], o['displayedName']))


if __name__ == '__main__':
    unittest.main()
