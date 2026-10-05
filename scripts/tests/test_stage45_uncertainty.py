"""Synthetic and real-adapter safeguards for the frozen aggregate uncertainty tree."""
from copy import deepcopy
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import expit, roots_hermitenorm

from scripts.uncertainty import streams
from scripts.uncertainty.common import read
from scripts.uncertainty.inventory import build as inventory_build
from scripts.uncertainty_revision import coordinates, estimation, simulation, common, construction
from scripts.transport import common as transport_common


def row(groups=None, year=2011, seat='synthetic', layer='local_party'):
    groups = ['national', 'labour', 'other', 'other'] if groups is None else groups
    size = len(groups)
    return {'layer': layer, 'targetYear': year, 'targetElectorateId': seat,
            'groups': groups, 'ids': ['synthetic-' + str(i) for i in range(size)],
            'ballotGroupKeys': ['national' if g == 'national' else 'labour' if g == 'labour'
                               else 'small-' + str(i) for i, g in enumerate(groups)],
            'features': [{'group': 'national' if g == 'national' else 'labour' if g == 'labour'
                          else None if g == 'no_group' else 'small-' + str(i)}
                         for i, g in enumerate(groups)],
            'mean': [1/size]*size, 'actual': [1/size]*size}


def scales(shared=.1, seat=.2):
    return {name: {'shared': shared, 'seat': seat} for name in ('balance', 'mass', 'within')}


class ArithmeticPartitionTests(unittest.TestCase):
    def test_balance_and_mass_are_raw_odds_not_clr_coordinate_count(self):
        base = [.4, .3, .2, .1]
        value = coordinates.coordinates(base, row()['groups'], replace=False)
        self.assertAlmostEqual(value['balance'], np.log(.4/.3), places=14)
        self.assertAlmostEqual(value['mass'], np.log(.7/.3), places=14)
        np.testing.assert_allclose(value['within'], [np.log(2)/2, -np.log(2)/2], atol=1e-14)

    def test_zero_resolution_matches_frozen_policy_and_retains_observed_zero(self):
        groups = ['national', 'labour', 'other']
        value = coordinates.coordinates([.6, .4, 0], groups)
        self.assertAlmostEqual(value['balance'], np.log((.6+1e-6)/(.4+1e-6)), places=14)
        self.assertAlmostEqual(value['mass'], np.log((1+2e-6)/1e-6), places=13)
        self.assertIsNone(value['within'])
        self.assertEqual(coordinates.coordinates([0, 0, 1], groups, replace=False)['balance'], None)

    def test_absent_major_or_remainder_omits_only_unidentified_coordinate(self):
        fixtures = [(['national', 'other', 'other'], (False, True, True)),
                    (['labour', 'other'], (False, True, False)),
                    (['other', 'no_group'], (False, False, True)),
                    (['national', 'labour'], (True, False, False))]
        for groups, expected in fixtures:
            value = coordinates.coordinates([1/len(groups)]*len(groups), groups)
            self.assertEqual(tuple(value[k] is not None for k in ('balance', 'mass', 'within')), expected)

    def test_duplicate_major_destinations_are_rejected(self):
        for groups in (['national', 'national', 'other'], ['labour', 'labour']):
            with self.assertRaisesRegex(ValueError, 'Duplicate major'):
                coordinates.partition(groups)

    def test_invalid_complete_vectors_and_scales_are_rejected(self):
        for invalid in ([.4, .4], [-.1, 1.1], [np.nan, 1], [np.inf, 0]):
            with self.assertRaises(ValueError):
                coordinates.coordinates(invalid, ['national', 'labour'])
        for p, sd in ((-.1, .2), (1.1, .2), (.5, -1), (.5, np.nan)):
            with self.assertRaises(ValueError):
                coordinates.mean_logit_location(p, sd)

    def test_splitting_remainder_cannot_change_top_level_coordinates(self):
        original = coordinates.coordinates([.4, .3, .3], ['national', 'labour', 'other'], replace=False)
        split = coordinates.coordinates([.4, .3, .299999, .000001],
                                        ['national', 'labour', 'other', 'other'], replace=False)
        self.assertEqual(original['balance'], split['balance'])
        self.assertEqual(original['mass'], split['mass'])


