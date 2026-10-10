"""Stage88: James's 2026-10-10 audit decisions. D127 Maori C-P range, D128 pinned electorate-poll run (tested with Stage79 and Stage86),
D129 overhang for a party-list party simulated inside Other (the seat layer itself is tested in TypeScript)."""
import copy
import unittest
import unittest.mock
import numpy as np
from scripts.maori_seat_calibration.common import PREFIX as STAGE71, read as read71
from scripts.maori_seat_calibration.inflation import arm_p
from scripts.maori_seat_layer.common import SEATS
from scripts.nowcast_assembly import assemble as A, maori
from scripts.nowcast_assembly.common import CONFIG, AssemblyError, read

COUNT = 2048


class Range(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.ids = maori.electorate_ids()
        cls.records = maori.simulate(cls.config, COUNT)

    def test_arm_p_reproduces_the_stored_stage71_parameters(self):
        est, lam = arm_p()
        stored = read71(STAGE71 + '/forecast-2026.json')['fitAllFourElections']
        self.assertEqual((est['sigma2'], est['tau2'], est['lambdaHat']), (stored['sigma2'], stored['tau2'], stored['lambdaHat']))
        for q in ('p05', 'p50', 'p95'):
            self.assertAlmostEqual(float(np.quantile(lam, float(q[1:]) / 100)), stored['lambdaInterval90'][q], places=12)

    def test_only_polled_seats_carry_the_range_and_its_winners_are_named_candidates(self):
        for seat in SEATS:
            record = self.records[self.ids[seat]]
            if record['source'] == maori.FALLBACK_SOURCE:
                self.assertNotIn('inflationWinners', record, seat)  # Stage78 froze no inflation of the fallback
                continue
            winners = record['inflationWinners']
            self.assertEqual(len(winners), COUNT)
            self.assertLess(max(winners), len(record['candidates']))

    def test_inflation_widens_every_polled_seat_and_leaves_the_control_untouched(self):
        for seat in SEATS:
            record = self.records[self.ids[seat]]
            if 'inflationWinners' not in record:
                continue
            k = len(record['candidates'])
            c = np.bincount(record['winners'], minlength=k) / COUNT
            p = np.bincount(record['inflationWinners'], minlength=k) / COUNT
            leader = int(c.argmax())
            self.assertLess(p[leader], c[leader], seat)  # Stage71: P lowers the overconfident leader's chance
        plain = copy.deepcopy(self.records)
        for record in plain.values():
            record.pop('inflationWinners', None)
        with unittest.mock.patch.object(maori, 'inflation_winners', return_value={}):
            self.assertEqual(maori.simulate(self.config, COUNT), plain)

    def test_presentation_other_than_the_range_fails_closed(self):
        bad = copy.deepcopy(self.config)
        bad['maori']['presentation'] = 'single'
        with self.assertRaises(AssemblyError):
            maori.simulate(bad, 8)


class Ballot(unittest.TestCase):
    def test_the_ballot_holds_every_party_list_and_te_tai_tokerau_party_is_bucketed(self):
        config = read(CONFIG)
        groups = ['nationalparty', 'labourparty', 'greenparty', 'actnewzealand', 'newzealandfirstparty', 'tepatimaori', 'opportunity', 'other']
        ballot = A.ballot_parties(config, groups)
        self.assertEqual(len(ballot), 17)
        self.assertIn('tetaitokerauparty', ballot)
        self.assertNotIn('other', ballot)
        with self.assertRaises(AssemblyError):
            A.ballot_parties(config, groups[:-1] + ['not-a-party', 'other'])


if __name__ == '__main__':
    unittest.main()
