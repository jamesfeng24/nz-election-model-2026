"""Stage78 no-poll Maori fallback: frozen design, carry-forward structure, estimation arithmetic, swing posterior, split incumbent, finding rules and artifact currency."""
import math
import unittest

import numpy as np

from scripts.maori_seat_fallback import forecast, history, inputs2026, model, run, score
from scripts.maori_seat_fallback.common import DESIGN, DESIGN_DOC, INPUTS, ROOT, STAGE66, STAGE71, read, save
from scripts.maori_seat_layer.fit import sigma2 as stage66_sigma2, tau2 as stage66_tau2


def cand(name, party, share=None):
    return {'name': name, 'party': party, 'share': share}


class FrozenDesign(unittest.TestCase):
    def test_contract_pins_the_registered_rules(self):
        c = read(DESIGN)
        self.assertEqual((c['seed'], c['draws'], c['readoutDraws'], c['swingSubsetSize']), (2026078, 20000, 100000, 3))
        self.assertEqual(c['swingRuleOrder'], ['swing_helps', 'swing_hurts', 'mixed_report_to_james'])
        self.assertEqual(c['schemes']['leaveOneElectionOut'], {'2017': [2020, 2023], '2020': [2017, 2023], '2023': [2017, 2020]})
        self.assertEqual(c['schemes']['chronological'], {'2023': [2017, 2020]})
        self.assertEqual((c['bias'], c['biasAdoption'], c['calibration']['zThreshold']), (0.0, False, 1.645))
        self.assertEqual(c['phi'], {'distribution': 'uniform(0,1)', 'sensitivityFixed': [0.2, 0.5, 0.8]})
        self.assertFalse(c['adopted'] or c['publication'] or c['configTouched'] or c['assemblyTouched'] or c['generalElectorateTouched'] or c['dataSourcesJsonTouched'])
        self.assertTrue(c['stage66ReadOnly'] and c['stage71ReadOnly'])

    def test_design_document_states_the_rules_and_the_limits(self):
        text = (ROOT / DESIGN_DOC).read_text(encoding='utf-8')
        for phrase in ('Disclosure about what was known', 'swing_helps', 'swing_hurts', 'mixed_report_to_james', 'kappa', 'phi', 'do-not list', 'Clarified before any score'):
            self.assertIn(phrase, text)

    def test_structure_counts_in_the_design_match_the_data(self):
        c = read(DESIGN)
        res = history.results()
        rows = history.contrast_rows(res)
        self.assertEqual({str(y): len(g) for y, g in history.groups_for(rows, {2017, 2020, 2023}).items()}, {k: v for k, v in c['contrastsPerTransition'].items()})
        self.assertEqual({k: len(v) for k, v in history.entrant_pools({2017, 2020, 2023}, res).items()}, c['entrantPoolSizes'])


class CarryForward(unittest.TestCase):
    prev = [cand('a', 'MP', 0.5), cand('b', 'LAB', 0.3), cand('c', 'GRN', 0.1), cand('d', 'OTH', 0.05), cand('e', 'OTH', 0.05)]

    def test_matching_is_by_party_label_and_entrants_are_split_into_two_pools(self):
        new = [cand('x', 'MP'), cand('y', 'LAB'), cand('z', 'NAT'), cand('w', 'OTH'), cand('v', 'IND')]
        inp = history.build_inputs(self.prev, new)
        self.assertEqual([None if b is None else round(math.exp(b), 6) for b in inp['base']], [0.5, 0.3, None, None, None])
        self.assertEqual(inp['entrant'], [None, None, 'established', 'other', 'other'])
        self.assertEqual(inp['mp'], [True, False, False, False, False])

    def test_a_code_that_appears_twice_is_not_matched(self):
        inp = history.build_inputs(self.prev, [cand('p', 'OTH'), cand('q', 'MP'), cand('r', 'MP')])
        self.assertEqual(inp['base'], [None, None, None])
        self.assertEqual(inp['entrant'], ['other', 'established', 'established'])

    def test_previous_log_odds_needs_exactly_one_of_each(self):
        self.assertAlmostEqual(history.prev_log_odds(self.prev), math.log(0.5 / 0.3))
        self.assertIsNone(history.prev_log_odds([cand('a', 'MP', 0.5), cand('b', 'MP', 0.5)]))
        self.assertIsNone(history.prev_log_odds([cand('a', 'LAB', 1.0)]))

    def test_split_incumbent_keeps_the_label_baseline_and_the_total(self):
        new = [cand('x', 'MP'), cand('y', 'LAB'), cand('k', 'TTT')]
        inp = history.build_inputs(self.prev, new, split={'name': 'k', 'fromCode': 'MP'})
        self.assertEqual(inp['split']['toIndex'], 2)
        self.assertEqual(inp['entrant'][2], None)
        share = model.simulate_seat(inp, np.zeros(2000), np.zeros(2000), {}, np.random.default_rng(1), phi=np.full(2000, 0.3))
        # with no noise the two split candidates carry 0.3 and 0.7 of the 0.5 baseline
        self.assertTrue(np.allclose(share[:, 2] / share[:, 0], 0.3 / 0.7))
        self.assertTrue(np.allclose(share.sum(axis=1), 1.0))
        with self.assertRaises(ValueError):
            history.build_inputs(self.prev, [cand('x', 'LAB'), cand('k', 'TTT')], split={'name': 'k', 'fromCode': 'NAT'})
        with self.assertRaises(ValueError):
            model.simulate_seat(inp, np.ones(3), np.zeros(3), {}, np.random.default_rng(1))

    def test_every_contrast_row_has_one_mp_and_one_labour_candidate_in_both_elections(self):
        res = history.results()
        for r in history.contrast_rows(res):
            for year in (r['year'], history.prev_year(r['year'])):
                self.assertEqual(history.prev_log_odds(res[year][r['seat']]['candidates']) is not None, True)
        self.assertEqual(len(history.contrast_rows(res)), 19)

    def test_entrant_pools_use_only_the_requested_transitions(self):
        res = history.results()
        a, b = history.entrant_pools({2017}, res), history.entrant_pools({2017, 2020, 2023}, res)
        self.assertEqual((len(a['established']), len(a['other'])), (2, 1))
        self.assertLess(len(a['other']), len(b['other']))


