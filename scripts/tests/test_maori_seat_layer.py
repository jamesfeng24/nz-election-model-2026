"""Stage66 Maori seat layer: frozen design, official results, calibration arithmetic, simulation properties and artifact currency."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.maori_seat_layer import data, fit, run, simulate, verify
from scripts.maori_seat_layer.common import (DESIGN, PREFIX, ROOT, SEATS, YEARS, CURRENT_POLLS, fold, group, read, digest)


def poll(seat, cands, end='2026-09-24', pid=None):
    return {'id': pid or 'x-' + seat + end, 'seat': seat, 'fieldworkEnd': end,
            'candidates': [{'name': n, 'party': p, 'pollPercent': v} for n, p, v in cands]}


PARAMS = {'sigma2': 0.05, 'sigma2Dof': 20, 'tau2': 0.06, 'tauDof': 4, 'bias': 0.0, 'unnamedShares': [0.0, 0.03, 0.06]}


class FrozenDesign(unittest.TestCase):
    def test_contract_pins_the_registered_rules(self):
        c = read(DESIGN)
        self.assertEqual((c['seed'], c['draws'], c['previewDraws']), (2026066, 100000, 500))
        self.assertEqual(c['biasAdoption']['loeoLogScoreImprovementNats'], 1.0)
        self.assertEqual(c['biasAdoption']['minimumSameSignElections'], 3)
        self.assertEqual(c['sigma']['degreesOfFreedom'], 20)
        self.assertEqual(c['sigma']['contrastPolls'], 24)
        self.assertFalse(c['partyVoteUsed'])
        self.assertFalse(c['publication'])
        self.assertFalse(c['generalElectorateCalibrationTouched'])
        self.assertEqual(c['diagnostics'], {'otherContrastFlagRatio': 1.5, 'horizonCutDays': 21, 'horizonFlagWinnerProbabilityShift': 0.10})

    def test_groups_and_name_folding(self):
        self.assertEqual([group(p) for p in ('MP', 'LAB', 'MANA', 'GRN', 'IND')], ['MP', 'LAB', 'OTH', 'OTH', 'OTH'])
        self.assertEqual(fold('Te Tai Hauāuru'), fold('Te Tai Hauauru'))


class OfficialResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = read(PREFIX + '/historical-results.json')['years']

    def test_every_election_has_the_seven_seats_and_shares_sum_to_one(self):
        for year in YEARS:
            self.assertEqual(sorted(self.results[str(year)]), sorted(SEATS))
            for seat, r in self.results[str(year)].items():
                self.assertAlmostEqual(sum(c['share'] for c in r['candidates']), 1.0, places=12)
                self.assertEqual(sum(c['votes'] for c in r['candidates']), r['validCandidateVotes'])

    def test_known_official_figures(self):
        ttt = {c['name']: c['votes'] for c in self.results['2023']['Te Tai Tonga']['candidates']}
        self.assertEqual(ttt['FERRIS, Tākuta'] - ttt['TIRIKATENE, Rino'], 2824)
        hw = {c['party']: c['votes'] for c in self.results['2023']['Hauraki-Waikato']['candidates']}
        self.assertEqual((hw['MP'], hw['LAB']), (12939, 10028))
        self.assertEqual(self.results['2017']['Waiariki']['winner'], 'COFFEY, Tamati Gerald')


class Calibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = data.calibration_rows()

    def test_inventory(self):
        self.assertEqual(len(self.rows), 25)
        self.assertEqual({r['year'] for r in self.rows}, set(YEARS))
        self.assertEqual(sum(r['contrastD'] is not None for r in self.rows), 24)
        self.assertEqual([r['id'] for r in self.rows if r['contrastD'] is None], ['2017-te-tai-tokerau'])
        self.assertTrue(all(r['winnerNamed'] for r in self.rows))
        for r in self.rows:
            self.assertAlmostEqual(sum(c['pollClosed'] for c in r['candidates']), 1.0, places=12)
            self.assertAlmostEqual(sum(c['resultClosed'] for c in r['candidates']), 1.0, places=12)
            self.assertGreaterEqual(r['unnamedShare'], 0.0)

    def test_contrast_matches_hand_arithmetic(self):
        r = next(x for x in self.rows if x['id'] == '2023-hauraki-waikato')
        poll_mp, poll_lab = 32 / 68, 36 / 68
        res_mp, res_lab = 12939 / (12939 + 10028), 10028 / (12939 + 10028)
        self.assertAlmostEqual(r['contrastD'], math.log(res_mp / res_lab) - math.log(poll_mp / poll_lab), places=12)
        self.assertAlmostEqual(r['unnamedShare'], 1220 / 24187, places=12)

    def test_zero_percent_candidate_is_dropped_from_the_named_set(self):
        r = next(x for x in self.rows if x['id'] == '2020-ikaroa-rawhiti')
        self.assertEqual(len(r['candidates']), 4)
        self.assertNotIn('THURSTON, Kelly', [c['name'] for c in r['candidates']])

    def test_ambiguous_or_missing_candidates_fail_loudly(self):
        official = [{'name': 'SMITH, A', 'party': 'LAB', 'votes': 1}, {'name': 'JONES, B', 'party': 'LAB', 'votes': 1}]
        with self.assertRaises(ValueError):
            data.resolve({'name': None, 'party': 'LAB', 'pollPercent': 1}, official)
        with self.assertRaises(ValueError):
            data.resolve({'name': 'Zed Nobody', 'party': 'LAB', 'pollPercent': 1}, official)
        self.assertEqual(data.resolve({'name': 'Anne Smith', 'party': 'LAB', 'pollPercent': 1}, official)['name'], 'SMITH, A')


class Estimation(unittest.TestCase):
    def test_sigma_tau_and_floor(self):
        groups = {2014: [0.1, 0.3], 2017: [-0.1, 0.1, 0.0]}
        s2, dof = fit.sigma2(groups)
        self.assertEqual(dof, 3)
        self.assertAlmostEqual(s2, (0.02 + 0.02) / 3 / 2, places=12)
        self.assertEqual(fit.tau2({2014: [0.0, 0.0], 2017: [0.0, 0.0]}, 1.0, 0.0), 0.0)
        self.assertAlmostEqual(fit.tau2({1: [0.5, 0.5], 2: [-0.5, -0.5]}, 0.0, 0.0), 0.25, places=12)

    def test_mvn_logpdf_one_dimension(self):
        self.assertAlmostEqual(fit.mvn_logpdf([0.3], 0.1, 0.2, 0.1), -0.5 * (math.log(2 * math.pi * 0.5) + 0.04 / 0.5), places=12)

    def test_bias_rule_adopts_a_consistent_shift_and_rejects_noise(self):
        rule = read(DESIGN)['biasAdoption']
        rng = np.random.default_rng(1)
        shifted = {e: list(0.8 + 0.05 * rng.standard_normal(6)) for e in range(4)}
        self.assertTrue(fit.adopt_bias(shifted, rule)['adopted'])
        flat = {e: list(0.0 + 0.3 * rng.standard_normal(6)) for e in range(4)}
        self.assertFalse(fit.adopt_bias(flat, rule)['adopted'])
        mixed = {0: [0.8, 0.9], 1: [0.8, 0.7], 2: [-0.8, -0.9], 3: [-0.8, -0.7]}
        self.assertFalse(fit.adopt_bias(mixed, rule)['adopted'])

    def test_the_registered_fit_is_recorded_and_bias_is_not_adopted(self):
        f = read(PREFIX + '/calibration.json')['fit']
        self.assertFalse(f['biasAdoption']['adopted'])
        self.assertEqual(f['bias'], 0.0)
        self.assertEqual((f['rows'], f['contrastPolls'], f['sigma2Dof']), (25, 24, 20))
        self.assertAlmostEqual(f['sigma'] ** 2, f['sigma2'], places=12)
        self.assertGreater(f['otherContrasts']['ratioTo2Sigma2'], 1.5)


class Simulation(unittest.TestCase):
    def test_zero_noise_returns_the_closed_poll(self):
        polls = {'Waiariki': poll('Waiariki', [('A', 'LAB', 30), ('B', 'MP', 10), ('C', 'GRN', 10)])}
        p = dict(PARAMS, sigma2=0.0, tau2=0.0, unnamedShares=[0.0])
        sim = simulate.simulate(polls, p, 50, 1)
        s = sim['seats']['Waiariki']
        np.testing.assert_allclose(s['share'][0], [0.6, 0.2, 0.2], atol=1e-12)
        self.assertTrue((s['winner'] == 0).all())

    def test_shares_sum_with_the_unnamed_mass_and_are_deterministic(self):
        polls = {'Waiariki': poll('Waiariki', [('A', 'LAB', 30), ('B', 'MP', 25)])}
        a = simulate.simulate(polls, PARAMS, 400, 7)
        b = simulate.simulate(polls, PARAMS, 400, 7)
        np.testing.assert_array_equal(a['seats']['Waiariki']['share'], b['seats']['Waiariki']['share'])
        total = a['seats']['Waiariki']['share'].sum(axis=1)
        self.assertTrue(set(np.round(1 - total, 12)) <= {0.0, 0.03, 0.06})

    def test_seat_streams_are_independent_of_which_other_seats_are_polled(self):
        one = {'Waiariki': poll('Waiariki', [('A', 'LAB', 30), ('B', 'MP', 25)])}
        two = dict(one, **{'Te Tai Tonga': poll('Te Tai Tonga', [('C', 'LAB', 30), ('D', 'MP', 17), ('E', 'GRN', 16), ('F', 'IND', 15)])})
        a, b = simulate.simulate(one, PARAMS, 300, 3), simulate.simulate(two, PARAMS, 300, 3)
        np.testing.assert_array_equal(a['seats']['Waiariki']['share'], b['seats']['Waiariki']['share'])
        np.testing.assert_array_equal(a['z'], b['z'])

    def test_shared_shift_moves_all_mp_candidates_together(self):
        polls = {'Waiariki': poll('Waiariki', [('A', 'LAB', 30), ('B', 'MP', 30)]), 'Te Tai Tonga': poll('Te Tai Tonga', [('C', 'LAB', 30), ('D', 'MP', 30)])}
        sim = simulate.simulate(polls, dict(PARAMS, sigma2=1e-12, tau2=0.5, unnamedShares=[0.0]), 4000, 11)
        a, b = sim['seats']['Waiariki']['share'][:, 1], sim['seats']['Te Tai Tonga']['share'][:, 1]
        self.assertGreater(np.corrcoef(a, b)[0, 1], 0.95)
        self.assertGreater(np.corrcoef(sim['z'], a)[0, 1], 0.9)
        indep = simulate.simulate(polls, dict(PARAMS, sigma2=1e-12, tau2=0.0, unnamedShares=[0.0]), 4000, 11)
        np.testing.assert_allclose(indep['seats']['Waiariki']['share'][:, 1], 0.5, atol=1e-5)

    def test_a_positive_bias_helps_the_mp_candidate(self):
        polls = {'Waiariki': poll('Waiariki', [('A', 'LAB', 30), ('B', 'MP', 25)])}
        base = simulate.summarise(simulate.simulate(polls, PARAMS, 20000, 5), 20000)['seats']['Waiariki']['candidates']
        up = simulate.summarise(simulate.simulate(polls, dict(PARAMS, bias=0.5), 20000, 5), 20000)['seats']['Waiariki']['candidates']
        self.assertGreater(up[1]['winProbability'], base[1]['winProbability'] + 0.1)

    def test_win_probabilities_sum_to_one(self):
        polls = {'Te Tai Tonga': poll('Te Tai Tonga', [('C', 'LAB', 30), ('D', 'MP', 17), ('E', 'GRN', 16), ('F', 'IND', 15)])}
        s = simulate.summarise(simulate.simulate(polls, PARAMS, 2000, 2), 2000)
        self.assertAlmostEqual(sum(c['winProbability'] for c in s['seats']['Te Tai Tonga']['candidates']), 1.0, places=12)
        self.assertAlmostEqual(sum(s['maoriPartyWinsAmongPolledSeats']['distribution']), 1.0, places=12)


class CurrentPollsData(unittest.TestCase):
    def write(self, polls):
        handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        json.dump({'polls': polls}, handle)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink())
        return handle.name

    def test_latest_poll_per_seat_is_used_and_earlier_ones_are_reported(self):
        old = poll('Waiariki', [('A', 'LAB', 30), ('B', 'MP', 25)], '2026-09-20', 'old')
        new = poll('Waiariki', [('A', 'LAB', 20), ('B', 'MP', 35)], '2026-10-05', 'new')
        latest, superseded, _ = simulate.current_polls(self.write([new, old]))
        self.assertEqual((latest['Waiariki']['id'], superseded), ('new', ['old']))

    def test_unknown_seat_single_candidate_and_duplicates_are_rejected(self):
        for bad in (poll('Nowhere', [('A', 'LAB', 1), ('B', 'MP', 1)]), poll('Waiariki', [('A', 'LAB', 1)]),
                    poll('Waiariki', [('A', 'LAB', 1), ('A', 'MP', 1)])):
            with self.assertRaises(ValueError):
                simulate.current_polls(self.write([bad]))

    def test_the_three_published_polls_are_in_and_four_seats_are_unpolled(self):
        latest, superseded, doc = simulate.current_polls()
        self.assertEqual(sorted(latest), ['Hauraki-Waikato', 'Te Tai Hauāuru', 'Te Tai Tonga'])
        self.assertEqual(superseded, [])
        self.assertEqual(sorted(doc['unpolledSeats']), sorted(set(SEATS) - set(latest)))


class Verification(unittest.TestCase):
    def test_transcriptions_match_the_preserved_bytes(self):
        self.assertEqual(verify.historical(), [])
        self.assertEqual(verify.current(), [])

    def test_number_and_run_matching_reject_wrong_values(self):
        self.assertEqual(verify.number(' 60.1 '), 60.1)
        self.assertIsNone(verify.number('N/A'))
        row = ['Maori TV-Reid Research', '2017', '39', 'N/A', '52', '9.1']
        self.assertTrue(verify.contiguous(row, [39, 52, 9.1]))
        self.assertFalse(verify.contiguous(row, [39, 53]))
        self.assertFalse(verify.contiguous(row, [52, 39]))


class ArtifactsAndBoundaries(unittest.TestCase):
    def test_committed_artifacts_equal_a_fresh_build(self):
        from scripts.maori_seat_layer.common import equivalent
        for name, value in run.build().items():
            tol = 2e-6 if name == 'draw-bank-preview.json' else run.TOLERANCE
            self.assertTrue(equivalent(read(PREFIX + '/' + name), value, tol), name)

    def test_unpolled_seats_have_no_values_and_nothing_is_published(self):
        f = read(PREFIX + '/forecast-2026.json')
        self.assertEqual(f['unpolledSeats'], ['Ikaroa-Rāwhiti', 'Tāmaki Makaurau', 'Te Tai Tokerau', 'Waiariki'])
        self.assertEqual(set(f['arms']['default']['seats']), set(f['polledSeats']))
        self.assertIn('INTERNAL', f['label'])
        self.assertIn('PREVIEW', read(PREFIX + '/draw-bank-preview.json')['label'])
        self.assertEqual(read(PREFIX + '/manifest.json')['dataSourcesJsonTouched'], False)

    def test_post_hoc_arms_are_labelled_and_default_is_the_registered_model(self):
        arms = read(PREFIX + '/forecast-2026.json')['arms']
        self.assertTrue(arms['curiaEraBias']['description'].startswith('POST HOC'))
        self.assertTrue(arms['widerOtherNoise']['description'].startswith('POST HOC'))
        self.assertEqual(arms['default']['flaggedShiftOver0.10'], [])

    def test_registry_hashes_match_and_sources_json_is_not_extended(self):
        reg = read(PREFIX + '/source-registry.json')['sources']
        self.assertEqual(len(reg), 13)
        for r in reg:
            self.assertEqual(digest(r['rawPath']), r['sha256'])
        existing = {s['id'] for s in read('data/sources.json')['sources']} if isinstance(read('data/sources.json'), dict) and 'sources' in read('data/sources.json') else set()
        self.assertFalse(existing & {r['id'] for r in reg})


if __name__ == '__main__':
    unittest.main()
