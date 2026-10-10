import unittest
import numpy as np
from scripts.models.party_vote_transform.formulas import transform
from scripts.party_vote_elasticity.transforms import ARMS, swing, swing_mixture, unclosed
from scripts.polling.candidate_integration.propagation import local_vectors


def example(n=5, seed=1):
    rng = np.random.default_rng(seed)
    p0 = rng.dirichlet([4, 3, 2, 1, 1, 0.5])
    p = rng.dirichlet(p0 * 30)
    p1 = rng.dirichlet(np.array([3, 4, 2, 2, 1, 1.0]) * 40, size=n)
    return p, p0, p1


class TransformTests(unittest.TestCase):
    def test_proportional_reproduces_the_live_local_party_layer(self):
        p, p0, p1 = example()
        live = local_vectors(p1, p / p0)
        self.assertLess(np.abs(swing('P', p, p0, p1) - live).max(), 1e-14)

    def test_arms_close_and_stay_non_negative(self):
        p, p0, p1 = example()
        for arm in ARMS:
            q = swing(arm, p, p0, p1)
            self.assertTrue(np.allclose(q.sum(axis=1), 1, atol=1e-14) and (q >= 0).all(), arm)

    def test_no_national_change_leaves_the_seat_unchanged(self):
        p, p0, _ = example()
        for arm in ARMS:
            self.assertLess(np.abs(swing(arm, p, p0, np.tile(p0, (3, 1))) - p).max(), 1e-14, arm)

    def test_unclosed_values_match_the_stage5_formulas(self):
        p, p0, p1 = example(1)
        for arm, name in (('A', 'additive'), ('L', 'log_odds')):
            expected = [transform(name, a, b, c)['prediction'] for a, b, c in zip(p, p0, p1[0])]
            self.assertTrue(np.allclose(unclosed(arm, p, p0, p1[0]), expected, atol=1e-14), arm)
        self.assertTrue(np.allclose(unclosed('P', p, p0, p1[0]),
                                    [transform('proportional', a, b, c)['prediction'] for a, b, c in zip(p, p0, p1[0])], atol=1e-14))

    def test_power_family_endpoints(self):
        p, p0, p1 = example()
        self.assertLess(np.abs(unclosed(1.0, p, p0, p1) - unclosed('A', p, p0, p1)).max(), 1e-14)
        self.assertLess(np.abs(unclosed(0.5, p, p0, p1) - unclosed('H', p, p0, p1)).max(), 1e-14)
        self.assertLess(np.abs(swing(1e-6, p, p0, p1) - swing('P', p, p0, p1)).max(), 1e-4)
        with self.assertRaises(ValueError):
            unclosed(0.0, p, p0, p1)

    def test_zero_local_share_stays_zero(self):
        p, p0, p1 = example()
        p = p.copy(); p[2] = 0.0; p /= p.sum()
        for arm in ARMS:
            self.assertTrue((swing(arm, p, p0, p1)[:, 2] == 0).all(), arm)

    def test_additive_clips_at_zero_and_closes(self):
        p0 = np.array([.5, .3, .2]); p1 = np.array([[.1, .5, .4]]); p = np.array([.05, .5, .45])
        raw = unclosed('A', p, p0, p1)
        self.assertEqual(raw[0, 0], 0.0)
        self.assertAlmostEqual(swing('A', p, p0, p1).sum(), 1.0, places=14)

    def test_the_arms_order_by_how_strongly_a_strong_seat_follows_a_falling_party(self):
        p0 = np.array([.4, .6]); p1 = np.array([[.2, .8]]); p = np.array([.6, .4])
        first = {arm: swing(arm, p, p0, p1)[0, 0] for arm in ('P', 'H', 'A')}
        self.assertTrue(first['P'] < first['H'] < first['A'] or first['P'] > first['H'] > first['A'])

    def test_mixture_uses_the_assigned_arm_per_row(self):
        p, p0, p1 = example(6)
        assignment = np.array(['P', 'A', 'L', 'H', 'P', 'A'])
        mixed = swing_mixture(ARMS, assignment, p, p0, p1)
        for i, arm in enumerate(assignment):
            self.assertLess(np.abs(mixed[i] - swing(arm, p, p0, p1[i:i + 1])[0]).max(), 1e-15)
        with self.assertRaises(ValueError):
            swing_mixture(ARMS, np.array(['Z'] * 6), p, p0, p1)

    def test_invalid_inputs_are_rejected(self):
        p, p0, p1 = example()
        bad = p0.copy(); bad[0] = 0.0
        with self.assertRaises(ValueError):
            swing('P', p, bad, p1)
        with self.assertRaises(ValueError):
            swing('P', p * np.nan, p0, p1)


if __name__ == '__main__':
    unittest.main()
