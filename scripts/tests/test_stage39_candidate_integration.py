"""Synthetic connection checks and preserved-source adapter tests; no inference."""
import copy
import unittest
from math import exp, fsum
import numpy as np

from scripts.polling.candidate_integration.common import (
    ROOT, DESIGN, PARTY, CATEGORY, CANDIDATE, read,
)
from scripts.polling.candidate_integration.inventory import build, weights, EXPLICIT
from scripts.polling.candidate_integration.adapter import allocate_draws
from scripts.polling.candidate_integration.propagation import (
    local_vectors, candidate_vectors, propagate, prepare_seat, source_affinities,
)
from scripts.polling.candidate_integration.construction import reproduction, store_draws, signature
from scripts.polling.candidate_integration.evaluation import summary
from scripts.models.joint_candidate_share.metrics import score


def synthetic_roster():
    return [
        {'categoryId': 'nationalparty', 'ballotGroupKey': 'nationalparty',
         'relationship': 'continuing', 'priorShare': .4},
        {'categoryId': 'conservative', 'ballotGroupKey': 'conservative',
         'relationship': 'continuing', 'priorShare': .04},
        {'categoryId': 'unitedfuture', 'ballotGroupKey': 'unitedfuture',
         'relationship': 'continuing', 'priorShare': .002},
        {'categoryId': 'freedomsnz', 'ballotGroupKey': 'freedomsnz',
         'relationship': 'entrant', 'priorShare': None},
        {'categoryId': 'maoriparty', 'ballotGroupKey': 'maoriparty',
         'relationship': 'continuing', 'priorShare': .01},
    ]


class AllocationTests(unittest.TestCase):
    def test_raw_nc_uf_explicit_and_other_mass(self):
        cats = ['National', 'New Conservative', 'United Future', 'Other']
        mapping = {k: EXPLICIT[k] for k in cats[:-1]}
        roster = synthetic_roster()
        allocation = weights(roster, set(mapping.values()), [], 'prior_only')
        draws = np.array([[.7, .04, .01, .25], [.6, .08, .02, .3]])
        q = allocate_draws(draws, cats, roster, allocation, mapping)
        np.testing.assert_array_equal(q[:, :3], draws[:, :3])
        np.testing.assert_allclose(q[:, 3:].sum(1), draws[:, -1], atol=1e-12)
        np.testing.assert_allclose(q.sum(1), 1, atol=1e-12)
        self.assertEqual([r['categoryId'] for r in allocation], ['freedomsnz', 'maoriparty'])
        self.assertEqual(allocation[0]['weight'], .001)

    def test_zero_other_keeps_all_roster_categories(self):
        cats = ['National', 'Other']; mapping = {'National': 'nationalparty'}
        roster = synthetic_roster()
        allocation = weights(roster, {'nationalparty'}, [], 'prior_only')
        q = allocate_draws(np.array([[1., 0.]]), cats, roster, allocation, mapping)
        np.testing.assert_array_equal(q, [[1., 0., 0., 0., 0.]])

    def test_missing_mapping_duplicate_groups_and_overlapping_recipients(self):
        roster = synthetic_roster(); cats = ['National', 'Other']
        mapping = {'National': 'nationalparty'}
        allocation = weights(roster, {'nationalparty'}, [], 'prior_only')
        for bad_mapping in ({}, {'National': 'absent'}, {'National': 'nationalparty', 'Other': 'maoriparty'}):
            with self.assertRaises(ValueError):
                allocate_draws(np.array([[.8, .2]]), cats, roster, allocation, bad_mapping)
        duplicate = copy.deepcopy(roster); duplicate[3]['ballotGroupKey'] = 'unitedfuture'
        with self.assertRaises(ValueError):
            allocate_draws(np.array([[.8, .2]]), cats, duplicate, allocation, mapping)
        overlap = copy.deepcopy(allocation); overlap[0]['categoryId'] = 'nationalparty'
        with self.assertRaises(ValueError):
            allocate_draws(np.array([[.8, .2]]), cats, roster, overlap, mapping)
        with self.assertRaises(ValueError):
            allocate_draws(np.array([[.8, .2]]), cats, roster, allocation[:-1], mapping)

    def test_invalid_draws_and_nonconserving_fractions(self):
        roster = synthetic_roster(); cats = ['National', 'Other']
        mapping = {'National': 'nationalparty'}
        allocation = weights(roster, {'nationalparty'}, [], 'prior_only')
        for x in ([.8, .2], [[.8, .1]], [[-.1, 1.1]], [[float('nan'), .2]], [[.8, .2, 0]]):
            with self.assertRaises(ValueError):
                allocate_draws(np.array(x), cats, roster, allocation, mapping)
        changed = copy.deepcopy(allocation); changed[0]['allocationFraction'] += .1
        with self.assertRaises(ValueError):
            allocate_draws(np.array([[.8, .2]]), cats, roster, changed, mapping)

    def test_reports_are_relative_weights_not_draw_constraints(self):
        roster = synthetic_roster()
        reports = [{'categoryId': 'maoriparty', 'pollster': 'P', 'pollId': 'synthetic',
                    'ageDays': 5, 'rawWeight': 1., 'share': .03}]
        allocation = weights(roster, {'nationalparty'}, reports, 'recent_report_prior')
        self.assertEqual(next(r for r in allocation if r['categoryId'] == 'maoriparty')['weight'], .03)
        q = allocate_draws(np.array([[.9, .1]]), ['National', 'Other'], roster, allocation,
                           {'National': 'nationalparty'})
        self.assertNotEqual(q[0, -1], .03)
        np.testing.assert_allclose(q[:, 1:].sum(1), [.1], atol=1e-12)


