"""Stage71 Maori seat calibration: frozen design, estimation arithmetic, reproduction of Stage66, the finding rule and artifact currency."""
import math
import unittest

import numpy as np

from scripts.maori_seat_calibration import model, run, score
from scripts.maori_seat_calibration.common import DESIGN, DESIGN_DOC, ROOT, STAGE66, era, read, save
from scripts.maori_seat_layer.data import calibration_rows


def row(year, pollster, cands, d=None):
    """cands: (name, party, group, pollClosed, resultClosed)."""
    return {'id': '%d-x' % year, 'year': year, 'pollster': pollster, 'contrastD': d,
            'candidates': [{'name': n, 'party': p, 'group': g, 'pollClosed': q, 'resultClosed': v} for n, p, g, q, v in cands]}


class FrozenDesign(unittest.TestCase):
    def test_contract_pins_the_registered_rules(self):
        c = read(DESIGN)
        self.assertEqual((c['seed'], c['draws'], c['bootstrapReplicates']), (2026071, 100000, 1000))
        self.assertEqual(c['findingOrder'], ['insufficient_data', 'mixed_report_to_james', 'not_helpful', 'restored', 'improves_not_restored'])
        self.assertEqual(c['calibrationZThreshold'], 1.645)
        self.assertEqual(c['schemes']['chronological'], {'2017': [2014], '2020': [2014, 2017], '2023': [2014, 2017, 2020]})
        self.assertFalse(c['adopted'] or c['publication'] or c['generalElectorateTouched'] or c['dataSourcesJsonTouched'])
        self.assertTrue(c['stage66ReadOnly'])

    def test_design_document_states_the_rule_and_the_cap(self):
        text = (ROOT / DESIGN_DOC).read_text(encoding='utf-8')
        for phrase in ('insufficient_data', 'improves_not_restored', 'suggestive_not_adopted', 'penalty-free', 'Disclosure about what was known'):
            self.assertIn(phrase, text)


class Estimation(unittest.TestCase):
    def test_era_follows_the_pollster(self):
        self.assertEqual(era('Maori TV-Reid Research'), 'Reid')
        self.assertEqual((era('Maori TV-Curia'), era('Whakaata Maori-Curia')), ('Curia', 'Curia'))

    def test_single_two_candidate_poll_closed_form(self):
        # K = 2: x = D, covariance 2 sigma^2 + tau^2, so lambda_hat = D^2 / (2 sigma^2 + tau^2)
        r = row(2020, 'Curia', [('a', 'MP', 'MP', 0.5, 0.6), ('b', 'LAB', 'LAB', 0.5, 0.4)])
        D = math.log(0.6 / 0.4)
        unit = model.make_unit(2020, 'Curia', [r])
        est = {'sigma2': 0.05, 'tau2': 0.03, 'bias': [0.0]}
        self.assertAlmostEqual(model.lambda_hat([unit], est), D ** 2 / (2 * 0.05 + 0.03), places=12)
        est['bias'] = [0.2]
        self.assertAlmostEqual(model.lambda_hat([unit], est), (D - 0.2) ** 2 / (2 * 0.05 + 0.03), places=12)

    def test_lambda_is_invariant_to_candidate_order(self):
        rows = calibration_rows()
        units = model.units_from_rows(rows, [2014, 2017, 2020, 2023])
        est = model.estimate(units, False)
        base = model.lambda_hat(units, est)
        flipped = [dict(u, polls=[dict(r, candidates=list(reversed(r['candidates']))) for r in u['polls']]) for u in units]
        self.assertAlmostEqual(model.lambda_hat(flipped, est), base, places=10)

    def test_control_estimates_equal_stage66(self):
        rows = calibration_rows()
        est = model.estimate(model.units_from_rows(rows, [2014, 2017, 2020, 2023]), False)
        cal = read(STAGE66 + '/calibration.json')['fit']
        self.assertAlmostEqual(est['sigma2'], cal['sigma2'], places=12)
        self.assertAlmostEqual(est['tau2'], cal['tau2'], places=12)
        self.assertEqual(est['sigma2Dof'], cal['sigma2Dof'])

    def test_era_bias_is_leave_self_out_and_ignores_duplicates_of_the_same_election(self):
        def u(year, era_name, d):
            return {'year': year, 'era': era_name, 'polls': [{'contrastD': x} for x in d]}
        units = [u(2014, 'Reid', [0.0, 0.2]), u(2017, 'Reid', [-0.4]), u(2020, 'Curia', [0.3]), u(2020, 'Curia', [0.3])]
        self.assertAlmostEqual(model.era_bias(units, 0), -0.4)
        self.assertAlmostEqual(model.era_bias(units, 1), 0.1)
        self.assertEqual(model.era_bias(units, 2), 0.0)  # its twin is the same source election
        self.assertAlmostEqual(model.era_bias_for(units[:2], 'Reid'), -0.15)
        self.assertEqual(model.era_bias_for(units[:2], 'Curia'), 0.0)

    def test_bootstrap_is_deterministic_and_counts_skips(self):
        rows = calibration_rows()
        units = model.units_from_rows(rows, [2014, 2017, 2020])
        a, sa = model.bootstrap(units, False, 30, np.random.default_rng(1))
        b, sb = model.bootstrap(units, False, 30, np.random.default_rng(1))
        self.assertTrue(np.array_equal(a, b) and sa == sb)
        self.assertEqual(len(a) + sa, 30)


