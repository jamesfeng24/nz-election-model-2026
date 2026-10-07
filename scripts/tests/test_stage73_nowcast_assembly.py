"""Stage73: the live nowcast draw bank is fail-closed, enters national uncertainty once and applies D107 only to the
candidate N/L balance seat scale. End-to-end runs use SYNTHETIC TEST FIXTURES (slates, classification, Maori winners)
over the real 2026 ids; a bank built from them is marked synthetic and can never pass the publication gate."""
import copy
import unittest
import numpy as np
from scripts.manual_adjustment.schema import seat_frame
from scripts.nowcast_assembly import assemble as A, general, maori, national, streams, summaries
from scripts.nowcast_assembly.common import CONFIG, OTHER, read, AssemblyError

GENERAL = sorted(seat_frame()['general'])
MAORI = sorted(seat_frame()['maori'])
COUNT = 8


def config():
    return copy.deepcopy(read(CONFIG))


def synthetic_slates():
    """SYNTHETIC TEST FIXTURE: invented three-party slates plus an independent; never a real roster."""
    parties = ('nationalparty', 'labourparty', 'greenparty', None)
    return {seat: [{'id': f'synthetic-{seat}-{i}', 'group': g, 'name': f'Synthetic candidate {i}', 'S': 0.0, 'R': 0.0}
                   for i, g in enumerate(parties)]
            for seat in GENERAL}


def synthetic_classification():
    """SYNTHETIC TEST FIXTURE: an invented classification, not a judgement."""
    return {seat: 'exceptional' if i % 8 == 0 else 'ordinary' for i, seat in enumerate(GENERAL)}


def synthetic_maori():
    """SYNTHETIC TEST FIXTURE: invented Maori winners for all seven seats."""
    def record(seat):
        ids = [f'synthetic-{seat}-a', f'synthetic-{seat}-b']
        parties = ['labourparty', 'tepatimaori']
        win = [d % 2 for d in range(COUNT)]
        return {'status': 'simulated', 'class': 'maori-layer', 'source': 'synthetic-test', 'candidates': ids,
                'candidateNames': ['Synthetic A', 'Synthetic B'], 'candidateParty': parties,
                'candidateShares': summaries.share_summaries(ids, np.array([[0.6, 0.4] if w == 0 else [0.4, 0.6] for w in win])),
                'winners': list(win)}
    return {seat: record(seat) for seat in MAORI}


class National(unittest.TestCase):
    def test_reads_last_data_support_only_and_fails_closed(self):
        draws, ids, groups = national.load(config(), COUNT)
        self.assertEqual(draws.shape, (COUNT, 8))
        self.assertEqual(len(set(ids)), COUNT)
        self.assertIn(OTHER, groups)
        again = national.load(config(), COUNT)
        self.assertTrue(np.array_equal(draws, again[0]) and ids == again[1])
        for edit in (lambda c: c['national'].update(stateKey='electionDay'),
                     lambda c: c['national'].update(forbiddenStateKeys=[]),
                     lambda c: c['national'].update(dataCutoff='2026-10-05'),
                     lambda c: c['national']['categoryMap'].pop('Other')):
            c = config(); edit(c)
            with self.assertRaises(AssemblyError):
                national.load(c, COUNT)
        with self.assertRaises(AssemblyError):
            national.load(config(), 6)

    def test_other_is_split_by_each_seats_own_2023_mix(self):
        c = config()
        draws, _, groups = national.load(c, COUNT)
        keys, national2023, base = general.baseline(c)
        continuing = general.relationships(c)
        fine = general.fine_national(draws, groups, keys, national2023, continuing)
        self.assertTrue(np.allclose(fine.sum(axis=1), 1, atol=1e-12))
        core = np.array([continuing.get(k) in groups for k in keys])
        self.assertTrue(np.allclose(fine[:, ~core].sum(axis=1), draws[:, groups.index(OTHER)]))
        seat = GENERAL[0]
        row = general.party_row(seat, keys, base[seat], national2023, continuing)
        local = fine[:, ~core] * np.asarray(row['affinities'])[~core]
        mix = local / local.sum(axis=1, keepdims=True)
        own = base[seat][~core] / base[seat][~core].sum()
        self.assertTrue(np.allclose(mix, own[None, :], atol=1e-12))