class PropagationTests(unittest.TestCase):
    def test_affinity_rule_uses_every_party_and_zero_affinity(self):
        fine = np.array([[.6, .3, .1], [.2, .4, .4]])
        affinities = np.array([2., .5, 0.])
        local = local_vectors(fine, affinities)
        expected = fine * affinities
        expected /= expected.sum(1, keepdims=True)
        np.testing.assert_allclose(local, expected, atol=1e-15)
        np.testing.assert_array_equal(local[:, -1], [0, 0])
        # Neutral entrant affinity1 keeps possible support, rather than fabricating a source zero.
        np.testing.assert_allclose(local_vectors(fine, np.ones(3)), fine, atol=1e-15)

    def test_candidate_intensities_and_no_group_floor(self):
        local = np.array([[.5, .3, .2], [.2, .7, .1]])
        destinations = np.array([0, 1, -1]); exponents = np.array([.2, -.1, 0.])
        q = candidate_vectors(local, destinations, exponents, .02)
        for d, vec in enumerate(local):
            w = [(vec[0] + .02)*exp(.2), (vec[1] + .02)*exp(-.1), .02]
            np.testing.assert_allclose(q[d], np.array(w)/fsum(w), atol=1e-15)
        self.assertTrue((q[:, -1] > 0).all())
        np.testing.assert_allclose(q.sum(1), 1, atol=1e-12)

    def test_absent_candidate_group_remains_in_local_vector(self):
        fine = np.array([[.4, .3, .3]])
        local = local_vectors(fine, np.array([2., 1., 4.]))
        self.assertGreater(local[0, 2], 0)
        q = candidate_vectors(local, np.array([0, -1]), np.zeros(2), .01)
        expected = (local[0, 0] + .01)/(local[0, 0] + .02)
        self.assertAlmostEqual(q[0, 0], expected)

    def test_shared_group_single_destination_not_duplicated(self):
        q = candidate_vectors(np.array([[.6, .4]]), np.array([0, 1, -1]), np.zeros(3), .01)
        np.testing.assert_allclose(q, [[.61/1.03, .41/1.03, .01/1.03]], atol=1e-15)
        with self.assertRaises(ValueError):
            candidate_vectors(np.array([[.6, .4]]), np.array([0, 0, -1]), np.zeros(3), .01)

    def test_shared_draws_batching_and_nonlinear_expectations(self):
        fine = np.array([[.99, .01], [.01, .99], [.4, .6]])
        args = (np.array([4., .25]), np.array([0, 1, -1]), np.array([.6, -.2, 0.]), .015)
        q = propagate(fine, *args, batch_size=1)
        for batch in (2, 256):
            np.testing.assert_array_equal(propagate(fine, *args, batch_size=batch), q)
        # Every seat consumes the same row-order national scenarios, with no resampling.
        np.testing.assert_array_equal(propagate(fine[[2, 0, 1]], *args), q[[2, 0, 1]])
        shortcut = propagate(fine.mean(0, keepdims=True), *args)[0]
        self.assertGreater(float(np.max(np.abs(q.mean(0) - shortcut))), .01)

    def test_extreme_valid_input_and_stable_exponents(self):
        q = propagate(np.array([[1., 0., 0.], [0., 0., 1.]]), np.ones(3),
                      np.array([0, 1, -1]), np.array([700., -700., 0.]), .0001)
        self.assertTrue(np.isfinite(q).all())
        self.assertTrue((q >= 0).all())
        np.testing.assert_allclose(q.sum(1), 1, atol=1e-12)

    def test_invalid_affinities_destinations_shapes_and_zero_mass(self):
        fine = np.array([[.6, .4]])
        for affinity in (np.array([0., 0.]), np.array([-1., 1.]), np.array([1.]), np.array([1., np.nan])):
            with self.assertRaises(ValueError):
                local_vectors(fine, affinity)
        for dest in (np.array([0, 2]), np.array([0, -2]), np.array([0., .5])):
            with self.assertRaises(ValueError):
                candidate_vectors(fine, dest, np.zeros(2), .01)
        with self.assertRaises(ValueError):
            candidate_vectors(fine, np.array([0, 1]), np.zeros(1), .01)
        for floor in (0., .2, np.nan):
            with self.assertRaises(ValueError):
                candidate_vectors(fine, np.array([0, 1]), np.zeros(2), floor)


