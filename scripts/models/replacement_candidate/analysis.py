"""Stage 10 conditional replacement diagnostics and chronological comparisons."""

from collections import Counter
from math import sqrt


def score(rows, predictor):
    """Calculate MAE and RMSE in percentage points on one sample."""
    errors = [(predictor(row) - row['targetResidual']) * 100 for row in rows]
    if not errors:
        return None
    return {'n': len(errors), 'maePP': sum(abs(error) for error in errors) / len(errors),
            'rmsePP': sqrt(sum(error * error for error in errors) / len(errors))}


def _scale_rows(rows, scale):
    result = []
    for row in rows:
        pair = {'priorResidual': row['priorResidual'], 'targetResidual': row['targetResidual']}
        if scale != 'additive':
            alternate = row['scaleResiduals'][scale]
            pair = {'priorResidual': alternate['prior'], 'targetResidual': alternate['target']}
        if None not in pair.values():
            result.append(pair)
    return result


def _group(rows, scale):
    pairs = _scale_rows(rows, scale)
    if not pairs:
        return {'n': 0, 'meanPriorPP': None, 'meanTargetPP': None,
                'meanChangePP': None, 'zero': None, 'carryForward': None}
    return {'n': len(pairs),
            'meanPriorPP': sum(row['priorResidual'] for row in pairs) * 100 / len(pairs),
            'meanTargetPP': sum(row['targetResidual'] for row in pairs) * 100 / len(pairs),
            'meanChangePP': sum(row['targetResidual'] - row['priorResidual']
                                for row in pairs) * 100 / len(pairs),
            'zero': score(pairs, lambda row: 0),
            'carryForward': score(pairs, lambda row: row['priorResidual'])}


