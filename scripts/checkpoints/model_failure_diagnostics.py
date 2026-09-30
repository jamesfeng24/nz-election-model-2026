"""Explore paired failures of already frozen predictions; never refit a model."""

from collections import Counter, defaultdict
from math import sqrt
from statistics import mean, median

from scripts.checkpoints.model_failure_inventory import PATHS, read


def unique(rows, key):
    indexed = {row[key]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f'Duplicate diagnostic join key: {key}')
    return indexed


def paired_row(identifier, actual, model, control, **fields):
    if any(value is None for value in (actual, model, control)):
        raise ValueError('Missing paired point')
    model_error = 100 * (model - actual)
    control_error = 100 * (control - actual)
    return {'id': identifier, 'actualShare': actual, 'modelShare': model,
            'controlShare': control, 'modelErrorPP': model_error,
            'controlErrorPP': control_error,
            'deltaAbsolutePP': abs(model_error) - abs(control_error),
            'deltaSquaredPP2': model_error ** 2 - control_error ** 2,
            **fields}


def stage18_rows(inventory, construction, actuals):
    actual_index = unique(actuals['records'], 'targetElectorateId')
    groups = {(row['targetYear'], row['comparison']): row
              for row in inventory['comparisons']['stage18']['groups']}
    output = []
    for holdout in construction['holdouts']:
        year = holdout['targetYear']
        for comparison, control_method in (
                ('fitted_floor_vs_uniform', 'uniform'),
                ('fitted_floor_vs_restricted_zero_floor', 'restricted_zero_floor')):
            expected = groups[(year, comparison)]
            rows = [row for row in holdout['records'] if row['status'] == 'constructed'
                    and (control_method != 'restricted_zero_floor' or
                         row['methods'][control_method] is not None)]
            if [row['targetElectorateId'] for row in rows] != expected['contestIds']:
                raise ValueError('Changed Stage18 paired contest sample')
            ids = []
            for row in rows:
                actual = actual_index[row['targetElectorateId']]['candidateShares']
                model = row['methods']['fitted_floor']['shares']
                control = row['methods'][control_method]['shares']
                candidates = row['candidates']
                if set(actual) != set(model) or set(actual) != set(control):
                    raise ValueError('Stage18 candidate denominator or ID mismatch')
                if any(abs(sum(vector.values()) - 1) > 1e-9
                       for vector in (actual, model, control)):
                    raise ValueError('Stage18 complete candidate-share mass mismatch')
                for candidate in candidates:
                    cid = candidate['candidateOccurrenceId']
                    ids.append(cid)
                    output.append(paired_row(
                        cid, actual[cid], model[cid], control[cid],
                        component='stage18', comparison=comparison, targetYear=year,
                        partyKey=candidate['sourcePartyKey'],
                        mappingStatus=candidate['mappingStatus'],
                        slateSize=len(candidates), contestId=row['targetElectorateId'],
                        informationSet='observed_target_local_party',
                        denominator='valid_candidate_votes'))
            if ids != expected['candidateOccurrenceIds']:
                raise ValueError('Changed Stage18 paired candidate sample')
    return output


def stage16_rows(inventory, analysis, inputs):
    covariates = unique(inputs['records'], 'id')
    output = []
    for group in inventory['comparisons']['stage16']['groups']:
        indexed = {row['model']: row for row in analysis['folds']
                   if row['party'] == group['party'] and row['targetYear'] == group['targetYear']
                   and row['mode'] == group['mode']}
        for comparison, model_key, control_key in (
                ('source_victory_vs_common_intercept', 'source_victory', 'common_intercept'),
                ('source_victory_beta1_vs_common_intercept_beta1',
                 'source_victory_beta1', 'common_intercept_beta1')):
            model = unique(indexed[model_key]['predictions'], 'id')
            control = unique(indexed[control_key]['predictions'], 'id')
            if list(model) != group['recordIds'] or list(control) != group['recordIds']:
                raise ValueError('Changed Stage16 paired sample')
            for identifier in group['recordIds']:
                source = covariates[identifier]
                if source['party'] != group['party'] or source['targetYear'] != group['targetYear']:
                    raise ValueError('Stage16 covariate join mismatch')
                output.append(paired_row(
                    identifier, source['c1'], model[identifier]['point'],
                    control[identifier]['point'], component='stage16',
                    comparison=comparison, targetYear=group['targetYear'],
                    partyKey=group['party'], mode=group['mode'],
                    contestId=source['electorateId'], sourceCandidateShare=source['c0'],
                    sourcePartyShare=source['p0'],
                    sourceCandidatePartyGap=source['c0'] - source['p0'],
                    observedPartyMovement=source['x'], sourceWon=bool(source['sourceWon']),
                    informationSet=('observed_target_local_party' if group['mode'] ==
                                    'actual_observed_local_party' else
                                    'stage5_conditional_on_observed_target_national_support'),
                    denominator='valid_candidate_votes'))
    return output


