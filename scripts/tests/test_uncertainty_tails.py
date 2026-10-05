"""Behavioural safeguards for the single frozen Stage46 uncertainty correction."""
from copy import deepcopy
import math
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import expit, softmax
from scipy.stats import norm, t

from scripts.uncertainty_tails import construction, estimation, integration, metrics, simulation, streams
from scripts.uncertainty_tails.common import CONTROL, INVENTORY, PREFIX, read


def scales(shared=.1, seat=.2):
    return {direction: {'shared': shared, 'seat': seat} for direction in ('balance', 'mass', 'within')}


def fixture_row(layer='candidate', seat='synthetic-a', year=2014):
    return {'layer': layer, 'targetElectorateId': seat, 'targetYear': year,
            'groups': ['national', 'labour', 'other', 'other'],
            'ids': ['national-option', 'labour-option', 'green-option', 'small-option'],
            'ballotGroupKeys': ['nationalparty', 'labourparty', 'greenparty', 'smallparty'],
            'features': [{'group': tag} for tag in ['nationalparty', 'labourparty', 'greenparty', 'smallparty']],
            'mean': [.4, .3, .2, .1], 'actual': [.4, .3, .2, .1]}


def training_rows():
    rows = []
    for index, error in enumerate([-.4, -.2, 0., .2, .4, 1.5]):
        row = fixture_row(seat=str(index))
        ratio = expit(math.log(.4 / .3) + error)
        row['actual'] = [.7 * ratio, .7 * (1. - ratio), .2, .1]
        rows.append(row)
    return rows


class CentralScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specification = read(PREFIX + '/specification.json')

    def test_prior_central_quantile_conversion_distinguishes_scale_and_sd(self):
        fit = estimation.central_fit(training_rows(), 2014, self.specification)
        self.assertEqual(fit['trainingYears'], [])
        self.assertEqual(fit['status'], 'prior_only')
        self.assertEqual(fit['nu'], 4)
        self.assertFalse(fit['nuEstimated'])
        self.assertAlmostEqual(fit['pooledMAD'], .35 * .6744897501960817, places=14)
        self.assertAlmostEqual(fit['studentScale'], fit['pooledMAD'] / .7406970841282597, places=14)
        self.assertAlmostEqual(fit['gaussianSD'], .35, places=14)
        self.assertAlmostEqual(fit['studentSD'], fit['studentScale'] * math.sqrt(2.), places=14)
        self.assertGreater(fit['studentSD'], fit['gaussianSD'])
        self.assertEqual(t.stats(fit['nu'], moments='v'), 2.)

    def test_earlier_only_mad_retains_all_seats_and_does_not_supply_bias(self):
        rows = training_rows()
        future = fixture_row(year=2020, seat='future')
        before = estimation.central_fit(rows + [future], 2017, self.specification)
        changed = deepcopy(future)
        changed['actual'] = [.98, .005, .005, .01]
        self.assertEqual(before, estimation.central_fit(rows + [changed], 2017, self.specification))
        raw = [math.log((row['actual'][0] + 1e-6) / (row['actual'][1] + 1e-6))
               - math.log((row['mean'][0] + 1e-6) / (row['mean'][1] + 1e-6)) for row in rows]
        shared = math.fsum(raw) / len(raw)
        centered = sorted(value - shared for value in raw)
        median = centered[(len(centered) - 1) // 2]
        deviations = sorted(abs(value - median) for value in centered)
        mad = deviations[(len(deviations) - 1) // 2]
        moment = before['moments'][0]
        self.assertEqual(moment['records'], len(rows))
        self.assertTrue(moment['allObservationsRetained'])
        self.assertAlmostEqual(moment['sharedEffect'], shared, places=14)
        self.assertAlmostEqual(moment['median'], median, places=14)
        self.assertAlmostEqual(moment['mad'], mad, places=14)
        self.assertNotAlmostEqual(moment['median'], 0.)
        self.assertNotIn('bias', before)
        pooled_squared = (mad ** 2 + 3 * (.35 * norm.ppf(.75)) ** 2) / 4
        self.assertAlmostEqual(before['pooledMAD'] ** 2, pooled_squared, places=14)
        self.assertEqual(before['trainingIds'], [row['targetElectorateId'] for row in rows])

    def test_elections_have_equal_scale_weight_despite_seat_count(self):
        first = training_rows()
        second = [dict(row, targetYear=2017, targetElectorateId='later-' + row['targetElectorateId'])
                  for row in training_rows()]
        original = estimation.central_fit(first + second, 2020, self.specification)
        duplicated = [dict(row, targetElectorateId=row['targetElectorateId'] + '-copy-' + str(copy))
                      for copy in range(3) for row in second]
        expanded = estimation.central_fit(first + duplicated, 2020, self.specification)
        for field in ['pooledMAD', 'studentScale', 'studentSD', 'gaussianSD']:
            self.assertAlmostEqual(original[field], expanded[field], places=14)

    def test_missing_earlier_major_balance_remains_missing_and_uses_prior(self):
        absent = fixture_row()
        absent['groups'][0] = 'other'
        fit = estimation.central_fit([absent], 2017, self.specification)
        self.assertEqual(fit['moments'], [])
        self.assertEqual(fit['status'], 'prior_only')
        self.assertAlmostEqual(fit['gaussianSD'], .35, places=14)
        self.assertAlmostEqual(fit['centralHistoricalSquaredContribution'], 0., places=14)

    def test_build_changes_only_candidate_seat_balance_and_keeps_primary_control(self):
        original = read(CONTROL + '/scales.json')
        result = estimation.build()
        self.assertEqual(result['methods']['stage45'], original)
        for method in ['student', 'robust_gaussian']:
            restored = deepcopy(result['methods'][method])
            self.assertEqual(restored['folds']['local_party'], original['folds']['local_party'])
            for fold, old in zip(restored['folds']['candidate'], original['folds']['candidate']):
                fit = fold.pop('centralScale')
                self.assertEqual(fold.pop('seatBalanceDistribution'), method)
                expected = fit['studentScale'] if method == 'student' else fit['gaussianSD']
                self.assertEqual(fold['scales']['balance']['seat'], expected)
                fold['scales']['balance']['seat'] = old['scales']['balance']['seat']
            self.assertEqual(restored, original)


class ConditionalIntegrationTests(unittest.TestCase):
    def test_sobol_endpoint_cells_have_finite_inverse_distribution_quantiles(self):
        # Map each 30-bit digital cell to its midpoint; this numerical transform
        # does not add a floor to simulated winner frequencies or probabilities.
        unit = integration.open_unit([0., 1. - 2. ** -30])
        np.testing.assert_array_equal(unit, [2. ** -31, 1. - 2. ** -31])
        self.assertTrue(np.all((unit > 0.) & (unit < 1.)))
        for quantiles in [norm.ppf(unit), t.ppf(unit, 4)]:
            self.assertTrue(np.isfinite(quantiles).all())
            np.testing.assert_allclose(quantiles[0], -quantiles[1], rtol=0, atol=1e-12)

    def test_conditional_remainder_offsets_preserve_means_and_zero_faces(self):
        probabilities = np.array([[.5, .3, .2], [.9, .1, 0.], [1., 0., 0.]])
        sd, count = .4, 64
        offset = integration.conditional_offsets(probabilities, sd, count)
        nodes = sd * norm.ppf(integration.quadrature(3, count))
        nodes -= nodes.mean(axis=1, keepdims=True)
        logs = np.full(probabilities.shape, -np.inf)
        np.log(probabilities, out=logs, where=probabilities > 0)
        simulated = softmax(logs[:, None, :] + offset[:, None, :] + nodes[None, :, :], axis=-1)
        np.testing.assert_allclose(simulated.mean(axis=1), probabilities, rtol=0, atol=1e-10)
        np.testing.assert_allclose(simulated.sum(axis=2), 1., rtol=0, atol=1e-14)
        self.assertTrue(np.all(simulated[probabilities[:, None, :].repeat(count, axis=1) == 0] == 0))
        np.testing.assert_array_equal(integration.conditional_offsets(probabilities, 0.), np.zeros_like(probabilities))

    def test_student_binary_locations_match_declared_larger_integration(self):
        probabilities = np.array([0., .01, .2, .5, .9, .99, 1.])
        shared, seat = .1, .2
        location = integration.student_location(probabilities, shared, seat)
        expectation = expit(location[:, None] + integration.student_nodes(shared, seat, 8192)).mean(axis=1)
        active = (probabilities > 0) & (probabilities < 1)
        self.assertLess(100 * np.max(abs(expectation[active] - probabilities[active])), .05)
        self.assertAlmostEqual(location[3], 0., places=10)

    def test_equal_central_quantile_student_retains_larger_tail_probability(self):
        mad = .2
        gaussian_sd, student_scale = mad / norm.ppf(.75), mad / t.ppf(.75, 4)
        self.assertAlmostEqual(gaussian_sd * norm.ppf(.75), student_scale * t.ppf(.75, 4), places=14)
        self.assertGreater(student_scale * t.ppf(.995, 4), gaussian_sd * norm.ppf(.995))
        self.assertGreater(2 * t.sf(3 * gaussian_sd / student_scale, 4), 2 * norm.sf(3))
        self.assertTrue(math.isfinite(student_scale ** 2 * 4 / (4 - 2)))

    def test_zero_noise_inverse_preserves_complete_variable_slates(self):
        base = np.array([[.4, .3, .2, .1], [0., .6, .4, 0.], [.6, .4, 0., 0.]])
        eta = {'balance': np.zeros(3), 'mass': np.zeros(3), 'within': np.zeros((3, 2))}
        total = {'balance': 0., 'mass': 0., 'within': 0., 'balanceShared': 0., 'balanceSeat': 0.}
        for student in [False, True]:
            q, metadata = integration.conditional_inverse(base, fixture_row()['groups'], eta, total, student)
            np.testing.assert_allclose(q, base, rtol=0, atol=1e-12)
            self.assertTrue(metadata['zeroLock'])
            np.testing.assert_allclose(q.sum(axis=1), 1., rtol=0, atol=1e-14)

    def test_independent_conditional_check_reports_actual_gap(self):
        base = np.array([.4, .3, .2, .1])
        total = {'balance': .2, 'mass': .2, 'within': .2, 'balanceShared': .1, 'balanceSeat': .2}
        report = integration.conditional_check(base, fixture_row()['groups'], total, True)
        ratio = base[0] / (base[0] + base[1])
        location = integration.student_location(np.array([ratio]), .1, .2)[0]
        actual = 100 * abs(np.mean(expit(location + integration.student_nodes(.1, .2, 8192))) - ratio)
        self.assertAlmostEqual(report['balanceMaximumGapPP'], actual, places=12)
        self.assertIn('withinMaximumGapPP128', report)
        self.assertIn('withinMaximumGapPP256', report)


class GlobalStreamTests(unittest.TestCase):
    def setUp(self):
        self.rows = [fixture_row(layer, seat) for layer in ['local_party', 'candidate']
                     for seat in ['synthetic-a', 'synthetic-b']]
        inventory = {key: [row for row in self.rows if row['layer'] == layer]
                     for key, layer in [('partyRecords', 'local_party'), ('candidateRecords', 'candidate')]}
        streams.uniforms.cache_clear()
        self.read_patch = patch.object(streams, 'read', return_value=inventory)
        self.read_patch.start()

    def tearDown(self):
        self.read_patch.stop()
        streams.uniforms.cache_clear()

    def test_global_prefix_is_reproducible_and_dimensions_are_distinct(self):
        names, small = streams.uniforms(2014, 64)
        long_names, large = streams.uniforms(2014, 128)
        self.assertEqual(names, long_names)
        self.assertEqual(names, sorted(set(names)))
        self.assertEqual(small.shape, (64, len(names)))
        np.testing.assert_array_equal(small, large[:64])
        self.assertFalse(np.array_equal(small[:, 0], small[:, 1]))
        short, _ = streams.noise(self.rows[2], scales(), 64, True)
        long, _ = streams.noise(self.rows[2], scales(), 128, True)
        for direction in short:
            np.testing.assert_array_equal(short[direction], long[direction][:64])

    def test_shared_noise_crosses_seats_and_layers_have_separate_streams(self):
        first, _ = streams.noise(self.rows[0], scales(.2, 0.), 128)
        second, _ = streams.noise(self.rows[1], scales(.2, 0.), 128)
        candidate, _ = streams.noise(self.rows[2], scales(.2, 0.), 128)
        for direction in first:
            np.testing.assert_array_equal(first[direction], second[direction])
            self.assertFalse(np.array_equal(first[direction], candidate[direction]))
        own, _ = streams.noise(self.rows[0], scales(0., .2), 128)
        other, _ = streams.noise(self.rows[1], scales(0., .2), 128)
        self.assertFalse(np.array_equal(own['balance'], other['balance']))

    def test_student_changes_only_the_seat_balance_quantile(self):
        row = self.rows[2]
        gaussian, _ = streams.noise(row, scales(), 128)
        student, _ = streams.noise(row, scales(), 128, True)
        np.testing.assert_array_equal(gaussian['mass'], student['mass'])
        np.testing.assert_array_equal(gaussian['within'], student['within'])
        names, bank = streams.uniforms(2014, 128)
        shared_key, seat_key = streams.keys(row)['balance']
        expected = .1 * norm.ppf(bank[:, names.index(shared_key)]) + .2 * t.ppf(bank[:, names.index(seat_key)], 4)
        np.testing.assert_array_equal(student['balance'], expected)
        self.assertFalse(np.array_equal(gaussian['balance'], student['balance']))
        shared_gaussian, _ = streams.noise(row, scales(.2, 0.), 128)
        shared_student, _ = streams.noise(row, scales(.2, 0.), 128, True)
        for direction in shared_gaussian:
            np.testing.assert_array_equal(shared_gaussian[direction], shared_student[direction])

    def test_party_simulation_does_not_activate_student_seat_balance(self):
        row = self.rows[0]
        with patch.object(simulation, 'noise', wraps=streams.noise) as noise_call:
            simulation.invert(row['mean'], row, scales(), 32, 'student')
        self.assertFalse(noise_call.call_args.args[-1])


class ActualPipelineAndMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inventory = read(INVENTORY)
        cls.candidate = next(row for row in inventory['candidateRecords'] if row['targetYear'] == 2020)
        cls.party = next(row for row in inventory['partyRecords']
                         if row['targetElectorateId'] == cls.candidate['targetElectorateId'])

    def test_actual_component_and_composition_ignore_target_outcomes_and_keep_parameters(self):
        candidate, party = deepcopy(self.candidate), deepcopy(self.party)
        changed_candidate, changed_party = deepcopy(candidate), deepcopy(party)
        for row in [changed_candidate, changed_party]:
            row['actual'] = row['actual'][::-1]
            row['outcomeReference'] = 'synthetic changed evaluation reference'
            row['winnerId'] = 'synthetic changed winner'
        frozen = deepcopy(candidate['parameters'])
        national = np.full((32, len(party['ids'])), 1. / len(party['ids']))
        original_national = national.copy()
        for method in ['stage45', 'robust_gaussian', 'student']:
            q, meta = simulation.component(candidate, scales(), 32, method)
            altered, altered_meta = simulation.component(changed_candidate, scales(), 32, method)
            np.testing.assert_array_equal(q, altered)
            self.assertEqual(meta, altered_meta)
            original, audit = simulation.compose(party, candidate, national, scales(), scales(), method)
            changed, changed_audit = simulation.compose(changed_party, changed_candidate, national, scales(), scales(), method)
            np.testing.assert_array_equal(original, changed)
            self.assertEqual(audit, changed_audit)
            self.assertFalse(audit['nationalRedrawn'])
            np.testing.assert_allclose(original.sum(axis=1), 1., rtol=0, atol=1e-14)
        self.assertEqual(candidate['parameters'], frozen)
        self.assertEqual(changed_candidate['parameters'], frozen)
        np.testing.assert_array_equal(national, original_national)

    def test_cached_national_bank_is_repeated_with_weights_and_consumed_once(self):
        candidate, party = self.candidate, self.party
        base = np.full((4096, len(party['ids'])), 1. / len(party['ids']))
        ids = [f'synthetic-national:{index}' for index in range(4096)]
        banks = []
        def fake_compose(party_row, candidate_row, national, *args):
            banks.append(national.copy())
            return np.tile(candidate_row['mean'], (len(national), 1)), {'nationalRedrawn': False}
        def fake_pair(party_row, candidate_row, national, *args):
            return {method:fake_compose(party_row,candidate_row,national) for method in ('robust_gaussian','student')}
        def fake_seal(case_id, count, kind, vectors, metadata):
            return metadata
        with patch.object(construction, 'national_case', return_value=(base, ids, {'cached': True})) as national_call, \
                patch.object(construction, 'compose', side_effect=fake_compose), \
                patch.object(construction, 'compose_pair', side_effect=fake_pair), \
                patch.object(construction, 'seal', side_effect=fake_seal):
            result = construction.case_build('composed', 2020, [candidate], 8192, 'synthetic',
                                             estimation.build(), {party['targetElectorateId']: party}, regenerate=True)
        national_call.assert_called_once_with(2020, party['ids'], 4096)
        self.assertEqual(len(banks), 3)
        for bank in banks:
            np.testing.assert_array_equal(bank[:4096], bank[4096:])
            np.testing.assert_array_equal(bank, banks[0])
        descriptor = result['nationalDrawIds']
        self.assertEqual(descriptor['independentNationalScenarios'], 4096)
        self.assertEqual(descriptor['replicas'], 2)
        self.assertEqual(descriptor['weight'], 1. / 8192)
        self.assertEqual(len(set(descriptor['baseIds'])), 4096)
        self.assertFalse(result['outcomesConsumed'])
        self.assertFalse(result['meanRefitting'])

    def test_interval80_and_energy_have_independent_proper_score_arithmetic(self):
        draws = np.array([[0., 10.], [1., 9.], [2., 8.], [3., 7.], [4., 6.]])
        actual = np.array([-1., 8.])
        result = metrics.interval(draws, actual, .8)
        np.testing.assert_allclose(result['lower'], [.4, 6.4], atol=1e-14)
        np.testing.assert_allclose(result['upper'], [3.6, 9.6], atol=1e-14)
        np.testing.assert_allclose(result['widths'], [3.2, 3.2], atol=1e-14)
        np.testing.assert_allclose(result['scores'], [17.2, 3.2], atol=1e-14)
        self.assertEqual(result['covered'], [False, True])
        with self.assertRaises(ValueError):
            metrics.interval(draws, actual, .95)
        score = metrics.energy(draws, actual, 'synthetic-case')
        expected = []
        for repeat in [0, 1]:
            order = streams.permutation(len(draws), f'synthetic-case:energy:{repeat}')
            self.assertTrue(np.all(order != np.roll(order, 1)))
            distances = [math.dist(draws[index], actual) for index in range(len(draws))]
            pairs = [math.dist(draws[order[index]], draws[order[(index - 1) % len(draws)]])
                     for index in range(len(draws))]
            expected.append(math.fsum(distances) / len(draws) - .5 * math.fsum(pairs) / len(draws))
        self.assertAlmostEqual(score['score'], math.fsum(expected) / 2, places=14)
        self.assertEqual(score, metrics.energy(draws, actual, 'synthetic-case'))
        self.assertFalse(score['selfPairs'])


if __name__ == '__main__':
    unittest.main()
