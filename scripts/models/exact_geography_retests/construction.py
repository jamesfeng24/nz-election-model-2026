"""Earlier-only fits and outcome-free predictions for both Stage27 families."""
import argparse
from hashlib import sha256
import json

import numpy as np

from scripts.checkpoints.stage22_construction import contextual_predictions
from scripts.checkpoints.stage22_fit import SCENARIOS, Profile, candidate_arrays, earlier_actuals, fit, predict
from scripts.models.conditional_nat_lab_response import model as response
from . import adapters as a
from .common import (DEST, METHODS, OLD_RESPONSE, OLD_SHARE, encode, keyed, read,
                     save_outputs, verify_inputs, phase_manifest)


def candidate_fit(training, elections, scenario, method, cache, reuse=None):
    means = a.s_means(training, scenario)
    gate = a.rank_gate(training, means, scenario)
    if not gate['passes']:
        return {'status': 'abstain', 'reason': 'training_rank_or_coverage_gate'}, means
    base, columns, starts = candidate_arrays(training, means, scenario)
    actual = earlier_actuals(training, elections)
    selected = columns[:, (0,)] if method == 'baseline_plus_S' else np.empty((len(base), 0))
    signature = sha256(encode({'method': method, 'trainingIds': [r['targetElectorateId'] for r in training],
                               'base': base.tolist(), 'features': selected.tolist(),
                               'starts': starts.tolist(), 'actual': actual.tolist()})).hexdigest()
    profile = Profile(base, columns, starts, actual, method)
    if signature not in cache:
        if reuse is not None and signature in reuse:
            fitted = reuse[signature]
            loss, gradient = profile.value_gradient(fitted['kappa'], np.array(fitted['theta']))
            if abs(loss - fitted['objective']) > 1e-12 or np.max(np.abs(gradient), initial=0) > 1e-7:
                raise ValueError('Cached objective/gradient does not match permitted training')
            cache[signature] = fitted
        else:
            print(json.dumps({'fitting': method, 'trainingContests': len(training), 'scenario': scenario}), flush=True)
            try:
                cache[signature] = fit(profile)
            except ValueError as error:
                cache[signature] = {'status': 'abstain', 'reason': 'numerical_failure', 'detail': str(error)}
    return cache[signature], means


def candidate_case(fold, data, elections, training_variant, cache, reuse=None):
    key = 'originalTrainingIds' if training_variant == 'original_only' else 'trainingIds'
    train, test = a.permitted_fold(fold, data['shareRecords'], key)
    allowed = {r['targetYear'] for r in train}
    prior = {year: elections[year] for year in allowed}
    output = {'foldId': fold['foldId'], 'targetYear': fold['targetYear'],
              'chronologyProtocol': fold['chronologyProtocol'], 'trainingVariant': training_variant,
              'trainingIds': fold[key], 'evaluationIds': fold['evaluationIds'],
              'contextual': contextual_predictions(test), 'scenarios': {}}
    for scenario in SCENARIOS:
        fits, predictions = {}, {}
        means = None
        for method in METHODS:
            if not train:
                fitted = {'status': 'abstain', 'reason': 'no_earlier_training_transition'}
            else:
                fitted, means = candidate_fit(train, prior, scenario, method, cache, reuse)
                if not a.rank_gate(test, means, scenario)['passes']:
                    fitted = {'status': 'abstain', 'reason': 'evaluation_coverage_or_rank_gate'}
            fits[method] = fitted
            predictions[method] = (predict(test, means, scenario, method, fitted)
                                   if fitted['status'] == 'fitted' else [])
        output['scenarios'][scenario] = {'trainingOnlyMeans': means, 'fits': fits, 'predictions': predictions}
    return output


def response_case(fold, data, elections, training_variant, definitions):
    key = 'originalTrainingIds' if training_variant == 'original_only' else 'trainingIds'
    train, test = a.permitted_fold(fold, data['responseRecords'], key)
    prior = {year: elections[year] for year in {r['targetYear'] for r in train}}
    training = a.response_training(train, prior)
    output = {'foldId': fold['foldId'], 'targetYear': fold['targetYear'],
              'chronologyProtocol': fold['chronologyProtocol'], 'trainingVariant': training_variant,
              'trainingIds': fold[key], 'evaluationIds': fold['evaluationIds'], 'parties': {}}
    for party in ('nationalparty', 'labourparty'):
        rows = [r for r in training if r['party'] == party]
        tests = [r for r in test if r['party'] == party]
        output['parties'][party] = {}
        for method, definition in definitions.items():
            fitted = response.fit(rows, definition)
            predictions = [response.predict(r, fitted, 'actual_observed_local_party') for r in tests]
            output['parties'][party][method] = {'fit': fitted,
                'predictions': [p for p in predictions if p is not None],
                'abstentions': sum(p is None for p in predictions)}
    return output


