"""Stage85 per-seat evidence: derived display data that must not change any simulated number."""
import copy
import math
import unittest
from scripts.nowcast_assembly import assemble as A, evidence
from scripts.nowcast_assembly.common import read, CONFIG
from scripts.maori_seat_layer import live as maori_live
from scripts.seat_polls import live

FIXTURE = 'data/fixtures/synthetic/nowcast-draw-bank.json'
AS_OF = '2026-10-07'


def seat_rows(name):
    rows = copy.deepcopy(live.live_rows())
    return [r for r in rows if r['electorate'] != name], [r for r in rows if r['electorate'] == name]


class Combine(unittest.TestCase):
    def test_inputs_are_the_inputs_half_of_combine(self):
        out, detail = live.combine(AS_OF)
        self.assertEqual(out, live.inputs(AS_OF))
        self.assertTrue(set(out) <= set(detail))

    def test_used_polls_split_the_combined_poll_and_the_shares_sum_to_one(self):
        rest, mt = seat_rows('Mt Albert')
        first = dict(mt[0], id='a', pollster='Curia', fieldworkStart='2026-09-30', fieldworkEnd='2026-10-05', sampleSize=400,
                     candidateVotePct={'NAT': 40, 'LAB': 30}, sponsorGroup='all other groups')
        second = dict(first, id='b', pollster='Other Pollster', sampleSize=1600, candidateVotePct={'NAT': 30, 'LAB': 40})
        out, detail = live.combine(AS_OF, rows=rest + [first, second])
        seat = live.seat_ids()['mtalbert']
        used = {p['pollId']: p for p in detail[seat] if p['status'] == 'used'}
        self.assertAlmostEqual(sum(p['share'] for p in used.values()), 1)
        value = sum(p['share'] * math.log(p['candidateVotePct']['NAT'] / p['candidateVotePct']['LAB']) for p in used.values())
        self.assertAlmostEqual(value, out[seat]['value'])  # the shares reproduce the combined poll exactly
        self.assertGreater(used['b']['share'], used['a']['share'])  # the larger sample counts for more

    def test_same_source_polls_inside_the_gap_split_their_source_share(self):
        rest, wk = seat_rows('Waitaki')
        a = dict(wk[0], id='a', fieldworkStart='2026-09-20', fieldworkEnd='2026-09-25', candidateVotePct={'NAT': 41, 'LAB': 28})
        b = dict(a, id='b', fieldworkStart='2026-09-30', fieldworkEnd='2026-10-05', candidateVotePct={'NAT': 38, 'LAB': 30})
        out, detail = live.combine(AS_OF, rows=rest + [a, b])
        shares = {p['pollId']: p['share'] for p in detail[live.seat_ids()['waitaki']]}
        self.assertAlmostEqual(shares['a'] + shares['b'], 1)
        self.assertGreater(shares['a'], shares['b'])  # the later poll counts at 1.5 times the variance
        self.assertEqual(out[live.seat_ids()['waitaki']]['pollIds'], ['a', 'b'])

    def test_unused_polls_are_listed_with_their_reason_and_never_a_share(self):
        rest, wk = seat_rows('Waitaki')
        newer = dict(wk[0], id='newer', fieldworkStart='2026-10-01', fieldworkEnd='2026-10-05', candidateVotePct={'NAT': 41, 'LAB': 28})
        older = dict(newer, id='older', fieldworkStart='2026-07-01', fieldworkEnd='2026-07-05')
        green = dict(newer, id='green', pollster='Green Pollster', candidateVotePct={'NAT': 20, 'LAB': 25, 'GRN': 40})
        late = dict(newer, id='late', pollster='Late Pollster', fieldworkStart='2026-10-09', fieldworkEnd='2026-10-12')
        _, detail = live.combine(AS_OF, rows=rest + [older, newer, green, late])
        by_id = {p['pollId']: p for p in detail[live.seat_ids()['waitaki']]}
        self.assertEqual(by_id['newer']['status'], 'used')
        self.assertAlmostEqual(by_id['newer']['share'], 1)
        for key, text in (('older', 'superseded'), ('green', 'are not the top two'), ('late', 'after the data cutoff')):
            self.assertEqual(by_id[key]['status'], 'not-used', key)
            self.assertIn(text, by_id[key]['reason'])
            self.assertIsNone(by_id[key]['share'])

    def test_the_default_live_poll_inputs_are_unchanged(self):
        self.assertEqual(live.inputs(AS_OF), live.inputs(AS_OF, rows=live.live_rows()))


