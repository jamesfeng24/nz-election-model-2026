"""Reuse saved Stage22 fits while substituting only Stage23 party inputs."""
import argparse
from decimal import Decimal, localcontext
from hashlib import sha256
import math

from scripts.checkpoints.stage22_fit import predict, source_s
from scripts.checkpoints.stage24_common import (
    PREFIX, STAGE22, digest, encode, read, verify_contract, write_or_check,
)

METHODS = {'A': 'baseline', 'B': 'baseline_plus_S',
           'C': 'baseline', 'D': 'baseline_plus_S'}
SCENARIOS = ('printed', 'selected_lower', 'selected_upper')
TOL = 1e-12


def adapter_rows(contests, party_input):
    if party_input not in ('observed', 'predicted'):
        raise ValueError('Unknown party input')
    key = 'observedTargetPartySupport' if party_input == 'observed' else 'predictedTargetPartySupport'
    rows = []
    for contest in contests:
        candidates = []
        for candidate in contest['candidates']:
            support = candidate[key]
            if type(support) not in (int, float) or not math.isfinite(support) or support < 0:
                raise ValueError('Incomplete candidate party input')
            candidates.append({
                'targetOccurrenceId': candidate['candidateOccurrenceId'],
                'targetPartySupport': support,
                's0Reported': candidate['s0Reported'],
                'coupledSamePartyPercent': candidate['coupledSamePartyPercent'],
                'v0': None,  # Read by generic Stage22 adapter; unused by both frozen restrictions.
            })
        rows.append({'targetElectorateId': contest['targetElectorateId'],
                     'candidates': candidates})
    return rows


def reproduce_observed(predicted, saved, method):
    if len(predicted) != len(saved):
        raise ValueError('Saved observed-input contest sample differs')
    maximum = 0.0
    for new, old in zip(predicted, saved):
        if (new['targetElectorateId'] != old['targetElectorateId'] or
                set(new['candidateShares']) != set(old['candidateShares'])):
            raise ValueError('Saved observed-input candidate IDs differ')
        for cid, value in new['candidateShares'].items():
            maximum = max(maximum, abs(value - old['candidateShares'][cid]))
    if maximum > TOL:
        raise ValueError(f'Observed-input {method} reproduction failed: {maximum}')
    return maximum


def model_predictions(rows, means, scenario, method, parameters):
    if parameters['status'] != 'fitted':
        raise ValueError('Saved Stage22 fit is unavailable')
    if method == 'baseline' and parameters['theta'] != []:
        raise ValueError('Baseline unexpectedly has feature coefficient')
    if method == 'baseline_plus_S' and len(parameters['theta']) != 1:
        raise ValueError('S-only fit is not one-dimensional')
    return predict(rows, means, scenario, method, parameters)


def portable_predictions(rows, means, scenario, method, parameters):
    """Evaluate the frozen intensity equation with platform-stable precision."""
    if parameters['status'] != 'fitted' or method not in ('baseline', 'baseline_plus_S'):
        raise ValueError('Unsupported saved Stage22 restriction')
    if len(parameters['theta']) != (method == 'baseline_plus_S'):
        raise ValueError('Saved Stage22 parameter count changed')
    result = []
    with localcontext() as context:
        context.prec = 50
        kappa = Decimal(str(parameters['kappa']))
        theta = Decimal(str(parameters['theta'][0])) if parameters['theta'] else None
        center = Decimal(str(means['S']))
        for row in rows:
            intensities = []
            for candidate in row['candidates']:
                base = Decimal(str(candidate['targetPartySupport'])) + kappa
                if base <= 0:
                    raise ValueError('Candidate intensity is nonpositive')
                s = source_s(candidate, scenario)
                if theta is not None and s is not None:
                    base *= (theta * (Decimal(str(s)) - center)).exp()
                intensities.append(base)
            total = sum(intensities)
            shares = [float(value / total) for value in intensities]
            if abs(sum(shares) - 1) > TOL:
                raise ValueError('Candidate shares do not conserve')
            result.append({'targetElectorateId': row['targetElectorateId'],
                           'candidateShares': {candidate['targetOccurrenceId']: share
                                               for candidate, share in zip(row['candidates'], shares)}})
    return result


def equivalent_predictions(actual, reference):
    if len(actual) != len(reference):
        raise ValueError('Platform-stable prediction changed contest count')
    for new, old in zip(actual, reference):
        reproduce_observed([new], [old], 'portable')


