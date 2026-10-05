"""Independent Stage46 residual decomposition and descriptive weighting checks."""
import math
import unittest

import numpy as np

from scripts.uncertainty_tails.common import CONTROL, INVENTORY, PREFIX, read
from scripts.uncertainty_tails.diagnosis import (
    heterogeneity, residual_records, summary, top_squared_fraction,
    weighted_quantile,
)


def fixture_record(value, year=2014, weight=1., identifier='seat', stratum='group'):
    return {'seatResidual': value, 'rawResidual': value, 'sharedResidual': 0.,
            'year': year, 'weight': weight, 'id': f'{year}:{identifier}',
            'option': 'option', 'electionRMS': 1., 'earlierSeatSD': 1.,
            'stratum': stratum}


def independent_coordinates(values, groups):
    """Scalar log arithmetic, independent of the vectorized coordinate helper."""
    x = [value + 1e-6 for value in values]
    national = [i for i, group in enumerate(groups) if group == 'national']
    labour = [i for i, group in enumerate(groups) if group == 'labour']
    majors = national + labour
    other = [i for i in range(len(groups)) if i not in majors]
    balance = math.log(x[national[0]] / x[labour[0]]) if national and labour else None
    mass = math.log(math.fsum(x[i] for i in majors) / math.fsum(x[i] for i in other)) if majors and other else None
    logs = [math.log(x[i]) for i in other]
    within = [value - math.fsum(logs) / len(logs) for value in logs] if len(logs) > 1 else None
    return balance, mass, within, other


class TailDiagnosisWeightingTests(unittest.TestCase):
    def test_pooled_summary_weights_elections_equally(self):
        records = [fixture_record(0., 2014, identifier='a'),
                   fixture_record(0., 2014, identifier='b'),
                   fixture_record(10., 2017, identifier='c')]
        result = summary(records, pooled=True)
        self.assertEqual(result['records'], 3)
        self.assertEqual(result['environments'], 2)
        self.assertAlmostEqual(result['mean'], 5.)
        self.assertAlmostEqual(result['rms'], math.sqrt(50.))
        self.assertEqual(result['quantiles']['0.5'], 0.)

    def test_coordinate_weights_give_each_seat_one_weight(self):
        records = [fixture_record(2., weight=.5, identifier='a'),
                   fixture_record(2., weight=.5, identifier='a'),
                   fixture_record(0., weight=1., identifier='b')]
        self.assertAlmostEqual(summary(records)['mean'], 1.)
        self.assertAlmostEqual(summary(records)['rms'], math.sqrt(2.))

    def test_top_squared_fraction_uses_fractional_boundary_record(self):
        values, weights = np.array([1., 10.]), np.array([.9, .1])
        # Five percent consumes half of the ten-percent high-error record.
        self.assertAlmostEqual(top_squared_fraction(values, weights, .05), 5. / 10.9)
        self.assertAlmostEqual(top_squared_fraction(values, weights, .1), 10. / 10.9)
        self.assertAlmostEqual(top_squared_fraction(values, weights, 1.), 1.)
        self.assertIsNone(top_squared_fraction(np.zeros(2), weights, .05))

    def test_weighted_quantiles_use_frozen_empirical_inverse_cdf(self):
        result = weighted_quantile([30., 10., 20.], [.5, .25, .25], [.25, .5, .75])
        np.testing.assert_array_equal(result, [10., 20., 30.])
        for values, weights in [([], []), ([1.], [0.]), ([math.nan], [1.])]:
            with self.assertRaises(ValueError):
                weighted_quantile(values, weights, [.5])

    def test_heterogeneity_control_retains_small_strata_and_warns(self):
        records = [fixture_record((-1.) ** i, identifier=str(i), stratum='ordinary') for i in range(8)]
        records += [fixture_record(10. * (-1.) ** i, identifier=str(i + 8), stratum='wide') for i in range(8)]
        small = fixture_record(3., identifier='small', stratum='sparse')
        small['electionRMS'] = 2.
        records.append(small)
        result = heterogeneity(records)
        self.assertIn('not a variance model', result['rule'])
        self.assertIn('otherwise election RMS', result['rule'])
        self.assertEqual(result['standardized']['records'], len(records))
        self.assertTrue(result['standardized']['noObservationsRemoved'])
        sparse = result['strata'][str((2014, 'sparse'))]
        self.assertEqual(sparse['records'], 1)
        # Eight values at each scale become absolute standardized residual one;
        # the retained sparse record uses its election fallback of 3/2.
        self.assertAlmostEqual(result['standardized']['rms'], math.sqrt((16. + 2.25) / 17.))


class TailDiagnosisSavedArithmeticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = read(INVENTORY)
        cls.control = read(CONTROL + '/scales.json')
        cls.diagnosis = read(PREFIX + '/diagnosis.json')

    def test_saved_records_retain_every_defined_coordinate_and_named_case(self):
        for layer, source in [('local_party', 'partyRecords'), ('candidate', 'candidateRecords')]:
            rows = self.inventory[source]
            actual = self.diagnosis['layers'][layer]['records']
            self.assertEqual(len(actual['balance']), len(rows))
            self.assertEqual(len(actual['mass']), len(rows))
            expected = sum(len(independent_coordinates(row['actual'], row['groups'])[3])
                           for row in rows if independent_coordinates(row['actual'], row['groups'])[2] is not None)
            self.assertEqual(len(actual['within']), expected)
            self.assertEqual({record['id'] for record in actual['balance']},
                             {row['targetElectorateId'] for row in rows})
            self.assertTrue(any(record['name'] == 'Tāmaki' for record in actual['balance']))
            self.assertTrue(self.diagnosis['layers'][layer]['pooled']['within']['noObservationsRemoved'])
        self.assertTrue(self.diagnosis['retainedAllObservations'])

    def test_scalar_shared_subtraction_and_within_df_match_independent_arithmetic(self):
        for layer, source in [('local_party', 'partyRecords'), ('candidate', 'candidateRecords')]:
            for environment in self.control['descriptive'][layer]['moments']:
                year, moments = environment['year'], environment['moments']
                rows = [row for row in self.inventory[source] if row['targetYear'] == year]
                fold = next(f for f in self.control['folds'][layer] if f['targetYear'] == year)
                produced = residual_records(rows, moments, fold)
                lookup = {(direction, record['id'], record['option']): record
                          for direction, records in produced.items() for record in records}
                saved_lookup = {(direction, record['id'], record['option']): record
                                for direction, records in self.diagnosis['layers'][layer]['records'].items()
                                for record in records if record['year'] == year}
                self.assertEqual(lookup.keys(), saved_lookup.keys())
                for key, record in lookup.items():
                    for field in ['rawResidual', 'sharedResidual', 'seatResidual', 'weight']:
                        self.assertAlmostEqual(record[field], saved_lookup[key][field], places=12)
                for row in rows:
                    actual = independent_coordinates(row['actual'], row['groups'])
                    mean = independent_coordinates(row['mean'], row['groups'])
                    for index, direction in enumerate(['balance', 'mass']):
                        record = lookup[direction, row['targetElectorateId'], direction]
                        raw = actual[index] - mean[index]
                        shared = moments[direction]['descriptiveElectionEffect']
                        self.assertAlmostEqual(record['rawResidual'], raw, places=12)
                        self.assertAlmostEqual(record['seatResidual'], raw - shared, places=12)
                    if actual[2] is None:
                        continue
                    indices = actual[3]
                    tags = ([row['ballotGroupKeys'][i] for i in indices] if layer == 'local_party'
                            else [row['features'][i]['group'] or 'no_group' for i in indices])
                    effects = [moments['within'].get('classEffects', {}).get(tag, 0.) for tag in tags]
                    center = math.fsum(effects) / len(effects)
                    leftovers = [a - m - effect + center for a, m, effect in zip(actual[2], mean[2], effects)]
                    normalized_second_moment = 0.
                    for index, leftover in zip(indices, leftovers):
                        record = lookup['within', row['targetElectorateId'], row['ids'][index]]
                        expected = leftover * math.sqrt(len(indices) / (len(indices) - 1))
                        self.assertAlmostEqual(record['seatResidual'], expected, places=12)
                        self.assertEqual(record['weight'], 1 / len(indices))
                        normalized_second_moment += record['weight'] * record['seatResidual'] ** 2
                    self.assertAlmostEqual(normalized_second_moment,
                                           math.fsum(value * value for value in leftovers) / (len(indices) - 1), places=12)
                for direction, records in produced.items():
                    total_weight = math.fsum(record['weight'] for record in records)
                    second_moment = math.fsum(record['weight'] * record['seatResidual'] ** 2 for record in records) / total_weight
                    self.assertAlmostEqual(second_moment, moments[direction]['seat'], places=12)

    def test_saved_candidate_balance_pool_and_tail_concentration_independently(self):
        rows = self.inventory['candidateRecords']
        years = sorted({row['targetYear'] for row in rows})
        pairs = []
        for year in years:
            election = [row for row in rows if row['targetYear'] == year]
            moments = next(environment['moments']['balance']
                           for environment in self.control['descriptive']['candidate']['moments']
                           if environment['year'] == year)
            for row in election:
                actual = independent_coordinates(row['actual'], row['groups'])[0]
                mean = independent_coordinates(row['mean'], row['groups'])[0]
                pairs.append((actual - mean - moments['descriptiveElectionEffect'],
                              1. / len(years) / len(election)))
        saved = self.diagnosis['layers']['candidate']['pooled']['balance']
        denominator = math.fsum(weight * value * value for value, weight in pairs)
        self.assertAlmostEqual(saved['rms'], math.sqrt(denominator), places=12)
        self.assertAlmostEqual(saved['mean'], math.fsum(weight * value for value, weight in pairs), places=12)
        remaining, numerator = .05, 0.
        for value, weight in sorted(pairs, key=lambda pair: -abs(pair[0])):
            take = min(weight, remaining)
            numerator += take * value * value
            remaining -= take
            if remaining <= 0.:
                break
        self.assertAlmostEqual(saved['largestSquaredFractions']['0.05'], numerator / denominator, places=12)


if __name__ == '__main__':
    unittest.main()
