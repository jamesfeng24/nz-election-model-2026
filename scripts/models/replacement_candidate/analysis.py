"""Stage 10 arithmetic diagnostics with explicit non-identifiability."""

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


def analyze(records, counterfactual, elected_ids=None):
    """Summarize supported continuations and winner-selected replacements separately."""
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
    status = [{'sourceYear': year, 'targetYear': target,
               'treatment': sum(row['sourceYear'] == year for row in treated),
               'comparator': sum(row['sourceYear'] == year for row in continuing),
               'retrospectiveDistinctPeople': sum(row['sourceYear'] == year for row in retrospective)}
              for year, target in ((2008, 2011), (2014, 2017), (2020, 2023))]
    grouped = {scale: {
        'supportedContinuation': {str(year): _group([row for row in continuing if row['sourceYear'] == year], scale)
                                  for year in (2008, 2014, 2020)},
        'retrospectiveDistinctPeople': {str(year): _group([row for row in retrospective if row['sourceYear'] == year], scale)
                                        for year in (2008, 2014, 2020)}}
        for scale in ('additive', 'proportional', 'log_odds')}
    return {'schemaVersion': 1, 'primaryTransitionCounts': status,
            'primaryTreatmentCount': len(treated), 'primaryComparatorCount': len(continuing),
            'retrospectiveDistinctPeopleCount': len(retrospective),
            'retrospectiveTargetWinners': retrospective_target_winners,
            'chronologicalFittedComparison': None,
            'chronologicalUnavailableReason': 'No pre-target-supported source-winner replacement in any unchanged-boundary transition; neither full nor no-replacement model has a common two-group evaluation sample.',
            'descriptiveBenchmarks': grouped,
            'retrospectiveTargetWinnerSelected': True,
            'outgoingStatusCounts': dict(sorted(Counter(row['outgoingStatus'] for row in records).items())),
            'identityClassCounts': dict(sorted(Counter(row['identityClass'] for row in records).items())),
            'interpretation': 'Zero/carry-forward arithmetic uses observed outcomes only for evaluation. Retrospective distinct-person events can rely on target/later winner anchors and are not validation. No fitted replacement coefficient or candidate-pair iid inference is warranted.'}


def select(analysis):
    """Keep operational selection null when a two-group holdout is unidentified."""
    counts = analysis['primaryTransitionCounts']
    both_groups = all(row['treatment'] and row['comparator'] for row in counts)
    return {'schemaVersion': 1, 'selectedOperationalReplacementEffectPP': None,
            'selectionStatus': 'insufficient_outcome_independent_treatment_evidence',
            'gates': {'bothGroupsEachTransition': bool(both_groups),
                      'chronologicalImprovement': None,
                      'normalizationIdentityStability': None},
            'reason': analysis['chronologicalUnavailableReason']}
