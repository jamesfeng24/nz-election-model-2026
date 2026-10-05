"""Frozen CLR uncertainty, chronological adapters and stable stream safeguards."""
from copy import deepcopy
import unittest

import numpy as np

from scripts.uncertainty.common import PREFIX, YEARS, read, verify
from scripts.uncertainty.inventory import build, simplex
from scripts.uncertainty import estimation, streams, transforms, simulation


def synthetic_row(layer='local_party', year=2014, seat='synthetic', groups=None):
    groups = ['national', 'labour', 'other'] if groups is None else groups
    k = len(groups)
    return {'layer': layer, 'targetYear': year, 'targetElectorateId': seat,
            'ids': ['synthetic-option-' + str(i) for i in range(k)],
            'groups': groups, 'mean': [1/k]*k, 'actual': [1/k]*k,
            'geography': 'exact'}


class SimplexResidualTests(unittest.TestCase):
    def test_clr_inverse_and_zero_resolution_are_explicit(self):
        original = np.array([.6, .4, 0])
        replaced = (original + 1e-6)/(1 + 3e-6)
        self.assertTrue(np.allclose(transforms.inverse(transforms.clr(original)), replaced,
                                    rtol=0, atol=1e-15))
        self.assertAlmostEqual(float(transforms.clr(original).sum()), 0, places=13)
        self.assertTrue(np.isfinite(transforms.clr(original)).all())
        self.assertTrue(np.array_equal(transforms.residual(original, original), np.zeros(3)))

    def test_residual_matches_independent_log_ratio_arithmetic(self):
        actual, mean = np.array([.2, .3, .5]), np.array([.4, .3, .3])
        raw = np.log(actual + 1e-6) - np.log(mean + 1e-6)
        expected = raw - raw.mean()
        self.assertTrue(np.allclose(transforms.residual(actual, mean), expected,
                                    rtol=0, atol=1e-15))

    def test_invalid_or_incomplete_simplexes_are_rejected(self):
        for invalid in ([1], [.3, .3], [-.1, 1.1], [float('nan'), 1], [.4, float('inf')]):
            with self.assertRaises(ValueError):
                transforms.clr(invalid)
            with self.assertRaises(ValueError):
                simplex(invalid)

    def test_permutation_equivariance_across_variable_schemas(self):
        for k in (2, 3, 7, 16):
            mean = np.arange(1, k+1, dtype=float)
            mean /= mean.sum()
            noise = np.column_stack([streams.normal('synthetic-transform-'+str(i), 128)
                                     for i in range(k)])
            permutation = np.arange(k)[::-1]
            original, audit = transforms.preserve_mean(mean, noise)
            permuted, _ = transforms.preserve_mean(mean[permutation], noise[:, permutation])
            self.assertTrue(np.allclose(permuted, original[:, permutation], rtol=0, atol=1e-13))
            self.assertLessEqual(audit['maximumMeanGapPP'], 1e-8)
            self.assertTrue(np.allclose(original.mean(axis=0), mean, rtol=0, atol=1e-10))
            self.assertTrue(np.allclose(original.sum(axis=1), 1, rtol=0, atol=1e-12))

    def test_zero_face_locked_and_extreme_valid_means_preserved(self):
        mean = np.array([1 - 1e-8, 1e-8, 0])
        noise = np.column_stack([streams.normal('extreme-'+str(i), 512)*3 for i in range(3)])
        draws, audit = transforms.preserve_mean(mean, noise)
        self.assertTrue(np.array_equal(draws[:, 2], np.zeros(512)))
        self.assertEqual(audit['zeroMeanLockedOptions'], [2])
        self.assertTrue(np.isfinite(draws).all())
        self.assertTrue((draws >= 0).all())
        self.assertTrue(np.allclose(draws.mean(axis=0), mean, rtol=0, atol=1e-10))

    def test_varying_national_inputs_preserve_marginal_not_conditional_mean(self):
        base = np.tile([[.8, .2, 0], [.2, .7, .1]], (128, 1))
        noise = np.column_stack([streams.normal('varying-'+str(i), 256) for i in range(3)])
        draws, audit = transforms.preserve_mean(base, noise)
        self.assertTrue(np.allclose(draws.mean(axis=0), base.mean(axis=0), rtol=0, atol=1e-10))
        self.assertTrue((draws[::2, 2] == 0).all())
        self.assertIn('per-national-draw conditional mean not guaranteed', audit['preservation'])
        self.assertGreater(float(np.max(np.abs(draws[::2].mean(axis=0)-base[::2].mean(axis=0)))), 1e-4)

    def test_synthetic_larger_noise_keeps_mean_but_does_not_shrink_width(self):
        bank = np.column_stack([streams.normal('width-'+str(i), 512) for i in range(3)])
        small, _ = transforms.preserve_mean([1/3]*3, .1*bank)
        large, _ = transforms.preserve_mean([1/3]*3, bank)
        small_width = np.quantile(small, .95, axis=0)-np.quantile(small, .05, axis=0)
        large_width = np.quantile(large, .95, axis=0)-np.quantile(large, .05, axis=0)
        self.assertTrue((large_width > small_width).all())
        self.assertTrue(np.allclose(small.mean(axis=0), large.mean(axis=0), rtol=0, atol=1e-10))

    def test_mean_adjustment_failure_is_explicit_without_target_correction(self):
        with self.assertRaisesRegex(ValueError, 'iteration failure'):
            transforms.preserve_mean([.7, .3], [[1, -1], [-1, 1]], maximum=1)
        with self.assertRaises(ValueError):
            transforms.preserve_mean([.7, .3], [[float('nan'), 0]])
        with self.assertRaises(ValueError):
            transforms.preserve_mean([.7, .3], [[1, 2, 3]])


