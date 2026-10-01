"""Evaluation-only actuals and frozen Stage 23 party-share diagnostics."""
import argparse
import math
from collections import defaultdict

from scripts.models.complete_party_vector.common import read_json, verify_contract, write_or_check
from scripts.models.party_vote_transform.inputs import Inputs
from scripts.transform.historical import key


def metrics(rows, weights=None):
    """Within-seat category average, then equal-seat or stated vote weights."""
    if not rows:
        return None
    ws = [1 if weights is None else weights[i] for i in range(len(rows))]
    total = sum(ws)
    if total <= 0:
        raise ValueError('Invalid evaluation weights')
    mae = sum(w * r['contestMaePP'] for w, r in zip(ws, rows)) / total
    mse = sum(w * r['contestMsePP2'] for w, r in zip(ws, rows)) / total
    return {'contests': len(rows), 'partyCells': sum(len(r['actualLocalShares']) for r in rows),
            'maePP': mae, 'rmsePP': math.sqrt(mse)}


def contest_errors(predicted, actual):
    if set(predicted) != set(actual) or not predicted:
        raise ValueError('Comparison is not on a complete common vector')
    errors = [predicted[c] - actual[c] for c in predicted]
    return 100 * sum(abs(e) for e in errors) / len(errors), 10000 * sum(e * e for e in errors) / len(errors)


def build_actuals(construction, elections):
    records = []
    frame = read_json('data/processed/models/complete-party-vector/input-inventory.json')['frame']
    labels = {(r['targetYear'], r['targetElectorateId']): r['targetSeatLabel'] for r in frame}
    if len(labels) != len(frame):
        raise ValueError('Duplicate target frame key')
    for r in construction['records']:
        target = elections[r['targetYear']]['scopes'][r['scope']][key(
            labels[r['targetYear'], r['targetElectorateId']])]
        actual = {cid: party['share'] for cid, party in target['parties'].items()}
        if r['applicability'] != 'constructed':
            records.append({**{k: r[k] for k in ('sourceYear', 'targetYear', 'scope', 'contestStatus', 'targetElectorateId')},
                            'applicability': r['applicability'], 'reason': r['reason'],
                            'targetObservedValidPartyVotes': target['validVotes'],
                            'actualLocalShares': actual})
            continue
        pred = r['localPartyShares']
        q = r['suppliedNationalScenario']
        model_mae, model_mse = contest_errors(pred, actual)
        flat_mae, flat_mse = contest_errors(q, actual)
        records.append({
            **{k: r[k] for k in ('sourceYear', 'targetYear', 'scope', 'contestStatus', 'targetElectorateId')},
            'applicability': 'constructed', 'reason': None,
            'targetObservedValidPartyVotes': target['validVotes'],
            'actualLocalShares': dict(sorted(actual.items())),
            'modelContestMaePP': model_mae, 'modelContestMsePP2': model_mse,
            'flatContestMaePP': flat_mae, 'flatContestMsePP2': flat_mse,
        })
    return {'schemaVersion': 1, 'stage': 23,
            'role': 'evaluation_only_target_local_party_actuals_and_oracle_denominators',
            'records': records}


def rows_for_method(actuals, method):
    return [{**r, 'contestMaePP': r[f'{method}ContestMaePP'],
             'contestMsePP2': r[f'{method}ContestMsePP2']}
            for r in actuals if r['applicability'] == 'constructed']


def national_gap(predictions, actuals, year):
    pairs = [(p, a) for p, a in zip(predictions, actuals) if p['targetYear'] == year]
    if any(p['applicability'] != 'constructed' for p, _ in pairs):
        return {'status': 'abstain_incomplete_population'}
    total = sum(a['targetObservedValidPartyVotes'] for _, a in pairs)
    ids = set(pairs[0][0]['localPartyShares'])
    aggregate = {cid: sum(a['targetObservedValidPartyVotes'] * p['localPartyShares'][cid]
                          for p, a in pairs) / total for cid in sorted(ids)}
    scenario = pairs[0][0]['suppliedNationalScenario']
    gaps = {cid: 100 * (aggregate[cid] - scenario[cid]) for cid in sorted(ids)}
    return {'status': 'diagnostic_oracle_target_valid_party_weights_no_reconciliation_imposed',
            'electorates': len(pairs), 'observedTargetValidPartyVotes': total,
            'maxAbsoluteCategoryGapPP': max(abs(v) for v in gaps.values()),
            'halfL1GapPP': sum(abs(v) for v in gaps.values()) / 2,
            'categoryGapsPP': gaps}


def category_breakdown(predictions, actuals, year, scope):
    sample = [(p, a) for p, a in zip(predictions, actuals)
              if p['targetYear'] == year and p['scope'] == scope and p['applicability'] == 'constructed']
    sums = defaultdict(list)
    classes = defaultdict(list)
    for p, a in sample:
        for cid, x in p['localPartyShares'].items():
            err = 100 * (x - a['actualLocalShares'][cid])
            sums[cid].append(err)
            status = p['sourceAffinityStatus'][cid]
            classes[status['relationship']].append(err)
            if status['sourceLocalStatus'] == 'observed_zero':
                classes['observed_source_zero'].append(err)
            if p['suppliedNationalScenario'][cid] < .01:
                classes['target_national_share_below_one_percent'].append(err)
            if cid in ('internetmana', 'freedomsnz'):
                classes['alliance_ballot_group'].append(err)
    describe = lambda es: {'cells': len(es), 'meanSignedBiasPP': sum(es) / len(es),
                            'maePP': sum(abs(e) for e in es) / len(es)}
    return {'byCategory': {cid: describe(es) for cid, es in sorted(sums.items())},
            'byPredeclaredClass': {name: describe(es) for name, es in sorted(classes.items())}}


