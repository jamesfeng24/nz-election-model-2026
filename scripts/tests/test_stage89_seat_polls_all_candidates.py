"""Seat polls for every candidate: the update moves each polled candidate, keeps masses, stays inside the D117 cap and reduces to the Gaussian
rule on a two-candidate poll."""
import copy
import unittest
import numpy as np
from scripts.nowcast_assembly.common import read, CONFIG
from scripts.nowcast_config.validate import check_config
from scripts.seat_polls import candidates as C, live, rescore

AS_OF = '2026-10-07'
PARTIES = ['actnewzealand', 'nationalparty', 'labourparty', 'greenparty', 'opportunity', None]


def draws(rows=4000, seed=3):
    """Shares of six candidates over simulated elections: Epsom-like, with a wide spread."""
    rng = np.random.default_rng(seed)
    z = np.log([0.36, 0.15, 0.17, 0.16, 0.10, 0.06]) + rng.normal(0, [0.5, 0.3, 0.3, 0.6, 0.5, 0.4], size=(rows, 6))
    w = np.exp(z)
    return w / w.sum(axis=1, keepdims=True)


def poll(shares, ends='2026-10-01', n=400, pollster='Curia', pid='p1', group='all other groups'):
    return {'id': pid, 'election': 2026, 'electorate': 'Epsom', 'pollster': pollster, 'sponsorGroup': group, 'fieldworkStart': ends,
            'fieldworkEnd': ends, 'sampleSize': n, 'candidateVotePct': shares, 'excluded': False}


def run(q, shares, **kw):
    inputs = {'polls': [poll(shares, **kw)], 'asOf': AS_OF}
    return C.apply(q, PARTIES, inputs, 0.18, 7)


