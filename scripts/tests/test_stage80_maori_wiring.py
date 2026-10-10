"""Stage80: the chosen Stage78 fallback (arm F) is wired into the assembly, with the official roster ids on all seven Maori seats.

Unit tests need no network. The fallback draws are Stage78's own code with a different seed; with the Stage78 seed and draw count they
reproduce the stored arm F exactly, so the wiring adds no new statistical model.
"""
import copy
import unittest
import numpy as np
from scripts.manual_adjustment.schema import seat_frame
from scripts.maori_seat_fallback import draws
from scripts.maori_seat_fallback.common import SEATS, read as read_json, DESIGN
from scripts.maori_seat_fallback.forecast import UNPOLLED as STAGE78_UNPOLLED
from scripts.maori_seat_layer import live
from scripts.nowcast_assembly import maori
from scripts.nowcast_assembly.common import CONFIG, AssemblyError, read

COUNT = 4096
# Stage86 (D125): the polled seats are those with a Maori poll in the newest Stage82 live-inputs run, not the four fixed in the Stage78 artifacts.
LIVE_POLLED = {live.seat_name(p['seat']) for p in live.live_polls()}
UNPOLLED = tuple(seat for seat in SEATS if seat not in LIVE_POLLED)
STORED = 'data/processed/maori-seat-fallback/forecast-2026.json'


def config(**edits):
    c = copy.deepcopy(read(CONFIG))
    for path, value in edits.items():
        section, key = path.split('.')
        c[section][key] = value
    return c


def win_probabilities(record):
    return np.bincount(record['winners'], minlength=len(record['candidates'])) / len(record['winners'])


class Draws(unittest.TestCase):
    def test_reproduces_the_stored_stage78_arm_f_exactly_with_the_stage78_seed(self):
        stored = read(STORED)
        n = stored['draws']
        for seat, (inp, share) in draws.f_shares(STAGE78_UNPOLLED, n).items():
            p = np.bincount(np.argmax(share, axis=1), minlength=len(inp['names'])) / n
            self.assertTrue(np.allclose([c['winProbability'] for c in stored['arms']['F']['seats'][seat]['candidates']], p, atol=0, rtol=0))

    def test_a_seat_does_not_depend_on_which_others_are_requested(self):
        both = draws.f_shares(('Waiariki', 'Te Tai Tokerau'), 2000, seed=7)
        alone = draws.f_shares(('Te Tai Tokerau',), 2000, seed=7)
        self.assertTrue(np.array_equal(both['Te Tai Tokerau'][1], alone['Te Tai Tokerau'][1]))
        self.assertFalse(np.array_equal(both['Waiariki'][1][:, :2], both['Te Tai Tokerau'][1][:, :2]))

    def test_shares_close_and_seeds_differ(self):
        a = draws.f_shares(('Waiariki',), 1000, seed=1)['Waiariki'][1]
        b = draws.f_shares(('Waiariki',), 1000, seed=2)['Waiariki'][1]
        self.assertTrue(np.allclose(a.sum(axis=1), 1, atol=1e-12) and (a >= 0).all())
        self.assertFalse(np.array_equal(a, b))
        with self.assertRaises(ValueError):
            draws.f_shares(('Auckland Central',), 10)


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = config()
        cls.records = maori.simulate(cls.config, COUNT)
        cls.ids = maori.electorate_ids()
        cls.roster = maori.roster(cls.config, cls.ids)

    def test_config_registers_the_chosen_fallback(self):
        self.assertEqual(self.config['maori']['unpolledFallbackModel'], maori.FALLBACK_MODEL)
        self.assertEqual(self.config['pending'], {})

    def test_all_seven_seats_are_simulated_with_one_winner_per_draw(self):
        self.assertEqual(sorted(self.records), sorted(seat_frame()['maori']))
        for record in self.records.values():
            self.assertEqual(record['status'], 'simulated')
            self.assertEqual(record['class'], 'maori-layer')
            self.assertEqual(len(record['winners']), COUNT)
            self.assertTrue(all(0 <= w < len(record['candidates']) for w in record['winners']))

    def test_unpolled_seats_carry_the_fallback_label_and_polled_seats_their_poll(self):
        for seat in SEATS:
            record = self.records[self.ids[seat]]
            if seat in UNPOLLED:
                self.assertEqual(record['source'], maori.FALLBACK_SOURCE)
                self.assertNotIn('pollFieldworkEnd', record)
            else:
                self.assertTrue(record['source'].startswith('Stage66 default; poll '))
                self.assertIn('pollFieldworkEnd', record)

    def test_candidates_are_official_roster_entries_with_roster_ballot_groups(self):
        for seat in SEATS:
            record = self.records[self.ids[seat]]
            by_id = {p['id']: p for p in self.roster[seat]}
            self.assertEqual(len(set(record['candidates'])), len(record['candidates']))
            for cid, name, party in zip(record['candidates'], record['candidateNames'], record['candidateParty']):
                self.assertEqual((name, party), (by_id[cid]['name'], by_id[cid]['group']))
            if seat in UNPOLLED:   # the fallback models the whole official slate
                self.assertEqual(sorted(record['candidates']), sorted(by_id))
        self.assertTrue(all('poll-candidate' not in c for r in self.records.values() for c in r['candidates']))

    def test_win_probabilities_match_the_stored_stage78_readout_within_monte_carlo_error(self):
        stored = read(STORED)['arms']['F']['seats']
        for seat in UNPOLLED:
            p = win_probabilities(self.records[self.ids[seat]])
            for candidate, q in zip(stored[seat]['candidates'], p):
                self.assertAlmostEqual(candidate['winProbability'], q, delta=5 * np.sqrt(0.25 / COUNT) + 0.003)

    def test_shares_are_summarised_for_every_candidate(self):
        for seat in SEATS:
            record = self.records[self.ids[seat]]
            total = sum(c['mean'] for c in record['candidateShares'])
            self.assertEqual([c['candidateId'] for c in record['candidateShares']], record['candidates'])
            if seat in UNPOLLED:   # the fallback closes over the whole official slate
                self.assertAlmostEqual(total, 1.0, places=9)
            else:                  # the Stage66 layer leaves the unnamed remainder out of the named candidates
                self.assertTrue(0.9 < total < 1.0)

    def test_deterministic(self):
        again = maori.simulate(self.config, COUNT)
        self.assertEqual(again, self.records)


