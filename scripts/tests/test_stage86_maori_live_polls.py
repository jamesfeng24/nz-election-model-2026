"""Stage86 (D125): Maori seat polls are read from the Stage82 live-inputs file by the nowcast assembly.

Unit tests need no network. Synthetic rows are built in the test and are never written anywhere; they stand in for a future weekly refresh.
"""
import copy
import unittest
import unittest.mock
import numpy as np
from scripts.maori_seat_layer import live
from scripts.maori_seat_layer.common import CURRENT_POLLS, SEATS, fold, read as read_plan
from scripts.maori_seat_layer.fit import fit
from scripts.maori_seat_layer.run import parameters
from scripts.maori_seat_layer.simulate import current_polls as pinned_polls, simulate as simulate_layer
from scripts.nowcast_assembly import maori
from scripts.nowcast_assembly.common import CONFIG, AssemblyError, namespace_seed, read

COUNT = 2048


def closed(poll):
    total = sum(c['pollPercent'] for c in poll['candidates'])
    return {c['party']: c['pollPercent'] / total for c in poll['candidates']}


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.ids = maori.electorate_ids()
        cls.people = maori.roster(cls.config, cls.ids)
        cls.resolve = staticmethod(maori.resolver(cls.people))
        cls.rows = live.live_polls()

    def row(self, seat, end, shares, pollster='Whakaata Māori–Curia', poll_id=None):
        """SYNTHETIC live row for a test; never a real poll."""
        return {'id': poll_id or f'synthetic-{seat}-{end}', 'type': 'maori', 'seat': seat, 'pollster': pollster, 'sampleSize': 500,
                'fieldwork': {'start': end[:8] + '01', 'end': end}, 'electorateVotePct': shares}


class Reader(Fixture):
    def test_the_live_file_holds_the_four_maori_polls_of_the_first_refresh(self):
        self.assertEqual(sorted(live.seat_name(p['seat']) for p in self.rows), ['Hauraki-Waikato', 'Te Tai Hauāuru', 'Te Tai Tonga', 'Waiariki'])
        polls, superseded = live.current_polls(self.resolve)
        self.assertEqual(sorted(polls), ['Hauraki-Waikato', 'Te Tai Hauāuru', 'Te Tai Tonga', 'Waiariki'])
        self.assertEqual(superseded, [])

    def test_hash_mismatch_with_the_index_fails_closed(self):
        real = live.read
        def tampered(path):
            value = real(path)
            if path.endswith('/polls.json'):
                value = copy.deepcopy(value)
                value['polls'].pop()
            return value
        with unittest.mock.patch.object(live, 'read', side_effect=tampered), self.assertRaises(ValueError):
            live.live_polls()

    def test_candidates_agree_with_the_pinned_transcription_and_shares_within_rounding(self):
        # The pinned file stays as the 2026-10-07 transcription; the live shares are published ex-undecided and rounded, so the closed shares
        # differ by rounding only. This bounds the input change of the switch-over (D125).
        pinned, _, _ = pinned_polls()
        new, _ = live.current_polls(self.resolve)
        worst = 0.0
        for seat, old in pinned.items():
            self.assertEqual([c['party'] for c in old['candidates']], [c['party'] for c in new[seat]['candidates']], seat)
            for before, after in zip(old['candidates'], new[seat]['candidates']):
                self.assertTrue(fold(before['name']).endswith(fold(maori.surname(after['name']))), (before['name'], after['name']))
            a, b = closed(old), closed(new[seat])
            worst = max(worst, max(abs(a[k] - b[k]) for k in a))
        self.assertLess(worst, 0.02)   # largest observed 0.012 (Te Tai Hauāuru Māori Party)

    def test_candidates_are_ordered_by_descending_share_with_ties_by_party_code(self):
        poll = live.poll_record(self.row('Waiariki', '2026-10-20', {'TPM': 40.0, 'LAB': 20.0, 'GRN': 20.0, 'TOP': 5.0}), self.resolve)
        self.assertEqual([c['party'] for c in poll['candidates']], ['MP', 'GRN', 'LAB', 'TOP'])

    def test_others_is_not_a_candidate_and_is_not_read(self):
        poll = live.poll_record(self.row('Waiariki', '2026-10-20', {'TPM': 40.0, 'LAB': 20.0, 'OTH': 9.0}), self.resolve)
        self.assertEqual([c['party'] for c in poll['candidates']], ['MP', 'LAB'])

    def test_latest_poll_per_seat_wins_and_earlier_ones_are_reported(self):
        older = self.row('Waiariki', '2026-10-10', {'TPM': 40.0, 'LAB': 20.0}, poll_id='b-older')
        newer = self.row('Waiariki', '2026-10-24', {'TPM': 30.0, 'LAB': 30.0}, poll_id='a-newer')
        polls, superseded = live.current_polls(self.resolve, polls=[newer, older])
        self.assertEqual(polls['Waiariki']['id'], 'a-newer')
        self.assertEqual(superseded, ['b-older'])

    def test_fail_closed(self):
        for shares, seat in (({'TPM': 40.0, 'ACT': 20.0}, 'Waiariki'),           # party the Maori layer has no code for
                             ({'TPM': 40.0}, 'Waiariki'),                         # fewer than two candidates
                             ({'TPM': 40.0, 'LAB': 0.0}, 'Waiariki'),             # a listed zero cannot enter a log-share model
                             ({'TPM': 40.0, 'LAB': 20.0}, 'Auckland Central')):   # not a Maori seat
            with self.assertRaises(ValueError, msg=(seat, shares)):
                live.poll_record(self.row(seat, '2026-10-20', shares), self.resolve)