def stage6_rows(inventory, backtests, records):
    covariates = unique(records['records'], 'id')
    output = []
    for group in inventory['comparisons']['stage6']['groups']:
        indexed = {row['model']: row for row in backtests['records']
                   if row['party'] == group['party']
                   and row['holdoutSourceYear'] == group['sourceYear']
                   and row['mode'] == 'chronological'
                   and row['baseline'] == 'actual_observed_local_party'}
        model = unique(indexed['fitted']['predictions'], 'recordId')
        control = unique(indexed['one_for_one']['predictions'], 'recordId')
        if list(model) != group['recordIds'] or list(control) != group['recordIds']:
            raise ValueError('Changed Stage6 paired sample')
        for identifier in group['recordIds']:
            source = covariates[identifier]
            if abs(model[identifier]['actual'] - source['targetCandidateShare']) > 1e-12:
                raise ValueError('Stage6 actual/record mismatch')
            output.append(paired_row(
                identifier, source['targetCandidateShare'], model[identifier]['prediction'],
                control[identifier]['prediction'], component='stage6',
                comparison='zero_intercept_fitted_vs_one_for_one',
                targetYear=group['targetYear'], partyKey=group['party'],
                contestId=source['electorateId'],
                sourceCandidateShare=source['sourceCandidateShare'],
                sourcePartyShare=source['sourcePartyShare'],
                sourceCandidatePartyGap=(source['sourceCandidateShare'] -
                                         source['sourcePartyShare']),
                observedPartyMovement=source['deltaParty'],
                informationSet='observed_target_local_party',
                denominator='valid_candidate_votes'))
    return output


def metrics(rows):
    if not rows:
        return None
    by_contest = defaultdict(list)
    for row in rows:
        by_contest[row['contestId']].append(row)
    contest_values = list(by_contest.values())
    return {'n': len(rows),
            'contests': len(contest_values),
            'meanDeltaAbsolutePP': mean(row['deltaAbsolutePP'] for row in rows),
            'medianDeltaAbsolutePP': median(row['deltaAbsolutePP'] for row in rows),
            'meanDeltaSquaredPP2': mean(row['deltaSquaredPP2'] for row in rows),
            'modelMaePP': mean(abs(row['modelErrorPP']) for row in rows),
            'controlMaePP': mean(abs(row['controlErrorPP']) for row in rows),
            'modelRmsePP': sqrt(mean(row['modelErrorPP'] ** 2 for row in rows)),
            'controlRmsePP': sqrt(mean(row['controlErrorPP'] ** 2 for row in rows)),
            'contestEqualMeanDeltaAbsolutePP': mean(mean(r['deltaAbsolutePP'] for r in seat)
                                                    for seat in contest_values),
            'contestEqualModelMaePP': mean(mean(abs(r['modelErrorPP']) for r in seat)
                                             for seat in contest_values),
            'contestEqualControlMaePP': mean(mean(abs(r['controlErrorPP']) for r in seat)
                                               for seat in contest_values),
            'contestEqualModelRmsePP': sqrt(mean(mean(r['modelErrorPP'] ** 2 for r in seat)
                                                   for seat in contest_values)),
            'contestEqualControlRmsePP': sqrt(mean(mean(r['controlErrorPP'] ** 2 for r in seat)
                                                     for seat in contest_values)),
            'improved': sum(row['deltaAbsolutePP'] < -1e-10 for row in rows),
            'worse': sum(row['deltaAbsolutePP'] > 1e-10 for row in rows),
            'tied': sum(abs(row['deltaAbsolutePP']) <= 1e-10 for row in rows)}


def bin_label(value, edges):
    if value is None:
        return 'unknown'
    if value < edges[0]:
        return f'below_{edges[0]:g}'
    if value > edges[-1]:
        return f'above_{edges[-1]:g}'
    for left, right in zip(edges, edges[1:]):
        if left <= value < right or (right == edges[-1] and value == right):
            return f'[{left:g},{right:g}{"]" if right == edges[-1] else ")"}'
    raise ValueError('Unclassified binned value')


