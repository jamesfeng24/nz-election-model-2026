"""Bounded freshman association fits and chronological diagnostics."""

from math import sqrt


def prepare_rows(inventory, pairs, scale='additive', extra=None, allowed_pair_ids=None):
    """Join frozen pre-fit eligibility to residuals; target outcomes never set eligibility."""
    extra = extra or 'primary'
    by_id = {pair['pairId']: pair for pair in pairs}
    if len(by_id) != len(pairs):
        raise ValueError('Duplicate Stage 8 pair ID')
    rows = []
    for record in inventory:
        reasons = set(record['exclusionReasons'])
        eligible = record['primaryEligible']
        if extra == 'prior_list' and reasons == {'prior_list_service_primary_exclusion'}:
            eligible = True
        if extra == 'off_cycle' and reasons == {'off_cycle_entrant_primary_exclusion'}:
            eligible = True
        if extra == 'both_confirmed':
            eligible = eligible and record['sourceIdentityStatus'] == 'confirmed' and record['targetIdentityStatus'] == 'confirmed'
        if allowed_pair_ids is not None and record['pairId'] not in allowed_pair_ids:
            eligible = False
        if not eligible or record['electorateType'] != 'general':
            continue
        pair = by_id.get(record['pairId'])
        if pair is None:
            raise ValueError(f'Dangling inventory pair: {record["pairId"]}')
        if scale == 'additive':
            source, target = pair['priorResidual'], pair['targetResidual']
        else:
            values = pair['scaleResiduals'][scale]
            source, target = values['prior'], values['target']
        if source is None or target is None:
            continue
        rows.append({'pairId': record['pairId'], 'personId': record['personId'],
                     'sourceYear': record['sourceYear'], 'targetYear': record['targetYear'],
                     'treatment': int(record['tenureCategory'] == 'first_term'),
                     'xPP': source * 100, 'yPP': target * 100,
                     'sourceIdentityStatus': record['sourceIdentityStatus'],
                     'targetIdentityStatus': record['targetIdentityStatus']})
    rows.sort(key=lambda row: (row['targetYear'], row['pairId']))
    return rows