class StableStreamTests(unittest.TestCase):
    def test_antithetic_pairs_prefix_batching_and_separate_keys(self):
        short = streams.normal('synthetic-stream', 128)
        long = streams.normal('synthetic-stream', 256)
        self.assertTrue(np.array_equal(short, long[:128]))
        self.assertTrue(np.array_equal(short[::2], -short[1::2]))
        self.assertFalse(np.array_equal(short, streams.normal('different-stream', 128)))
        self.assertTrue(np.array_equal(short[:32], streams.normal('synthetic-stream', 32)))
        for invalid in (0, 3, -2, 4.0):
            with self.assertRaises(ValueError):
                streams.normal('invalid', invalid)

    def test_shared_classes_reuse_election_draws_across_seats(self):
        first, second = synthetic_row(seat='one'), synthetic_row(seat='two')
        shared = {'shared': .2, 'seat': 0}
        self.assertTrue(np.array_equal(streams.noise(first, shared, 128),
                                       streams.noise(second, shared, 128)))
        specific = {'shared': 0, 'seat': .5}
        self.assertFalse(np.array_equal(streams.noise(first, specific, 128),
                                        streams.noise(second, specific, 128)))
        changed_year = dict(first, targetYear=2017)
        self.assertFalse(np.array_equal(streams.noise(first, shared, 128),
                                        streams.noise(changed_year, shared, 128)))
        changed_layer = dict(first, layer='candidate')
        self.assertFalse(np.array_equal(streams.noise(first, shared, 128),
                                        streams.noise(changed_layer, shared, 128)))

    def test_option_permutation_and_shared_same_class_effect(self):
        row = synthetic_row(groups=['national', 'other', 'other', 'labour'])
        shared = streams.noise(row, {'shared': .2, 'seat': 0}, 128)
        self.assertTrue(np.array_equal(shared[:, 1], shared[:, 2]))
        order = [3, 1, 0, 2]
        permuted = dict(row, ids=[row['ids'][i] for i in order],
                        groups=[row['groups'][i] for i in order])
        total = streams.noise(row, {'shared': .2, 'seat': .5}, 128)
        shuffled = streams.noise(permuted, {'shared': .2, 'seat': .5}, 128)
        self.assertTrue(np.allclose(shuffled, total[:, order], rtol=0, atol=1e-12))
        self.assertTrue(np.allclose(total.sum(axis=1), 0, rtol=0, atol=1e-15))

    def test_transport_stress_changes_only_nonexact_candidate_seat_variance(self):
        row = synthetic_row('candidate')
        scales = {'shared': 0, 'seat': .5}
        original = streams.noise(row, scales, 128)
        self.assertTrue(np.array_equal(original, streams.noise(row, scales, 128, stress=True)))
        nonexact = dict(row, geography='fallback')
        stressed = streams.noise(nonexact, scales, 128, stress=True)
        self.assertTrue(np.allclose(stressed, original*np.sqrt(1.5), rtol=0, atol=3e-16))
        party = dict(nonexact, layer='local_party')
        self.assertTrue(np.array_equal(streams.noise(party, scales, 128),
                                       streams.noise(party, scales, 128, stress=True)))

    def test_national_subset_keeps_chain_ids_and_precision_prefix(self):
        selected = streams.national_indices((4, 2000, 6), 512)
        larger = streams.national_indices((4, 2000, 6), 1024)
        self.assertTrue(np.array_equal(selected, larger[:512]))
        self.assertEqual(len(set(selected.tolist())), 512)
        self.assertEqual(np.bincount(selected//2000).tolist(), [128]*4)
        self.assertTrue(all(len(set(selected[i:i+4] % 2000)) == 1 for i in range(0, 512, 4)))
        with self.assertRaises(ValueError):
            streams.national_indices((4, 10), 512)


class PooledScaleTests(unittest.TestCase):
    def test_no_earlier_evidence_uses_explicit_assumed_prior(self):
        row = synthetic_row()
        result = estimation.fit([row], 'local_party', 2014)
        self.assertEqual(result['trainingYears'], [])
        self.assertEqual(result['trainingIds'], [])
        self.assertEqual(result['status'], 'assumed_prior_no_earlier_residuals')
        self.assertAlmostEqual(result['scales']['shared'], .15, places=15)
        self.assertAlmostEqual(result['scales']['seat'], .35, places=15)

    def test_missing_moment_evidence_does_not_create_false_precision(self):
        assumption = estimation.fit([], 'local_party', 2014)
        zero_error = estimation.fit([synthetic_row(year=2011)], 'local_party', 2014)
        for component in ('shared', 'seat'):
            self.assertGreater(assumption['scales'][component], zero_error['scales'][component])
        self.assertEqual(assumption['environments'], 0)
        self.assertEqual(zero_error['environments'], 1)

    def test_target_and_later_residuals_cannot_enter_earlier_fit(self):
        rows = [synthetic_row(year=year, seat=str(year)) for year in (2011, 2014, 2017)]
        original = estimation.fit(rows, 'local_party', 2014)
        changed = deepcopy(rows)
        for row in changed[1:]:
            row['actual'] = [.98, .01, .01]
            row['mean'] = [.01, .98, .01]
        self.assertEqual(estimation.fit(changed, 'local_party', 2014), original)
        self.assertEqual(original['trainingYears'], [2011])
        changed[0]['actual'] = [.98, .01, .01]
        self.assertNotEqual(estimation.fit(changed, 'local_party', 2014)['scales'], original['scales'])

    def test_equal_election_shrinkage_and_independent_moment_arithmetic(self):
        first = synthetic_row(year=2011, seat='first')
        first['actual'] = [.5, .2, .3]
        second = synthetic_row(year=2014, seat='second')
        second['actual'] = [.2, .5, .3]
        rows = [first] + [dict(second, targetElectorateId='duplicate-'+str(i)) for i in range(8)]
        result = estimation.fit(rows, 'local_party', 2017)
        e1 = transforms.residual(first['actual'], first['mean'])
        e2 = transforms.residual(second['actual'], second['mean'])
        expected_shared = np.sqrt((e1@e1/2 + e2@e2/2 + 3*.15**2)/5)
        self.assertAlmostEqual(result['scales']['shared'], float(expected_shared), places=13)
        self.assertAlmostEqual(result['scales']['seat'], np.sqrt(3*.35**2/5), places=13)
        self.assertEqual(result['environments'], 2)
        self.assertEqual([m['contests'] for m in result['moments']], [1, 8])

    def test_missing_shared_class_is_rank_failure_not_pseudoinverse_fit(self):
        row = synthetic_row('candidate', groups=['national', 'labour', 'other'])
        row['actual'] = [.6, .2, .2]
        moment = estimation.environment([row], 'candidate')
        self.assertFalse(moment['sharedIdentifiable'])
        self.assertIsNone(moment['sharedSecondMoment'])
        self.assertEqual(moment['classEffects'], dict.fromkeys(('national', 'labour', 'other', 'no_group'), 0.0))
        e = transforms.residual(row['actual'], row['mean'])
        self.assertAlmostEqual(moment['seatSecondMoment'], float(e@e/2), places=13)
        result = estimation.fit([row], 'candidate', 2017)
        self.assertEqual(result['scales']['shared'], .2)
        self.assertGreater(result['scales']['seat'], 0)


class FrozenSimulationTests(unittest.TestCase):
    def setUp(self):
        self.party = synthetic_row()
        self.party.update(ballotGroupKeys=['nat', 'lab', 'minor'], affinities=[1.2, .8, 1.])
        self.candidate = synthetic_row('candidate', groups=['national', 'labour', 'no_group'])
        self.candidate.update(ids=['nat-person', 'lab-person', 'new-independent'],
            parameters={'status': 'fitted', 'kappa': .02, 'theta': [1., .5], 'coefficients': {'S': 1., 'R': .5}},
            features=[{'id': 'nat-person', 'group': 'nat', 'centered': [.2, -.1]},
                      {'id': 'lab-person', 'group': 'lab', 'centered': [-.1, .2]},
                      {'id': 'new-independent', 'group': None, 'centered': [0., 0.]}])
        self.national = np.tile([[.5, .3, .2], [.3, .5, .2]], (32, 1))
        self.scales = {'shared': .2, 'seat': .3}

    def test_component_outcome_independence_and_arithmetic_mean(self):
        first, metadata = simulation.component(self.candidate, self.scales, 128)
        changed = deepcopy(self.candidate)
        changed.update(actual=[.98, .01, .01], winnerId='anything', denominator=9999)
        second, second_metadata = simulation.component(changed, self.scales, 128)
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(metadata, second_metadata)
        self.assertTrue(np.allclose(first.mean(axis=0), self.candidate['mean'], rtol=0, atol=1e-10))

    def test_composed_streams_and_seeded_batching_ignore_outcomes(self):
        first, metadata = simulation.compose(self.party, self.candidate, self.national,
                                            self.scales, self.scales, batch_size=8)
        party, candidate = deepcopy(self.party), deepcopy(self.candidate)
        party['actual'] = [.01, .01, .98]
        candidate.update(actual=[.01, .98, .01], winnerId='changed')
        second, second_metadata = simulation.compose(party, candidate, self.national,
                                                     self.scales, self.scales, batch_size=64)
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(metadata, second_metadata)
        self.assertFalse(metadata['nationalRedrawn'])
        self.assertTrue(np.allclose(first.sum(axis=1), 1, rtol=0, atol=1e-12))
        self.assertTrue((first >= 0).all())
        self.assertLess(np.max(np.abs(metadata['candidateAdjustmentMeanShiftPP'])), 1e-8)
        self.assertLess(np.max(np.abs(metadata['localMarginalMeanShiftPP'])), 1e-8)

    def test_zero_error_uses_supplied_joint_national_scenario_once(self):
        scales = {'shared': 0., 'seat': 0.}
        draws, metadata = simulation.compose(self.party, self.candidate, self.national,
                                             scales, scales)
        local = self.national*np.array(self.party['affinities'])
        local /= local.sum(axis=1, keepdims=True)
        exponents = np.exp([.15, 0., 0.])
        weights = np.column_stack([local[:, 0]+.02, local[:, 1]+.02, np.full(len(local), .02)])*exponents
        independently = weights/weights.sum(axis=1, keepdims=True)
        self.assertTrue(np.allclose(draws, independently, rtol=0, atol=1e-14))
        self.assertTrue(np.allclose(metadata['simulatedMean'], independently.mean(axis=0), rtol=0, atol=1e-14))
        changed_party, changed_candidate = deepcopy(self.party), deepcopy(self.candidate)
        changed_party['targetElectorateId'] = 'another-seat'
        changed_candidate['targetElectorateId'] = 'another-seat'
        other, _ = simulation.compose(changed_party, changed_candidate, self.national, scales, scales)
        self.assertTrue(np.array_equal(draws, other))

    def test_shared_group_destinations_are_unique_and_missing_is_not_zero(self):
        self.assertEqual(simulation.candidate_inputs(self.candidate, self.party)[0], [0, 1, -1])
        for invalid_group in ('nat', 'absent'):
            changed = deepcopy(self.candidate)
            changed['features'][1]['group'] = invalid_group
            with self.assertRaises(ValueError):
                simulation.candidate_inputs(changed, self.party)
        duplicate = deepcopy(self.party)
        duplicate['ballotGroupKeys'][1] = 'nat'
        with self.assertRaises(ValueError):
            simulation.candidate_inputs(self.candidate, duplicate)

    def test_missing_person_features_do_not_copy_an_outgoing_residual(self):
        changed = deepcopy(self.candidate)
        changed['features'][0]['centered'] = [0., 0.]
        destinations, exponents, kappa = simulation.candidate_inputs(changed, self.party)
        self.assertEqual(exponents[0], 0.)
        self.assertEqual(exponents[2], 0.)
        self.assertEqual(destinations[2], -1)
        self.assertEqual(kappa, self.candidate['parameters']['kappa'])
        self.assertEqual(self.candidate['features'][0]['centered'], [.2, -.1])

    def test_zero_category_entry_and_invalid_national_scenarios(self):
        zero_minor = np.tile([.6, .4, 0.], (64, 1))
        draws, _ = simulation.compose(self.party, self.candidate, zero_minor,
                                     self.scales, self.scales)
        self.assertTrue(np.isfinite(draws).all())
        self.assertTrue((draws >= 0).all())
        with self.assertRaises(ValueError):
            simulation.compose(self.party, self.candidate, np.tile([.6, .3, 0], (64, 1)),
                               self.scales, self.scales)
        with self.assertRaises(ValueError):
            simulation.compose(self.party, self.candidate, zero_minor,
                               self.scales, self.scales, batch_size=0)


class ActualUncertaintyAdaptersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = read(PREFIX+'/inventory.json')
        cls.elections = {y: read(f'data/processed/elections/{y}.json') for y in YEARS}

    def test_exact_coverage_full_frame_and_continuous_prediction_provenance(self):
        self.assertEqual({y: sum(r['targetYear'] == y for r in self.inventory['partyRecords'])
                          for y in YEARS}, dict(zip(YEARS, (63, 64, 64, 65, 65))))
        self.assertEqual({y: sum(r['targetYear'] == y for r in self.inventory['candidateRecords'])
                          for y in YEARS}, dict(zip(YEARS, (0, 64, 64, 65, 64))))
        self.assertEqual(sum(len(r['ids']) for r in self.inventory['candidateRecords']), 1902)
        for row in self.inventory['candidateRecords']:
            self.assertIn('earlier_fit', row['predictionStatus'])
            self.assertTrue(all(int(cid.split('-')[2]) < row['targetYear'] for cid in row['trainingIds']))
            self.assertTrue(all(0 <= x <= 1 for f in row['features'] for x in f['supportedMass'].values()))
            if row['targetYear'] in (2014, 2020):
                self.assertEqual(row['predictionReference'], 'Stage43 continuous joint')
            else:
                self.assertEqual(row['predictionReference'], 'Stage33 primary_fixed_to_observed joint')
            self.assertAlmostEqual(sum(row['mean']), 1, places=12)

    def test_residual_predictor_is_source_only_unique_person_and_neutral_if_missing(self):
        supported = 0
        missing = 0
        for row in self.inventory['candidateRecords']:
            for feature in row['features']:
                if feature['supportedMass']['R'] == 0:
                    missing += 1
                    self.assertEqual(feature['centered'][1], 0.)
                    continue
                supported += 1
                source_ids = set()
                for evidence in feature['residualEvidence']:
                    if not evidence.get('sourceOccurrenceId'):
                        continue
                    source_ids.add(evidence['sourceOccurrenceId'])
                    self.assertEqual(int(evidence['sourceOccurrenceId'].split('-')[2]), row['sourceYear'])
                    self.assertTrue(evidence['edgeId'].endswith('->' + feature['id']))
                    self.assertIn(evidence['evidenceTier'],
                                  ('accepted_algorithmic_same_person', 'documentary_same_person'))
                    self.assertNotIn('targetResidual', evidence)
                self.assertEqual(len(source_ids), 1)
        self.assertGreater(supported, 0)
        self.assertGreater(missing, 0)

    def test_saved_stage43_and_stage33_mean_predictions_reproduce_exact_ids(self):
        extended = read('data/processed/continuous-candidate-comparison/construction.json')['folds']
        saved = read('data/processed/models/joint-candidate-share/construction.json')['folds']
        for row in self.inventory['candidateRecords']:
            year = row['targetYear']
            if year in (2014, 2020):
                fold = next(f for f in extended if f['targetYear'] == year)
                pred = next(p for p in fold['predictions']['joint']
                            if p['targetElectorateId'] == row['targetElectorateId'])
            else:
                fold = next(f for f in saved if f['targetYear'] == year and f['branch'] == 'primary_fixed_to_observed')
                pred = next(p for p in fold['predictions']['baseline_plus_S_plus_R']
                            if p['targetElectorateId'] == row['targetElectorateId'])
            self.assertEqual([pred['candidateShares'][cid] for cid in row['ids']], row['mean'])

    def test_maori_cancelled_and_no_earlier_fit_remain_explicit(self):
        frame = self.inventory['fullFrame']
        maori = [r for r in frame if r['scope'] == 'maori']
        self.assertTrue(maori)
        self.assertTrue(all(r['candidateStatus'] == 'coverage_only_separate_maori_layer' for r in maori))
        early = [r for r in frame if r['year'] == 2011 and r['scope'] == 'general']
        self.assertTrue(all(r['candidateStatus'] == 'no_earlier_fit' for r in early))
        cancelled = [r for r in frame if r['candidateStatus'] == 'cancelled']
        self.assertEqual(len(cancelled), 1)
        self.assertTrue(any(r['targetElectorateId'] == cancelled[0]['id'] for r in self.inventory['partyRecords']))
        self.assertFalse(any(r['targetElectorateId'] == cancelled[0]['id'] for r in self.inventory['candidateRecords']))

    def test_actual_adapter_heldout_outcomes_change_only_evaluation_references(self):
        changed = deepcopy(self.elections)
        for seat in changed[2020]['electorates']:
            if len(seat['candidates']) < 2:
                continue
            a, b = seat['candidates'][:2]
            a['votes'], b['votes'] = b['votes'], a['votes']
            seat['winnerCandidateId'] = a['id']
        result = build(changed)
        for old, new in zip(self.inventory['candidateRecords'], result['candidateRecords']):
            self.assertEqual({k: v for k, v in old.items() if k not in ('actual', 'winnerId')},
                             {k: v for k, v in new.items() if k not in ('actual', 'winnerId')})
        self.assertEqual(result['partyRecords'], self.inventory['partyRecords'])
        self.assertEqual(result['fullFrame'], self.inventory['fullFrame'])
        self.assertNotEqual([r['actual'] for r in result['candidateRecords']],
                            [r['actual'] for r in self.inventory['candidateRecords']])
        original_fit = estimation.fit(self.inventory['candidateRecords'], 'candidate', 2020)
        self.assertEqual(original_fit, estimation.fit(result['candidateRecords'], 'candidate', 2020))

    def test_local_outcome_change_does_not_change_party_mean_or_uncertainty_training(self):
        changed = deepcopy(self.elections)
        for seat in changed[2023]['electorates']:
            a, b = seat['parties'][:2]
            a['votes'], b['votes'] = b['votes'], a['votes']
        result = build(changed)
        for old, new in zip(self.inventory['partyRecords'], result['partyRecords']):
            self.assertEqual({k: v for k, v in old.items() if k != 'actual'},
                             {k: v for k, v in new.items() if k != 'actual'})
        self.assertEqual(result['candidateRecords'], self.inventory['candidateRecords'])
        self.assertEqual(estimation.fit(result['partyRecords'], 'local_party', 2023),
                         estimation.fit(self.inventory['partyRecords'], 'local_party', 2023))

    def test_missing_preserved_record_is_explicit_not_zero_filled(self):
        changed = deepcopy(self.elections)
        removed = changed[2020]['electorates'].pop(0)
        result = build(changed)
        frame = next(r for r in result['fullFrame'] if r['id'] == removed['id'])
        self.assertEqual(frame['partyStatus'], 'missing_preserved_election_record')
        self.assertEqual(frame['candidateStatus'], 'missing_preserved_election_record')
        self.assertFalse(any(r['targetElectorateId'] == removed['id'] for r in result['partyRecords']))

    def test_consumed_provenance_and_previous_data_preserved(self):
        self.assertGreater(verify(), 1756)
        contract = read(PREFIX+'/input-contract.json')
        self.assertIn('data/processed/continuous-transport/inventory.json', contract['inputHashes'])
        self.assertIn('data/processed/models/joint-candidate-share/construction.json', contract['inputHashes'])


if __name__ == '__main__':
    unittest.main()
