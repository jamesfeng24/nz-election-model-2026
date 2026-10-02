"""Declarative, unfitted historical fold and experiment plans for Stage 25."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from itertools import product

from scripts.checkpoints.stage25_geography import ROOT, DEST, read, encode, write_or_check


GEOGRAPHY = 'data/processed/checkpoints/stage25-historical-geography/geography.json'
AVAILABILITY = 'data/processed/checkpoints/stage25-historical-geography/availability.json'
ORIGINAL_DESIGN = 'data/processed/checkpoints/stage25-historical-geography/original-design-contract.json'
ELECTIONS = {year: f'data/processed/elections/{year}.json' for year in (2008, 2011, 2014, 2017, 2020, 2023)}
INPUTS = (GEOGRAPHY, AVAILABILITY, ORIGINAL_DESIGN, *ELECTIONS.values())
FAMILIES = ('nat_lab_response', 'complete_share_baseline_s', 'complete_party_vector',
            'stage11_matched_split', 'source_victory_comparison', 'v_deferred')
PROTOCOLS = ('expanding_window', 'more_separated')


def training_years(target_years, source_year, target_year, protocol):
    """Select completed transitions; publication by a historical cutoff is not certified."""
    if source_year >= target_year:
        raise ValueError('Source must precede target election')
    if protocol not in PROTOCOLS:
        raise ValueError('Unknown chronology protocol')
    return sorted(y for y in set(target_years) if y < target_year and
                  (y <= source_year if protocol == 'expanding_window' else y < source_year))


def preprocessing_plan(training_rows, training_ids, family):
    admitted = [r for r in training_rows if r['targetElectorateId'] in training_ids or
                any(p.get('recordId') in training_ids for p in r['natLab'])]
    return {'trainingContestIds': [r['targetElectorateId'] for r in admitted],
            'trainingCandidateOccurrenceIds': {
                'artifact': AVAILABILITY, 'field': 'candidateOccurrenceIds',
                'selector': 'exact_trainingContestIds_above; no_holdout_or_later_rows'},
            'centering': ('supported_training_values_weight_1_over_slate_size_only; '
                          'neutral_fallback_adjustment_zero; each_rounding_scenario_separate'
                          if family in ('complete_share_baseline_s', 'v_deferred') else
                          'no_feature_centering_in_inherited_specification'),
            'holdoutContributionToFittedPreprocessing': 'forbidden',
            'parameterFree': family in ('complete_party_vector', 'stage11_matched_split')}


def response_training_gates(training_rows):
    """Evidence/count gates only; permitted conditional party movement awaits an adapter."""
    result = {}
    for party in ('nationalparty', 'labourparty'):
        records = [p for r in training_rows for p in r['natLab']
                   if p['status'] == 'available' and p['partyKey'] == party]
        winners = sum(p['sourceVictory'] for p in records)
        result[party] = {'records': len(records), 'sourceWinners': winners,
                         'sourceNonwinners': len(records) - winners,
                         'minimumFiveRecordsPerCoefficientForThreeTermModel': len(records) >= 15,
                         'minimumFiveInEachSourceVictoryGroup': min(winners, len(records)-winners) >= 5}
    return result


def ids_for_family(rows, family):
    ids = []
    for row in rows:
        if family in ('nat_lab_response', 'source_victory_comparison'):
            ids.extend(part['recordId'] for part in row['natLab'] if part['status'] == 'available')
        elif family == 'complete_share_baseline_s':
            if row['completeShare']['status'] == row['sOnly']['status'] == 'available':
                ids.append(row['targetElectorateId'])
        elif family == 'v_deferred':
            if row['completeShare']['status'] == 'available' and all(
                    feature['vStatus'] not in ('unresolved_party_continuity', 'missing_source_party_row',
                                               'ambiguous_source_destination', 'missing_source_denominator')
                    for feature in row['candidateFeatures']):
                ids.append(row['targetElectorateId'])
        elif family == 'complete_party_vector':
            if row['partyVector']['status'] == 'source_and_target_party_categories_present':
                ids.append(row['targetElectorateId'])
        elif family == 'stage11_matched_split':
            if row['splitTicket']['status'] == 'source_and_target_tables_present':
                ids.append(row['targetElectorateId'])
    if len(set(ids)) != len(ids):
        raise ValueError(f'Duplicate {family} evaluation ID')
    return sorted(ids)


def feature_rank(rows, training_rows):
    """Structural within-slate rank only; no target party or candidate outcome."""
    support = [(f['s0Printed'], 1 / len(r['candidateFeatures']))
               for r in training_rows for f in r['candidateFeatures']
               if f['sStatus'] == 'supported_rounded_source_split']
    if not support:
        return {'supportedS': 0, 'trainingOnlyMeanS': None, 'withinSlateContrastRankS': 0,
                'fullIntensityConditioning': 'requires_later_permitted_party_inputs'}
    mean = sum(value * weight for value, weight in support) / sum(weight for _, weight in support)
    contrast_energy = 0.0
    for row in rows:
        features = [f['s0Printed'] - mean if f['sStatus'] == 'supported_rounded_source_split'
                    else 0.0 for f in row['candidateFeatures']]
        if not features:
            continue
        center = sum(features) / len(features)
        contrast_energy += sum((value - center) ** 2 for value in features)
    return {'supportedS': len(support), 'trainingOnlyMeanS': mean,
            'withinSlateContrastRankS': int(contrast_energy > 1e-12),
            'withinSlateContrastEnergyS': contrast_energy,
            'fullIntensityConditioning': 'requires_later_permitted_party_inputs'}


def stable_chains(geography):
    by_target = {(r['targetYear'], r['scope'], r['targetElectorateId']): r
                 for r in geography if r['certifiedTwoSidedExact']}
    target_years = sorted({r['targetYear'] for r in geography})
    final = target_years[-1]
    chains = []
    for row in geography:
        if row['targetYear'] != final or row['scope'] != 'general':
            continue
        chain, current = [], row
        for year in reversed(target_years):
            if current is None or current['targetYear'] != year:
                break
            chain.append(current['targetElectorateId'])
            current = by_target.get((current['sourceYear'], 'general', current['dominantPredecessorId']))
        if len(chain) == len(target_years):
            chains.append({'targetElectorateIds': list(reversed(chain)),
                           'targetYears': target_years})
    return sorted(chains, key=lambda r: r['targetElectorateIds'][-1])


def source_composition(geography, elections):
    seats = {year: {seat['id']: seat for seat in document['electorates']}
             for year, document in elections.items()}
    groups = []
    for year in (2014, 2020):
        records = [r for r in geography if r['targetYear'] == year and r['scope'] == 'general']
        for label, subset in (('strict_exact', [r for r in records if r['certifiedTwoSidedExact']]),
                              ('excluded', [r for r in records if not r['certifiedTwoSidedExact']])):
            represented = []
            for geo in subset:
                seat = seats[geo['sourceYear']].get(geo['dominantPredecessorId'])
                if seat is None:
                    continue
                parties = {p['partyKey']: p for p in seat['parties']}
                represented.append({'sourceElectorateId': seat['id'],
                    'sourceCandidateSlateSize': len(seat['candidates']),
                    'sourceValidPartyVotes': seat['validPartyVotes'],
                    'sourceNationalShare': parties['nationalparty']['share'] if 'nationalparty' in parties else None,
                    'sourceLabourShare': parties['labourparty']['share'] if 'labourparty' in parties else None,
                    'sourceWinnerPartyKey': next((c['partyKey'] for c in seat['candidates']
                                                 if c['id'] == seat['winnerCandidateId']), None)})
            def mean(field):
                values = [r[field] for r in represented if r[field] is not None]
                return sum(values) / len(values) if values else None
            groups.append({'targetYear': year, 'group': label, 'targetCount': len(subset),
                'sourceDescriptorCount': len(represented),
                'sourceSlateSizeMean': mean('sourceCandidateSlateSize'),
                'sourceValidPartyVotesMean': mean('sourceValidPartyVotes'),
                'sourceNationalShareMean': mean('sourceNationalShare'),
                'sourceLabourShareMean': mean('sourceLabourShare'),
                'sourceWinnerPartyCounts': dict(sorted(Counter(r['sourceWinnerPartyKey']
                                                        for r in represented).items()))})
    return groups


def fold_plans(geography, availability, chains):
    target_years = sorted({r['targetYear'] for r in geography})
    by_year = defaultdict(list)
    for row in availability:
        by_year[row['targetYear']].append(row)
    stable_by_year = defaultdict(set)
    for chain in chains:
        for year, target_id in zip(chain['targetYears'], chain['targetElectorateIds']):
            stable_by_year[year].add(target_id)
    plans = []
    for family, protocol in product(FAMILIES, PROTOCOLS):
        for year in target_years:
            here = by_year[year]
            source_years = {r['sourceYear'] for r in here}
            if len(source_years) != 1:
                raise ValueError('Fold mixes source elections')
            source_year = next(iter(source_years))
            prior_years = training_years(target_years, source_year, year, protocol)
            training_rows = [r for y in prior_years for r in by_year[y]]
            eval_ids = ids_for_family(here, family)
            training_ids = ids_for_family(training_rows, family)
            original = ids_for_family([r for r in here if r['originalFrame']], family)
            added = ids_for_family([r for r in here if not r['originalFrame']], family)
            stable = ids_for_family([r for r in here if r['targetElectorateId'] in stable_by_year[year]], family)
            original_training = ids_for_family([r for r in training_rows if r['originalFrame']], family)
            added_training = ids_for_family([r for r in training_rows if not r['originalFrame']], family)
            candidate_rows = [r for r in here if r['targetElectorateId'] in eval_ids]
            s_rank = feature_rank(candidate_rows, [r for r in training_rows
                         if r['targetElectorateId'] in training_ids]) if family == 'complete_share_baseline_s' else None
            train_s_contests = sum(any(f['sStatus'] == 'supported_rounded_source_split'
                                        for f in r['candidateFeatures'])
                                   for r in training_rows if r['targetElectorateId'] in training_ids)
            eval_s_contests = sum(any(f['sStatus'] == 'supported_rounded_source_split'
                                       for f in r['candidateFeatures']) for r in candidate_rows)
            saved_fit = None
            if family in ('nat_lab_response', 'source_victory_comparison', 'complete_share_baseline_s'):
                if year == 2020:
                    saved_fit = {'savedHoldoutYear': 2017,
                                 'rule': 'fit_trained_before_2020_source_2017_result; verify_parameter_contract_before_use'}
                elif year in (2017, 2023):
                    saved_fit = {'savedHoldoutYear': year,
                                 'rule': 'existing_chronological_fit_only; later_retest_must_verify_saved_training_ids'}
            if family == 'complete_share_baseline_s':
                gate = {'minimumTrainingContests': len(training_ids) >= 20,
                        'minimumTrainingSupportedSContests': train_s_contests >= 20,
                        'minimumEvaluationSupportedSContests': eval_s_contests >= 20,
                        'structuralWithinSlateRank': s_rank['withinSlateContrastRankS'],
                        'fullNumericalRankAndCondition': 'pending_authorized_pre_fit_adapter'}
            elif family in ('nat_lab_response', 'source_victory_comparison'):
                source_winners = [p['sourceVictory'] for r in here for p in r['natLab']
                                  if p['status'] == 'available']
                gate = {'evaluationSourceVictoryTrue': sum(source_winners),
                        'evaluationSourceVictoryFalse': len(source_winners) - sum(source_winners),
                        'trainingByParty': response_training_gates(training_rows),
                        'partyMovementAndFullNumericalRank': 'pending_permitted_input_adapter'}
            else:
                gate = {'fit': 'parameter_free_source_election_construction' if family in
                        ('complete_party_vector', 'stage11_matched_split')
                        else 'family_specific_future_gate'}
            plans.append({'foldId': f'{family}:{source_year}-{year}:two_sided_exact:{protocol}',
                'family': family, 'targetYear': year, 'sourceYear': source_year,
                'chronologyProtocol': protocol,
                'protocolRole': 'primary' if protocol == 'expanding_window' else 'prespecified_sensitivity',
                'geographyTier': 'certified_two_sided_exact',
                'trainingTransitionTargetYears': prior_years,
                'trainingIds': training_ids, 'evaluationIds': eval_ids,
                'preprocessing': preprocessing_plan(training_rows, training_ids, family),
                'overlappingTrainingTargetYears': [y for y in prior_years if y == source_year],
                'historicalPublicationByForecastCutoff': 'not_verified; retrospective_conditional_only',
                'originalTrainingIds': original_training, 'addedTrainingIds': added_training,
                'originalEvaluationIds': original, 'addedEvaluationIds': added,
                'stableSeatSensitivityIds': stable,
                'trainingContrastOnSameEvaluationIds': {
                    'originalTrainingIds': original_training,
                    'expandedTrainingIds': training_ids,
                    'evaluationIds': eval_ids,
                    'status': 'design_only_no_refit_authorized'},
                'informationSet': ('observed_target_local_party_conditional' if family in
                                   ('complete_share_baseline_s', 'nat_lab_response',
                                    'source_victory_comparison', 'v_deferred') else
                                   'observed_target_national_party_conditional' if family == 'complete_party_vector'
                                   else 'matched_party_ballot_component_retrospective'),
                'savedFixedFitTransport': saved_fit,
                'sourceFeatureRankAudit': s_rank,
                'expandedChronologicalFit': ('not_authorized; verify_full_rank_and_training_only_preprocessing'
                                            if family not in ('complete_party_vector', 'stage11_matched_split')
                                            else 'parameter_free_rule'),
                'gates': gate,
                'abstentions': {'fullTargetFrameSeats': len(here),
                                'generalTargetSeats': sum(r['scope'] == 'general' for r in here),
                                'maoriCoverageOnlySeats': sum(r['scope'] == 'maori' for r in here),
                                'exactGeneralSeats': sum(r['scope'] == 'general' and r['primaryExactGeography'] for r in here),
                                'modelRecordCount': len(eval_ids),
                                'nonExactGeographyIds': [r['geographyId'] for r in here
                                                         if r['scope'] == 'general' and not r['primaryExactGeography']],
                                'exactButModelUnavailableIds': [r['geographyId'] for r in here
                                                                if r['scope'] == 'general' and r['primaryExactGeography']
                                                                and (r['targetElectorateId'] not in eval_ids if family not in
                                                                     ('nat_lab_response', 'source_victory_comparison')
                                                                     else not any(p['status'] == 'available' for p in r['natLab']))]},
                'weights': ('equal_party_seat_records_with_fold_specific_reporting' if family in
                            ('nat_lab_response', 'source_victory_comparison') else
                            'equal_contests_training_and_primary_reporting; candidate_equal_sensitivity'),
                'status': 'unfitted_design_only'})
    return plans


def experiment_register(plans):
    by_family = defaultdict(list)
    for plan in plans:
        by_family[plan['family']].append(plan['foldId'])
    definitions = [
        ('nat_lab_response', 'Existing NAT/LAB local-party response conditional on retained party baseline',
         'party_seat_candidate_share_of_valid_candidate_votes', 'Stage6_and_Stage16_existing_beta0_beta1_and_source_victory_controls'),
        ('complete_share_baseline_s', 'Does existing S-only share allocation beat refitted baseline on added exact seats?',
         'complete_candidate_share_of_valid_candidate_votes', 'Stage22_refitted_baseline_vs_S_only'),
        ('complete_party_vector', 'Can Stage23 construct complete conditional local party vectors for added exact seats?',
         'complete_local_party_share_of_valid_party_votes', 'national_share_neutral_profile_and_existing_stage23_controls'),
        ('source_victory_comparison', 'Existing source-victory response contrast on supported pairs',
         'party_seat_candidate_share_of_valid_candidate_votes', 'Stage16_source_victory_vs_no_source_victory'),
        ('stage11_matched_split', 'Availability for existing matched-party-ballot split component',
         'candidate_destination_fraction_of_matched_party_ballot_component', 'Stage11_corrected_matched_component_controls'),
        ('v_deferred', 'Existing V feature availability; no automatic S+V repetition',
         'complete_candidate_share_of_valid_candidate_votes', 'deferred_existing_comparator_only')]
    records = []
    for family, question, outcome, benchmarks in definitions:
        if family in ('nat_lab_response', 'source_victory_comparison'):
            primary = 'equal_party_seat_MAE_percentage_points'
            secondary = ['RMSE', 'party_specific_signed_bias', 'outside_unit_share_count']
        elif family in ('complete_share_baseline_s', 'v_deferred'):
            primary = 'equal_contest_candidate_share_MAE_percentage_points'
            secondary = ['equal_contest_RMSE', 'candidate_equal_sensitivity',
                         'party_category_bias', 'unique_winner_accuracy_and_ties', 'margin_error']
        elif family == 'complete_party_vector':
            primary = 'equal_electorate_equal_party_share_MAE_percentage_points'
            secondary = ['RMSE', 'party_specific_signed_bias', 'national_gap_diagnostic_only']
        else:
            primary = 'matched_party_ballot_component_interval_error_percentage_points'
            secondary = ['matched_component_RMSE', 'party_category_coverage',
                         'unmatched_mass_and_full_vote_range_diagnostics']
        records.append({'experimentId': family, 'question': question,
            'existingSpecification': {'nat_lab_response': 'data/processed/models/conditional-nat-lab-response/specification.json',
                                      'complete_share_baseline_s': 'data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json',
                                      'complete_party_vector': 'data/processed/models/complete-party-vector/specification.json',
                                      'stage11_matched_split': 'data/processed/models/historical-split-ticket/specification.json',
                                      'source_victory_comparison': 'data/processed/models/conditional-nat-lab-response/specification.json',
                                      'v_deferred': 'data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json'}[family],
            'outcomeAndDenominator': outcome, 'foldPlans': by_family[family],
            'primaryChronology': 'expanding_window',
            'chronologySensitivity': 'more_separated',
            'familyAvailability': ('parameter_free_source_election_construction; no_fitted_holdout_invented'
                                   if family in ('complete_party_vector', 'stage11_matched_split') else
                                   'earlier_completed_transition_fits_only; numerical_gates_pending'),
            'benchmarks': benchmarks,
            'primaryMetric': primary, 'secondaryMetrics': secondary,
            'commonReporting': ['original_common_added_expanded_IDs', 'coverage', 'abstention',
                                'worst_fold_deterioration', 'influence_retaining_primary_records'],
            'coverageAndRankGates': 'use_each_referenced_fold_plan_and_inherited_model_contract; no_relaxation',
            'comparability': 'within_family_identical_ids_only; never_rank_incompatible_outcome_contracts',
            'materiality': 'retained_0.25_percentage_point_development_diagnostic_where_existing_spec_applies',
            'stopping': 'no_automatic_variants_or_broad_search_after_disappointing_results',
            'status': 'proposed_separate_authorization_required'})
    return {'schemaVersion': 1, 'stage': 25, 'role': 'bounded_unfitted_experiment_register',
            'records': records,
            'nextSeparatelyAuthorizedTask': 'practical_preserved_evidence_candidate_linkage; docs/stage25-chronology-amendment.md',
            'sequence': ['finalize_geography_and_chronology', 'practical_linkage_and_coverage',
                         'registered_identity_free_exact_geography_tests',
                         'identity_effects_only_with_linkage_and_career_gates',
                         'dated_replay_national_reconciliation_joint_uncertainty'],
            'identityFreeDependency': 'does_not_require_linkage; exceptions_cannot_block_identity_free_tests',
            'developmentEvidence': 'all_historical_elections_already_inspected_not_untouched_confirmation'}


def build():
    original = read(ORIGINAL_DESIGN)
    for path, expected in original['preservedArtifacts'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Changed original Stage25 evidence: {path}')
    geography = read(GEOGRAPHY)['records']
    availability = read(AVAILABILITY)['records']
    if {r['geographyId'] for r in geography} != {r['geographyId'] for r in availability}:
        raise ValueError('Geography and availability keys disagree')
    elections = {year: read(path) for year, path in ELECTIONS.items()}
    chains = stable_chains(geography)
    plans = fold_plans(geography, availability, chains)
    for plan in plans:
        if plan['chronologyProtocol'] != 'more_separated':
            continue
        sample = {field: plan[field] for field in ('trainingIds', 'evaluationIds')}
        raw = json.dumps(sample, sort_keys=True, separators=(',', ':')).encode()
        key = plan['foldId'].removesuffix(':more_separated')
        if sha256(raw).hexdigest() != original['originalFoldSampleSha256'][key]:
            raise ValueError(f'Changed inherited separated sample: {key}')
    composition = source_composition(geography, elections)
    design = {'schemaVersion': 1, 'stage': 25, 'role': 'unfitted_chronological_fold_plan',
              'folds': plans, 'stableExactSeatChains': chains,
              'chronologyAmendment': {'originalCommit': original['originalCommit'],
                                     'originalDesignContract': ORIGINAL_DESIGN,
                                     'dependencyAudit': 'docs/stage25-chronology-amendment.md',
                                     'historicalStage16And22Artifacts': 'unchanged'},
              'stableSeatUse': 'sample_composition_sensitivity_only_not_primary_or_representative',
              'chronology': {'primary': 'expanding_window: training_target_year <= holdout_source_year and < holdout_target_year',
                             'sensitivity': 'more_separated: training_target_year < holdout_source_year',
                             'interpretation': 'retrospective_conditional_not_verified_as_of_forecast; overlapping_elections_induce_dependence'},
              'approximateTiers': 'inventory_only_no_candidate_vote_transport_or_prediction',
              'weights': 'equal_contest_or_party_seat_within_fold; report_folds_separately; pooled_contest_equal_sensitivity_only',
              'status': 'requires_separate_retest_authorization'}
    return design, {'schemaVersion': 1, 'stage': 25, 'role': 'pre_target_source_composition',
                    'groups': composition,
                    'limitations': 'dominant_source_descriptors_for_excluded_seats_not_representativeness_weights'}, experiment_register(plans)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    design, composition, register = build()
    files = {'fold-plan.json': design, 'source-composition.json': composition,
             'experiment-register.json': register}
    for name, value in files.items():
        write_or_check(name, value, args.check)
    manifest = {'schemaVersion': 1, 'stage': 25,
                'inputSha256': {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS},
                'outputSha256': {name: sha256(encode(value)).hexdigest() for name, value in files.items()}}
    write_or_check('design-manifest.json', manifest, args.check)
    print(json.dumps({'folds': len(design['folds']), 'stableChains': len(design['stableExactSeatChains']),
                      'sourceComposition': composition['groups']}))


if __name__ == '__main__':
    main()