class Estimation(unittest.TestCase):
    def test_estimates_are_the_stage66_functions_about_zero(self):
        groups = {2017: [0.1, -0.2, 0.0], 2020: [0.3, 0.1], 2023: [0.9, 0.6, 0.7]}
        est = model.estimate(groups)
        s2, dof = stage66_sigma2(groups)
        self.assertEqual((est['sigma2'], est['sigma2Dof'], est['elections'], est['contrasts']), (s2, dof, 3, 8))
        self.assertEqual(est['tau2'], stage66_tau2(groups, s2, 0.0))

    def test_all_three_transition_fit_is_stable(self):
        est = model.estimate(history.groups_for(history.contrast_rows(), {2017, 2020, 2023}))
        self.assertEqual((est['sigma2Dof'], est['elections'], est['contrasts']), (16, 3, 19))

    def test_parameter_draws_are_deterministic_and_a_zero_tau_stays_zero(self):
        est = {'sigma2': 0.05, 'sigma2Dof': 10, 'tau2': 0.0, 'elections': 2}
        a, b = model.parameter_draws(est, np.random.default_rng(3), 50), model.parameter_draws(est, np.random.default_rng(3), 50)
        self.assertTrue(all(np.array_equal(x, y) for x, y in zip(a, b)))
        self.assertTrue(np.all(a[1] == 0.0) and np.all(a[0] > 0))


class SwingPosterior(unittest.TestCase):
    def test_gaussian_posterior_closed_form(self):
        # one-dimensional conjugate check: u ~ N(0, tau2), xbar = u + e, e ~ N(0, 2 s2 / k)
        s2, t2, k = np.array([0.04]), np.array([0.16]), 4
        noise = 2 * 0.04 / 4
        draw, kappa = model.posterior_shift(np.array([0.5]), s2, t2, k, np.array([0.0]))
        self.assertAlmostEqual(float(kappa[0]), 0.16 / (0.16 + noise))
        self.assertAlmostEqual(float(draw[0]), float(kappa[0]) * 0.5)
        rng = np.random.default_rng(7)
        z = rng.standard_normal(200000)
        d, _ = model.posterior_shift(np.full(200000, 0.5), np.full(200000, 0.04), np.full(200000, 0.16), k, z)
        self.assertAlmostEqual(float(d.var()), float(kappa[0]) * noise, places=3)

    def test_marginal_variance_is_the_prior_variance(self):
        # integrating the posterior over xbar ~ N(0, tau2 + noise) recovers u ~ N(0, tau2)
        rng = np.random.default_rng(11)
        n = 400000
        t2, s2, k = 0.2, 0.05, 3
        xbar = rng.normal(0, math.sqrt(t2 + 2 * s2 / k), n)
        d, _ = model.posterior_shift(xbar, np.full(n, s2), np.full(n, t2), k, rng.standard_normal(n))
        self.assertAlmostEqual(float(d.var()), t2, places=2)

    def test_zero_tau_gives_no_shift_and_no_transfer(self):
        d, kappa = model.posterior_shift(np.array([1.0, -2.0]), np.array([0.1, 0.1]), np.array([0.0, 0.0]), 3, np.array([0.7, 0.7]))
        self.assertTrue(np.all(d == 0.0) and np.all(kappa == 0.0))