class Update(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = draws()

    def win(self, q, i):
        return float((q.argmax(axis=1) == i).mean())

    def test_a_poll_moves_every_polled_candidate_and_keeps_the_masses(self):
        shares = {'ACT': 42, 'NAT': 20, 'LAB': 12, 'GRN': 10, 'TOP': 5}
        out, record = run(self.q, shares)
        np.testing.assert_allclose(out.sum(axis=1), 1, atol=1e-9)
        np.testing.assert_allclose(out[:, :5].sum(axis=1), self.q[:, :5].sum(axis=1), atol=1e-9)  # matched mass is kept
        np.testing.assert_allclose(out[:, 5], self.q[:, 5], atol=1e-12)  # the unmatched candidate keeps its share
        self.assertGreater(out[:, 0].mean(), self.q[:, 0].mean())  # the leader the poll shows rises
        self.assertLess(out[:, 3].mean(), self.q[:, 3].mean())  # the Green the poll puts at 10 falls
        self.assertGreater(self.win(out, 0), self.win(self.q, 0))
        self.assertTrue((out.std(axis=0)[:5] < self.q.std(axis=0)[:5]).all())  # a poll narrows every polled candidate
        self.assertEqual(set(record), {'pollIds', 'pollValue', 'pollVariance', 'ageWeeks', 'rho', 'weight', 'modelCentre', 'modelSD', 'shift',
                                       'posteriorSD', 'sharedSD'})

    def test_no_poll_leaves_the_shares_alone(self):
        out, record = C.apply(self.q, PARTIES, {'polls': [], 'asOf': AS_OF}, 0.18, 7)
        np.testing.assert_array_equal(out, self.q)
        self.assertIsNone(record)

    def test_older_polls_count_less_and_larger_samples_count_more(self):
        shares = {'ACT': 42, 'NAT': 20, 'LAB': 12, 'GRN': 10, 'TOP': 5}
        fresh = run(self.q, shares, ends='2026-10-06')[0][:, 0].mean()
        old = run(self.q, shares, ends='2026-07-20')[0][:, 0].mean()
        big = run(self.q, shares, ends='2026-07-20', n=4000)[0][:, 0].mean()
        self.assertGreater(fresh, old)
        self.assertGreater(big, old)
        self.assertGreater(old, self.q[:, 0].mean())

    def test_the_gain_never_exceeds_the_cap(self):
        out, record = run(self.q, {'ACT': 60, 'NAT': 5, 'LAB': 5, 'GRN': 5, 'TOP': 5}, n=1000000, ends='2026-10-07')
        gap = record['pollValue'] - record['modelCentre']
        self.assertLessEqual(record['shift'] / gap, C.CAP + 0.05)  # cap on the gain (sampling noise in the draws allows a little)

    def test_two_candidate_poll_is_the_gaussian_update(self):
        rng = np.random.default_rng(5)
        x = rng.normal(0.4, 0.35, size=200000)  # log(NAT/LAB) across elections
        q = np.stack([np.exp(x) / (1 + np.exp(x)), 1 / (1 + np.exp(x))], axis=1)
        inputs = {'polls': [poll({'NAT': 50, 'LAB': 25}, ends='2026-10-07')], 'asOf': AS_OF}
        out, record = C.apply(q, ['nationalparty', 'labourparty'], inputs, 0.18, 1)
        variance = C.error_covariance(inputs['polls'][0], read(live.DESIGN), 'NAT')[0, 0]
        k = 0.1225 / (0.1225 + variance)
        self.assertLess(k, C.CAP)
        expected = 0.4 + k * (np.log(2) - 0.4)
        self.assertAlmostEqual(float(np.log(out[:, 0] / out[:, 1]).mean()), expected, places=2)
        self.assertAlmostEqual(float(np.log(out[:, 0] / out[:, 1]).var()), (1 - k) * 0.1225, places=2)  # posterior variance of a Gaussian update

    def test_unmatchable_columns_and_a_single_matched_candidate_are_ignored(self):
        out, record = run(self.q, {'OTH': 40, 'ACT': 30})
        np.testing.assert_array_equal(out, self.q)
        self.assertIsNone(record)


class Polls(unittest.TestCase):
    def test_every_live_poll_counts_including_those_the_balance_rule_rejects(self):
        polls, detail = C.combine(AS_OF)
        seats = live.seat_ids()
        for name in ('Auckland Central', 'Wellington Bays'):
            used = [p for p in detail[seats[live.fold(name)]] if p['status'] == 'used']
            self.assertTrue(used, name)
            self.assertAlmostEqual(sum(p['share'] for p in used), 1)
        self.assertTrue(set(live.inputs(AS_OF)) <= set(polls))  # nothing the old rule used is lost

    def test_one_poll_per_pollster_and_the_cutoff_and_exclusions(self):
        rows = [r for r in live.live_rows() if r['electorate'] != 'Waitaki']
        base = next(r for r in live.live_rows() if r['electorate'] == 'Waitaki')
        older = dict(base, id='older', fieldworkStart='2026-07-01', fieldworkEnd='2026-07-05')
        late = dict(base, id='late', pollster='Late Pollster', fieldworkStart='2026-10-09', fieldworkEnd='2026-10-12')
        out = dict(base, id='out', pollster='Out Pollster', excluded='withdrew')
        green = dict(base, id='green', pollster='Green Pollster', candidateVotePct={'NAT': 20, 'LAB': 25, 'GRN': 40})
        polls, detail = C.combine(AS_OF, rows=rows + [older, base, late, out, green])
        seat = live.seat_ids()['waitaki']
        status = {p['pollId']: (p['status'], p['reason']) for p in detail[seat]}
        self.assertEqual(status[base['id']][0], 'used')
        self.assertEqual(status['green'][0], 'used')
        self.assertIn('superseded', status['older'][1])
        self.assertIn('after the data cutoff', status['late'][1])
        self.assertIn('excluded', status['out'][1])
        self.assertEqual(sorted(p['id'] for p in polls[seat]['polls']), sorted([base['id'], 'green']))


class Inflation(unittest.TestCase):
    def test_the_constant_is_what_the_historical_rescoring_supports(self):
        got = rescore.summary()
        self.assertEqual((got['contrasts'], got['polls']), (40, 13))
        self.assertGreater(got['ratio'], C.INFLATION * 0.9)  # the constant is not narrower than the history it was set from
        self.assertLess(got['ratio'], C.INFLATION * 1.3)


class Config(unittest.TestCase):
    def test_the_live_config_uses_the_rule_and_validates(self):
        c = copy.deepcopy(read(CONFIG))
        self.assertEqual(c['seatPolls']['rule'], 'all-candidates')
        check_config(c)

    def test_every_mapped_column_is_a_2026_party_group(self):
        keys = {r['targetGroupKey'] for r in read(read(CONFIG)['partyRelationships'])['records']}
        self.assertTrue(set(C.COLUMNS) <= keys)


if __name__ == '__main__':
    unittest.main()