class SeatLayers(unittest.TestCase):
    def test_multiplier_changes_only_the_candidate_balance(self):
        c = config()
        draws, _, groups = national.load(c, COUNT)
        keys, national2023, base = general.baseline(c)
        continuing = general.relationships(c)
        fine = general.fine_national(draws, groups, keys, national2023, continuing)
        parameters, _ = general.fold_parameters(c)
        scales = read(c['uncertainty']['scales'])['layers']
        seat = GENERAL[3]
        party = general.party_row(seat, keys, base[seat], national2023, continuing)
        candidate = general.candidate_row(seat, synthetic_slates()[seat], party, parameters)
        with streams.substituted([party, candidate], COUNT, 'synthetic-test'):
            _, wide = general.simulate(party, candidate, fine, scales['local_party']['scales'], scales['candidate']['scales'], 1.0)
            _, narrow = general.simulate(party, candidate, fine, scales['local_party']['scales'], scales['candidate']['scales'], 0.6)
        n, l = candidate['groups'].index('national'), candidate['groups'].index('labour')
        rest = [i for i in range(len(candidate['ids'])) if i not in (n, l)]
        self.assertTrue(np.allclose(wide[:, rest], narrow[:, rest], atol=1e-14))
        self.assertTrue(np.allclose(wide[:, n] + wide[:, l], narrow[:, n] + narrow[:, l], atol=1e-14))
        self.assertFalse(np.allclose(wide[:, n], narrow[:, n]))

    def test_slate_and_maori_codes_fail_closed(self):
        c = config()
        keys, national2023, base = general.baseline(c)
        party = general.party_row(GENERAL[0], keys, base[GENERAL[0]], national2023, general.relationships(c))
        parameters, _ = general.fold_parameters(c)
        slate = synthetic_slates()[GENERAL[0]]
        for bad in ([slate[0]], slate + [dict(slate[0])], slate + [dict(slate[0], id='synthetic-x')]):
            with self.assertRaises((AssemblyError, ValueError)):
                general.candidate_row(GENERAL[0], bad, party, parameters)
        self.assertNotIn('OTH', maori.PARTIES)


class Bank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = config()
        cls.bank = A.assemble(cls.config, COUNT, slates=synthetic_slates(), classification=synthetic_classification(),
                              maori_records=synthetic_maori(), workers=2)

    def test_complete_synthetic_bank_has_every_winner_on_every_row(self):
        bank = self.bank
        self.assertEqual(bank['provenance'], 'synthetic-fixture')
        self.assertEqual([s['electorateId'] for s in bank['seats']], GENERAL + MAORI)
        for seat in bank['seats']:
            self.assertEqual(seat['status'], 'simulated')
            self.assertEqual(len(seat['winners']), COUNT)
        classes = synthetic_classification()
        for seat in bank['seats'][:64]:
            self.assertEqual(seat['multiplier'], {'ordinary': 0.60, 'exceptional': 1.00}[classes[seat['electorateId']]])

    def test_bank_carries_share_intervals_and_the_export_directory(self):
        seat = self.bank['seats'][0]
        self.assertEqual([c['candidateId'] for c in seat['candidateShares']], seat['candidates'])
        for c in seat['candidateShares']:
            levels = c['intervals']
            self.assertEqual([v['level'] for v in levels], [0.5, 0.8, 0.9])
            self.assertTrue(all(levels[i]['lower'] <= levels[i - 1]['lower'] and levels[i]['upper'] >= levels[i - 1]['upper'] for i in (1, 2)))
        directory = self.bank['directory']
        self.assertEqual(len(directory['electorates']), 71)
        self.assertEqual([p['partyId'] for p in directory['parties']], self.bank['partyVote']['groups'])
        independents = [c for c in directory['candidates'] if c['partyLabel'] is None]
        self.assertTrue(independents and all(c['partyId'] is None for c in independents))

    def test_gate_refuses_synthetic_and_incomplete_banks(self):
        passed, checks = A.gate(self.bank, self.config)
        failed = {c['check'] for c in checks if not c['passed']}
        self.assertFalse(passed)
        self.assertEqual(failed, {'configComplete', 'provenanceLive'})
        broken = copy.deepcopy(self.bank)
        broken['seats'][5] = {'electorateId': broken['seats'][5]['electorateId'], 'scope': 'general', 'status': 'unavailable'}
        failed = {c['check'] for c in A.gate(broken, self.config)[1] if not c['passed']}
        self.assertIn('everySeatSimulatedOrExplicitlyUnavailable', failed)
        broken['seats'].pop()
        self.assertIn('universe71', {c['check'] for c in A.gate(broken, self.config)[1] if not c['passed']})

    def test_live_inputs_are_blocked_not_defaulted(self):
        report = read('data/processed/nowcast-assembly/development-gate.json')
        self.assertFalse(report['publishable'])
        self.assertEqual(report['provenance'], 'live')
        self.assertEqual(set(report['seatStatus']), set(GENERAL + MAORI))
        reasons = {b['reason']: b['seats'] for b in report['blockers']}
        self.assertEqual(sum(reasons.values()) + sum(v == 'simulated' for v in report['seatStatus'].values()), 71)
        self.assertTrue(any('Stage50' in r for r in reasons))


if __name__ == '__main__':
    unittest.main()
