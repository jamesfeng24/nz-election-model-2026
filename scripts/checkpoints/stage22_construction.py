"""Construct only Stage22 fitted parameters and conditional predictions."""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from scripts.checkpoints import stage22_prefit as prefit
from scripts.checkpoints.complete_share_feature_rank import PROBES, design, rank_details
from scripts.checkpoints.stage22_fit import (
    METHODS, SCENARIOS, Profile, candidate_arrays, earlier_actuals,
    fit, means_for_training, predict, source_s)


ROOT = prefit.ROOT
DEST = ROOT / 'data/processed/checkpoints/stage22-shared-group-experiment'
FEATURES = 'data/processed/checkpoints/stage22-shared-group-prefit/amended-features.json'
CONTRACT = 'data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json'
PREFIT_MANIFEST = 'data/processed/checkpoints/stage22-shared-group-prefit/manifest.json'


def scenario_rows(rows, scenario):
    updated = deepcopy(rows)
    for seat in updated:
        for candidate in seat['candidates']:
            candidate['s0Reported'] = source_s(candidate, scenario)
    return updated


def verify_rank(rows, means):
    details = []
    for kappa in PROBES:
        matrix = design(rows, means, kappa)
        feature = rank_details(matrix, [1, 2])
        combined = rank_details(matrix, [0, 1, 2])
        if (feature['rank'] != 2 or combined['rank'] != 3 or
                combined['weakCondition']):
            raise ValueError('Scenario training design rank or conditioning failed')
        details.append({'kappa': kappa, 'featureRank': feature['rank'],
                        'combinedRank': combined['rank'],
                        'conditionRatio': combined['conditionRatio']})
    return details


def construct_fold(training, evaluation, training_elections, scenario):
    """Target outcomes are absent from this adapter by construction."""
    training = scenario_rows(training, scenario)
    evaluation = scenario_rows(evaluation, scenario)
    means = means_for_training(training, 'printed')
    rank = verify_rank(training, means)
    base, features, starts = candidate_arrays(training, means, 'printed')
    actual = earlier_actuals(training, training_elections)
    fits, predictions = {}, {}
    for method in METHODS:
        fitted = fit(Profile(base, features, starts, actual, method))
        fits[method] = fitted
        predictions[method] = predict(evaluation, means, 'printed', method, fitted)
    return {'trainingOnlyMeans': means, 'rankCheck': rank,
            'fits': fits, 'predictions': predictions}


def contextual_predictions(rows):
    result = []
    for row in rows:
        if row['status'] != 'constructed':
            continue
        candidates = row['candidates']
        uniform = {c['targetOccurrenceId']: 1 / len(candidates) for c in candidates}
        supports = [c['targetPartySupport'] for c in candidates]
        restricted = None
        if all(c['targetPartyKey'] is not None and support > 0
               for c, support in zip(candidates, supports)):
            total = sum(supports)
            restricted = {c['targetOccurrenceId']: support / total
                          for c, support in zip(candidates, supports)}
        result.append({'targetElectorateId': row['targetElectorateId'],
                       'uniform': uniform, 'restrictedZeroFloor': restricted})
    return result