class Resolver(Fixture):
    def test_resolves_party_to_the_one_official_candidate(self):
        self.assertEqual(self.resolve('Waiariki', 'MP'), 'Rawiri WAITITI')
        self.assertEqual(self.resolve('Te Tai Tonga', 'IND'), 'Tākuta FERRIS')    # the seat's one independent
        self.assertEqual(self.resolve('Hauraki-Waikato', 'IND'), 'Neil DENBY')

    def test_no_match_or_several_matches_or_unmapped_code_is_refused(self):
        with self.assertRaises(AssemblyError):
            self.resolve('Waiariki', 'IND')           # no independent on the roster
        with self.assertRaises(AssemblyError):
            self.resolve('Hauraki-Waikato', 'GRN')    # no Green candidate
        with self.assertRaises(AssemblyError):
            self.resolve('Waiariki', 'ACT')           # unmapped code
        people = copy.deepcopy(self.people)
        people['Te Tai Tonga'].append({'id': 'second-independent', 'name': 'Someone ELSE', 'group': None})
        with self.assertRaises(AssemblyError):
            maori.resolver(people)('Te Tai Tonga', 'IND')   # two independents: the column cannot be tied to a person


class Assembly(Fixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.records = maori.simulate(cls.config, COUNT)

    def test_waiariki_is_now_polled_and_three_seats_use_the_fallback(self):
        by_seat = {seat: self.records[self.ids[seat]] for seat in SEATS}
        for seat in ('Hauraki-Waikato', 'Te Tai Hauāuru', 'Te Tai Tonga', 'Waiariki'):
            self.assertTrue(by_seat[seat]['source'].startswith('Stage66 default; poll nz-seatpoll-'), seat)
        for seat in ('Ikaroa-Rāwhiti', 'Tāmaki Makaurau', 'Te Tai Tokerau'):
            self.assertEqual(by_seat[seat]['source'], maori.FALLBACK_SOURCE)

    def test_a_new_poll_moves_only_its_own_seat(self):
        before = self.records
        extra = [dict(p) for p in self.rows] + [self.row('Te Tai Tokerau', '2026-10-30', {'LAB': 45.0, 'TPM': 25.0, 'IND': 20.0}, poll_id='synthetic-ttt')]
        with unittest.mock.patch.object(live, 'live_polls', return_value=extra):
            after = maori.simulate(self.config, COUNT)
        moved = {s for s in SEATS if after[self.ids[s]] != before[self.ids[s]]}
        self.assertEqual(moved, {'Te Tai Tokerau'})
        self.assertTrue(after[self.ids['Te Tai Tokerau']]['source'].startswith('Stage66 default; poll synthetic-ttt'))

    def test_removing_the_waiariki_poll_restores_the_fallback_and_leaves_the_other_seats(self):
        rest = [p for p in self.rows if live.seat_name(p['seat']) != 'Waiariki']
        with unittest.mock.patch.object(live, 'live_polls', return_value=rest):
            without = maori.simulate(self.config, COUNT)
        self.assertEqual(without[self.ids['Waiariki']]['source'], maori.FALLBACK_SOURCE)
        for seat in SEATS:
            if seat != 'Waiariki':
                self.assertEqual(without[self.ids[seat]], self.records[self.ids[seat]], seat)

    def test_every_officially_nominated_candidate_appears_in_every_seat(self):
        # Audit finding (James, 2026-10-10): a polled seat carried only the candidates the poll named, so Neil Denby (Hauraki-Waikato) and
        # Christine Fisher and Tania Lee Henare (Te Tai Tonga) were missing from the outputs.
        for seat in SEATS:
            record = self.records[self.ids[seat]]
            self.assertEqual(sorted(record['candidates']), sorted(p['id'] for p in self.people[seat]), seat)
            self.assertEqual([c['candidateId'] for c in record['candidateShares']], record['candidates'])
        names = lambda seat: {n for n in self.records[self.ids[seat]]['candidateNames']}
        self.assertTrue({'Neil DENBY'} <= names('Hauraki-Waikato'))
        self.assertTrue({'Christine FISHER', 'Tania Lee HENARE'} <= names('Te Tai Tonga'))

    def test_unpolled_candidates_share_the_unnamed_remainder_and_never_win(self):
        record = self.records[self.ids['Te Tai Tonga']]
        named = [i for i, n in enumerate(record['candidateNames']) if n not in ('Christine FISHER', 'Tania Lee HENARE')]
        extra = [i for i in range(len(record['candidates'])) if i not in named]
        mean = [c['mean'] for c in record['candidateShares']]
        self.assertAlmostEqual(sum(mean), 1.0, places=9)                     # shares close over the whole slate
        self.assertAlmostEqual(mean[extra[0]], mean[extra[1]], places=12)    # equal split of the remainder (placeholder allocation)
        self.assertTrue(all(w in named for w in record['winners']))          # Stage66: only the poll's candidates can win
        # winners are exactly those of the Stage66 layer on the same poll (the extra columns change nothing)
        polls, _ = live.current_polls(self.resolve)
        sim = simulate_layer(polls, parameters(fit()[0]['fit']), COUNT, namespace_seed(self.config['simulation']['seedNamespace'], 'maori'))
        self.assertEqual([record['candidates'][w] for w in record['winners']],
                         [maori.match('Te Tai Tonga', polls['Te Tai Tonga']['candidates'][w]['name'], polls['Te Tai Tonga']['candidates'][w]['party'], self.people['Te Tai Tonga'])['id']
                          for w in sim['seats']['Te Tai Tonga']['winner']])

    def test_the_pinned_transcription_is_not_changed(self):
        self.assertEqual(sorted(p['seat'] for p in read_plan(CURRENT_POLLS)['polls']), ['Hauraki-Waikato', 'Te Tai Hauāuru', 'Te Tai Tonga'])


if __name__ == '__main__':
    unittest.main()