class Bank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = read(FIXTURE)

    def test_one_record_per_simulated_seat_with_the_seats_class(self):
        seats = {s['electorateId']: s for s in self.bank['seats'] if s['status'] == 'simulated'}
        self.assertEqual(sorted(e['electorateId'] for e in self.bank['seatEvidence']), sorted(seats))
        for e in self.bank['seatEvidence']:
            seat = seats[e['electorateId']]
            self.assertEqual(e['uncertaintyClass'], seat['class'])
            if seat['scope'] == 'general':
                self.assertEqual(e['multipliers'], {'balance': seat['multiplier'], 'within': seat['withinMultiplier'], 'mass': seat['massMultiplier']})
                self.assertAlmostEqual(sum(p['share'] for p in e['baseline']['partyVote']), 1)
                self.assertEqual([p['partyId'] for p in e['baseline']['partyVote']], self.bank['partyVote']['groups'])
            else:
                self.assertIsNone(e['multipliers'])
                self.assertIsNone(e['baseline'])
                self.assertEqual(e['polls'], [])  # the synthetic Maori records have no poll

    def test_the_poll_update_is_the_banks_seat_poll_and_the_weights_decompose_it_exactly(self):
        seats = {s['electorateId']: s for s in self.bank['seats']}
        polled = 0
        for e in self.bank['seatEvidence']:
            update, record = e['pollUpdate'], seats[e['electorateId']].get('seatPoll')
            self.assertEqual(update is None, record is None)
            if update is None:
                self.assertTrue(all(p['status'] == 'not-used' and p['weight'] is None for p in e['polls']))
                continue
            polled += 1
            used = [p for p in e['polls'] if p['status'] == 'used']
            self.assertEqual({p['pollId'] for p in used}, set(record['pollIds']))
            self.assertAlmostEqual(update['effectiveWeight'], record['rho'] * record['weight'])
            self.assertAlmostEqual(update['effectiveWeight'] + update['modelWeight'], 1)
            self.assertAlmostEqual(sum(p['weight'] for p in used), update['effectiveWeight'])
            self.assertAlmostEqual(update['updatedBalance'], update['modelBalance'] + record['shift'])
            pct = lambda p, party: next(c['pct'] for c in p['candidateVotePct'] if c['party'] == party)
            if read(CONFIG)['seatPolls']['rule'] == 'balance':
                moved = sum(p['weight'] * (math.log(pct(p, 'NAT') / pct(p, 'LAB')) - update['modelBalance']) for p in used)
                self.assertAlmostEqual(update['updatedBalance'], update['modelBalance'] + moved)  # linear in the combined poll
            # all-candidates (D133): the poll moves every candidate, so the National/Labour balance also moves through the others and
            # is no longer a weighted mean of the polls' own log(NAT/LAB); the weights are the clipped realised share of the gap
        self.assertGreater(polled, 0)

    def test_the_bank_digest_ignores_the_evidence_so_existing_digests_stand(self):
        without = {k: v for k, v in self.bank.items() if k != 'seatEvidence'}
        self.assertEqual(A.bank_digest(self.bank), A.bank_digest(without))
        changed = copy.deepcopy(self.bank)
        changed['seatEvidence'][0]['uncertaintyClass'] = 'changed'
        self.assertEqual(A.bank_digest(changed), A.bank_digest(self.bank))


class Maori(unittest.TestCase):
    def test_a_polled_seat_lists_its_polls_and_a_mismatch_fails_closed(self):
        rows = evidence.maori_polls('Te Tai Tonga', {'pollFieldworkEnd': '2026-09-24'})
        self.assertEqual([(r['pollId'], r['status'], r['weight']) for r in rows], [('nz-seatpoll-12c8e1ed977e9782d67d', 'used', None)])
        self.assertEqual({c['party'] for c in rows[0]['candidateVotePct']}, {'LAB', 'TPM', 'GRN', 'IND'})
        self.assertEqual(evidence.maori_polls('Te Tai Tonga', {}), [])  # a seat on the fallback has no poll
        with self.assertRaises(Exception):
            evidence.maori_polls('Te Tai Tonga', {'pollFieldworkEnd': '2026-01-01'})

    def test_earlier_polls_of_a_seat_are_superseded_by_the_latest(self):
        live_rows = [p for p in maori_live.live_polls() if p['seat'] == 'Waiariki']
        older = dict(live_rows[0], id='older', fieldwork={'start': '2026-08-01', 'end': '2026-08-07', 'raw': ''})
        rows = evidence.maori_polls('Waiariki', {'pollFieldworkEnd': '2026-10-01'}, polls=live_rows + [older])
        self.assertEqual([(r['pollId'], r['status']) for r in rows], [('older', 'not-used'), (live_rows[0]['id'], 'used')])
        self.assertIn('superseded', rows[0]['reason'])

    def test_every_live_maori_poll_is_listed_for_a_polled_seat_in_the_assembly(self):
        polled = {maori_live.seat_name(p['seat']) for p in maori_live.live_polls()}
        self.assertEqual(polled, {'Te Tai Hauāuru', 'Te Tai Tonga', 'Hauraki-Waikato', 'Waiariki'})


if __name__ == '__main__':
    unittest.main()
