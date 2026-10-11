"""D132: James's TOP candidate-weight offset (-0.35 on the log-weight, Mt Albert exempt) is configured, validated and applied
only to TOP candidates outside the exempt seat. Runs on the real 2026 slates and baseline; nothing is simulated."""
import copy
import unittest
import numpy as np
from scripts.nowcast_assembly import assemble as A, general
from scripts.nowcast_assembly.common import CONFIG, read
from scripts.nowcast_config import validate as V
from scripts.polling.candidate_integration.propagation import candidate_vectors, local_vectors

MT_ALBERT = 'nz-general-2026-boundary-025'
CHRISTCHURCH_CENTRAL = 'nz-general-2026-boundary-004'


def config():
    return copy.deepcopy(read(CONFIG))


def shares(seat, offsets):
    """Deterministic candidate shares at the mean national draw, with and without the offsets."""
    c = config()
    keys, national2023, base = general.baseline(c)
    continuing = general.relationships(c)
    party = general.party_row(seat, keys, base[seat], national2023, continuing)
    parameters, _ = general.fold_parameters(c)
    slates, _ = A.live_slates(c)
    row = general.candidate_row(seat, slates[seat], party, parameters, offsets)
    destinations, exponents, kappa = general.weights(row, party)
    local = local_vectors(np.array([base[seat]]), party['affinities'])
    return row, candidate_vectors(local, destinations, exponents, kappa)[0]


class TopOffset(unittest.TestCase):
    def test_config_carries_the_decision_and_validates(self):
        c = config()
        setting = c['candidate']['partyExponentOffsets']['opportunity']
        self.assertEqual((setting['offset'], setting['exemptSeats'], setting['decision']), (-0.35, [MT_ALBERT], 'D132'))
        self.assertIn('D132', c['decisions'])
        V.check_config(c)

    def test_config_rejects_other_shapes(self):
        for edit in (lambda c: c['candidate']['partyExponentOffsets']['opportunity'].update(offset=0.1),
                     lambda c: c['candidate']['partyExponentOffsets']['opportunity'].update(offset=-1.5),
                     lambda c: c['candidate']['partyExponentOffsets']['opportunity'].update(offset=0),
                     lambda c: c['candidate']['partyExponentOffsets']['opportunity'].update(exemptSeats=['Mt Albert']),
                     lambda c: c['candidate']['partyExponentOffsets']['opportunity'].pop('decision'),
                     lambda c: c['candidate']['partyExponentOffsets'].update(nonsense=copy.deepcopy(c['candidate']['partyExponentOffsets']['opportunity']))):
            c = config(); edit(c)
            with self.assertRaises(V.ConfigError):
                V.check_config(c)

    def test_exempt_seat_gets_no_offsets(self):
        c = config()
        self.assertEqual(general.exponent_offsets(c, MT_ALBERT), {})
        self.assertEqual(general.exponent_offsets(c, CHRISTCHURCH_CENTRAL), {'opportunity': -0.35})

    def test_only_top_candidates_are_offset_and_shares_still_close(self):
        c = config()
        row, with_offset = shares(CHRISTCHURCH_CENTRAL, general.exponent_offsets(c, CHRISTCHURCH_CENTRAL))
        plain, without = shares(CHRISTCHURCH_CENTRAL, {})
        self.assertNotIn('exponentOffsets', plain)
        top = [i for i, p in enumerate(row['partyOf']) if p == 'opportunity']
        self.assertEqual(len(top), 1)
        self.assertEqual([o for i, o in enumerate(row['exponentOffsets']) if i not in top], [0.0] * (len(row['partyOf']) - 1))
        self.assertAlmostEqual(row['exponentOffsets'][top[0]], -0.35)
        self.assertAlmostEqual(with_offset.sum(), 1.0, places=12)
        self.assertLess(with_offset[top[0]], 0.8 * without[top[0]])
        others = [i for i in range(len(with_offset)) if i not in top]
        for i in others:  # the freed share goes to every other candidate in proportion to its weight
            self.assertGreater(with_offset[i], without[i])
        ratios = with_offset[others] / without[others]
        self.assertTrue(np.allclose(ratios, ratios[0], rtol=1e-9))

    def test_mt_albert_is_unchanged(self):
        _, with_offset = shares(MT_ALBERT, general.exponent_offsets(config(), MT_ALBERT))
        _, without = shares(MT_ALBERT, {})
        self.assertTrue(np.array_equal(with_offset, without))


class Evidence(unittest.TestCase):
    def test_the_live_path_never_imports_the_evidence_script(self):
        from scripts.tests.test_historical_flag_isolation import ROOT as repo
        for base in ('scripts/nowcast_assembly', 'scripts/nowcast_config', 'scripts/seat_polls', 'scripts/publish_workflow'):
            for path in (repo / base).rglob('*.py'):
                self.assertNotIn('top_candidate_offset', path.read_text(encoding='utf-8'), path.as_posix())


    def test_saved_evidence_reproduces_and_supports_the_wording(self):
        from scripts.balance_scale.common import equivalent
        from scripts.top_candidate_offset import evidence
        saved = evidence.read(evidence.OUTPUT)
        self.assertTrue(equivalent(saved, evidence.build(), 1e-9))
        parties = saved['parties']
        self.assertEqual([parties[p]['all']['n'] for p in ('ACT', 'NZF', 'GRN', 'TOP')], [132, 99, 140, 41])
        self.assertLess(parties['ACT']['all']['ratioOfSums'], 0.55)
        self.assertTrue(0.8 < parties['NZF']['all']['ratioOfSums'] < 0.9 and 0.8 < parties['GRN']['all']['ratioOfSums'] < 0.9)
        self.assertGreater(parties['TOP']['all']['ratioOfSums'], 1.0)  # TOP's own clean history is no support for a cut


if __name__ == '__main__':
    unittest.main()