def reproduce_original(candidate_cases, response_cases, data):
    old_fits = keyed(read(OLD_SHARE + 'fitted-parameters.json')['folds'], 'targetYear')
    old_predictions = keyed(read(OLD_SHARE + 'predictions.json')['folds'], 'targetYear')
    by_id = keyed(data['shareRecords'], 'targetElectorateId')
    checks = []
    for case in candidate_cases:
        if case['trainingVariant'] != 'original_only' or case['targetYear'] not in old_fits:
            continue
        year = case['targetYear']
        if case['trainingIds'] != old_fits[year]['trainingContestIds']:
            continue
        test = [by_id[k] for k in case['evaluationIds']]
        for scenario in SCENARIOS:
            old = old_fits[year]['scenarios'][scenario]
            new = case['scenarios'][scenario]
            if abs(new['trainingOnlyMeans']['S'] - old['trainingOnlyMeans']['S']) > 1e-12:
                raise ValueError('Original S means differ')
            for method in METHODS:
                before, after = old['fits'][method], new['fits'][method]
                if after['status'] != 'fitted':
                    raise ValueError('Original fit failed reproduction')
                direct = predict(test, old['trainingOnlyMeans'], scenario, method, before)
                saved = old_predictions[year]['scenarios'][scenario][method]
                direct_by_id = keyed(direct, 'targetElectorateId')
                saved_by_id = keyed(saved, 'targetElectorateId')
                after_by_id = keyed(new['predictions'][method], 'targetElectorateId')
                direct_gap = max(abs(direct_by_id[cid]['candidateShares'][k] - v)
                    for cid, r in saved_by_id.items() for k, v in r['candidateShares'].items())
                refit_gap = max(abs(after_by_id[cid]['candidateShares'][k] - v)
                    for cid, r in saved_by_id.items() for k, v in r['candidateShares'].items())
                if (direct_gap > 1e-12 or refit_gap > 1e-7 or
                    abs(before['objective'] - after['objective']) > 1e-8 or
                    abs(before['kappa'] - after['kappa']) > 1e-4):
                    raise ValueError('Original Stage22 predictions/fit differ')
                checks.append({'family': 'complete_share', 'foldId': case['foldId'],
                               'scenario': scenario, 'method': method,
                               'directSavedMaximumShareDiscrepancy': direct_gap,
                               'refittedMaximumShareDiscrepancy': refit_gap})
    saved_response = read(OLD_RESPONSE + 'analysis.json')['folds']
    for case in response_cases:
        if case['trainingVariant'] != 'original_only':
            continue
        for party, methods in case['parties'].items():
            for method, current in methods.items():
                old = next((f for f in saved_response if f['targetYear'] == case['targetYear']
                            and f['party'] == party and f['model'] == method
                            and f['mode'] == 'actual_observed_local_party'), None)
                if old is None or current['fit']['status'] != 'available':
                    continue
                prior_ids = [k.replace(':general:', ':') for k in current['fit']['trainingRecordIds']]
                if prior_ids != old['fit']['trainingRecordIds']:
                    continue
                if any(abs(old['fit'][k] - current['fit'][k]) > 1e-8 for k in ('alpha', 'beta', 'gamma')):
                    raise ValueError('Original Stage16 fit differs')
                preds = {p['id'].replace(':general:', ':'): p for p in current['predictions']}
                gap = max(abs(preds[p['id']]['point'] - p['point']) for p in old['predictions'])
                if gap > 1e-12:
                    raise ValueError('Original Stage16 predictions differ')
                checks.append({'family': 'response', 'foldId': case['foldId'],
                               'party': party, 'method': method, 'maximumPredictionDiscrepancy': gap})
    return {'checks': checks, 'passed': True}


def build(data, folds, elections, definitions, reuse=None):
    cache, candidates, responses = {}, [], []
    # Original-only construction precedes expanded cases. No held-out scores read.
    for variant in ('original_only', 'expanded'):
        for f in folds:
            if f['family'] == 'complete_share_baseline_s':
                candidates.append(candidate_case(f, data, elections, variant, cache, reuse))
            else:
                responses.append(response_case(f, data, elections, variant, definitions))
        if variant == 'original_only':
            reproduction = reproduce_original(candidates, responses, data)
    return {'stage': 27, 'role': 'conditional_predictions_earlier_fits_no_holdout_actuals',
            'candidateCases': candidates, 'responseCases': responses,
            'originalReproduction': reproduction, 'operationalSelection': None}, cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--refit', action='store_true', help='Re-estimate instead of validating pinned identical-fit cache')
    args = parser.parse_args()
    verify_inputs()
    data = read(DEST + 'inventory.json')
    folds = read(DEST + 'folds.json')['folds']
    elections, _ = a.datasets()
    old_manifest = read(DEST + 'construction-manifest.json') if args.check else None
    reuse = None
    if args.check and not args.refit:
        cache_doc = read(DEST + 'fit-cache.json')
        if sha256(encode(cache_doc)).hexdigest() != old_manifest['outputSha256']['fit-cache.json']:
            raise ValueError('Changed fit cache')
        reuse = cache_doc
    predictions, cache = build(data, folds, elections, read(DEST + 'input-contract.json')['responseModels'], reuse)
    result = {'predictions.json': predictions, 'fit-cache.json': cache}
    result['construction-manifest.json'] = phase_manifest(
        [DEST + p for p in ('input-contract.json', 'inventory.json', 'folds.json')], result)
    save_outputs(result, args.check)
    print(json.dumps({'distinctCandidateFits': len(cache), 'originalReproduction': predictions['originalReproduction']['passed']}))


if __name__ == '__main__':
    main()