class EvaluationArithmeticTests(unittest.TestCase):
    def test_paired_signs_group_denominators_and_complete_slate_metrics(self):
        row = {'candidates': [
            {'targetOccurrenceId': cid, 'partyBallotGroupKey': group,
             'R': {'broad': {'availabilityPattern': 'neither_feature'}}}
            for cid, group in [('N', 'nationalparty'), ('L', 'labourparty'), ('I', None)]]}
        actual = {'candidateShares': {'N': .5, 'L': .3, 'I': .2}, 'winnerCandidateId': 'N'}
        predictions = {'baseline': {'N': .4, 'L': .4, 'I': .2},
                       'baseline_plus_S': {'N': .45, 'L': .35, 'I': .2},
                       'baseline_plus_S_plus_R': {'N': .5, 'L': .3, 'I': .2}}
        scores = {m: score(q, actual, row, 'broad') for m, q in predictions.items()}
        result = summary([{'targetElectorateId': 'synthetic-contest', 'scores': scores}])
        self.assertAlmostEqual(result['methods']['baseline']['contestEqualMaePP'], 20/3)
        self.assertAlmostEqual(result['methods']['baseline']['contestEqualRmsePP'], (200/3)**.5)
        self.assertAlmostEqual(result['pairs']['baseline_plus_S__versus__baseline']['maeImprovementPP'], 10/3)
        self.assertEqual(result['groups']['national_labour']['candidates'], 2)
        self.assertEqual(result['groups']['affirmative_no_party_group']['presentContests'], 1)
        self.assertAlmostEqual(result['groups']['national']['methods']['baseline']['candidateEqualSignedBiasPP'], -10)
        self.assertAlmostEqual(result['groups']['labour']['methods']['baseline']['candidateEqualSignedBiasPP'], 10)
        self.assertAlmostEqual(result['methods']['baseline']['fullSlateSignedBiasPPAccounting'], 0)

    def test_tied_winner_is_not_broken_using_observed_winner(self):
        row = {'candidates': [{'targetOccurrenceId': cid, 'partyBallotGroupKey': group,
                              'R': {'broad': {'availabilityPattern': 'neither_feature'}}}
                             for cid, group in [('N', 'nationalparty'), ('L', 'labourparty')]]}
        actual = {'candidateShares': {'N': .6, 'L': .4}, 'winnerCandidateId': 'N'}
        result = score({'N': .5, 'L': .5}, actual, row, 'broad')
        self.assertEqual(set(result['predictedWinnerSet']), {'N', 'L'})
        self.assertFalse(result['uniqueCorrect']); self.assertTrue(result['tieContainsWinner'])
        self.assertAlmostEqual(result['actualTopTwoMarginAbsoluteErrorPP'], 20)
        self.assertAlmostEqual(result['predictedTopTwoGapAbsoluteErrorPP'], 20)


class ActualInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.construction = read(CANDIDATE/'construction.json')
        cls.design = read(DESIGN/'inventory.json')
        cls.party = read(PARTY/'input-inventory.json')
        cls.categories = read(CATEGORY/'inventory.json')
        cls.polls = read(ROOT/'data/processed/polling/national-foundation/polls.json')['records']
        cls.inventory = build(cls.construction, cls.design, cls.party, cls.categories, cls.polls)

    def test_exact_common_slates_parameters_and_means_unchanged(self):
        self.assertEqual([len(c['evaluationIds']) for c in self.inventory['cases']], [64, 34, 64])
        self.assertEqual([len(c['evaluationCandidateIds']) for c in self.inventory['cases']], [431, 286, 459])
        for case in self.inventory['cases']:
            fold = next(f for f in self.construction['folds'] if f['id'] == case['foldId'])
            self.assertEqual(case['trainingOnlyMeans'], fold['trainingOnlyMeans'])
            self.assertEqual(case['evaluationCandidateIds'], fold['evaluationCandidateIds'])
            for model, fit in case['fits'].items():
                self.assertEqual(fit, fold['fits'][model])
            self.assertEqual(case['cutoff'], case['allocationCutoff'][:10])
            self.assertEqual(len(set(case['nationalDrawIds'])), 8000)

    def test_heldout_outcome_and_identity_extras_not_inventory_inputs(self):
        design = copy.deepcopy(self.design)
        construction = copy.deepcopy(self.construction)
        party = copy.deepcopy(self.party)
        for row in design['contestRecords']:
            row['winnerCandidateId'] = 'synthetic-unknown'
            row['targetVotes'] = 987654
            for c in row['candidates']:
                c['candidateVotes'] = 12345; c['winner'] = False
                c['targetResidual'] = 99; c['identityConfidence'] = 'synthetic'
        for fold in construction['folds']:
            fold['evaluationOnlyActuals'] = {'synthetic': 0}
            fold['predictions'] = {}
        for row in party['categoryRelationships']:
            for c in row['categories']:
                c['suppliedTargetNationalShare'] = .999
                c['targetNationalVotesScenario'] = 99999999
        self.assertEqual(build(construction, design, party, self.categories, self.polls), self.inventory)

    def test_2020_mri_and_top_inside_other_2017_explicit_nc_uf(self):
        by_year = {c['year']: c for c in self.inventory['cases']}
        c = by_year[2017]
        self.assertEqual(c['explicitMapping']['New Conservative'], 'conservative')
        self.assertEqual(c['explicitMapping']['United Future'], 'unitedfuture')
        for policy in c['weights'].values():
            self.assertFalse({'conservative', 'unitedfuture'} & {r['categoryId'] for r in policy})
        c = by_year[2020]
        self.assertNotIn('Te Pāti Māori', c['explicitMapping'])
        for policy in c['weights'].values():
            self.assertTrue({'maoriparty', 'theopportunitiespartytop'} <= {r['categoryId'] for r in policy})
        self.assertTrue(any(r['code'] == 'MRI' for r in c['allocationReports']))
        c = by_year[2023]
        self.assertEqual(c['explicitMapping']['TOP'], 'theopportunitiespartytop')
        for policy in c['weights'].values():
            self.assertNotIn('theopportunitiespartytop', {r['categoryId'] for r in policy})
            self.assertEqual(sum(r['categoryId'] == 'freedomsnz' for r in policy), 1)

    def test_actual_draw_allocation_explicit_preservation(self):
        for case in self.inventory['cases']:
            archive = ROOT/f"data/processed/polling/external-comparison/fits/{case['year']}/attempt1.npz"
            with np.load(archive, allow_pickle=False) as data:
                draws = data['electionDay'].reshape(-1, len(case['rawCategories']))[[0, 2000, 7999]]
            fine_ids = [r['categoryId'] for r in case['roster']]
            for policy in case['weights'].values():
                q = allocate_draws(draws, case['rawCategories'], case['roster'], policy, case['explicitMapping'])
                np.testing.assert_allclose(q.sum(1), 1, atol=1e-12)
                for label, cid in case['explicitMapping'].items():
                    np.testing.assert_array_equal(q[:, fine_ids.index(cid)], draws[:, case['rawCategories'].index(label)])

    def test_future_minor_reports_do_not_enter_allocation_weights(self):
        future = copy.deepcopy(self.polls[0]); future['id'] = 'synthetic-future'
        future['cycle'] = 2020; future['publication'] = '2099-01-01T00:00:00+13:00'
        changed = build(self.construction, self.design, self.party, self.categories, self.polls+[future])
        self.assertEqual(changed, self.inventory)

    def test_actual_pipeline_outcome_independence_and_independent_intensities(self):
        rows = {r['targetElectorateId']: r for r in self.design['contestRecords']}
        source = {r['targetElectorateId']: r for r in self.party['partyFrame']}
        categories = {r['targetYear']: r['categories'] for r in self.party['categoryRelationships']}
        for case in self.inventory['cases']:
            cid = case['evaluationIds'][0]; row = rows[cid]
            a, _ = source_affinities(source[cid], categories[case['year']], case['roster'])
            fine = np.full((1, len(case['roster'])), 1/len(case['roster']))
            changed = copy.deepcopy(row)
            changed['winnerCandidateId'] = 'synthetic-impossible'
            for candidate in changed['candidates']:
                candidate['winner'] = True; candidate['candidateVotes'] = 987654
                candidate['targetResidual'] = -123; candidate['identityConfidence'] = 'unknown'
                candidate['observedPartySupport'] = .999
                candidate['constructedPartySupport'] = .001
            for model in case['fits']:
                dest, z, floor = prepare_seat(row, case, model)
                d2, z2, f2 = prepare_seat(changed, case, model)
                np.testing.assert_array_equal(d2, dest); np.testing.assert_array_equal(z2, z)
                self.assertEqual(f2, floor)
                q = propagate(fine, a, dest, z, floor)[0]
                np.testing.assert_array_equal(propagate(fine, a, d2, z2, f2)[0], q)
                # Independent direct reductions use the same complete national denominator.
                masses = [float(x)*float(affinity) for x, affinity in zip(fine[0], a)]
                local = [m/fsum(masses) for m in masses]
                intensity = [(local[d] + floor if d >= 0 else floor)*exp(float(v)) for d, v in zip(dest, z)]
                np.testing.assert_allclose(q, [w/fsum(intensity) for w in intensity], atol=1e-12, rtol=0)

    def test_neutral_missing_features_and_affirmative_no_group(self):
        case = self.inventory['cases'][0]
        row = copy.deepcopy(next(r for r in self.design['contestRecords'] if r['targetElectorateId'] == case['evaluationIds'][0]))
        candidate = row['candidates'][0]
        candidate['s0Reported'] = None
        candidate['R']['broad']['valueFraction'] = None
        candidate['partyBallotGroupKey'] = None
        candidate['mappingStatus'] = 'verified_no_party_group_synthetic'
        d, z, _ = prepare_seat(row, case, 'baseline_plus_S_plus_R')
        self.assertEqual(d[0], -1); self.assertEqual(z[0], 0)
        # A replacement's unsupported personal history stays neutral even if unrelated
        # outgoing-residual or target-residual fields are attached to the row.
        candidate['outgoingResidual'] = .9; candidate['targetResidual'] = .8
        _, changed, _ = prepare_seat(row, case, 'baseline_plus_S_plus_R')
        np.testing.assert_array_equal(changed, z)
        candidate['mappingStatus'] = 'ambiguous'
        with self.assertRaises(ValueError):
            prepare_seat(row, case, 'baseline_plus_S_plus_R')

    def test_actual_original_conditional_predictions_reproduce(self):
        rows = {r['targetElectorateId']: r for r in self.design['contestRecords']}
        source = {r['targetElectorateId']: r for r in self.party['partyFrame']}
        categories = {r['targetYear']: r['categories'] for r in self.party['categoryRelationships']}
        for case in self.inventory['cases']:
            saved = next(f for f in self.construction['folds'] if f['id'] == case['foldId'])
            for cid in (case['evaluationIds'][0], case['evaluationIds'][-1]):
                gaps = reproduction(case, rows[cid], source[cid], categories[case['year']], saved)
                self.assertTrue(all(v <= 1e-12 for v in gaps.values()))

    def test_draw_cache_check_is_reversible_and_deterministic(self):
        # Check mode does not create an absent local cache; no historical file is touched.
        name = 'synthetic-unit-cache-not-written.json.gz'
        a = store_draws(name, {'drawIds': ['synthetic-1'], 'shares': [[.5, .5]]}, check=True)
        b = store_draws(name, {'shares': [[.5, .5]], 'drawIds': ['synthetic-1']}, check=True)
        self.assertEqual(a, b)
        self.assertFalse((ROOT/a['path']).exists())

    def test_cached_construction_signature_includes_batch_and_source_affinity_ignores_target_values(self):
        self.assertEqual(signature(256), signature(256))
        self.assertNotEqual(signature(256), signature(1))
        case = self.inventory['cases'][0]
        source = next(r for r in self.party['partyFrame'] if r['targetElectorateId'] == case['evaluationIds'][0])
        categories = next(r['categories'] for r in self.party['categoryRelationships'] if r['targetYear'] == case['year'])
        a, states = source_affinities(source, categories, case['roster'])
        changed = copy.deepcopy(categories)
        for c in changed:
            c['suppliedTargetNationalShare'] = .999
            c['targetNationalVotesScenario'] = 987654321
        other, other_states = source_affinities(source, changed, case['roster'])
        np.testing.assert_array_equal(other, a)
        self.assertEqual(other_states, states)


if __name__ == '__main__':
    unittest.main()
