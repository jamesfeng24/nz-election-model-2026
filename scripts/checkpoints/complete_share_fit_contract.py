"""Freeze Stage 20's next-stage four-model contract without fitting or scoring."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.checkpoints.complete_share_feature_run import DEST, ROOT, digest, encode, read


INVENTORY = 'data/processed/checkpoints/complete-share-feature-applicability/feature-inventory.json'
AUDIT = 'data/processed/checkpoints/complete-share-feature-applicability/design-audit.json'
SOURCE = 'data/processed/checkpoints/complete-share-feature-applicability/source-contract.json'
MANIFEST = 'data/processed/checkpoints/complete-share-feature-applicability/manifest.json'
PROPOSAL = 'data/processed/checkpoints/model-failure-diagnostics/proposed-experiments.json'


def candidate_ids(contests):
    return [candidate['targetOccurrenceId']
            for seat in contests for candidate in seat['candidates']]


def build():
    inventory, audit, pinned = read(INVENTORY), read(AUDIT), read(MANIFEST)
    if not audit['allFittingGatesPass']:
        raise ValueError('Predeclared Stage 20 coverage or rank gate failed')
    for name, path in (('feature-inventory.json', INVENTORY),
                       ('design-audit.json', AUDIT), ('source-contract.json', SOURCE)):
        if digest(path) != pinned['outputSha256'][name]:
            raise ValueError('Changed committed pre-fit evidence inventory')
    by_year = {year: [r for r in inventory['records'] if r['targetYear'] == year
                      and r['status'] == 'constructed'] for year in (2011, 2017, 2023)}
    folds = []
    for record in audit['folds']:
        holdout = record['targetYear']
        training = [r for year in record['trainingTargetYears'] for r in by_year[year]]
        evaluation = by_year[holdout]
        if ([r['targetElectorateId'] for r in training] != record['trainingContestIds'] or
                [r['targetElectorateId'] for r in evaluation] != record['evaluationContestIds']):
            raise ValueError('Stage 20 common sample changed')
        folds.append({'targetYear': holdout,
                      'trainingTargetYears': record['trainingTargetYears'],
                      'trainingContestIds': record['trainingContestIds'],
                      'trainingCandidateOccurrenceIds': candidate_ids(training),
                      'commonEvaluationContestIds': record['evaluationContestIds'],
                      'commonEvaluationCandidateOccurrenceIds': candidate_ids(evaluation),
                      'trainingOnlyFeatureMeansFromAudit': record['trainingOnlyMeans'],
                      'trainingContests': len(training), 'evaluationContests': len(evaluation),
                      'trainingCandidates': len(candidate_ids(training)),
                      'evaluationCandidates': len(candidate_ids(evaluation))})
    contract = {
        'schemaVersion': 1, 'stage': 20,
        'status': 'fit_ready_proposal_frozen_before_any_stage20_or_later_fit_or_score',
        'authorization': 'separate_future_stage_required_for_fitting_or_historical_scoring',
        'estimand': 'conditional_complete_valid_candidate_share_allocation_on_unchanged_boundary_general_contests',
        'informationSet': {'sourceFeatures': 'completed_prior_general_election_official_results',
                           'targetParty': 'observed_target_local_valid_party_share_conditional_only',
                           'targetSlate': 'retrospective_complete_election_local_candidature',
                           'targetCandidateVotesAndWinners': 'training_for_earlier_completed_elections_or_holdout_evaluation_only',
                           'personIdentityAndStatus': 'never_inputs'},
        'units': {'s0': 'fraction_of_source_party_ballot_row_to_unique_source_same_party_candidate',
                  'v0': 'source_candidate_valid_vote_share_minus_source_party_valid_vote_share',
                  'targetPartySupport': 'fraction_of_target_valid_party_votes',
                  'target': 'fraction_of_target_valid_candidate_votes'},
        'features': {'s0WorkingValue': 'published_two_decimal_percentage_divided_by_100_explicit_rounded_approximation',
                     's0FeasibleSet': 'selected_cell_fraction_under_all_source_row_cell_rounding_bounds_and_row_sum_100',
                     'v0': 'source_candidate_votes/source_valid_candidate_votes_minus_source_party_votes/source_valid_party_votes',
                     'noPartyGroup': 'affirmative_stage18_no_group_baseline_support_zero',
                     'missingFeature': 'omit_only_that_adjustment; keep_neutral_party_support_plus_floor; never_impute_zero_observation_or_personal_strength',
                     'stage18AmbiguousMapping': 'whole_contest_abstain',
                     'missingSourceTableOrEligibleRow': 'whole_contest_abstain',
                     'ambiguousContinuityOrSourceCandidateDestination': 'whole_contest_abstain',
                     'unsupportedEntrantOrNoSourceCandidate': 'candidate_level_neutral_fallback',
                     'zeroMassSourceRow': 's0_undefined_v0_can_remain_supported'},
        'formula': 'base_c=P1_party(c)+kappa_or_kappa_for_affirmative_no_group; xS_c=S0_c-muS_if_supported_else_0; xV_c=V0_c-muV_if_supported_else_0; w_c=base_c*exp(thetaS*xS_c+thetaV*xV_c); m_c=w_c/sum_d(w_d)',
        'restrictions': [
            {'id': 'baseline', 'jointParameters': ['kappa']},
            {'id': 'baseline_plus_S', 'jointParameters': ['kappa', 'thetaS']},
            {'id': 'baseline_plus_V', 'jointParameters': ['kappa', 'thetaV']},
            {'id': 'baseline_plus_S_plus_V', 'jointParameters': ['kappa', 'thetaS', 'thetaV']}],
        'ablationComparisons': ['S_vs_baseline', 'V_vs_baseline',
                                'S_plus_V_vs_S', 'S_plus_V_vs_V',
                                'S_plus_V_vs_baseline'],
        'parameterBounds': {'kappa': [0.0001, 0.1],
                            'thetaS': [-4, 4], 'thetaV': [-4, 4],
                            'thetaInterpretation': 'log_intensity_per_unit_fraction_feature; finite_box_prevents_nonexistent_or_extreme_unregularized_solution; exp_4_about_54_6_per_unit',
                            'boundaryHandling': 'report_boundary_optimum; do_not_expand_or_retune_after_scores'},
        'training': {'objective': 'equal_contest_mean_negative_sum_over_candidate_observed_valid_candidate_share_times_log_predicted_share',
                     'candidateWeightWithinContest': 'each_standing_candidate_in_shared_softmax; each_contest_equal_objective_weight',
                     'centering': 'for_each_feature_use_training_only_supported_values_weight_1_over_slate_size_then_normalize_by_total_supported_weight; unsupported_candidate_adjustment_exactly_zero',
                     'chronology': '2017_trains_2011_targets;_2023_trains_2011_and_2017_targets;_2011_no_fitted_model',
                     'allRestrictions': 'independently_and_jointly_refit_on_identical_training_contest_and_candidate_IDs; no_imported_Stage18_kappa_or_Stage8_to_10_effect'},
        'optimizer': {'method': 'deterministic_profile_kappa_with_convex_box_constrained_theta_subproblem',
                      'theta': 'at_each_kappa_use_analytic_gradient_L_BFGS_B_from_fixed_starts_-2_0_2_per_included_coordinate; require_agreeing_objectives_within_1e-8_and_projected_gradient_infinity_at_most_1e-7',
                      'kappa': 'SciPy_SHGO_1D_Sobol_256_points_2_iterations_f_tol_1e-12; explicitly_evaluate_both_bounds_and_all_returned_local_minima',
                      'independentCheck': '4097_point_fixed_uniform_kappa_grid_plus_bounded_local_refinement_of_each_sampled_local_minimum; objective_agreement_1e-8_parameter_agreement_1e-4_unless_flat_tie',
                      'ties': 'objective_within_1e-12_choose_smaller_kappa_then_lexicographically_smaller_thetas',
                      'failure': 'nonfinite_rank_deficient_nonconverged_or_disagreeing_solvers_are_fit_abstention_not_substantive_null'},
        'rounding': {'primary': 'reported_decimal_source_cell_as_working_approximation_not_exact_probability',
                     'coupledWitness': 'for_each_positive_source_party_row_fix_selected_same_party_cell_at_its_exact_coupled_lower_or_upper_bound; initialize_all_other_cells_at_lower_bounds_then_fill_remaining_mass_in_published_column_order_until_row_sum_100',
                     'sensitivity': 'two_predeclared_all_row_lower_and_all_row_upper_joint_feasible_scenarios; recalculate_training_only_means_and_refit_each_restriction_on_same_IDs_for_each_scenario; no_independent_incompatible_cell_endpoints',
                     'interpretation': 'source_publication_rounding_sensitivity_not_future_predictive_interval'},
        'evaluation': {'commonSamples': 'all_four_restrictions_same_ids_with_feature_fallback; no_feature_specific_complete_case_selection',
                       'primaryMae': 'mean_over_contests_of_100_times_mean_candidate_absolute_share_error',
                       'primaryRmse': 'sqrt_mean_over_contests_of_10000_times_mean_candidate_squared_share_error',
                       'candidateEqualSensitivity': 'mean_over_all_common_candidates_then_RMSE_sqrt',
                       'bias': 'overall_full_slate_signed_bias_is_zero_accounting_check; report_category_and_feature_support_bias',
                       'winner': 'predicted_argmax_set_absolute_share_tolerance_1e-12; report_unique_accuracy_and_tie_set_inclusion_separately',
                       'coverage': 'all_213_frame_contests_191_held_general_21_Maori_one_cancelled; full_abstentions_and_supported_fallback_strata',
                       'influence': 'show_five_largest_contest_level_absolute_error_differences_per_fold_and_leave_one_contest_out_gain_range_without_dropping_any_from_primary_score'},
        'benchmarks': {'uniform': 'parameter_free_all_complete_standing_slates_including_2011',
                       'restrictedZeroFloor': 'only_all_mapped_positive_party_support_no_no_group_subset; same_sample_context_not_primary_ablation',
                       '2011': 'no_earlier_eligible_feature_transition_for_fitted_methods'},
        'screen': {'prerequisites': 'at_least_20_constructed_contests_and_20_with_supported_S_in_each_training_and_trained_holdout; within_slate_feature_rank_2_full_floor_rank_3_and_scaled_condition_at_most_1e6_at_fixed_probes',
                   'materiality': 'combined_vs_jointly_refitted_baseline_gain_at_least_0.25pp_contest_equal_MAE_in_each_2017_and_2023_fold',
                   'rmse': 'no_fold_RMSE_regression_of_0.25pp_or_more',
                   'influence': 'leave_one_contest_out_MAE_gain_must_keep_positive_sign_in_each_trained_fold',
                   'rounding': 'no_practical_gain_sign_reversal_under_either_coupled_endpoint_scenario',
                   'interpretation': 'development_screen_only_not_significance_or_operational_selection'},
        'earliestBenchmarkContestIds': [r['targetElectorateId'] for r in by_year[2011]],
        'folds': folds,
        'operationalSelection': None,
        'limitations': ['only_three_previously_inspected_election_transitions',
                        'observed_target_party_and_retrospective_slate_not_as_of_forecast',
                        'source_party_level_features_do_not_establish_personal_transfer',
                        'neutral_fallback_preserves_unknown_strength_uncertainty',
                        'Maori_local_split_route_unavailable',
                        'changed_boundary_2026_candidate_baseline_unidentified',
                        'Stage11_old_exact_seat_name_coverage_requires_separate_correction_before_citing_its_score_as_model_selection_evidence']}
    outputs = {'fit-contract.json': contract}
    outputs['fit-contract-manifest.json'] = {
        'schemaVersion': 1, 'stage': 20, 'phase': 'final_prefit_contract_no_fit_or_score',
        'inputSha256': {path: digest(path) for path in (INVENTORY, AUDIT, SOURCE,
                                                       MANIFEST, PROPOSAL)},
        'generatorSha256': digest('scripts/checkpoints/complete_share_fit_contract.py'),
        'outputSha256': {'fit-contract.json': sha256(encode(contract)).hexdigest()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    for name, data in outputs.items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != encode(data):
                raise ValueError(f'Changed Stage 20 {name}')
        else:
            path.write_bytes(encode(data))
    print({'fitReady': True, 'folds': [(r['targetYear'], r['trainingContests'],
                                       r['evaluationContests'])
                                      for r in outputs['fit-contract.json']['folds']]})


if __name__ == '__main__':
    main()