class ConditionalMeanTests(unittest.TestCase):
    def test_gauss_hermite_prior_units_and_higher_order_expectations(self):
        spec = read(common.PREFIX + '/specification.json')
        probabilities = np.array([.001, .05, .3, .5, .9, .999])
        nodes, weights = roots_hermitenorm(81)
        weights /= np.sqrt(2*np.pi)
        for layer in ('local_party', 'candidate'):
            for name in ('balance', 'mass'):
                prior = spec['priors'][layer][name]
                sd = np.hypot(prior['shared'], prior['seat'])
                location = coordinates.mean_logit_location(probabilities, sd)
                expected = (expit(location[:, None]+sd*nodes)*weights).sum(axis=1)
                np.testing.assert_allclose(expected, probabilities, rtol=0, atol=1e-12)
                np.testing.assert_allclose(location, coordinates.mean_logit_location(probabilities, sd, order=81),
                                           rtol=0, atol=1e-10)
        self.assertAlmostEqual(np.hypot(.08, .15), .17, places=14)
        self.assertAlmostEqual(np.hypot(.15, .35), np.sqrt(.145), places=14)

    def test_zero_variance_inverse_reproduces_variable_slates(self):
        fixtures = [(['national', 'labour'], [.6, .4]),
                    (['national', 'other'], [.6, .4]),
                    (['other', 'no_group'], [.6, .4]),
                    (['national', 'labour', 'other', 'no_group'], [.4, .3, .2, .1])]
        for groups, base in fixtures:
            r = row(groups)
            r['mean'] = base
            q, _ = simulation.component(r, scales(0, 0), 32)
            np.testing.assert_allclose(q, np.tile(base, (32, 1)), rtol=0, atol=1e-12)

    def test_zero_faces_and_extreme_valid_probabilities_remain_locked(self):
        for base in ([0, .4, .6, 0], [1, 0, 0, 0], [0, 0, .2, .8], [1-1e-8, 1e-8, 0, 0]):
            r = row()
            r['mean'] = base
            q, metadata = simulation.component(r, scales(.2, .5), 128)
            self.assertTrue(np.isfinite(q).all())
            self.assertTrue((q >= 0).all())
            np.testing.assert_allclose(q.sum(axis=1), 1, rtol=0, atol=1e-12)
            self.assertTrue((q[:, np.array(base) == 0] == 0).all())
            self.assertTrue(metadata['location']['zeroFacePreserved'])

    def test_mean_preserving_within_adjustment_does_not_change_aggregate_mass(self):
        base = np.tile([.4, .3, .2, .1], (256, 1))
        eta, total = simulation.noise(row(), scales(.2, .5), 256)
        q, location = coordinates.inverse(base, row()['groups'], eta, total)
        expected_mass = coordinates.binary_draw(np.repeat(.7, 256), eta['mass'], total['mass'])
        np.testing.assert_allclose(q[:, :2].sum(axis=1), expected_mass, rtol=0, atol=1e-14)
        np.testing.assert_allclose(q[:, 2:].mean(axis=0), np.array([2/3, 1/3])*(1-expected_mass).mean(),
                                   rtol=0, atol=1e-10)
        self.assertIn('per-input remainder allocation not preserved', location['withinLocation']['scope'])

    def test_small_category_split_keeps_major_draws_identical(self):
        original = row(['national', 'labour', 'other'])
        split = row(['national', 'labour', 'other', 'other'])
        original['mean'], split['mean'] = [.4, .3, .3], [.4, .3, .299999, .000001]
        a, _ = simulation.component(original, scales(.1, .2), 256)
        b, _ = simulation.component(split, scales(.1, .2), 256)
        np.testing.assert_array_equal(a[:, :2], b[:, :2])
        np.testing.assert_allclose(a[:, 2], b[:, 2:].sum(axis=1), rtol=0, atol=1e-15)

    def test_permutation_moves_options_and_noise_without_changing_shares(self):
        r = row(['other', 'national', 'no_group', 'labour', 'other'])
        r['mean'] = [.1, .4, .05, .3, .15]
        order = [4, 3, 2, 1, 0]
        moved = deepcopy(r)
        for key in ('mean', 'actual', 'groups', 'ids', 'ballotGroupKeys', 'features'):
            moved[key] = [r[key][i] for i in order]
        a, _ = simulation.component(r, scales(), 128)
        b, _ = simulation.component(moved, scales(), 128)
        np.testing.assert_allclose(b, a[:, order], rtol=0, atol=1e-14)

    def test_draw_dimension_mismatch_is_explicit(self):
        eta, total = simulation.noise(row(), scales(), 32)
        with self.assertRaisesRegex(ValueError, 'Draw dimensions differ'):
            coordinates.inverse(np.tile([.25]*4, (31, 1)), row()['groups'], eta, total)