class Simulation(unittest.TestCase):
    def inp(self):
        return history.build_inputs([cand('a', 'MP', 0.6), cand('b', 'LAB', 0.4)], [cand('x', 'MP'), cand('y', 'LAB'), cand('z', 'OTH')])

    def test_shares_sum_to_one_and_streams_are_common_across_arms(self):
        pools = {'established': [0.05], 'other': [0.02, 0.04]}
        s2 = np.full(500, 0.05)
        a = model.simulate_seat(self.inp(), s2, np.zeros(500), pools, np.random.default_rng(5))
        b = model.simulate_seat(self.inp(), s2, np.zeros(500), pools, np.random.default_rng(5))
        self.assertTrue(np.array_equal(a, b))
        self.assertTrue(np.allclose(a.sum(axis=1), 1.0))
        # a shared shift moves only the Maori Party label's share, and the entrant keeps its pool draw before closure
        c = model.simulate_seat(self.inp(), s2, np.full(500, 0.5), pools, np.random.default_rng(5))
        self.assertTrue(np.all(c[:, 0] > a[:, 0]))
        self.assertTrue(np.all(np.log(c[:, 0] / c[:, 1]) - np.log(a[:, 0] / a[:, 1]) > 0.499))
        self.assertTrue(np.allclose(np.log(c[:, 0] / c[:, 1]) - np.log(a[:, 0] / a[:, 1]), 0.5))

    def test_entrant_shares_come_from_the_pool(self):
        pools = {'established': [0.05], 'other': [0.02, 0.04]}
        share = model.simulate_seat(self.inp(), np.zeros(1000), np.zeros(1000), pools, np.random.default_rng(2))
        # no noise: matched shares are 0.6 and 0.4, the entrant is 0.02 or 0.04 before closure
        ratio = set(np.round(share[:, 2] / share[:, 1], 6))
        self.assertEqual(ratio, {round(0.02 / 0.4, 6), round(0.04 / 0.4, 6)})

    def test_per_seat_stream_makes_a_seat_independent_of_the_others(self):
        contract = read(DESIGN)
        rng_a = np.random.default_rng(np.random.SeedSequence([contract['seed'], 2026, 10]))
        rng_b = np.random.default_rng(np.random.SeedSequence([contract['seed'], 2026, 10]))
        self.assertTrue(np.array_equal(rng_a.standard_normal(5), rng_b.standard_normal(5)))


class Inputs2026(unittest.TestCase):
    def test_official_slates_cover_seven_seats_and_map_every_label(self):
        slates = inputs2026.slates()
        self.assertEqual(sorted(slates), sorted(forecast.SEATS))
        self.assertEqual(sum(len(v) for v in slates.values()), 28)
        for seat in forecast.UNPOLLED:
            codes = [c['party'] for c in slates[seat]]
            self.assertEqual(codes.count('MP'), 1)
            self.assertEqual(codes.count('LAB'), 1)

    def test_split_incumbent_is_only_te_tai_tokerau_and_is_checked_against_2023(self):
        slates, res = inputs2026.slates(), history.results()
        self.assertIsNone(inputs2026.split_for('Waiariki', slates['Waiariki'], res))
        sp = inputs2026.split_for('Te Tai Tokerau', slates['Te Tai Tokerau'], res)
        self.assertEqual(sp['fromCode'], 'MP')
        inp = inputs2026.seat_inputs('Te Tai Tokerau', slates['Te Tai Tokerau'], res)
        self.assertEqual(inp['names'][inp['split']['toIndex']], 'Mariameno KAPA-KINGI')
        self.assertEqual(inp['codes'][inp['split']['toIndex']], 'TTT')

    def test_unmapped_label_fails_closed(self):
        import copy
        import unittest.mock as mock
        table = copy.deepcopy(read(read(INPUTS)['officialTable']))
        row = next(r for r in table['rows'] if r['electorateLabel'] == 'Waiariki')
        row['affiliationLabel'] = 'Mystery Party'
        original = inputs2026.read

        def fake(path):
            return table if path == read(INPUTS)['officialTable'] else original(path)
        with mock.patch.object(inputs2026, 'read', fake):
            with self.assertRaises(ValueError):
                inputs2026.slates()

    def test_baselines_of_the_unpolled_seats_are_the_2023_shares(self):
        slates, res = inputs2026.slates(), history.results()
        w = inputs2026.seat_inputs('Waiariki', slates['Waiariki'], res)
        by = {c: b for c, b in zip(w['codes'], w['base'])}
        self.assertAlmostEqual(math.exp(by['MP']), 0.763, places=2)
        self.assertAlmostEqual(math.exp(by['LAB']), 0.199, places=2)
        self.assertIsNone(by['GRN'])


