"""Outcome-free within-slate design diagnostics for the proposed four restrictions."""

from collections import Counter
from math import sqrt

import numpy as np


PROBES = (0.0001, 0.01, 0.1)
RANK_RELATIVE_TOLERANCE = 1e-8
CONDITION_WARNING = 1e6


def training_means(contests):
    """Equal contest weight; each candidate within a slate has weight 1/n."""
    result = {}
    for label, field in (('S', 's0Reported'), ('V', 'v0')):
        numerator = denominator = 0.0
        for seat in contests:
            candidates = seat['candidates']
            weight = 1 / len(candidates)
            for candidate in candidates:
                if candidate[field] is not None:
                    numerator += weight * candidate[field]
                    denominator += weight
        result[label] = numerator / denominator if denominator else None
    return result


def design(contests, means, kappa):
    rows = []
    for seat in contests:
        values = []
        for candidate in seat['candidates']:
            support = candidate['targetPartySupport']
            values.append([1 / (support + kappa),
                           (candidate['s0Reported'] - means['S']
                            if candidate['s0Reported'] is not None and means['S'] is not None else 0),
                           (candidate['v0'] - means['V']
                            if candidate['v0'] is not None and means['V'] is not None else 0)])
        block = np.asarray(values, dtype=float)
        rows.extend((block - block.mean(axis=0)) / sqrt(len(block)))
    return np.asarray(rows, dtype=float)


def rank_details(matrix, columns):
    selected = matrix[:, columns]
    norms = np.linalg.norm(selected, axis=0)
    scaled = np.divide(selected, norms, out=np.zeros_like(selected), where=norms > 0)
    singular = np.linalg.svd(scaled, full_matrices=False, compute_uv=False)
    threshold = max(float(singular[0]) * RANK_RELATIVE_TOLERANCE, 1e-12)
    rank = sum(value > threshold for value in singular)
    return {'rank': int(rank), 'columns': len(columns),
            'unscaledColumnNorms': [round(float(x), 6) for x in norms],
            'singularValues': [round(float(x), 6) for x in singular],
            'conditionRatio': (round(float(singular[0] / singular[-1]), 6)
                               if singular[-1] > 0 else None),
            'weakCondition': bool(singular[-1] <= 0 or
                                  singular[0] / singular[-1] > CONDITION_WARNING)}


def group_diagnostics(contests, means):
    by_party = Counter()
    candidates = [c for seat in contests for c in seat['candidates']]
    for c in candidates:
        if c['s0Reported'] is not None:
            by_party[c['targetPartyKey']] += 1
    s_contrasts = v_contrasts = 0
    for seat in contests:
        for field, label in (('s0Reported', 'S'), ('v0', 'V')):
            values = [(c[field] - means[label] if c[field] is not None and
                       means[label] is not None else 0) for c in seat['candidates']]
            if max(values) - min(values) > 1e-9:
                if label == 'S':
                    s_contrasts += 1
                else:
                    v_contrasts += 1
    return {'candidates': len(candidates),
            'sSupportedCandidates': sum(c['s0Reported'] is not None for c in candidates),
            'vSupportedCandidates': sum(c['v0'] is not None for c in candidates),
            'sWithinSlateContrastContests': s_contrasts,
            'vWithinSlateContrastContests': v_contrasts,
            'topSupportedParties': [{'partyKey': party, 'candidateCount': count}
                                    for party, count in by_party.most_common(8)]}


def fold(contests, means):
    if not contests or means['S'] is None or means['V'] is None:
        return {'status': 'insufficient_feature_support', 'contests': len(contests)}
    probes = []
    for kappa in PROBES:
        matrix = design(contests, means, kappa)
        probes.append({'kappaProbe': kappa,
                       'featureTerms': rank_details(matrix, [1, 2]),
                       'combinedWithFloor': rank_details(matrix, [0, 1, 2]),
                       'centeredFeatureCorrelation': (round(float(np.corrcoef(
                           matrix[:, 1], matrix[:, 2])[0, 1]), 6)
                           if np.std(matrix[:, 1]) > 0 and np.std(matrix[:, 2]) > 0
                           else None)})
    return {'status': 'audited', 'contests': len(contests),
            'features': group_diagnostics(contests, means), 'probeDesigns': probes}


def build(features):
    by_year = {year: [r for r in features['records'] if r['targetYear'] == year
                      and r['status'] == 'constructed'] for year in (2011, 2017, 2023)}
    folds = []
    for holdout, training_years in ((2017, (2011,)), (2023, (2011, 2017))):
        training = [r for year in training_years for r in by_year[year]]
        evaluation = by_year[holdout]
        means = training_means(training)
        train = fold(training, means)
        evaluate = fold(evaluation, means)
        min_training = len(training) >= 20 and sum(
            any(c['s0Reported'] is not None for c in r['candidates']) for r in training) >= 20
        min_evaluation = len(evaluation) >= 20 and sum(
            any(c['s0Reported'] is not None for c in r['candidates']) for r in evaluation) >= 20
        identifiable = (train['status'] == 'audited' and all(
            p['featureTerms']['rank'] == 2 and p['combinedWithFloor']['rank'] == 3 and
            not p['combinedWithFloor']['weakCondition'] for p in train['probeDesigns']))
        folds.append({'targetYear': holdout, 'trainingTargetYears': list(training_years),
                      'trainingContestIds': [r['targetElectorateId'] for r in training],
                      'evaluationContestIds': [r['targetElectorateId'] for r in evaluation],
                      'trainingOnlyMeans': means, 'training': train,
                      'evaluation': evaluate,
                      'coverageGate': {'training': min_training, 'evaluation': min_evaluation},
                      'trainingDesignIdentifiableAtAllProbes': identifiable,
                      'passesProposedPreFitGates': min_training and min_evaluation and identifiable})
    return {'schemaVersion': 1, 'stage': 20,
            'role': 'outcome_free_within_slate_feature_rank_and_fixed_sample_audit',
            'rankRelativeTolerance': RANK_RELATIVE_TOLERANCE,
            'conditionWarningAbove': CONDITION_WARNING,
            'floorProbes': list(PROBES), 'folds': folds,
            'allFittingGatesPass': all(f['passesProposedPreFitGates'] for f in folds)}