def _solve(matrix, vector):
    """Small deterministic least-squares normal-equation solver."""
    n = len(vector)
    augmented = [list(matrix[i]) + [vector[i]] for i in range(n)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda i: abs(augmented[i][column]))
        if abs(augmented[pivot][column]) < 1e-10:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        factor = augmented[column][column]
        augmented[column] = [value / factor for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [value - factor * other for value, other in
                              zip(augmented[row], augmented[column])]
    return [row[-1] for row in augmented]


def _model_rows(records, scale):
    rows = []
    for record in records:
        pair = {'prior': record['priorResidual'], 'target': record['targetResidual']}
        if scale != 'additive':
            pair = record['scaleResiduals'][scale]
        if pair['prior'] is None or pair['target'] is None:
            continue
        rows.append({'eventId': record['eventId'], 'sourceYear': record['sourceYear'],
                     'targetYear': record['targetYear'], 'partyKey': record['partyKey'],
                     'replacement': int(record['identityClass'] == 'supported_replacement'),
                     'priorPP': 100 * pair['prior'], 'targetPP': 100 * pair['target']})
    return rows


def _features(row, formulation):
    result = [1.0, row['priorPP']]
    if formulation == 'replacement':
        result.append(row['replacement'])
    elif formulation == 'retention':
        result.append(row['replacement'] * row['priorPP'])
    return result


def fit(rows, formulation):
    """Fit an intercept and source residual, with a prespecified optional term."""
    if formulation not in ('no_replacement', 'replacement', 'retention'):
        raise ValueError('Unknown replacement formulation')
    width = 2 if formulation == 'no_replacement' else 3
    matrix = [[0.0] * width for _ in range(width)]
    vector = [0.0] * width
    for row in rows:
        features = _features(row, formulation)
        for i in range(width):
            vector[i] += features[i] * row['targetPP']
            for j in range(width):
                matrix[i][j] += features[i] * features[j]
    coefficients = _solve(matrix, vector) if len(rows) >= width else None
    if coefficients is None:
        return None
    result = {'interceptPP': coefficients[0], 'priorSlope': coefficients[1]}
    if formulation == 'replacement':
        result['replacementShiftPP'] = coefficients[2]
    if formulation == 'retention':
        result['replacementPriorInteraction'] = coefficients[2]
    return result


def _predict(row, model, formulation):
    features = _features(row, formulation)
    return sum(coefficient * feature for coefficient, feature in zip(
        [model['interceptPP'], model['priorSlope']] +
        ([model['replacementShiftPP']] if formulation == 'replacement' else
         [model['replacementPriorInteraction']] if formulation == 'retention' else []),
        features))


def _score_pp(rows, predictor):
    errors = [predictor(row) - row['targetPP'] for row in rows]
    if not errors:
        return None
    return {'n': len(errors), 'maePP': sum(map(abs, errors)) / len(errors),
            'rmsePP': sqrt(sum(error * error for error in errors) / len(errors))}


def chronological(rows):
    """Use only earlier target elections for each trained holdout."""
    result = []
    for target in (2017, 2023):
        train = [row for row in rows if row['targetYear'] < target]
        holdout = [row for row in rows if row['targetYear'] == target]
        groups = {'trainingReplacement': sum(row['replacement'] for row in train),
                  'trainingContinuation': sum(not row['replacement'] for row in train),
                  'holdoutReplacement': sum(row['replacement'] for row in holdout),
                  'holdoutContinuation': sum(not row['replacement'] for row in holdout)}
        available = all(groups.values())
        fitted = fit(train, 'replacement') if available else None
        no_effect = fit(train, 'no_replacement') if available else None
        retention = fit(train, 'retention') if available else None
        result.append({'targetYear': target, 'trainingTargetYears': sorted({r['targetYear'] for r in train}),
                       'counts': groups, 'fittedReplacement': fitted,
                       'fittedNoReplacement': no_effect,
                       'fittedRetentionSensitivity': retention,
                       'replacementScore': (_score_pp(holdout, lambda r: _predict(r, fitted, 'replacement'))
                                            if fitted else None),
                       'noReplacementScore': (_score_pp(holdout, lambda r: _predict(r, no_effect, 'no_replacement'))
                                              if no_effect else None),
                       'retentionScore': (_score_pp(holdout, lambda r: _predict(r, retention, 'retention'))
                                          if retention else None),
                       'zeroScore': _score_pp(holdout, lambda r: 0),
                       'carryForwardScore': _score_pp(holdout, lambda r: r['priorPP']),
                       'holdoutEventIds': [r['eventId'] for r in holdout]})
    return result


def analyze(records, counterfactual, elected_ids=None):
    """Keep prospective-style diagnostics separate from retrospective illustrations."""
    if len(counterfactual['records']) != len(records):
        raise ValueError('Incomplete winner-flag counterfactual')
    eligible = [row for row in records if row['primaryEligible']]
    if any(not row['classificationAndEligibilityStable'] and row['originalPrimaryEligible']
           for row in counterfactual['records']):
        raise ValueError('Primary cohort depends on target/later winner flags')
    treated = [row for row in eligible if row['identityClass'] == 'supported_replacement']
    continuing = [row for row in eligible if row['identityClass'] == 'supported_continuation']
    retrospective = [row for row in records
                     if row['identityClass'] == 'retrospective_distinct_people' and
                     row['outgoingStatus'] == 'source_winner' and
                     row['exclusionReasons'] == ['identity_not_pre_target_supported']]
    retrospective_target_winners = (sum(row['targetOccurrenceId'] in elected_ids
                                        for row in retrospective)
                                    if elected_ids is not None else None)
    by_election = [row for row in records if row['identityClass'] == 'supported_by_election_successor']
    alias_diagnostic = [row for row in records if row['identityClass'] == 'retrospective_alias_replacement']
    status = [{'sourceYear': year, 'targetYear': target,
               'treatment': sum(row['sourceYear'] == year for row in treated),
               'comparator': sum(row['sourceYear'] == year for row in continuing),
               'retrospectiveDistinctPeople': sum(row['sourceYear'] == year for row in retrospective),
               'byElectionSuccessors': sum(row['sourceYear'] == year for row in by_election),
               'laterSuccessCoveredAliases': sum(row['sourceYear'] == year for row in alias_diagnostic)}
              for year, target in ((2008, 2011), (2014, 2017), (2020, 2023))]
    grouped = {scale: {
        'supportedContinuation': {str(year): _group([row for row in continuing if row['sourceYear'] == year], scale)
                                  for year in (2008, 2014, 2020)},
        'retrospectiveDistinctPeople': {str(year): _group([row for row in retrospective if row['sourceYear'] == year], scale)
                                        for year in (2008, 2014, 2020)}}
        for scale in ('additive', 'proportional', 'log_odds')}
    model_records = treated + continuing
    model_rows = {scale: _model_rows(model_records, scale)
                  for scale in ('additive', 'proportional', 'log_odds')}
    strict = [row for row in model_records if not row['stage10IdentityEvidence'] or
              row['stage10IdentityEvidence']['sourceRoute'] == 'source_winner_anchor']
    party_counts = Counter((row['sourceYear'], row['partyKey'], row['identityClass'])
                           for row in model_records)
    cohort_counts = Counter((row['sourceYear'], row['targetYear'], row['partyKey'],
                             row['electorateType'], row['outgoingStatus'],
                             row['identityClass'], row['sourceOccurrenceConfidence'],
                             row['targetOccurrenceConfidence'], row['primaryEligible'])
                            for row in records)
    full_sample = {scale: {'replacement': fit(rows, 'replacement'),
                           'noReplacement': fit(rows, 'no_replacement'),
                           'retentionSensitivity': fit(rows, 'retention')}
                   for scale, rows in model_rows.items()}
    return {'schemaVersion': 2, 'primaryTransitionCounts': status,
            'primaryTreatmentCount': len(treated), 'primaryComparatorCount': len(continuing),
            'retrospectiveDistinctPeopleCount': len(retrospective),
            'retrospectiveTargetWinners': retrospective_target_winners,
            'byElectionSuccessorCount': len(by_election),
            'laterSuccessCoveredAliasCount': len(alias_diagnostic),
            'partyCounts': [{'sourceYear': year, 'partyKey': party, 'identityClass': identity,
                             'count': count} for (year, party, identity), count in sorted(party_counts.items())],
            'cohortBreakdown': [
                {'sourceYear': year, 'targetYear': target, 'partyKey': party,
                 'electorateType': scope, 'outgoingStatus': outgoing,
                 'identityClass': identity, 'sourceOccurrenceConfidence': source_confidence,
                 'targetOccurrenceConfidence': target_confidence,
                 'primaryEligible': eligible, 'count': count}
                for (year, target, party, scope, outgoing, identity, source_confidence,
                     target_confidence, eligible), count in sorted(cohort_counts.items())],
            'chronologicalFittedComparison': {scale: chronological(rows)
                                               for scale, rows in model_rows.items()},
            'strictSourceAnchorSensitivity': {
                'n': len(strict), 'additiveChronological': chronological(_model_rows(strict, 'additive')),
                'fullSample': fit(_model_rows(strict, 'additive'), 'replacement')},
            'fullSampleDescriptions': full_sample,
            'descriptiveBenchmarks': grouped,
            'retrospectiveTargetWinnerSelected': True,
            'outgoingStatusCounts': dict(sorted(Counter(row['outgoingStatus'] for row in records).items())),
            'identityClassCounts': dict(sorted(Counter(row['identityClass'] for row in records).items())),
            'interpretation': 'Conditional fits and chronological scores are predictive diagnostics only. Retrospective target/later-anchored identities and later-success-covered aliases cannot determine operational selection. Few election clusters and shared references preclude candidate-pair iid uncertainty or causal claims.'}


def select(analysis, acquisition_independent=False):
    """Apply the original predeclared gates to corrected evidence without tuning."""
    holdouts = analysis['chronologicalFittedComparison']['additive']
    both = all(row['fittedReplacement'] and row['fittedNoReplacement'] and
               row['counts']['holdoutReplacement'] and row['counts']['holdoutContinuation']
               for row in holdouts)
    nonworse = (all(row['replacementScore']['maePP'] <= row['noReplacementScore']['maePP'] and
                    row['replacementScore']['rmsePP'] <= row['noReplacementScore']['rmsePP']
                    for row in holdouts) if both else None)
    pooled_gain = (sum(row['noReplacementScore']['maePP'] * row['noReplacementScore']['n'] -
                       row['replacementScore']['maePP'] * row['replacementScore']['n']
                       for row in holdouts) /
                   sum(row['replacementScore']['n'] for row in holdouts) if both else None)
    fitted = [analysis['fullSampleDescriptions'][scale]['replacement']
              for scale in ('additive', 'proportional', 'log_odds')]
    strict = analysis['strictSourceAnchorSensitivity']['fullSample']
    signs = ([model['replacementShiftPP'] for model in fitted if model] +
             ([strict['replacementShiftPP']] if strict else []))
    stable = (len(signs) == 4 and all(value > 0 for value in signs) or
              len(signs) == 4 and all(value < 0 for value in signs))
    approved = bool(both and nonworse and pooled_gain is not None and
                    pooled_gain >= 0.25 and stable and acquisition_independent)
    failed = [name for name, passes in (
        ('both_groups_each_trained_holdout', both),
        ('nonworse_mae_rmse_each_holdout', nonworse),
        ('pooled_mae_gain_at_least_0_25_pp', pooled_gain is not None and pooled_gain >= 0.25),
        ('normalization_and_identity_direction_stable', stable),
        ('acquisition_independent_of_target_later_outcomes', acquisition_independent)) if not passes]
    return {'schemaVersion': 2,
            'selectedOperationalReplacementEffectPP': (fitted[0]['replacementShiftPP'] if approved else None),
            'selectionStatus': 'selected' if approved else 'not_selected_under_frozen_gates',
            'gates': {'bothGroupsEachTrainedHoldout': bool(both),
                      'nonworseMAEAndRMSEEachHoldout': nonworse,
                      'pooledMAEImprovementPP': pooled_gain,
                      'pooledMAEImprovementAtLeast0_25PP': pooled_gain is not None and pooled_gain >= 0.25,
                      'normalizationIdentityDirectionStable': bool(stable),
                      'acquisitionIndependentOfTargetLaterOutcomes': bool(acquisition_independent)},
            'failedGates': failed,
            'reason': ('All predeclared gates passed' if approved else
                       'Corrected evidence did not satisfy the predeclared operational gates; descriptive fits remain non-operational.')}
