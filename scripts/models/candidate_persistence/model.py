"""Chronological candidate-residual persistence diagnostics."""

from math import sqrt


TARGET_YEARS = (2011, 2017, 2023)


def fit(rows, intercept=True):
    """Fit target = alpha + beta * prior, without using a future row."""
    if len(rows) < 2:
        return None
    x = [row['x'] for row in rows]
    y = [row['y'] for row in rows]
    if intercept:
        mean_x, mean_y = sum(x) / len(x), sum(y) / len(y)
        denominator = sum((value - mean_x) ** 2 for value in x)
        if denominator <= 0:
            return None
        beta = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y)) / denominator
        alpha = mean_y - beta * mean_x
    else:
        denominator = sum(value * value for value in x)
        if denominator <= 0:
            return None
        beta = sum(a * b for a, b in zip(x, y)) / denominator
        alpha = 0.0
    residuals = [b - alpha - beta * a for a, b in zip(x, y)]
    return {'n': len(rows), 'intercept': alpha, 'slope': beta,
            'inSampleRMSEPP': 100 * sqrt(sum(value * value for value in residuals) / len(rows))}


def score(rows, predictions):
    if len(rows) != len(predictions) or not rows:
        raise ValueError('Nonempty aligned score inputs required')
    errors = [100 * (prediction - row['y']) for row, prediction in zip(rows, predictions)]
    return {'n': len(rows), 'maePP': sum(abs(value) for value in errors) / len(errors),
            'rmsePP': sqrt(sum(value * value for value in errors) / len(errors)),
            'biasPP': sum(errors) / len(errors)}


def _observations(pairs, scope, scale, include_probable):
    observations = []
    for pair in pairs:
        if pair['electorateType'] != scope:
            continue
        if not (pair['probableSensitivityEligible'] if include_probable else pair['primaryEligible']):
            continue
        if scale == 'additive':
            x, y = pair['priorResidual'], pair['targetResidual']
        else:
            values = pair['scaleResiduals'][scale]
            x, y = values['prior'], values['target']
        if x is None or y is None:
            continue
        observations.append({'pairId': pair['pairId'], 'year': pair['targetYear'],
                             'x': x, 'y': y, 'partyUnchanged': pair['sourcePartyKey'] == pair['targetPartyKey']})
    return observations


def analyze(pairs, scope='general', scale='additive', include_probable=False):
    """Separate full-sample descriptions from expanding chronological folds."""
    observations = _observations(pairs, scope, scale, include_probable)
    descriptive = fit(observations)
    zero_intercept = fit(observations, intercept=False)
    by_transition = []
    for year in TARGET_YEARS:
        target = [row for row in observations if row['year'] == year]
        training = [row for row in observations if row['year'] < year]
        fitted = fit(training)
        result = {'targetYear': year, 'targetCount': len(target), 'trainingCount': len(training),
                  'trainingTargetYears': sorted({row['year'] for row in training}),
                  'trainingFit': fitted, 'scores': None}
        if target:
            scores = {'zero': score(target, [0.0] * len(target)),
                      'prior': score(target, [row['x'] for row in target])}
            if fitted:
                scores['fitted'] = score(target, [fitted['intercept'] + fitted['slope'] * row['x']
                                                 for row in target])
            result['scores'] = scores
        by_transition.append(result)
    trained = [row for row in by_transition if row['scores'] and 'fitted' in row['scores']]
    macro = {}
    for name in ('zero', 'prior', 'fitted'):
        if trained:
            macro[name] = {metric: sum(row['scores'][name][metric] for row in trained) / len(trained)
                           for metric in ('maePP', 'rmsePP', 'biasPP')}
    return {
        'scope': scope, 'scale': scale, 'identitySet': 'confirmed_plus_probable' if include_probable else 'confirmed',
        'n': len(observations), 'samePartyCount': sum(row['partyUnchanged'] for row in observations),
        'descriptiveFullSampleFit': descriptive, 'zeroInterceptSensitivityFit': zero_intercept,
        'individualTransitionFits': [{'targetYear': year, 'fit': fit([row for row in observations if row['year'] == year])}
                                     for year in TARGET_YEARS],
        'chronological': by_transition, 'equalTransitionMacroTrained': macro,
        'interpretation': 'Retrospective prediction conditional on known target candidacy and corroborated identity; target residuals are evaluation outcomes only. Same-seat conditions and returnee selection remain confounded with person persistence.'
    }


def select(primary, sensitivity, identity_coverage):
    """Apply the frozen practical gate; never deploy an MP-only fit."""
    trained = [row for row in primary['chronological'] if row['scores'] and 'fitted' in row['scores']]
    gains = []
    for row in trained:
        scores = row['scores']
        better_mae = min(scores['zero']['maePP'], scores['prior']['maePP'])
        better_rmse = min(scores['zero']['rmsePP'], scores['prior']['rmsePP'])
        gains.append({'targetYear': row['targetYear'],
                      'gainVsBetterBenchmarkMAEPP': better_mae - scores['fitted']['maePP'],
                      'gainVsBetterBenchmarkRMSEPP': better_rmse - scores['fitted']['rmsePP']})
    performance_pass = len(gains) == 2 and all(g['gainVsBetterBenchmarkMAEPP'] >= 0.25 and
                                                 g['gainVsBetterBenchmarkRMSEPP'] >= 0 for g in gains)
    primary_fit = primary['descriptiveFullSampleFit']
    scale_pass = primary_fit is not None and all(
        result['n'] > 0 and result['descriptiveFullSampleFit'] is not None and
        result['descriptiveFullSampleFit']['slope'] * primary_fit['slope'] >= 0
        for result in sensitivity)
    coverage_pass = False  # Parliamentary corroboration requires a winner; challengers remain unverified.
    return {'schemaVersion': 1, 'selectedOperationalCoefficient': None,
            'status': 'unresolved_insufficient_predictive_and_identity_evidence',
            'holdoutGains': gains, 'performanceGatePassed': performance_pass,
            'scaleDirectionGatePassed': scale_pass, 'identityBreadthGatePassed': coverage_pass,
            'confirmedOccurrenceCount': identity_coverage['confirmedCount'],
            'reason': 'Confirmed links are Parliament-selected and do not cover the wider returning-challenger population; a universal persistence coefficient is not supported even if a fitted holdout diagnostic improves. No Stage6 bonus is created.'}
