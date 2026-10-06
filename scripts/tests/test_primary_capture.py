"""Stage52 primary-source capture: preserved bytes, ledger, verified facts and registry (no fitting)."""
import json
from pathlib import Path
import unittest

from scripts.polling import current_cycle as cc
from scripts.polling import primary_capture as pc
from scripts.validate.source_files import verify_source_files

ROOT = Path(__file__).resolve().parents[2]


class PrimaryCaptureTests(unittest.TestCase):
    def test_ledger_checksums_and_deterministic_rebuild(self):
        ledger = pc.verify_ledger()
        self.assertEqual(len(ledger['resources']), len(pc.FILES) + len(pc.USER_SUPPLIED))
        for r in ledger['resources']:
            self.assertEqual(r['httpStatus'], None if r.get('supplied') else 200)
            self.assertRegex(r['retrievedAt'], r'^2026-10-06T')
        supplied = [r for r in ledger['resources'] if r.get('supplied')]
        self.assertEqual(sorted(Path(r['rawPath']).name for r in supplied), sorted(pc.USER_SUPPLIED))
        self.assertTrue(all(r['headersPath'] is None and r['textSidecarSha256'] for r in supplied))

    def test_every_file_on_disk_is_ledgered_and_failures_leave_no_bytes(self):
        ledger = json.loads((pc.RAW / 'acquisition-ledger.json').read_text())
        on_disk = {p.name for p in pc.RAW.iterdir()}
        expected = {Path(r['rawPath']).name for r in ledger['resources']}
        expected |= {Path(r['headersPath']).name for r in ledger['resources'] if r['headersPath']} | {'acquisition-ledger.json', 'fetch-log.tsv'}
        self.assertEqual(on_disk, expected)
        failed = [a for a in ledger['attempts'] if a['status'] == 'failed']
        self.assertTrue(failed)
        self.assertTrue(all(not (pc.RAW / a['name']).exists() or a['name'] in pc.FILES for a in failed))  # retried names keep the later success
        self.assertTrue(all(not s['present'] for s in ledger['discardedShells']))
        self.assertTrue({a['httpStatus'] for a in failed} >= {403, 404, 429})

    def test_audit_is_deterministic_and_every_fact_is_in_the_bytes(self):
        a = pc.audit()
        self.assertEqual((pc.OUT / 'primary-capture-audit.json').read_bytes(), pc.encode(a))
        self.assertEqual(len(a['verified']), len(pc.CHECKS))
        self.assertTrue(all(all(pc.norm(n) in pc.text_of(pc.RAW / v['file']) for n in v['evidencePhrases']) for v in a['verified']))

    def test_taxpayers_union_polls_match_wikipedia_table_and_are_user_supplied(self):
        facts = {v['id']: v['facts'] for v in pc.audit()['verified']}
        rows = pc.wikipedia_rows()
        labels = {'06': '4–8 Jun 2026', '07': '1–5 Jul 2026', '08': '1–4 Aug 2026', '09': '1–3 Sep 2026'}
        for mm, label in labels.items():
            f = facts['tu-curia-2026-' + mm]
            self.assertEqual(f['n'], 1000)
            row = next(r for r in rows if r.startswith(label + " Taxpayers' Union–Curia 1,000 ") and 'Libs' not in r)
            nums = [float(x) for x in row.split('1,000 ')[1].split()[:2]]
            self.assertEqual(nums, [f['shares']['NAT'], f['shares']['LAB']])
        self.assertFalse(any('Union-Curia' in u['item'] for u in pc.audit()['unresolved']))

    def test_unrecovered_evidence_is_not_filled_in(self):
        facts = {v['id']: v['facts'] for v in pc.audit()['verified']}
        for key in ('talbot-2026-06', 'talbot-2026-07', 'talbot-2026-08', 'talbot-2024-11'):
            self.assertIsNone(facts[key]['n'])
        self.assertEqual(facts['rnz-reid-2026-10-06']['fieldwork'], '2026-09-24 to 2026-10-01')
        self.assertEqual(facts['rnz-reid-2026-10-06']['n'], 1000)
        self.assertTrue(any('May 2024' in u['item'] for u in pc.audit()['unresolved']))

    def test_maori_seat_polls_are_unmodelled_and_coverage_not_overclaimed(self):
        a = pc.audit()
        seats = {v['facts']['seat'] for v in a['verified'] if 'seat' in v['facts']}
        self.assertEqual(seats, set(pc.MAORI_COVERAGE['publishedSeatPolls']))
        self.assertEqual(len(pc.MAORI_COVERAGE['publishedSeatPolls']) + len(pc.MAORI_COVERAGE['seatsWithoutPublishedPoll']), 7)
        self.assertFalse(a['maoriCoverage']['allSevenPolledConfirmed'])

    def test_dated_registry_is_valid_and_central_registries_untouched(self):
        registry = json.loads((pc.OUT / 'source-registry-primary.json').read_text())
        verify_source_files(ROOT, registry)
        self.assertEqual((pc.OUT / 'source-registry-primary.json').read_bytes(), pc.encode(pc.build_registry()))
        central = json.loads((ROOT / 'data/sources.json').read_text())['sources']
        self.assertEqual(len(central), 926)
        earlier = json.loads((cc.OUT / 'source-registry.json').read_text())['sources']
        ids = {s['id'] for s in registry['sources']}
        self.assertFalse(ids & {s['id'] for s in central})
        self.assertFalse(ids & {s['id'] for s in earlier})

    def test_earlier_stage52_snapshots_and_stage35_unchanged(self):
        cc.verify_ledger()
        ledger = json.loads((ROOT / 'data/raw/polling/stage35/acquisition-ledger.json').read_text())
        for r in ledger['resources']:
            self.assertEqual(pc.sha(ROOT / r['rawPath']), r['sha256'])

    def test_live_fit_window_is_an_input_not_a_filter(self):
        self.assertIn('no data dropped', pc.LIVE_FIT_INPUT['status'])


if __name__ == '__main__':
    unittest.main()