def _solve(matrix, vector):
    order = len(vector)
    augmented = [matrix[i][:] + [vector[i]] for i in range(order)]
    for column in range(order):
        pivot = max(range(column, order), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(order):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [left - factor * right
                              for left, right in zip(augmented[row], augmented[column])]
    return [augmented[row][-1] for row in range(order)]


def fit(rows, freshman=True):
    """Equal-weight OLS with an intercept and optionally one freshman indicator."""
    dimension = 3 if freshman else 2
    if len(rows) < dimension or (freshman and {row['treatment'] for row in rows} != {0, 1}):
        return None
    design = [[1.0, row['xPP'], *([row['treatment']] if freshman else [])] for row in rows]
    matrix = [[sum(features[i] * features[j] for features in design)
               for j in range(dimension)] for i in range(dimension)]
    vector = [sum(features[i] * row['yPP'] for features, row in zip(design, rows))
              for i in range(dimension)]
    coefficients = _solve(matrix, vector)
    if coefficients is None:
        return None
    return {'interceptPP': coefficients[0], 'priorSlope': coefficients[1],
            'freshmanEffectPP': coefficients[2] if freshman else None,
            'n': len(rows), 'firstTermN': sum(row['treatment'] for row in rows),
            'experiencedN': sum(not row['treatment'] for row in rows)}


def predict(row, fitted):
    return (fitted['interceptPP'] + fitted['priorSlope'] * row['xPP'] +
            (fitted['freshmanEffectPP'] or 0.0) * row['treatment'])


def score(rows, predictions):
    if len(rows) != len(predictions):
        raise ValueError('Predictions and evaluation rows differ')
    if not rows:
        return None
    errors = [prediction - row['yPP'] for row, prediction in zip(rows, predictions)]
    return {'n': len(rows), 'firstTermN': sum(row['treatment'] for row in rows),
            'experiencedN': sum(not row['treatment'] for row in rows),
            'maePP': sum(abs(error) for error in errors) / len(errors),
            'rmsePP': sqrt(sum(error * error for error in errors) / len(errors))}


def change_contrast(rows):
    groups = {group: [row['yPP'] - row['xPP'] for row in rows
                      if row['treatment'] == group] for group in (0, 1)}
    if not all(groups.values()):
        return None
    return {'firstTermMeanChangePP': sum(groups[1]) / len(groups[1]),
            'experiencedMeanChangePP': sum(groups[0]) / len(groups[0]),
            'differencePP': sum(groups[1]) / len(groups[1]) - sum(groups[0]) / len(groups[0])}


def analyze(rows):
    """Separate descriptive full-sample fits from earlier-election-only holdouts."""
    full = fit(rows)
    baseline = fit(rows, freshman=False)
    chronological = []
    for target_year in (2011, 2017, 2023):
        holdout = [row for row in rows if row['targetYear'] == target_year]
        training = [row for row in rows if row['targetYear'] < target_year] if target_year > 2011 else []
        fitted = fit(training) if training else None
        no_freshman = fit(training, freshman=False) if training else None
        chronological.append({
            'targetYear': target_year, 'trainingTargetYears': sorted({row['targetYear'] for row in training}),
            'trainingN': len(training), 'holdoutN': len(holdout),
            'holdoutFirstTermN': sum(row['treatment'] for row in holdout),
            'holdoutExperiencedN': sum(not row['treatment'] for row in holdout),
            'trainingFit': fitted, 'trainingNoFreshmanFit': no_freshman,
            'scores': {
                'fitted': score(holdout, [predict(row, fitted) for row in holdout]) if fitted else None,
                'noFreshman': score(holdout, [predict(row, no_freshman) for row in holdout]) if no_freshman else None,
                'prior': score(holdout, [row['xPP'] for row in holdout]),
                'zero': score(holdout, [0.0 for _ in holdout]),
            }})
    leave_one_out = []
    for year in (2011, 2017, 2023):
        subset = [row for row in rows if row['targetYear'] != year]
        leave_one_out.append({'omittedTargetYear': year, 'fit': fit(subset)})
    return {'n': len(rows), 'firstTermN': sum(row['treatment'] for row in rows),
            'experiencedN': sum(not row['treatment'] for row in rows),
            'fullSampleDescriptiveFit': full, 'fullSampleNoFreshmanFit': baseline,
            'changeContrast': change_contrast(rows), 'chronological': chronological,
            'leaveOneTransitionOutDescriptive': leave_one_out,
            'interpretation': 'Full-sample fits and omitted-transition diagnostics are retrospective; only chronological holdout scores assess earlier-election training.'}


def select(primary, sensitivities, target_confirmed_count, outcome_composition):
    """Apply frozen gates, returning null whenever support is insufficient."""
    trained = [row for row in primary['chronological'] if row['targetYear'] in (2017, 2023)]
    identified = all(row['trainingFit'] and row['holdoutFirstTermN'] and row['holdoutExperiencedN']
                     for row in trained)
    fitted_effects = [row['trainingFit']['freshmanEffectPP'] for row in trained if row['trainingFit']]
    full_effect = primary['fullSampleDescriptiveFit']['freshmanEffectPP'] if primary['fullSampleDescriptiveFit'] else None
    direction = bool(identified and full_effect is not None and all(
        effect * full_effect > 0 for effect in fitted_effects))
    non_worse = bool(identified and all(
        row['scores']['fitted'][metric] <= row['scores']['noFreshman'][metric]
        for row in trained for metric in ('maePP', 'rmsePP')))
    pooled_gain = (sum(row['holdoutN'] * (row['scores']['noFreshman']['maePP'] -
                                         row['scores']['fitted']['maePP']) for row in trained) /
                   sum(row['holdoutN'] for row in trained)) if identified else None
    material = pooled_gain is not None and pooled_gain >= 0.25
    sensitivity_direction = bool(full_effect is not None and all(
        item['fullSampleDescriptiveFit'] and
        item['fullSampleDescriptiveFit']['freshmanEffectPP'] * full_effect > 0
        for item in sensitivities))
    breadth = all(row['confirmedTargetLosers'] > 0 and row['targetWinners'] > 0
                  for row in outcome_composition if row['targetYear'] in (2017, 2023))
    gates = {'twoChronologicalHoldoutsIdentified': identified,
             'effectDirectionStable': direction, 'nonWorseHoldoutMAEAndRMSE': non_worse,
             'pooledMAEGainPP': pooled_gain, 'materialGainAtLeast025PP': material,
             'normalizationAndPriorListDirectionStable': sensitivity_direction,
             'adequateIdentityGeographyBreadth': breadth}
    selected = full_effect if all(value for key, value in gates.items()
                                  if key != 'pooledMAEGainPP') else None
    return {'schemaVersion': 1, 'selectedOperationalFreshmanEffectPP': selected,
            'gates': gates, 'targetConfirmedPairCountRetrospective': target_confirmed_count,
            'identityBreadthEvidence': 'Requires independently corroborated target losers as well as winners in each trained holdout. Confirmed-target restriction alone is winner-selected.',
            'reason': ('Criteria satisfied' if selected is not None else
                       'At least one frozen validation, sensitivity or coverage criterion failed; evidence supports descriptive diagnostics only.'),
            'prohibition': 'Do not add a freshman bonus to Stage 6/7/8 outputs or transport this estimate to changed boundaries.'}