def build(inventory, saved):
    saved_by_year = {f['targetYear']: f for f in saved['folds']}
    if len(saved_by_year) != 2 or set(saved_by_year) != {2017, 2023}:
        raise ValueError('Stage22 saved trained holdouts changed')
    reproduced, folds = [], []
    for fold in inventory['folds']:
        year = fold['targetYear']
        reference = saved_by_year[year]
        observed = adapter_rows(fold['contests'], 'observed')
        by_scenario = {}
        for scenario in SCENARIOS:
            parameters = fold['scenarios'][scenario]['parameters']
            means = fold['scenarios'][scenario]['trainingOnlyMeans']
            if set(parameters) != {'baseline', 'baseline_plus_S'} or set(means) != {'S', 'V'}:
                raise ValueError('Saved fit or training mean contract changed')
            a = model_predictions(observed, means, scenario, 'baseline', parameters['baseline'])
            b = model_predictions(observed, means, scenario, 'baseline_plus_S', parameters['baseline_plus_S'])
            reproduce_observed(a, reference['scenarios'][scenario]['baseline'], 'A')
            reproduce_observed(b, reference['scenarios'][scenario]['baseline_plus_S'], 'B')
            # The saved A/B shares are the authoritative observed-input
            # reference after exact-ID and tolerance reproduction.
            by_scenario[scenario] = {
                'A': reference['scenarios'][scenario]['baseline'],
                'B': reference['scenarios'][scenario]['baseline_plus_S']}
            reproduced.append({'targetYear': year, 'scenario': scenario,
                               'observedAWithinTolerance': True,
                               'observedBWithinTolerance': True,
                               'absoluteShareTolerance': TOL})
        # Every observed-input reference must reproduce before the first
        # Stage23 candidate substitution is calculated for this fold.
        substitute = adapter_rows(fold['contests'], 'predicted')
        for scenario in SCENARIOS:
            parameters = fold['scenarios'][scenario]['parameters']
            means = fold['scenarios'][scenario]['trainingOnlyMeans']
            for cell, method in (('C', 'baseline'), ('D', 'baseline_plus_S')):
                saved_fit = parameters[method]
                stable = portable_predictions(substitute, means, scenario, method, saved_fit)
                equivalent_predictions(stable, model_predictions(
                    substitute, means, scenario, method, saved_fit))
                by_scenario[scenario][cell] = stable
        folds.append({'targetYear': year,
                      'commonEvaluationContestIds': fold['commonEvaluationContestIds'],
                      'commonEvaluationCandidateOccurrenceIds': fold['commonEvaluationCandidateOccurrenceIds'],
                      'scenarios': by_scenario})
    return folds, reproduced


def outputs():
    verify_contract()
    inventory = read(PREFIX + 'input-inventory.json')
    analysis = read(PREFIX + 'analysis-contract.json')
    if (not analysis['frozenBeforeCandidatePredictionAndScoring'] or
            analysis['targetYears'] != [2017, 2023] or
            set(analysis['cells']) != set(METHODS) or
            set(analysis['scenarios']) != set(SCENARIOS)):
        raise ValueError('Stage24 pre-calculation rule changed')
    saved = read(STAGE22 + 'predictions.json')
    folds, reproduction = build(inventory, saved)
    result = {'schemaVersion': 1, 'stage': 24,
              'role': 'four_cell_candidate_construction_no_heldout_candidate_outcomes',
              'informationSet': analysis['informationSet'],
              'observedReproduction': reproduction,
              'folds': folds, 'operationalSelection': None}
    manifest = {'schemaVersion': 1, 'stage': 24,
                'phase': 'construction_committed_before_target_candidate_evaluation',
                'inputSha256': {path: digest(path) for path in (
                    PREFIX + 'input-contract.json', PREFIX + 'input-inventory.json',
                    PREFIX + 'analysis-contract.json', STAGE22 + 'predictions.json')},
                'codeSha256': {path: digest(path) for path in (
                    'scripts/checkpoints/stage24_common.py',
                    'scripts/checkpoints/stage24_construction.py')},
                'outputSha256': sha256(encode(result)).hexdigest()}
    return result, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    predictions, manifest = outputs()
    write_or_check('predictions.json', predictions, args.check)
    write_or_check('construction-manifest.json', manifest, args.check)
    print({'folds': [f['targetYear'] for f in predictions['folds']],
           'observedInputReproductionTolerance': TOL,
           'allObservedInputChecksPassed': all(
               r['observedAWithinTolerance'] and r['observedBWithinTolerance']
               for r in predictions['observedReproduction'])})


if __name__ == '__main__':
    main()