def build(features, contract, training_elections):
    if contract['status'] != 'amended_shared_group_sample_frozen_before_fit_or_score':
        raise ValueError('Missing amended pre-fit checkpoint')
    by_id = {r['targetElectorateId']: r for r in features['records']}
    if len(by_id) != 213 or any(r['status'] != 'constructed'
                                for f in contract['folds']
                                for cid in (*f['trainingContestIds'],
                                            *f['commonEvaluationContestIds'])
                                for r in (by_id[cid],)):
        raise ValueError('Amended exact contest frame changed')
    fit_rows, prediction_rows = [], []
    for fold in contract['folds']:
        year = fold['targetYear']
        training = [by_id[cid] for cid in fold['trainingContestIds']]
        evaluation = [by_id[cid] for cid in fold['commonEvaluationContestIds']]
        if (sum(len(r['candidates']) for r in training) != fold['trainingCandidates'] or
                sum(len(r['candidates']) for r in evaluation) != fold['evaluationCandidates'] or
                {r['targetYear'] for r in training} != set(fold['trainingTargetYears']) or
                any(r['targetYear'] != year for r in evaluation) or
                any(r['targetYear'] >= year for r in training)):
            raise ValueError('Chronological or candidate sample contract changed')
        cases = {}
        for scenario in SCENARIOS:
            cases[scenario] = construct_fold(training, evaluation,
                                             {prior: training_elections[prior]
                                              for prior in fold['trainingTargetYears']},
                                             scenario)
        fit_rows.append({'targetYear': year,
                         'trainingContestIds': fold['trainingContestIds'],
                         'trainingCandidateOccurrenceIds': fold['trainingCandidateOccurrenceIds'],
                         'scenarios': {s: {'trainingOnlyMeans': cases[s]['trainingOnlyMeans'],
                                          'rankCheck': cases[s]['rankCheck'],
                                          'fits': cases[s]['fits']} for s in SCENARIOS}})
        prediction_rows.append({'targetYear': year,
                                'evaluationContestIds': fold['commonEvaluationContestIds'],
                                'evaluationCandidateOccurrenceIds': fold['commonEvaluationCandidateOccurrenceIds'],
                                'scenarios': {s: cases[s]['predictions'] for s in SCENARIOS},
                                'contextual': contextual_predictions(evaluation)})
    earliest = [r for r in features['records']
                if r['targetYear'] == 2011 and r['status'] == 'constructed']
    return {'schemaVersion': 1, 'stage': 22,
            'role': 'earlier_election_fits_only_no_holdout_actuals',
            'folds': fit_rows, 'operationalSelection': None}, {
            'schemaVersion': 1, 'stage': 22,
            'role': 'conditional_holdout_predictions_no_target_outcomes',
            'fullFrameContestCount': 213,
            'fullFrameStatus': [{'targetYear': r['targetYear'],
                                 'targetElectorateId': r['targetElectorateId'],
                                 'status': r['status'], 'reason': r['reason'],
                                 'candidateCount': r['candidateCount']}
                                for r in features['records']],
            'earliest2011Contextual': contextual_predictions(earliest),
            'folds': prediction_rows, 'operationalSelection': None}


def outputs():
    manifest = prefit.read(PREFIT_MANIFEST)
    for name in ('amended-features.json', 'amended-fit-contract.json'):
        path = f'data/processed/checkpoints/stage22-shared-group-prefit/{name}'
        if prefit.digest(path) != manifest['outputSha256'][name]:
            raise ValueError('Changed committed pre-fit input')
    features, contract = prefit.read(FEATURES), prefit.read(CONTRACT)
    elections = {year: prefit.read(prefit.ELECTIONS[year]) for year in (2011, 2017)}
    fits, predictions = build(features, contract, elections)
    result = {'fitted-parameters.json': fits, 'predictions.json': predictions}
    inputs = (FEATURES, CONTRACT, PREFIT_MANIFEST, prefit.ELECTIONS[2011],
              prefit.ELECTIONS[2017])
    result['construction-manifest.json'] = {
        'schemaVersion': 1, 'stage': 22,
        'phase': 'construction_committed_before_target_evaluation',
        'inputSha256': {path: prefit.digest(path) for path in inputs},
        'generatorSha256': {name: prefit.digest('scripts/checkpoints/' + name)
                            for name in ('stage22_fit.py', 'stage22_construction.py')},
        'outputSha256': {name: sha256(prefit.encode(doc)).hexdigest()
                         for name, doc in result.items()}}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = outputs()
    DEST.mkdir(parents=True, exist_ok=True)
    for name, doc in result.items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != prefit.encode(doc):
                raise ValueError(f'Changed Stage22 construction {name}')
        else:
            path.write_bytes(prefit.encode(doc))
    print(json.dumps({'fits': {str(f['targetYear']): {
        scenario: {method: value['kappa'] for method, value in details['fits'].items()}
        for scenario, details in f['scenarios'].items()}
        for f in result['fitted-parameters.json']['folds']}}, sort_keys=True))


if __name__ == '__main__':
    main()