class Scoring(unittest.TestCase):
    def test_training_sets_are_strictly_earlier_or_all_others(self):
        rows = calibration_rows()
        self.assertEqual(score.training_sets(rows, 'chronological'), {2017: [2014], 2020: [2014, 2017], 2023: [2014, 2017, 2020]})
        self.assertEqual(score.training_sets(rows, 'leaveOneElectionOut')[2020], [2014, 2017, 2023])

    def test_arm_c_reproduces_the_stored_stage66_backtest(self):
        rows = calibration_rows()
        stored = read(STAGE66 + '/calibration.json')['fit']['backtest']['zero']
        got = score.reproduce_stage66_control(rows, read(STAGE66 + '/design-contract.json')['seed'], 20000, 1e-4)
        self.assertAlmostEqual(got['meanPredictedLeaderWin'], stored['meanPredictedLeaderWin'], places=9)
        self.assertAlmostEqual(got['brierLeaderWins'], stored['brierLeaderWins'], places=9)
        self.assertAlmostEqual(got['meanLogScoreActualWinner'], stored['meanLogScoreActualWinner'], places=9)

    def test_calibration_z_and_metrics(self):
        recs = [{'leaderWinProbability': 0.8, 'leaderWon': w, 'brierLeader': (0.8 - w) ** 2, 'brierMulti': 0.0, 'logScoreWinner': -0.1,
                 'shareCover': {'0.5': [True], '0.8': [True], '0.9': [True]}} for w in (True, True, True, True, False)]
        m = score.metrics(recs)
        self.assertAlmostEqual(m['meanPredictedLeaderWin'], 0.8)
        self.assertAlmostEqual(m['calibrationZ'], 0.0, places=12)
        self.assertEqual(m['leaderWins'], 4)

    def _case(self, lo_p05, brier_p, log_p, z_p, dev_p, fold_p, skipped=0):
        c = {'brierLeader': 0.2, 'meanLogScoreWinner': -0.6, 'calibrationZ': -3.0, 'coverageDeviation': 0.1}
        p = {'brierLeader': brier_p, 'meanLogScoreWinner': log_p, 'calibrationZ': z_p, 'coverageDeviation': dev_p}
        fits = {e: {'P': {'lambdaInterval': {'p05': lo_p05, 'p95': 9.0}, 'bootstrapSkipped': skipped, 'bootstrapReplicates': 100}} for e in (2020, 2023)}
        fold_c = {e: {'brierLeader': 0.2} for e in (2017, 2020, 2023)}
        fold_pp = {e: {'brierLeader': b} for e, b in zip((2017, 2020, 2023), fold_p)}
        return score.classify(c, p, fold_c, fold_pp, fits, 0.05, 1.645, 2)

    def test_finding_rule_branches(self):
        self.assertEqual(self._case(0.9, 0.1, -0.4, -1.0, 0.05, (0.1, 0.1, 0.1)), 'insufficient_data')
        self.assertEqual(self._case(1.5, 0.1, -0.7, -1.0, 0.05, (0.1, 0.1, 0.1)), 'mixed_report_to_james')
        self.assertEqual(self._case(1.5, 0.3, -0.7, -3.0, 0.05, (0.3, 0.3, 0.3)), 'not_helpful')
        self.assertEqual(self._case(1.5, 0.1, -0.4, -1.0, 0.05, (0.1, 0.1, 0.1)), 'restored')
        self.assertEqual(self._case(1.5, 0.1, -0.4, -1.7, 0.05, (0.1, 0.1, 0.1)), 'improves_not_restored')  # z outside 1.645
        self.assertEqual(self._case(1.5, 0.1, -0.4, -1.0, 0.2, (0.1, 0.1, 0.1)), 'improves_not_restored')  # coverage guard
        self.assertEqual(self._case(1.5, 0.1, -0.4, -1.0, 0.05, (0.1, 0.3, 0.3)), 'improves_not_restored')  # fewer than two folds better
        self.assertEqual(self._case(1.5, 0.1, -0.4, -1.0, 0.05, (0.1, 0.1, 0.1), skipped=10), 'insufficient_data')


class Artifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = run.build()

    def test_artifacts_are_current(self):
        for name, value in self.artifacts.items():
            save(name, value, check=True)
        save('manifest.json', run.manifest(list(self.artifacts)), check=True)

    def test_control_arm_equals_the_stage66_forecast_and_unpolled_seats_are_absent(self):
        forecast = self.artifacts['forecast-2026.json']
        s66 = read(STAGE66 + '/forecast-2026.json')['arms']['default']
        for seat, v in forecast['arms']['C']['seats'].items():
            for c, d in zip(v['candidates'], s66['seats'][seat]['candidates']):
                self.assertAlmostEqual(c['winProbability'], d['winProbability'], places=12)
        self.assertEqual(sorted(forecast['arms']['C']['seats']), sorted(s66['seats']))
        self.assertEqual(len(forecast['arms']['C']['seats']), 3)

    def test_finding_matches_the_pooled_scores_and_nothing_is_adopted(self):
        f = self.artifacts['findings.json']
        h = f['headline']
        self.assertIn(h['finding'], read(DESIGN)['findingOrder'])
        self.assertEqual(h['polls'], 21)
        self.assertEqual(h['eraBiasVsInflation']['finding'] in read(DESIGN)['pbCap'], True)
        manifest = run.manifest(list(self.artifacts))
        self.assertFalse(manifest['stage66Modified'] or manifest['dataSourcesJsonTouched'])
        scores = self.artifacts['scores.json']
        self.assertLess(scores['stage66Reproduction']['maxAbsoluteGap'], 1e-9)
        self.assertEqual(len(scores['chronological']['pollRecords']['C']), 21)
        self.assertEqual(len(scores['leaveOneElectionOut']['pollRecords']['C']), 25)


if __name__ == '__main__':
    unittest.main()