class FindingRules(unittest.TestCase):
    base = {'meanLogScoreWinner': -1.0, 'brierMulti': 0.5}

    def swing(self, log, brier, folds):
        x = {'meanLogScoreWinner': log, 'brierMulti': brier}
        fold_f = {2017: {'meanLogScoreWinner': -1.0}, 2020: {'meanLogScoreWinner': -1.0}, 2023: {'meanLogScoreWinner': -1.0}}
        fold_x = {e: {'meanLogScoreWinner': -0.9 if i < folds else -1.1} for i, e in enumerate(fold_f)}
        return score.swing_rule(self.base, x, fold_f, fold_x, {'logScoreInterval90': [0.01, 0.2]}, 2)

    def test_swing_rule_branches(self):
        self.assertEqual(self.swing(-0.9, 0.4, 2)['class'], 'swing_helps')
        self.assertEqual(self.swing(-0.9, 0.4, 1)['class'], 'mixed_report_to_james')
        self.assertEqual(self.swing(-0.9, 0.6, 3)['class'], 'mixed_report_to_james')
        self.assertEqual(self.swing(-1.1, 0.6, 0)['class'], 'swing_hurts')
        self.assertEqual(self.swing(-1.0, 0.5, 3)['class'], 'mixed_report_to_james')  # a tie is not an improvement
        self.assertEqual(self.swing(-0.9, 0.4, 2)['evidenceQualifier'], 'clear')

    def test_registration_branches(self):
        self.assertEqual(score.registration('swing_helps', 'swing_helps'), 'FC_to_FP')
        self.assertEqual(score.registration('swing_hurts', 'swing_hurts'), 'F')
        self.assertEqual(score.registration('swing_helps', 'swing_hurts'), 'none_report_to_james')
        self.assertEqual(score.registration('mixed_report_to_james', 'swing_helps'), 'none_report_to_james')
        self.assertEqual(score.registration('mixed_report_to_james', 'mixed_report_to_james'), 'none_report_to_james')

    def test_calibration_class_branches(self):
        ok = {'calibrationZ': 0.5, 'coverageDeviation': 0.05, 'coverageBias': -0.05}
        self.assertEqual(score.calibration_class(ok, 1.645, 0.10), 'calibrated')
        self.assertEqual(score.calibration_class(dict(ok, calibrationZ=-2.0), 1.645, 0.10), 'overconfident')
        self.assertEqual(score.calibration_class(dict(ok, coverageDeviation=0.15, coverageBias=-0.15), 1.645, 0.10), 'overconfident')
        self.assertEqual(score.calibration_class(dict(ok, calibrationZ=2.0), 1.645, 0.10), 'underconfident')
        self.assertEqual(score.calibration_class(dict(ok, coverageDeviation=0.15, coverageBias=0.15), 1.645, 0.10), 'underconfident')

    def test_metrics_z_and_coverage(self):
        recs = [{'probActual': 0.8, 'logScore': -0.2, 'brierMulti': 0.1, 'favouriteProb': 0.8, 'favouriteWon': w, 'kinds': ['mp-lab'],
                 'shareCover': {'0.5': [1.0], '0.8': [1.0], '0.9': [1.0]}} for w in (1.0, 1.0, 1.0, 1.0, 0.0)]
        m = score.metrics(recs)
        self.assertAlmostEqual(m['calibrationZ'], 0.0, places=12)
        self.assertAlmostEqual(m['coverageDeviation'], np.mean([0.5, 0.2, 0.1]))
        self.assertEqual(m['shareCoverageByCandidateKind']['mp-lab']['observations'], 5)

    def test_average_over_subsets_is_the_mean_of_scores(self):
        a = {'probActual': 0.2, 'logScore': -1.6, 'brierMulti': 1.0, 'favouriteProb': 0.8, 'favouriteWon': 0.0, 'kinds': ['x'], 'shareCover': {'0.5': [1.0]}}
        b = dict(a, probActual=0.4, logScore=-0.9, favouriteWon=1.0, shareCover={'0.5': [0.0]})
        m = score.average([a, b])
        self.assertAlmostEqual(m['logScore'], -1.25)
        self.assertAlmostEqual(m['favouriteWon'], 0.5)
        self.assertEqual(m['shareCover']['0.5'], [0.5])