class FailClosed(unittest.TestCase):
    def test_pending_model_keeps_unpolled_seats_unavailable(self):
        c = config(**{'maori.unpolledFallbackModel': None})
        records = maori.simulate(c, 64)
        unavailable = [r for r in records.values() if r['status'] == 'unavailable']
        self.assertEqual(len(unavailable), len(UNPOLLED))
        self.assertTrue(all('no fallback model is registered' in r['reason'] for r in unavailable))

    def test_unregistered_model_and_missing_decision_are_refused(self):
        with self.assertRaises(AssemblyError):
            maori.simulate(config(**{'maori.unpolledFallbackModel': 'stage78-fc'}), 64)
        with self.assertRaises(AssemblyError):
            maori.simulate(config(**{'maori.unpolledSeats': 'withhold'}), 64)

    def test_pending_roster_is_refused(self):
        c = config()
        c['roster']['snapshotId'] = None
        with self.assertRaises(AssemblyError):
            maori.simulate(c, 64)

    def test_poll_candidates_that_match_no_or_many_roster_entries_are_refused(self):
        c = config()
        people = maori.roster(c, maori.electorate_ids())['Waiariki']
        with self.assertRaises(AssemblyError):
            maori.match('Waiariki', 'Rawiri Nobody', 'MP', people)
        with self.assertRaises(AssemblyError):
            maori.match('Waiariki', 'Rawiri Waititi', 'LAB', people)          # right surname, wrong party
        with self.assertRaises(AssemblyError):
            maori.match('Waiariki', 'Rawiri Waititi', 'XYZ', people)          # unmapped party code
        self.assertEqual(maori.match('Waiariki', 'Rawiri Waititi', 'MP', people)['group'], 'tepatimaori')
        waititi = next(p for p in people if p['name'].endswith('WAITITI'))
        doubled = people + [dict(waititi, id='duplicate')]
        with self.assertRaises(AssemblyError):
            maori.match('Waiariki', 'Rawiri Waititi', 'MP', doubled)

    def test_surnames_are_the_upper_case_run(self):
        self.assertEqual(maori.surname('Lisa TE MORENGA'), 'TE MORENGA')
        self.assertEqual(maori.surname('Hana-Rawhiti MAIPI-CLARKE'), 'MAIPI-CLARKE')
        with self.assertRaises(AssemblyError):
            maori.surname('no surname here')

    def test_every_stage78_code_has_a_roster_key_and_unknown_codes_are_absent(self):
        codes = set(read_json('data/source-plans/maori-seat-fallback/inputs-2026.json')['labelCodes'].values())
        self.assertTrue(codes <= set(maori.PARTIES))
        self.assertNotIn('OTH', maori.PARTIES)

    def test_the_fallback_design_contract_is_unchanged(self):
        self.assertEqual(read_json(DESIGN)['seed'], 2026078)


if __name__ == '__main__':
    unittest.main()
