"""Pin frozen prediction/control artifacts and their valid comparison samples."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/processed/checkpoints/model-failure-diagnostics'
PATHS = {
    'stage18Construction': 'data/processed/models/conditional-candidate-share/construction.json',
    'stage18Actuals': 'data/processed/models/conditional-candidate-share/actuals.json',
    'stage18Diagnostics': 'data/processed/models/conditional-candidate-share/diagnostics.json',
    'stage18Manifest': 'data/processed/models/conditional-candidate-share/evaluation-manifest.json',
    'stage16Analysis': 'data/processed/models/conditional-nat-lab-response/analysis.json',
    'stage16Inputs': 'data/processed/models/conditional-nat-lab-response/numerical-inputs.json',
    'stage16Manifest': 'data/processed/models/conditional-nat-lab-response/manifest.json',
    'stage6Backtests': 'data/processed/models/nat-lab-elasticity/backtests.json',
    'stage6Records': 'data/processed/models/nat-lab-elasticity/records.json',
    'stage6Manifest': 'data/processed/models/nat-lab-elasticity/manifest.json',
    'stage8Analysis': 'data/processed/models/candidate-persistence/analysis.json',
    'stage8Pairs': 'data/processed/models/candidate-persistence/pairs.json',
    'stage8Manifest': 'data/processed/models/candidate-persistence/manifest.json',
    'stage9Analysis': 'data/processed/models/freshman-incumbency/analysis.json',
    'stage9Audit': 'data/processed/models/freshman-incumbency/cohort-audit.json',
    'stage9Manifest': 'data/processed/models/freshman-incumbency/analysis-manifest.json',
    'stage10Analysis': 'data/processed/models/replacement-candidate/analysis.json',
    'stage10Audit': 'data/processed/models/replacement-candidate/cohort-audit.json',
    'stage10Manifest': 'data/processed/models/replacement-candidate/analysis-manifest.json',
    'stage11Predictions': 'data/processed/models/historical-split-ticket/predictions.json',
    'stage11Manifest': 'data/processed/models/historical-split-ticket/analysis-manifest.json',
    'stage15Diagnostics': 'data/processed/models/conditional-candidate-ledger/diagnostics.json',
    'stage15Manifest': 'data/processed/models/conditional-candidate-ledger/evaluation-manifest.json',
}


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def _stage18(construction):
    groups = []
    for holdout in construction['holdouts']:
        year = holdout['targetYear']
        for method, predicate in (
                ('fitted_floor_vs_uniform', lambda row: True),
                ('fitted_floor_vs_restricted_zero_floor',
                 lambda row: row['methods']['restricted_zero_floor'] is not None)):
            rows = [row for row in holdout['records'] if row['status'] == 'constructed'
                    and predicate(row)]
            groups.append({'targetYear': year, 'comparison': method,
                           'contestIds': [row['targetElectorateId'] for row in rows],
                           'candidateOccurrenceIds': [c['candidateOccurrenceId']
                                                      for row in rows for c in row['candidates']]})
    return {'unit': 'candidate_share_of_valid_candidate_votes',
            'inputInformationSet': 'retrospective_slate_and_observed_target_local_party_share',
            'candidateEvidenceTier': 'election_local_party_mapping_identity_free',
            'construction': PATHS['stage18Construction'],
            'evaluationOnlyActuals': PATHS['stage18Actuals'],
            'controls': ['uniform_full_slate', 'restricted_zero_floor_on_supported_subset'],
            'pairedGranularity': 'candidate_and_contest', 'groups': groups}


def _stage16(analysis):
    groups = []
    for party in ('nationalparty', 'labourparty'):
        for year in (2017, 2023):
            for mode in ('actual_observed_local_party', 'additive',
                         'proportional', 'log_odds'):
                rows = [row for row in analysis['folds']
                        if row['party'] == party and row['targetYear'] == year
                        and row['mode'] == mode]
                indexed = {row['model']: row for row in rows}
                required = ('source_victory', 'common_intercept',
                            'source_victory_beta1', 'beta1')
                if any(name not in indexed for name in required):
                    raise ValueError('Missing frozen Stage16 paired control')
                ids = [[item['id'] for item in indexed[name]['predictions']]
                       for name in required]
                if any(ids[0] != sample for sample in ids[1:]):
                    raise ValueError('Stage16 paired sample misalignment')
                groups.append({'party': party, 'targetYear': year, 'mode': mode,
                               'recordIds': ids[0], 'models': list(required)})
    return {'unit': 'party_seat_candidate_share_of_valid_candidate_votes',
            'partyInputUnit': 'share_of_valid_party_votes',
            'inputInformationSet': 'observed_target_local_party_or_stage5_transform_using_observed_target_national_support',
            'candidateEvidenceTier': 'source_party_seat_victory_known; target_person_status_unresolved',
            'predictionFile': PATHS['stage16Analysis'],
            'evaluationOnlyActualsAndSourceCovariates': PATHS['stage16Inputs'],
            'controls': ['independently_fitted_common_intercept',
                         'nuisance_matched_fixed_beta1', 'simple_beta1_context'],
            'pairedGranularity': 'party_seat', 'groups': groups}


def _stage6(backtests):
    groups = []
    for party in ('nationalparty', 'labourparty'):
        for source_year in (2014, 2020):
            rows = [row for row in backtests['records'] if row['party'] == party
                    and row['holdoutSourceYear'] == source_year
                    and row['mode'] == 'chronological'
                    and row['baseline'] == 'actual_observed_local_party']
            indexed = {row['model']: row for row in rows}
            if set(indexed) != {'no_response', 'one_for_one', 'fitted'}:
                raise ValueError('Missing Stage6 chronological model/control')
            ids = [[item['recordId'] for item in indexed[name]['predictions']]
                   for name in ('fitted', 'one_for_one', 'no_response')]
            if any(ids[0] != sample for sample in ids[1:]):
                raise ValueError('Stage6 paired sample misalignment')
            groups.append({'party': party, 'sourceYear': source_year,
                           'targetYear': source_year + 3,
                           'recordIds': ids[0]})
    return {'unit': 'party_seat_candidate_share_of_valid_candidate_votes',
            'partyInputUnit': 'share_of_valid_party_votes',
            'inputInformationSet': 'observed_target_local_party_share',
            'candidateEvidenceTier': 'party_seat_not_person_identity',
            'predictionAndActualFile': PATHS['stage6Backtests'],
            'sourceCovariatesFile': PATHS['stage6Records'],
            'controls': ['beta_zero_no_response', 'beta_one_one_for_one'],
            'pairedGranularity': 'party_seat', 'groups': groups}


def build():
    docs = {name: read(path) for name, path in PATHS.items()}
    stage8_pairs = [row['pairId'] for row in docs['stage8Pairs']['pairs']
                    if row['validationEligible']]
    stage9_pairs = [row['pairId'] for row in docs['stage9Audit']['records']
                    if row['correctedEvaluationEligible']]
    stage10_ids = [id for row in docs['stage10Analysis']['chronologicalFittedComparison']['additive']
                   for id in row['holdoutEventIds']]
    stage11_ids = [row['targetOccurrenceId'] for row in docs['stage11Predictions']['records']]
    inventory = {'schemaVersion': 1, 'stage': 19,
                 'status': 'pre_diagnostic_frozen_artifact_inventory',
                 'inputs': {name: {'path': path, 'sha256': digest(path)}
                            for name, path in PATHS.items()},
                 'comparisons': {
                     'stage18': _stage18(docs['stage18Construction']),
                     'stage16': _stage16(docs['stage16Analysis']),
                     'stage6': _stage6(docs['stage6Backtests']),
                     'stage8': {'unit': 'additive_normalized_candidate_residual_pp',
                                'evidenceTier': 'prior_winner_selected_probable_target_identity_retrospective',
                                'validationPairIds': stage8_pairs,
                                'controls': ['zero', 'carry_prior'],
                                'pairedGranularity': 'aggregate_scores_only_no_saved_per_pair_predictions'},
                     'stage9': {'unit': 'additive_normalized_candidate_residual_pp',
                                'evidenceTier': 'source_winner_recontesters_dated_tenure_selected_profiles',
                                'correctedPairIds': stage9_pairs,
                                'controls': ['jointly_refitted_no_freshman', 'zero', 'carry_prior'],
                                'pairedGranularity': 'aggregate_scores_only_no_saved_per_pair_predictions'},
                     'stage10': {'unit': 'additive_normalized_candidate_residual_pp',
                                 'evidenceTier': 'retrospective_acquisition_selected_distinct_people',
                                 'chronologicalHoldoutEventIds': stage10_ids,
                                 'controls': ['jointly_refitted_no_replacement', 'zero', 'carry_prior'],
                                 'pairedGranularity': 'aggregate_scores_only_no_saved_per_event_predictions'},
                     'stage11': {'unit': 'matched_candidate_component_pp_of_all_target_party_ballots',
                                 'evidenceTier': 'party_continuity_not_person_identity',
                                 'candidateOccurrenceIds': stage11_ids,
                                 'controls': ['source_year_pooled_split', 'party_only_matched'],
                                 'pairedGranularity': 'rounded_interval_matched_component_not_complete_share'},
                     'stage15': {'unit': 'joint_candidate_vote_feasible_sets',
                                 'pointPredictions': False,
                                 'pairedGranularity': 'not_comparable_to_point_share_errors'}},
                 'noPoolingAcrossIncompatibleOutcomes': True}
    output = {'diagnostic-inventory.json': inventory}
    output['inventory-manifest.json'] = {
        'schemaVersion': 1, 'stage': 19, 'phase': 'inventory_before_new_summaries',
        'generatorSha256': digest('scripts/checkpoints/model_failure_inventory.py'),
        'inputSha256': {path: digest(path) for path in PATHS.values()},
        'outputSha256': {'diagnostic-inventory.json': sha256(encode(inventory)).hexdigest()}}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, data in outputs.items():
            if (DEST / name).read_bytes() != encode(data):
                raise ValueError(f'Changed Stage19 {name}')
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        for name, data in outputs.items():
            (DEST / name).write_bytes(encode(data))
    print({name: len(row.get('groups', [])) for name, row in
           outputs['diagnostic-inventory.json']['comparisons'].items()})


if __name__ == '__main__':
    main()
