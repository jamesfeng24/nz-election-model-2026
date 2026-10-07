"""Stage76: the accelerated Gaussian-softmax expectation equals the frozen Stage47 one to floating-point rounding, and
the assembly gives the same draws with or without it."""
import unittest
import numpy as np
from scripts.uncertainty_expectation import integration
from scripts.nowcast_assembly import fastmath, general, national, streams
from scripts.nowcast_assembly.common import CONFIG, read


class Kernel(unittest.TestCase):
    def test_matches_the_frozen_expectation_and_jacobian(self):
        rng = np.random.default_rng(76)
        for k, size in ((2, 512), (3, 2048), (15, 8192)):
            nodes, weights = integration.rule(tuple(['a'] * k), 0.2975, 0.5178, size)
            p = rng.dirichlet(np.full(k, 2.0), size=40)
            p[:, 0] *= 1e-6
            p /= p.sum(axis=1, keepdims=True)
            offset = rng.normal(0, 0.3, size=p.shape)
            frozen, frozen_jac = integration.expectation(p, offset, nodes, weights, True)
            fast, fast_jac = fastmath.expectation(p, offset, nodes, weights, True)
            self.assertLess(np.max(np.abs(frozen - fast)), 1e-13)
            self.assertLess(np.max(np.abs(frozen_jac - fast_jac)), 1e-13)
            self.assertLess(np.max(np.abs(integration.expectation(p[0], offset[0], nodes, weights) -
                                          fastmath.expectation(p[0], offset[0], nodes, weights))), 1e-13)

    def test_substitution_is_scoped(self):
        original = integration.expectation
        with fastmath.accelerated():
            self.assertIs(integration.expectation, fastmath.expectation)
        self.assertIs(integration.expectation, original)


class Seat(unittest.TestCase):
    def test_same_local_party_draws_with_and_without_acceleration(self):
        config = read(CONFIG)
        draws, _, groups = national.load(config, 16)
        keys, national2023, base = general.baseline(config)
        continuing = general.relationships(config)
        fine = general.fine_national(draws, groups, keys, national2023, continuing)
        scales = read(config['uncertainty']['scales'])['layers']['local_party']['scales']
        seat = sorted(base)[5]
        row = general.party_row(seat, keys, base[seat], national2023, continuing)
        with streams.substituted([row], 16, 'synthetic-test'):
            frozen, _ = general.simulate(row, None, fine, scales, None, 1.0)
            with fastmath.accelerated():
                fast, _ = general.simulate(row, None, fine, scales, None, 1.0)
        self.assertLess(np.max(np.abs(frozen - fast)), 1e-12)


if __name__ == '__main__':
    unittest.main()