class SharedStreamTests(unittest.TestCase):
    def test_prefix_antithetic_and_independent_layer_streams(self):
        r = row()
        short, _ = simulation.noise(r, scales(), 128)
        long, _ = simulation.noise(r, scales(), 256)
        changed, _ = simulation.noise(dict(r, layer='candidate'), scales(), 128)
        for key in short:
            np.testing.assert_array_equal(short[key], long[key][:128])
            np.testing.assert_allclose(short[key][::2], -short[key][1::2], rtol=0, atol=1e-15)
            self.assertFalse(np.array_equal(short[key], changed[key]))

    def test_shared_noise_retains_dependence_across_seats(self):
        first, _ = simulation.noise(row(seat='one'), scales(.2, 0), 128)
        second, _ = simulation.noise(row(seat='two'), scales(.2, 0), 128)
        for key in first:
            np.testing.assert_array_equal(first[key], second[key])
        independent, _ = simulation.noise(row(seat='two'), scales(0, .2), 128)
        own, _ = simulation.noise(row(seat='one'), scales(0, .2), 128)
        self.assertFalse(np.array_equal(independent['balance'], own['balance']))
        self.assertFalse(np.array_equal(independent['within'], own['within']))

    def test_implied_major_log_ratio_variance_independent_of_option_count(self):
        first, total = simulation.noise(row(), scales(.1, .2), 8192)
        other, _ = simulation.noise(row(['national', 'labour']+['other']*15), scales(.1, .2), 8192)
        np.testing.assert_array_equal(first['balance'], other['balance'])
        self.assertAlmostEqual(total['balance']**2, .1**2+.2**2, places=15)
        self.assertLess(abs(np.var(first['balance'])/total['balance']**2-1), .06)

    def test_balanced_cached_national_indices_keep_original_draw_identity(self):
        short = streams.national_indices((4, 2000, 6), 1024)
        complete = streams.national_indices((4, 2000, 6), 8000)
        np.testing.assert_array_equal(short, complete[:1024])
        self.assertEqual(len(set(complete.tolist())), 8000)
        self.assertEqual(np.bincount(short//2000).tolist(), [256]*4)


class EarlierMomentTests(unittest.TestCase):
    def test_prior_only_estimate_has_correct_log_odds_units(self):
        result = estimation.fit([row(year=2011)], 'local_party', 2011)
        self.assertEqual(result['trainingYears'], [])
        self.assertEqual(result['status'], 'assumed_prior_only')
        expected = read(common.PREFIX+'/specification.json')['priors']['local_party']
        for name in expected:
            for kind in expected[name]:
                self.assertAlmostEqual(result['scales'][name][kind], expected[name][kind], places=14)
        self.assertEqual(result['contributions']['balance']['shared']['environments'], 0)

    def test_scalar_population_variance_and_shared_squared_mean(self):
        first, second = row(seat='one'), row(seat='two')
        first['actual'], second['actual'] = [.4, .2, .2, .2], [.2, .4, .2, .2]
        result = estimation.environment([first, second])['moments']['balance']
        expected = np.log((.4+1e-6)/(.2+1e-6))
        self.assertAlmostEqual(result['shared'], 0, places=14)
        self.assertAlmostEqual(result['seat'], expected**2, places=14)
        self.assertEqual(result['records'], 2)

    def test_equal_election_weight_not_more_weight_for_more_seats(self):
        first, second = row(year=2011), row(year=2014)
        first['actual'], second['actual'] = [.5, .2, .2, .1], [.3, .4, .2, .1]
        simple = estimation.fit([first, second], 'local_party', 2017)
        many = estimation.fit([first]+[dict(second, targetElectorateId=str(i)) for i in range(12)],
                              'local_party', 2017)
        for coordinate in ('balance', 'mass', 'within'):
            for kind in ('shared', 'seat'):
                self.assertAlmostEqual(simple['scales'][coordinate][kind], many['scales'][coordinate][kind], places=12)

    def test_holdout_and_future_outcomes_cannot_enter_chronological_scales(self):
        rows = [row(year=y, seat=str(y)) for y in (2011, 2014, 2017)]
        before = estimation.fit(rows, 'local_party', 2014)
        changed = deepcopy(rows)
        changed[1]['actual'] = changed[2]['actual'] = [.9, .01, .01, .08]
        self.assertEqual(before, estimation.fit(changed, 'local_party', 2014))
        changed[0]['actual'] = [.9, .01, .01, .08]
        self.assertNotEqual(before['scales'], estimation.fit(changed, 'local_party', 2014)['scales'])

    def test_shrinkage_contributions_reconstruct_variance_in_exact_units(self):
        first = row(year=2011)
        first['actual'] = [.5, .2, .2, .1]
        result = estimation.fit([first], 'local_party', 2014)
        spec = read(common.PREFIX+'/specification.json')
        for name in ('balance', 'mass', 'within'):
            for kind in ('shared', 'seat'):
                contribution = result['contributions'][name][kind]
                variance = contribution['historicalVarianceContribution'] + contribution['priorVarianceContribution']
                self.assertAlmostEqual(result['scales'][name][kind]**2, variance, places=14)
                self.assertAlmostEqual(contribution['priorSD'], spec['priors']['local_party'][name][kind], places=14)
                environments = contribution['environments']
                self.assertAlmostEqual(contribution['priorVarianceContribution'],
                                       3*contribution['priorSD']**2/(environments+3), places=14)

    def test_single_remainder_option_does_not_create_within_evidence(self):
        r = row(['national', 'labour', 'other'])
        result = estimation.fit([r], 'local_party', 2014)
        self.assertEqual(result['moments'][0]['moments']['within']['records'], 0)
        for kind in ('shared', 'seat'):
            self.assertEqual(result['contributions']['within'][kind]['environments'], 0)

    def test_absent_coordinate_is_missing_not_zero_evidence(self):
        r = row(['national', 'other', 'other'])
        result = estimation.fit([r], 'local_party', 2014)
        self.assertEqual(result['contributions']['balance']['seat']['environments'], 0)
        self.assertAlmostEqual(result['scales']['balance']['seat'], .15, places=14)
        self.assertEqual(result['contributions']['mass']['seat']['environments'], 1)

    def test_disconnected_remainder_labels_abstain_from_shared_fit_without_pseudoinverse(self):
        first, second = row(seat='first'), row(seat='second')
        first['ballotGroupKeys'] = ['national', 'labour', 'a', 'b']
        second['ballotGroupKeys'] = ['national', 'labour', 'c', 'd']
        first['actual'] = second['actual'] = [.3, .3, .3, .1]
        moment = estimation.environment([first, second])['moments']['within']
        self.assertIsNone(moment['shared'])
        self.assertEqual(moment['rank'], 2)
        self.assertEqual(moment['columns'], 3)
        self.assertTrue(all(v == 0 for v in moment['classEffects'].values()))
        residual = np.log((.3+1e-6)/(.1+1e-6))/2
        self.assertAlmostEqual(moment['seat'], 2*residual**2, places=14)

    def test_rank_failure_preserves_unprojected_minor_errors(self):
        r = row(['national', 'labour', 'other', 'other'])
        r['ballotGroupKeys'] = ['national', 'labour', 'same', 'same']
        r['actual'] = [.3, .3, .3, .1]
        moment = estimation.environment([r])['moments']['within']
        self.assertIsNone(moment['shared'])
        # A single shared label cancels under projection; it cannot establish a shared scale.
        self.assertEqual(moment['rank'], 0)
        residual = np.log((.3+1e-6)/(.1+1e-6))/2
        self.assertAlmostEqual(moment['seat'], 2*residual**2, places=14)


class ActualAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = read(common.OLD+'/inventory.json')

    def test_inventory_retains_continuous_means_and_complete_candidates(self):
        self.assertEqual(len(self.inventory['partyRecords']), 321)
        self.assertEqual(len(self.inventory['candidateRecords']), 257)
        self.assertEqual(sum(len(r['ids']) for r in self.inventory['candidateRecords']), 1902)
        for r in self.inventory['candidateRecords']:
            expected = 'Stage43 continuous joint' if r['targetYear'] in (2014, 2020) else 'Stage33 primary_fixed_to_observed joint'
            self.assertEqual(r['predictionReference'], expected)
            self.assertTrue(all(int(cid.split('-')[2]) < r['targetYear'] for cid in r['trainingIds']))

    def test_actual_row_outcomes_do_not_enter_component_or_composed_predictions(self):
        candidate = next(r for r in self.inventory['candidateRecords'] if r['targetYear'] == 2020)
        party = next(r for r in self.inventory['partyRecords'] if r['targetElectorateId'] == candidate['targetElectorateId'])
        altered = deepcopy(candidate)
        altered['actual'] = altered['actual'][::-1]
        altered['winnerId'] = 'synthetic-changing-evaluation-only'
        q, meta = simulation.component(candidate, scales(), 32)
        q2, meta2 = simulation.component(altered, scales(), 32)
        np.testing.assert_array_equal(q, q2)
        self.assertEqual(meta, meta2)
        national = np.tile(np.repeat(1/len(party['ids']), len(party['ids'])), (32, 1))
        a, audit = simulation.compose(party, candidate, national, scales(), scales())
        changed_party = deepcopy(party)
        changed_party['actual'] = changed_party['actual'][::-1]
        b, audit2 = simulation.compose(changed_party, altered, national, scales(), scales())
        np.testing.assert_array_equal(a, b)
        self.assertEqual(audit, audit2)
        self.assertFalse(audit['nationalRedrawn'])

    def test_actual_pipeline_target_candidate_outcomes_change_only_evaluation(self):
        elections = {y: read(f'data/processed/elections/{y}.json') for y in (2008, 2011, 2014, 2017, 2020, 2023)}
        modified = deepcopy(elections)
        for seat in modified[2020]['electorates']:
            if len(seat['candidates']) > 1:
                a, b = seat['candidates'][:2]
                a['votes'], b['votes'] = b['votes'], a['votes']
                seat['winnerCandidateId'] = a['id']
        rebuilt = inventory_build(modified)
        for old, new in zip(self.inventory['candidateRecords'], rebuilt['candidateRecords']):
            self.assertEqual({k:v for k,v in old.items() if k not in ('actual', 'winnerId')},
                             {k:v for k,v in new.items() if k not in ('actual', 'winnerId')})
        self.assertEqual(self.inventory['partyRecords'], rebuilt['partyRecords'])
        self.assertEqual(estimation.fit(self.inventory['candidateRecords'], 'candidate', 2020),
                         estimation.fit(rebuilt['candidateRecords'], 'candidate', 2020))

    def test_neutral_missing_features_are_retained_without_mean_refitting(self):
        seen = 0
        for r in self.inventory['candidateRecords']:
            for feature in r['features']:
                if feature['supportedMass']['R'] == 0:
                    self.assertEqual(feature['centered'][1], 0)
                    seen += 1
            frozen = deepcopy(r['parameters'])
            simulation.component(r, scales(), 8)
            self.assertEqual(r['parameters'], frozen)
        self.assertGreater(seen, 0)

    def test_source_only_residual_evidence_never_transfers_outgoing_candidate_history(self):
        supported = 0
        for r in self.inventory['candidateRecords']:
            for feature in r['features']:
                if feature['supportedMass']['R'] == 0:
                    continue
                sources = set()
                for evidence in feature['residualEvidence']:
                    if evidence.get('sourceOccurrenceId'):
                        sources.add(evidence['sourceOccurrenceId'])
                        self.assertTrue(evidence['edgeId'].endswith('->'+feature['id']))
                        self.assertEqual(int(evidence['sourceOccurrenceId'].split('-')[2]), r['sourceYear'])
                        self.assertIn(evidence['evidenceTier'],
                                      ('accepted_algorithmic_same_person', 'documentary_same_person'))
                        self.assertNotIn('targetResidual', evidence)
                self.assertEqual(len(sources), 1)
                supported += 1
        self.assertGreater(supported, 0)

    def test_consumed_sources_and_prior_artifacts_are_pinned(self):
        common.verify()
        contract = read(common.PREFIX+'/input-contract.json')
        self.assertIn(common.OLD+'/inventory.json', contract['inputHashes'])
        self.assertIn(common.OLD+'/scales.json', contract['inputHashes'])

    def test_transitive_helper_changes_invalidate_the_signature(self):
        path = 'scripts/polling/candidate_integration/propagation.py'
        contract = read(common.PREFIX+'/input-contract.json')
        self.assertIn(path, contract['producerDependencyAudit']['helperPaths'])
        before = common.signature()
        original = common.digest
        with patch.object(common, 'digest', side_effect=lambda p: 'synthetic-changed-byte' if p == path else original(p)):
            self.assertNotEqual(before, common.signature())
            with self.assertRaisesRegex(ValueError, 'Changed consumed input'):
                common.verify()


class FrozenConvergenceTests(unittest.TestCase):
    def run_synthetic_convergence(self, values):
        spec = read(common.PREFIX+'/specification.json')
        inventory = {'partyRecords': [], 'candidateRecords': []}
        representative = row()
        def sealed(layer, year, rows, draws, *args):
            return {'id': 'local_party:2011', 'draws': draws}
        def monitor(case, rows):
            value = values[case['draws']]
            return {policy: [{'id': 'synthetic', 'meanPP': [value], 'crpsPP': [value],
                              'width90PP': [value]}]
                    for policy in ('revised', 'unchanged_stage44')}
        with patch.object(construction, 'inputs', return_value=(inventory, {}, {})), \
                patch.object(construction, 'read', return_value=spec), \
                patch.object(construction, 'cases', return_value=[('local_party', 2011, [representative])]), \
                patch.object(construction, 'case_build', side_effect=sealed), \
                patch.object(construction, 'monitored', side_effect=monitor):
            return construction.convergence()

    def test_stops_at_first_fixed_gate_success_without_more_draws(self):
        result = self.run_synthetic_convergence({1024: 1., 2048: 1.02})
        self.assertEqual(result['selectedDraws'], 2048)
        self.assertTrue(result['converged'])
        self.assertEqual([r['draws'] for r in result['rounds']], [1024, 2048])
        self.assertFalse(result['capReached'])

    def test_uses_frozen_cap_and_records_nonconvergence_without_relaxing_tolerances(self):
        result = self.run_synthetic_convergence({1024: 1., 2048: 2., 4096: 3., 8000: 4.})
        self.assertEqual(result['selectedDraws'], 8000)
        self.assertFalse(result['converged'])
        self.assertTrue(result['capReached'])
        self.assertEqual(result['status'], 'cap_used_precision_gate_unmet')
        self.assertEqual([r['draws'] for r in result['rounds']], [1024, 2048, 4096, 8000])
        self.assertIn('no further count or tolerance change', result['action'])


class CacheTests(unittest.TestCase):
    def test_npz_runtime_manifest_reuse_requires_exact_bytes_and_matching_contract(self):
        with TemporaryDirectory(prefix='stage45-synthetic-npz-') as directory:
            root = Path(directory)
            with patch.object(construction, 'ROOT', root), patch.object(transport_common, 'ROOT', root), \
                    patch.object(construction, 'signature', return_value='synthetic-signature'):
                bank = {'revised:synthetic-seat': np.array([[.4, .6], [.6, .4]])}
                metadata = {'kind': 'synthetic', 'records': [{'id': 'synthetic-seat', 'mean': [.5, .5]}]}
                case = construction.seal('local_party:2014', 2, 'synthetic', bank, metadata)
                self.assertEqual(construction.restore('local_party:2014', 2, 'synthetic'), case)
                with construction.arrays(case) as restored:
                    np.testing.assert_array_equal(restored['revised:synthetic-seat'], bank['revised:synthetic-seat'])
                committed = deepcopy(case)
                committed['drawCache']['sha256'] = 'different-platform-last-bit-compression'
                with construction.arrays(committed) as restored:
                    np.testing.assert_array_equal(restored['revised:synthetic-seat'], bank['revised:synthetic-seat'])
                changed = deepcopy(case)
                changed['records'][0]['id'] = 'wrong-seat'
                with self.assertRaisesRegex(ValueError, 'compatible construction'):
                    construction.arrays(changed)
                changed = deepcopy(case)
                changed['records'][0]['mean'][0] += 2e-10
                with self.assertRaisesRegex(ValueError, 'compatible construction'):
                    construction.arrays(changed)
                with self.assertRaisesRegex(ValueError, 'Changed deterministic cached'):
                    construction.seal('local_party:2014', 2, 'synthetic',
                                      {'revised:synthetic-seat': np.array([[.3, .7], [.6, .4]])}, metadata)
                with patch.object(construction, 'signature', return_value='wrong-signature'):
                    self.assertIsNone(construction.restore('local_party:2014', 2, 'synthetic'))
                    with self.assertRaisesRegex(ValueError, 'compatible construction'):
                        construction.arrays(case)
                (root/case['drawCache']['path']).write_bytes(b'corrupt npz bytes')
                with self.assertRaisesRegex(ValueError, 'Corrupt Stage45 cache'):
                    construction.arrays(case)

    def test_exact_cache_signature_and_byte_integrity(self):
        with TemporaryDirectory(prefix='stage45-synthetic-cache-') as directory:
            with patch.object(common, 'ROOT', Path(directory)):
                value = {'ids': ['synthetic:0'], 'vectors': [[.4, .6]]}
                result = common.cache('local_party:2014', value, 'synthetic-signature')
                file = Path(directory)/result['path']
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), result['sha256'])
                self.assertEqual(common.cache('local_party:2014', value, 'synthetic-signature'), result)
                with self.assertRaisesRegex(ValueError, 'Changed deterministic'):
                    common.cache('local_party:2014', {'vectors': [[.5, .5]]}, 'synthetic-signature')
                file.write_bytes(b'corrupt')
                with self.assertRaisesRegex(ValueError, 'Changed deterministic'):
                    common.cache('local_party:2014', value, 'synthetic-signature')
                other = common.cache('local_party:2014', value, 'different-signature')
                self.assertNotEqual(result['path'], other['path'])


if __name__ == '__main__':
    unittest.main()
