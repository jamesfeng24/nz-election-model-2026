"""D134: James's Epsom offset on David Seymour's candidate weight (+0.40 on the log-weight) is configured, validated and applied to that one
candidate only. Runs on the real 2026 slates and baseline; nothing is simulated."""
import copy
import unittest
import numpy as np
from scripts.nowcast_assembly import assemble as A, general
from scripts.nowcast_assembly.common import CONFIG, read
from scripts.nowcast_config import validate as V
from scripts.polling.candidate_integration.propagation import candidate_vectors, local_vectors

EPSOM = 'nz-general-2026-boundary-010'
SEYMOUR = 'nz-general-2026-boundary-010-candidate-ab7b6651f1dc3327'
MT_ALBERT = 'nz-general-2026-boundary-025'


def config():
    return copy.deepcopy(read(CONFIG))


def shares(seat, offsets=None, candidate_offsets=None):
    """Deterministic candidate shares at the mean national draw, with and without the offsets."""
    c = config()
    keys, national2023, base = general.baseline(c)
    party = general.party_row(seat, keys, base[seat], national2023, general.relationships(c))
    parameters, _ = general.fold_parameters(c)
    slates, _ = A.live_slates(c)
    row = general.candidate_row(seat, slates[seat], party, parameters, offsets, candidate_offsets)
    destinations, exponents, kappa = general.weights(row, party)
    local = local_vectors(np.array([base[seat]]), party['affinities'])
    return row, candidate_vectors(local, destinations, exponents, kappa)[0]


class SeymourOffset(unittest.TestCase):
    def test_config_carries_the_decision_and_validates(self):
        c = config()
        (setting,) = c['candidate']['candidateExponentOffsets']
        self.assertEqual((setting['seat'], setting['candidateId'], setting['offset'], setting['decision']), (EPSOM, SEYMOUR, 0.40, 'D134'))
        self.assertIn('D134', c['decisions'])
        V.check_config(c)

    def test_config_rejects_other_shapes(self):
        for edit in (lambda c: c['candidate']['candidateExponentOffsets'][0].update(offset=0),
                     lambda c: c['candidate']['candidateExponentOffsets'][0].update(offset=1.5),
                     lambda c: c['candidate']['candidateExponentOffsets'][0].update(offset=1),
                     lambda c: c['candidate']['candidateExponentOffsets'][0].update(seat='Epsom'),
                     lambda c: c['candidate']['candidateExponentOffsets'][0].update(candidateId='nz-general-2026-boundary-011-candidate-x'),
                     lambda c: c['candidate']['candidateExponentOffsets'][0].pop('decision')):
            c = config(); edit(c)
            with self.assertRaises(V.ConfigError):
                V.check_config(c)

    def test_only_epsom_has_the_offset(self):
        c = config()
        self.assertEqual(general.candidate_exponent_offsets(c, EPSOM), {SEYMOUR: 0.40})
        self.assertEqual(general.candidate_exponent_offsets(c, MT_ALBERT), {})

    def test_only_seymour_is_offset_and_the_shares_still_close(self):
        c = config()
        row, lifted = shares(EPSOM, general.exponent_offsets(c, EPSOM), general.candidate_exponent_offsets(c, EPSOM))
        plain_row, plain = shares(EPSOM)
        i = row['ids'].index(SEYMOUR)
        self.assertEqual([o for k, o in enumerate(row['exponentOffsets']) if k != i and row['partyOf'][k] != 'opportunity'],
                         [0.0] * (len(row['ids']) - 1 - row['partyOf'].count('opportunity') + (row['partyOf'][i] == 'opportunity')))
        self.assertAlmostEqual(row['exponentOffsets'][i], 0.40)
        self.assertNotIn('exponentOffsets', plain_row)
        self.assertAlmostEqual(float(lifted.sum()), 1.0)
        self.assertGreater(lifted[i], plain[i] + 0.05)
        self.assertTrue(all(lifted[k] < plain[k] for k in range(len(plain)) if k != i))

    def test_an_offset_for_a_candidate_not_on_the_slate_is_refused(self):
        with self.assertRaises(Exception):
            shares(EPSOM, None, {'not-a-candidate': 0.4})


if __name__ == '__main__':
    unittest.main()