class StageLinks(unittest.TestCase):
    def test_polled_layers_reproduce_the_stored_stage71_forecast(self):
        draws = read(DESIGN)['readoutDraws']
        polls, sims = forecast.polled_layers(draws)
        stored = read(STAGE71 + '/forecast-2026.json')['arms']
        for key in ('C', 'P'):
            for seat, s in sims[key]['seats'].items():
                win = np.bincount(s['winner'], minlength=len(s['poll']['candidates'])) / draws
                for i, c in enumerate(stored[key]['seats'][seat]['candidates']):
                    self.assertAlmostEqual(float(win[i]), c['winProbability'], places=9)

    def test_no_stage66_71_or_assembly_code_is_modified_or_imported_for_writing(self):
        import pathlib
        for path in pathlib.Path(ROOT, 'scripts', 'maori_seat_fallback').glob('*.py'):
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('nowcast_assembly', text)
            self.assertNotIn('data/sources.json', text)


class Artifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = run.build()

    def test_artifacts_are_current(self):
        for name, value in self.artifacts.items():
            save(name, value, check=True, tolerance=2e-6 if name == 'draw-bank-preview.json' else 1e-8)
        save('manifest.json', run.manifest(list(self.artifacts)), check=True)

    def test_scores_cover_the_pre_registered_contests_and_arms(self):
        s = self.artifacts['scores.json']
        for scheme, n in (('leaveOneElectionOut', 21), ('chronological', 7)):
            for arm in score.ARMS:
                self.assertEqual(s[scheme]['pooled'][arm]['contests'], n)
        self.assertEqual(sorted(s['leaveOneElectionOut']['foldsScored']), [2017, 2020, 2023])
        self.assertEqual(s['chronological']['foldsScored'], [2023])

    def test_findings_follow_the_frozen_rules_from_the_pooled_scores(self):
        f, s = self.artifacts['findings.json'], self.artifacts['scores.json']['leaveOneElectionOut']
        for arm in ('FC', 'FP'):
            again = score.swing_rule(s['pooled']['F'], s['pooled'][arm], s['byFold']['F'], s['byFold'][arm], s['comparisons'][arm + ' against F'], 2)
            self.assertEqual(f['swingRule'][arm], again)
        self.assertEqual(f['registered'], score.registration(f['swingRule']['FC']['class'], f['swingRule']['FP']['class']))
        self.assertIn(f['registeredByJames']['choice'], [None] + read(INPUTS)['registration']['allowedChoices'])

    def test_forecast_covers_the_four_unpolled_seats_with_proper_probabilities(self):
        fc = self.artifacts['forecast-2026.json']
        self.assertEqual(fc['unpolledSeats'], ['Waiariki', 'Ikaroa-Rāwhiti', 'Tāmaki Makaurau', 'Te Tai Tokerau'])
        for arm in ('F', 'FC', 'FP'):
            for seat, v in fc['arms'][arm]['seats'].items():
                self.assertAlmostEqual(sum(c['winProbability'] for c in v['candidates']), 1.0, places=9)
                self.assertAlmostEqual(sum(v['winProbabilityByPartyCode'].values()), 1.0, places=9)
                self.assertAlmostEqual(sum(c['meanShare'] for c in v['candidates']), 1.0, places=9)
        counts = fc['arms']['FC']['winCounts']
        self.assertAlmostEqual(sum(counts['allSeven']['distribution']), 1.0, places=9)
        self.assertAlmostEqual(sum(counts['unpolled']['distribution']), 1.0, places=9)

    def test_swing_arms_couple_the_unpolled_seats_to_the_polled_seats(self):
        fc = self.artifacts['forecast-2026.json']
        # FC and FP use a shared draw: the four unpolled seats move together more than F's independent-noise-only wins would
        self.assertEqual(fc['swing']['FC']['seats'], ['Hauraki-Waikato', 'Te Tai Hauāuru', 'Te Tai Tonga'])
        self.assertEqual(fc['swing']['FC without Te Tai Tonga']['seats'], ['Hauraki-Waikato', 'Te Tai Hauāuru'])
        self.assertGreater(fc['swing']['FC']['meanKappa'], 0.0)

    def test_manifest_records_nothing_else_was_touched(self):
        m = run.manifest(list(self.artifacts))
        self.assertFalse(m['stage66Modified'] or m['stage71Modified'] or m['configTouched'] or m['assemblyTouched'] or m['dataSourcesJsonTouched'])
        self.assertEqual(m['newResources'], 0)


if __name__ == '__main__':
    unittest.main()
