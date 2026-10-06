"""Current-cycle poll acquisition: preserved bytes, ledger and gap audit (no fitting)."""
import json
from pathlib import Path
import unittest

from scripts.polling import current_cycle as cc

ROOT = Path(__file__).resolve().parents[2]


class CurrentCycleAcquisitionTests(unittest.TestCase):
    def test_ledger_checksums_and_deterministic_rebuild(self):
        ledger = cc.verify_ledger()
        self.assertEqual(len(ledger['resources']), 9)
        self.assertLessEqual(len(ledger['resources']), ledger['resourceCap'])
        blocked = [a for a in ledger['attempts'] if a['status'] == 'blocked']
        self.assertTrue(blocked)
        self.assertTrue(all(a['rawPath'] is None for a in blocked))

    def test_every_raw_file_is_ledgered_and_pinned_to_a_commit(self):
        ledger = json.loads((cc.RAW / 'acquisition-ledger.json').read_text())
        on_disk = {p.name for p in cc.RAW.iterdir()} - {'acquisition-ledger.json', 'fetch-log.tsv', 'reachability-probe.tsv'}
        self.assertEqual(on_disk, {Path(r['rawPath']).name for r in ledger['resources']})
        for r in ledger['resources']:
            self.assertRegex(r['commit'], r'^[0-9a-f]{40}$')
            self.assertIn(r['commit'], r['url'])

    def test_gap_audit_is_deterministic_and_matches_committed_file(self):
        self.assertEqual((cc.OUT / 'gap-audit.json').read_bytes(), cc.encode(cc.audit()))

    def test_gap_audit_substantive_findings(self):
        a = cc.audit()
        self.assertEqual(a['panelMissingFromLabo49'], [])
        self.assertEqual(a['stage35Panel']['cycle2026Waves'], 120)
        self.assertEqual(sorted(r['pollster'] for r in a['labo49RowsNotInStage35Panel']),
                         ['RNZ—Reid Research', 'Talbot Mills', 'Talbot Mills'])
        self.assertEqual(len(a['labo49VersusDanylmcDateConflicts']), 1)
        self.assertEqual(a['stage35Panel']['latestFieldworkEnd'], '2026-09-27')

    def test_missing_party_is_none_not_zero(self):
        key = cc.keys_labo49([{'date': '2024-05-10', 'results': {'NAT': 35, 'LAB': 32}}])[0]
        self.assertEqual(key, ('2024-05-10', 35, 32, None, None, None))

    def test_duplicates_counted_with_multiplicity(self):
        rec = {'fieldworkEndBounds': ['2026-04-16', '2026-04-16'],
               'estimates': {k: {'share': 0.2} for k in cc.PARTIES}}
        counts = cc.Counter(cc.keys_panel([rec, rec]))
        self.assertEqual(list(counts.values()), [2])

    def test_stage35_files_untouched(self):
        ledger = json.loads((ROOT / 'data/raw/polling/stage35/acquisition-ledger.json').read_text())
        self.assertEqual(len(ledger['resources']), 44)
        for r in ledger['resources']:
            self.assertEqual(cc.sha(ROOT / r['rawPath']), r['sha256'])


if __name__ == '__main__':
    unittest.main()