def _strata_fields(row):
    if row['component'] == 'stage18':
        n = row['slateSize']
        return {'partyKey': row['partyKey'],
                'mappingStatus': row['mappingStatus'],
                'slateSize': '2-5' if n <= 5 else '6-8' if n <= 8 else '9+',
                'controlPredictedShare': bin_label(row['controlShare'],
                                                  (0, .02, .05, .10, .25, .50, 1))}
    result = {'partyKey': row['partyKey'],
              'sourceCandidateShare': bin_label(row['sourceCandidateShare'],
                                                (0, .10, .25, .40, .60, 1)),
              'sourcePartyShare': bin_label(row['sourcePartyShare'],
                                            (0, .10, .25, .40, .60, 1)),
              'sourceCandidatePartyGap': bin_label(row['sourceCandidatePartyGap'],
                                                   (-1, -.10, -.03, .03, .10, 1)),
              'observedPartyMovement': bin_label(row['observedPartyMovement'],
                                                 (-1, -.10, -.03, .03, .10, 1)),
              'controlPredictedShare': bin_label(row['controlShare'],
                                                (-1, .10, .25, .40, .60, 1))}
    if 'sourceWon' in row:
        result['sourcePartySeatVictory'] = 'yes' if row['sourceWon'] else 'no'
    return result


def summarize(rows):
    summaries = []
    group_keys = sorted({(r['component'], r['comparison'], r.get('mode'),
                          r['targetYear'], r.get('partyKey') if r['component'] != 'stage18' else None)
                         for r in rows})
    for component, comparison, mode, year, party in group_keys:
        subset = [r for r in rows if (r['component'], r['comparison'], r.get('mode'),
                                     r['targetYear'], r.get('partyKey') if r['component'] != 'stage18'
                                     else None) == (component, comparison, mode, year, party)]
        strata = defaultdict(list)
        for row in subset:
            for field, value in _strata_fields(row).items():
                strata[(field, value)].append(row)
        min_n = 20 if component == 'stage18' else 10
        strata_summary = []
        for (field, value), members in sorted(strata.items()):
            supported = len(members) >= min_n and (
                component != 'stage18' or len({m['contestId'] for m in members}) >= 5)
            strata_summary.append({'field': field, 'value': value,
                                   'n': len(members),
                                   'contests': len({m['contestId'] for m in members}),
                                   'tooSparse': not supported,
                                   'pairedMetrics': metrics(members) if supported else None})
        top = sorted(subset, key=lambda r: (-abs(r['deltaAbsolutePP']), r['id']))[:5]
        summaries.append({'component': component, 'comparison': comparison, 'mode': mode,
                          'targetYear': year, 'partyKey': party,
                          'pairedMetrics': metrics(subset),
                          'strata': strata_summary,
                          'largestAbsolutePairedChanges': [
                              {'id': r['id'], 'contestId': r['contestId'],
                               'deltaAbsolutePP': r['deltaAbsolutePP'],
                               'modelErrorPP': r['modelErrorPP'],
                               'controlErrorPP': r['controlErrorPP']} for r in top]})
    return summaries


def build(inventory):
    input_hashes = {name: item['sha256'] for name, item in inventory['inputs'].items()}
    from scripts.checkpoints.model_failure_inventory import digest
    if any(digest(PATHS[name]) != expected for name, expected in input_hashes.items()):
        raise ValueError('Changed frozen model artifact after diagnostic inventory')
    rows = []
    rows.extend(stage18_rows(inventory, read(PATHS['stage18Construction']),
                             read(PATHS['stage18Actuals'])))
    rows.extend(stage16_rows(inventory, read(PATHS['stage16Analysis']),
                             read(PATHS['stage16Inputs'])))
    rows.extend(stage6_rows(inventory, read(PATHS['stage6Backtests']),
                            read(PATHS['stage6Records'])))
    summaries = summarize(rows)
    return {'schemaVersion': 1, 'stage': 19,
            'role': 'exploratory_paired_diagnostics_on_frozen_predictions_no_new_fit',
            'rows': rows, 'summary': summaries,
            'coverage': {'pairedRowsByComponent': dict(sorted(Counter(
                r['component'] for r in rows).items())),
                         'aggregateOnlyOrIncompatible': {
                             'stage8': len(inventory['comparisons']['stage8']['validationPairIds']),
                             'stage9': len(inventory['comparisons']['stage9']['correctedPairIds']),
                             'stage10': len(inventory['comparisons']['stage10']['chronologicalHoldoutEventIds']),
                             'stage11MatchedOnly': len(inventory['comparisons']['stage11']['candidateOccurrenceIds']),
                             'stage15PointPredictions': 0}}}