def aligned_stage5(predictions, actuals):
    saved = read_json('data/processed/models/party-vote-transform/backtest-records.json')['records']
    current = {(p['targetYear'], p['targetElectorateId'], cid):
               (p['localPartyShares'][cid], p['suppliedNationalScenario'][cid], a['actualLocalShares'][cid])
               for p, a in zip(predictions, actuals) if p['scope'] == 'general' and p['applicability'] == 'constructed'
               for cid in p['localPartyShares']}
    by_year = defaultdict(list)
    for row in saved:
        if not row['primary'] or row['electorateType'] != 'general' or row['boundarySourceClass'] != 'observed':
            continue
        k = (row['targetYear'], row['electorateId'], row['canonicalPartyId'])
        if k not in current:
            continue
        model, flat, actual = current[k]
        if abs(actual - row['actualTargetShare']) > 1e-12:
            raise ValueError('Stage5 aligned actual differs')
        pred = {'stage23_complete_vector': model, 'flat_national': flat}
        for method in ('additive', 'proportional', 'log_odds'):
            bounds = row['predictions'][method]
            if abs(bounds['lower'] - bounds['upper']) > 1e-12:
                raise ValueError('Stage5 comparison is not an exact point')
            pred['stage5_' + method] = bounds['lower']
        by_year[row['targetYear']].append((actual, pred))
    return [{'targetYear': year, 'alignedCategoryCells': len(rows),
             'methodErrors': {method: {'maePP': 100 * sum(abs(pred[method] - actual) for actual, pred in rows) / len(rows),
                                      'rmsePP': 100 * math.sqrt(sum((pred[method] - actual) ** 2 for actual, pred in rows) / len(rows))}
                              for method in rows[0][1]}}
            for year, rows in sorted(by_year.items())]


def build_scores(construction, actuals):
    predictions = construction['records']
    observed = actuals['records']
    if len(predictions) != len(observed):
        raise ValueError('Construction/evaluation frame differs')
    reports = []
    for year in (2011, 2017, 2023):
        for scope in ('general', 'maori'):
            sample = [a for a in observed if a['targetYear'] == year and a['scope'] == scope]
            model = rows_for_method(sample, 'model')
            flat = rows_for_method(sample, 'flat')
            weights = [a['targetObservedValidPartyVotes'] for a in sample if a['applicability'] == 'constructed']
            reports.append({'targetYear': year, 'scope': scope, 'frameContests': len(sample),
                            'constructedContests': len(model),
                            'abstentions': [{'targetElectorateId': a['targetElectorateId'], 'reason': a['reason']}
                                            for a in sample if a['applicability'] != 'constructed'],
                            'model': metrics(model), 'flatNational': metrics(flat),
                            'modelTargetValidPartyWeightedOracle': metrics(model, weights),
                            'flatTargetValidPartyWeightedOracle': metrics(flat, weights),
                            'categoryDiagnostics': category_breakdown(predictions, observed, year, scope)})
    restricted = [a for a in observed if a['scope'] == 'general' and a['contestStatus'] == 'held_both']
    pooled = []
    for scope in ('general', 'maori'):
        subset = [a for a in observed if a['scope'] == scope]
        pooled.append({'scope': scope, 'frameContests': len(subset),
                       'constructedContests': sum(a['applicability'] == 'constructed' for a in subset),
                       'model': metrics(rows_for_method(subset, 'model')),
                       'flatNational': metrics(rows_for_method(subset, 'flat'))})
    residuals = [abs(sum(p['localPartyShares'].values()) - 1)
                 for p in predictions if p['applicability'] == 'constructed']
    gates = []
    for year in (2017, 2023):
        report = next(r for r in reports if r['targetYear'] == year and r['scope'] == 'general')
        gates.append({'targetYear': year,
                      'maeGainPP': report['flatNational']['maePP'] - report['model']['maePP'],
                      'rmseRegressionPP': report['model']['rmsePP'] - report['flatNational']['rmsePP']})
    gate = all(x['maeGainPP'] >= .25 and x['rmseRegressionPP'] < .25 for x in gates)
    gate &= sum(a['applicability'] == 'constructed' for a in restricted) / len(restricted) >= .95
    return {'schemaVersion': 1, 'stage': 23,
            'role': 'conditional_development_party_share_diagnostics_no_operational_selection',
            'reports': reports, 'heldGeneralCandidateFrame': {
                'contests': len(restricted),
                'constructed': sum(a['applicability'] == 'constructed' for a in restricted),
                'model': metrics(rows_for_method(restricted, 'model')),
                'flatNational': metrics(rows_for_method(restricted, 'flat'))},
            'pooledByScope': pooled,
            'maxLocalSimplexResidual': max(residuals) if residuals else None,
            'fullPopulationNationalGaps': [national_gap(predictions, observed, y) for y in (2011, 2017, 2023)],
            'alignedStage5SelectedCategoryComparison': aligned_stage5(predictions, observed),
            'developmentMateriality': {'folds': gates, 'screenPass': bool(gate),
                                       'interpretation': 'descriptive only; no operational selection'},
            'selectedOperationalPartyInput': None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    verify_contract()
    construction = read_json('data/processed/models/complete-party-vector/construction.json')
    elections = Inputs().elections()
    actuals = build_actuals(construction, elections)
    scores = build_scores(construction, actuals)
    write_or_check('evaluation-actuals.json', actuals, args.check)
    write_or_check('scores.json', scores, args.check)
    print('Stage23 evaluated:', len(actuals['records']))


if __name__ == '__main__':
    main()
