import copy
import unittest
import numpy as np
from scripts.nowcast_assembly import general, national
from scripts.nowcast_assembly.common import CONFIG, read, AssemblyError
from scripts.party_vote_elasticity import backtest, rule
from scripts.party_vote_elasticity.common import DESIGN, PRIMARY, RECORDS, PREFIX, file_sha, ARMS
from scripts.party_vote_elasticity.run import scores, findings
from scripts.polling.candidate_integration.propagation import local_vectors


def block(values):
    """values: {transition: {arm: (M1, M2)}} -> the nested shape rule.classify reads, identical at both bounds."""
    out = {}
    for t, arms in values.items():
        inner = {'arms': {a: {'M1': {'mae': m1}, 'M2': {'macroMinorMae': m2}} for a, (m1, m2) in arms.items()}}
        out[t] = {'bounds': {'lower': inner, 'upper': inner}}
    return out


KEYS = ['2014-2017', '2017-2020', '2020-2023']
THRESH = {'M1': 0.25, 'M2': 0.10}


class DesignTests(unittest.TestCase):
    def test_contract_pins_the_stage5_records(self):
        contract = read(DESIGN)
        self.assertTrue(contract['frozenBeforeScoring'])
        self.assertEqual(file_sha(RECORDS), contract['inputs']['records']['sha256'])
        self.assertEqual(contract['arms']['primary'], list(ARMS))

    def test_backtest_covers_every_general_seat_with_a_complete_party_set(self):
        for source, target, seats in ((2014, 2017, 64), (2017, 2020, 65), (2020, 2023, 65)):
            data = backtest.load(source, target)
            self.assertEqual(len(data['seats']), seats)
            for key in ('p_lower', 'p_upper', 'actual', 'P0', 'P1'):
                self.assertTrue(np.allclose(data[key].sum(axis=-1), 1))
            self.assertTrue((data['p_lower'] <= data['p_upper'] + 0.0035).all())

    def test_2017_2020_source_bounds_are_narrow_and_conclusions_do_not_depend_on_the_bound(self):
        sc, _ = scores(read(DESIGN))
        verdict = findings(read(DESIGN), sc, _)
        self.assertTrue(verdict['boundsAgree'])
        t = sc['transitions']['2017-2020']['bounds']
        for arm in ARMS:
            self.assertLess(abs(t['lower']['arms'][arm]['M1']['mae'] - t['upper']['arms'][arm]['M1']['mae']), 0.05)

    def test_saved_artifacts_are_current(self):
        sc, _ = scores(read(DESIGN))
        from scripts.party_vote_elasticity.common import save
        save('scores.json', sc, check=True)


class RuleTests(unittest.TestCase):
    def test_one_clear_winner_is_adopted(self):
        v = block({t: {'P': (5, .9), 'A': (3, .5), 'L': (5, .9), 'H': (5, .9)} for t in KEYS})
        self.assertEqual(rule.classify(v, KEYS, list(ARMS), THRESH)['class'], 'adopt_A')

    def test_arms_that_cannot_be_separated_are_carried(self):
        v = block({t: {'P': (4, .6), 'A': (4.1, .62), 'L': (3.9, .6), 'H': (4, .58)} for t in KEYS})
        result = rule.classify(v, KEYS, list(ARMS), THRESH)
        self.assertEqual((result['class'], result['retainedArms']), ('carry_mixture', list(ARMS)))

    def test_a_trade_off_between_the_two_metrics_goes_to_james(self):
        v = block({t: {'P': (4, .5), 'A': (3, .9), 'L': (4, .5), 'H': (4, .5)} for t in KEYS})
        # A beats every other arm on M1 and every other arm beats A on M2: A is out, and so are the others (beaten on M1).
        self.assertEqual(rule.classify(v, KEYS, list(ARMS), THRESH)['class'], 'mixed_report_to_james')

    def test_winning_one_transition_only_is_not_a_win(self):
        v = block({'2014-2017': {'P': (6, .5), 'A': (3, .5), 'L': (6, .5), 'H': (6, .5)},
                   '2017-2020': {'P': (3, .5), 'A': (3.2, .5), 'L': (3, .5), 'H': (3, .5)},
                   '2020-2023': {'P': (3, .5), 'A': (3.2, .5), 'L': (3, .5), 'H': (3, .5)}})
        self.assertNotEqual(rule.classify(v, KEYS, list(ARMS), THRESH)['class'], 'adopt_A')

    def test_materiality_override_names_but_does_not_change_the_rule_class(self):
        v = block({t: {a: (4, .6) for a in ARMS} for t in KEYS})
        result = rule.classify(v, KEYS, list(ARMS), THRESH, {'invariant': True})
        self.assertEqual((result['class'], result['ruleClassBeforeOverride']), ('materially_invariant', 'carry_mixture'))

    def test_bounds_that_disagree_go_to_james(self):
        v = block({t: {'P': (4, .6), 'A': (3, .6), 'L': (4, .6), 'H': (4, .6)} for t in KEYS})
        v['2017-2020']['bounds']['upper'] = {'arms': {a: {'M1': {'mae': 6 if a == 'A' else 4}, 'M2': {'macroMinorMae': .6}} for a in ARMS}}
        self.assertEqual(rule.classify(v, KEYS, list(ARMS), THRESH)['class'], 'mixed_report_to_james')


class LiveWiringTests(unittest.TestCase):
    def setUp(self):
        self.config = read(CONFIG)
        keys, self.n23, self.base = general.baseline(self.config)
        draws, _, groups = national.load(self.config, 8)
        self.fine = general.fine_national(draws, groups, keys, self.n23, general.relationships(self.config))
        self.keys, self.continuing = keys, general.relationships(self.config)

    def row(self, seat):
        return general.party_row(seat, self.keys, self.base[seat], self.n23, self.continuing)

    def test_the_committed_configuration_keeps_the_frozen_layer(self):
        self.assertNotIn('localParty', self.config)
        self.assertIsNone(general.local_transform(self.config))

    def test_the_proportional_setting_reproduces_the_frozen_layer(self):
        cfg = copy.deepcopy(self.config)
        cfg['localParty'] = {'transform': 'P'}
        seat = sorted(self.base)[0]
        party = self.row(seat)
        new = general.local_transform(cfg)(party, self.fine, self.n23, 1)
        self.assertLess(np.abs(new - local_vectors(self.fine, party['affinities'])).max(), 1e-13)

    def test_the_mixture_is_one_arm_per_national_draw_and_deterministic(self):
        cfg = copy.deepcopy(self.config)
        cfg['localParty'] = {'transform': 'mixture', 'arms': ['P', 'L', 'H']}
        seat = sorted(self.base)[0]
        party = self.row(seat)
        make = general.local_transform(cfg)
        fine2 = np.repeat(self.fine, 2, axis=0)
        a = make(party, fine2, self.n23, 2)
        self.assertTrue(np.array_equal(a, make(party, fine2, self.n23, 2)))
        self.assertTrue(np.array_equal(a[0::2], a[1::2]))  # replicates of one national draw share the arm
        names = {arm: general.local_transform({**cfg, 'localParty': {'transform': arm}})(party, self.fine, self.n23, 1) for arm in ('P', 'L', 'H')}
        for i in range(len(self.fine)):
            self.assertTrue(any(np.allclose(a[2 * i], names[arm][i]) for arm in names))

    def test_unknown_settings_are_refused(self):
        cfg = copy.deepcopy(self.config)
        cfg['localParty'] = {'transform': 'banana'}
        with self.assertRaises(AssemblyError):
            general.local_transform(cfg)


if __name__ == '__main__':
    unittest.main()
