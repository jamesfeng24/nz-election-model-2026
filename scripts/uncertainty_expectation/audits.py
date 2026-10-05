"""Bounded saved-evidence widths, heterogeneity and dependence diagnostics."""
from copy import deepcopy
from fractions import Fraction
import numpy as np
from scipy.stats import spearmanr
from scripts.uncertainty_revision.coordinates import coordinates
from scripts.uncertainty_revision.construction import arrays as original_arrays
from scripts.uncertainty_tails.metrics import interval
from .common import INVENTORY, read, save, verify, arguments

LEVELS = (50, 80, 90)
GEOGRAPHY = 'data/processed/checkpoints/stage25-historical-geography/geography.json'
FLOW = 'data/processed/forecast-transport/party-construction.json'


def association(x, y, weights=None):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 2 or x.shape != y.shape or not np.isfinite(x).all() or not np.isfinite(y).all():
        return {'status': 'unavailable', 'reason': 'fewer than two finite paired records'}
    w = np.ones(len(x)) if weights is None else np.asarray(weights, float)
    if w.shape != x.shape or not np.isfinite(w).all() or np.any(w <= 0):
        raise ValueError('Invalid association weights')
    w = w / w.sum()
    a, b = x - np.sum(w*x), y - np.sum(w*y)
    variance = float(np.sum(w*a*a)*np.sum(w*b*b))
    if variance <= 1e-30:
        return {'status': 'unavailable', 'reason': 'absent predictor or response variation', 'records': len(x)}
    return {'status': 'descriptive', 'records': len(x),
            'pearson': float(np.sum(w*a*b)/np.sqrt(variance)),
            'spearman': float(spearmanr(x, y).statistic),
            'spearmanWeighting': 'equal paired records; Pearson alone uses supplied weights',
            'significanceTests': None}


def width_distribution(values):
    x = np.asarray(values, float)
    if not len(x):
        return {'status': 'unavailable'}
    return {'minimumPP': float(x.min()), 'maximumPP': float(x.max()),
            'quantilesPP': dict(zip(('10', '25', '50', '75', '90'), np.quantile(x, [.1, .25, .5, .75, .9]).tolist()))}


def original_cases():
    """Only the absent 80% summary is calculated; all original banks stay intact."""
    construction = read('data/processed/uncertainty-revision/construction.json')
    saved = {c['id']: c for c in read('data/processed/uncertainty-revision/evaluation.json')['cases']}
    cases = []
    for case in construction['cases']:
        if case['layer'] not in ('candidate', 'composed'):
            continue
        records = deepcopy(saved[case['id']]['methods']['revised']['records'])
        with original_arrays(case) as bank:
            for row in records:
                q = bank['revised:' + row['id']]
                row['interval80'] = interval(100*q, 100*np.array(row['actual']), .8)
                pair = row['ranking']['predictionTimePair']
                a, b = [row['ids'].index(i) for i in pair['ids']]
                pair['interval80'] = interval(100*(q[:, a]-q[:, b]), pair['actualSignedMarginPP'], .8)
        cases.append({'id': case['id'], 'year': case['year'], 'layer': case['layer'], 'records': records})
    return cases


def control_cases():
    return [{'id': c['id'], 'year': c['year'], 'layer': c['layer'],
             'records': c['methods']['stage45']['records']}
            for c in read('data/processed/uncertainty-tails/evaluation.json')['cases']
            if c['layer'] in ('candidate', 'composed')]


def selected_values(row, group):
    if group == 'forecast_pair':
        p = row['ranking']['predictionTimePair']
        return [{'option': '|'.join(p['ids']), 'crpsPP': p['crpsPP'],
                 'intervals': {str(level): {key: p['interval'+str(level)][key][0]
                                for key in ('covered', 'widths', 'scores')} for level in LEVELS}}]
    indices = [i for i, g in enumerate(row['groups']) if g == group or group == 'other' and g not in ('national', 'labour')]
    return [{'option': row['ids'][i], 'crpsPP': row['crpsPP'][i],
             'intervals': {str(level): {key: row['interval'+str(level)][key][i]
                            for key in ('covered', 'widths', 'scores')} for level in LEVELS}}
            for i in indices]


def width_summary(rows, group, equal_election=False):
    selected = [(r, selected_values(r, group)) for r in rows]
    selected = [(r, v) for r, v in selected if v]
    if not selected:
        return {'status': 'unavailable', 'reason': 'no standing options in group'}
    years = sorted({r['year'] for r, _ in selected})
    weights = np.ones(len(selected))
    if equal_election:
        for year in years:
            ix = [i for i, (r, _) in enumerate(selected) if r['year'] == year]
            weights[ix] = 1 / len(ix)
    weights /= weights.sum()
    all_values = [v for _, values in selected for v in values]
    result = {'contests': len(selected), 'coordinates': len(all_values), 'environments': len(years),
              'weighting': 'equal election, equal contests, equal selected options within contest' if equal_election else 'equal contests, equal selected options within contest',
              'crpsPP': float(np.sum(weights*[np.mean([v['crpsPP'] for v in values]) for _, values in selected])),
              'candidateEqualCRPSPP': float(np.mean([v['crpsPP'] for v in all_values])), 'intervals': {}}
    for level in LEVELS:
        key = str(level)
        flat = [v['intervals'][key] for v in all_values]
        seat_widths = [np.mean([v['intervals'][key]['widths'] for v in values]) for _, values in selected]
        result['intervals'][key] = {
            'covered': sum(v['covered'] for v in flat), 'total': len(flat),
            'coverage': float(np.mean([v['covered'] for v in flat])),
            'weightedCoverage': float(np.sum(weights*[np.mean([v['intervals'][key]['covered'] for v in values]) for _, values in selected])),
            'widthPP': float(np.sum(weights*seat_widths)),
            'intervalScorePP': float(np.sum(weights*[np.mean([v['intervals'][key]['scores'] for v in values]) for _, values in selected])),
            'optionWidthDistribution': width_distribution([v['widths'] for v in flat]),
            'seatMeanWidthDistribution': width_distribution(seat_widths)}
    return result


def audit_source(cases):
    groups = ('national', 'labour', 'other', 'forecast_pair')
    by_fold = [{**c, 'summaries': {g: width_summary(c['records'], g) for g in groups}} for c in cases]
    return {'cases': by_fold, 'pooled': {layer: {
        weighting: {g: width_summary([r for c in cases if c['layer'] == layer for r in c['records']], g, weighting == 'equalElection') for g in groups}
        for weighting in ('contestWeighted', 'equalElection')} for layer in ('candidate', 'composed')}}


def original_audit():
    return {'stage': 47, 'status': 'saved historical evidence only; no new distribution scored',
            'sources': {'originalStage45_8000': audit_source(original_cases()),
                        'unchangedGaussianStage46_32768': audit_source(control_cases())},
            'comparisonLimit': 'Same statistical law, different integration/sampler banks. Original50/90/CRPS are preserved; original80 derived from exact cached draws. Numerical repair must be compared on common streams separately.'}


def fragmentation(row, geography, flows):
    g = geography[row['targetElectorateId']]
    if g['certifiedTwoSidedExact']:
        return {'value': 0., 'status': 'exact_identity', 'incomingPopulationFractions': [1.]}
    transition = f"{row['sourceYear']}-{row['targetYear']}"
    scenario = flows['transitions'].get(transition, {}).get('scopes', {}).get('general')
    if scenario is None:
        return {'value': None, 'status': 'unavailable_missing_frozen_population_scenario'}
    target = str(int(row['targetElectorateId'].split('-')[-1])).zfill(3)
    total = scenario['targetPopulationControls'].get(target)
    if total is None or total <= 0:
        return {'value': None, 'status': 'unavailable_missing_target_control'}
    fractions = [Fraction(e['population'], total) for e in scenario['aggregatedEdges'] if e['targetCode'] == target]
    if sum(fractions) != 1:
        raise ValueError('Target-incoming feasible population does not conserve')
    return {'value': float(1-sum(p*p for p in fractions)), 'status': 'single_frozen_feasible_point',
            'incomingPopulationFractions': [float(p) for p in fractions],
            'pointAssumption': 'lexicographic feasible population vertex, not observed votes or a distribution'}


def characteristics(row, geography, flows):
    majors = [[f for f, g in zip(row['features'], row['groups']) if g == group] for group in ('national', 'labour')]
    r = float(np.mean([xs[0]['supportedMass']['R'] for xs in majors])) if all(len(xs) == 1 for xs in majors) else None
    return {'supportedR': r, 'RStatus': 'undefined_missing_or_nonunique_major' if r is None else 'unsupported' if r == 0 else 'full' if r == 1 else 'partial',
            'populationFragmentation': fragmentation(row, geography, flows), 'canonicalTier': row['geography']}


def raw_residual(row, coordinate):
    observed, predicted = coordinates(row['actual'], row['groups']), coordinates(row['mean'], row['groups'])
    return None if observed[coordinate] is None or predicted[coordinate] is None else float(observed[coordinate]-predicted[coordinate])


def descriptive_group(rows, coordinate):
    values = [r[coordinate+'SeatResidual'] for r in rows if r[coordinate+'SeatResidual'] is not None]
    if not values:
        return {'status': 'unavailable', 'records': len(rows)}
    x = np.array(values)
    return {'records': len(x), 'elections': sorted({r['year'] for r in rows}),
            'rms': float(np.sqrt(np.mean(x*x))), 'mad': float(np.median(np.abs(x-np.median(x)))),
            'coverage': {str(level): {'covered': sum(r['majorCoverage'][str(level)]['covered'] for r in rows),
                                    'total': sum(r['majorCoverage'][str(level)]['total'] for r in rows)} for level in LEVELS}}


def heterogeneity(inventory=None):
    inventory = read(INVENTORY) if inventory is None else inventory
    geography = {r['targetElectorateId']: r for r in read(GEOGRAPHY)['records']}
    flows = read(FLOW)
    score = {r['id']: r for c in control_cases() if c['layer'] == 'candidate' for r in c['records']}
    rows = []
    for row in inventory['candidateRecords']:
        value = characteristics(row, geography, flows)
        major = [i for i, g in enumerate(row['groups']) if g in ('national', 'labour')]
        old = score[row['targetElectorateId']]
        rows.append({'id': row['targetElectorateId'], 'year': row['targetYear'], 'name': row['name'], **value,
                     'balanceRawResidual': raw_residual(row, 'balance'), 'massRawResidual': raw_residual(row, 'mass'),
                     'majorCoverage': {str(level): {'covered': sum(old['interval'+str(level)]['covered'][i] for i in major), 'total': len(major),
                        'widthPP': float(np.mean([old['interval'+str(level)]['widths'][i] for i in major])) if major else None} for level in LEVELS}})
    by_election = {}
    for year in sorted({r['year'] for r in rows}):
        selected = [r for r in rows if r['year'] == year]
        for coordinate in ('balance', 'mass'):
            finite = [r[coordinate+'RawResidual'] for r in selected if r[coordinate+'RawResidual'] is not None]
            center = float(np.mean(finite)) if finite else None
            for row in selected:
                raw = row[coordinate+'RawResidual']
                row[coordinate+'SeatResidual'] = None if raw is None else raw-center
        associations = {}
        for characteristic in ('supportedR', 'populationFragmentation'):
            eligible = [r for r in selected if (r[characteristic]['value'] if characteristic == 'populationFragmentation' else r[characteristic]) is not None]
            x = [r[characteristic]['value'] if characteristic == 'populationFragmentation' else r[characteristic] for r in eligible]
            associations[characteristic] = {}
            for coordinate in ('balance', 'mass'):
                valid = [(a, r) for a, r in zip(x, eligible) if r[coordinate+'SeatResidual'] is not None]
                associations[characteristic][coordinate] = association([a for a, _ in valid], [r[coordinate+'SeatResidual']**2 for _, r in valid])
            valid = [(a, r) for a, r in zip(x, eligible) if r['majorCoverage']['50']['total'] > 0]
            associations[characteristic]['coverage'] = {str(level): association([a for a, _ in valid], [r['majorCoverage'][str(level)]['covered']/r['majorCoverage'][str(level)]['total'] for _, r in valid]) for level in LEVELS}
        by_election[str(year)] = {'records': len(selected), 'continuousAssociationsWithSquaredSeatResidual': associations,
            'RLabels': {label: {coordinate: descriptive_group([r for r in selected if r['RStatus'] == label], coordinate) for coordinate in ('balance', 'mass')}
                        for label in ('unsupported', 'partial', 'full', 'undefined_missing_or_nonunique_major')},
            'canonicalGeographyTiers': {tier: {coordinate: descriptive_group([r for r in selected if r['canonicalTier'] == tier], coordinate) for coordinate in ('balance', 'mass')}
                for tier in sorted({r['canonicalTier'] for r in selected})}}
    return {'stage': 47, 'records': rows, 'byElection': by_election,
            'noNewVariancePredictorFit': True, 'pooledComposition': {label: {str(y): sum(r['RStatus'] == label and r['year'] == y for r in rows) for y in (2014, 2017, 2020, 2023)} for label in ('unsupported', 'partial', 'full')},
            'interpretation': 'Within-election descriptive squared residual associations; centres use observed election means only for diagnosis, never prediction. Coverage is unchangedGaussianStage46 control. Geography largely varies in redistribution elections; pooled bins confound election composition.'}


def dependence(inventory=None):
    inventory = read(INVENTORY) if inventory is None else inventory
    party = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    candidate = {r['targetElectorateId']: r for r in inventory['candidateRecords']}
    matched = []
    for cid, row in candidate.items():
        p = party.get(cid)
        if p is None:
            continue
        matched.append({'id': cid, 'year': row['targetYear'], 'local': {c: raw_residual(p, c) for c in ('balance', 'mass')},
                        'candidate': {c: raw_residual(row, c) for c in ('balance', 'mass')}})
    associations = {}
    for coordinate in ('balance', 'mass'):
        rows = [r for r in matched if r['local'][coordinate] is not None and r['candidate'][coordinate] is not None]
        per_year, centered, means = {}, [], []
        for year in sorted({r['year'] for r in rows}):
            subset = [r for r in rows if r['year'] == year]
            x = np.array([r['local'][coordinate] for r in subset]); y = np.array([r['candidate'][coordinate] for r in subset])
            per_year[str(year)] = {'records': len(subset), 'localMean': float(x.mean()), 'candidateMean': float(y.mean()), 'association': association(x, y)}
            centered.extend([(float(a-x.mean()), float(b-y.mean()), 1/len(subset)) for a, b in zip(x, y)])
            means.append((float(x.mean()), float(y.mean())))
        associations[coordinate] = {'byElection': per_year,
            'withinElectionCenteredEqualElection': association([r[0] for r in centered], [r[1] for r in centered], [r[2] for r in centered]),
            'sharedElectionMeans': association([r[0] for r in means], [r[1] for r in means])}
    geography = read(GEOGRAPHY)['records']
    pairs = []
    for g in geography:
        current, previous = candidate.get(g['targetElectorateId']), candidate.get(g['dominantPredecessorId'])
        if not g['certifiedTwoSidedExact'] or current is None or previous is None or previous['targetYear'] != current['sourceYear']:
            continue
        pairs.append({'earlierId': previous['targetElectorateId'], 'laterId': current['targetElectorateId'],
            'transition': f"{previous['targetYear']}-{current['targetYear']}", 'geographyId': g['geographyId'],
            'earlier': {c: raw_residual(previous, c) for c in ('balance', 'mass')},
            'later': {c: raw_residual(current, c) for c in ('balance', 'mass')}})
    persistence = {transition: {coordinate: association(
        [p['earlier'][coordinate] for p in pairs if p['transition'] == transition and p['earlier'][coordinate] is not None and p['later'][coordinate] is not None],
        [p['later'][coordinate] for p in pairs if p['transition'] == transition and p['earlier'][coordinate] is not None and p['later'][coordinate] is not None]) for coordinate in ('balance', 'mass')}
        for transition in sorted({p['transition'] for p in pairs})}
    return {'stage': 47, 'crossLayer': associations, 'matchedRecords': matched,
            'remainingSeatErrorPersistence': {'pairs': pairs, 'byTransition': persistence, 'prediction': 'complete frozen S+R conditional on observed local party inputs',
                'interpretation': 'Exact-seat descriptive repeat error after S+R, not personal causality or a fitted latent seat effect; overlapping transitions and reused elections remain dependent'},
            'definitionLimitations': 'Local errors condition on national truth; candidate errors condition on local truth and depend on it through the nonlinear frozen mean. Associations do not identify a covariance model or imply national error is counted twice. Within-remainder schemas differ and are intentionally not correlated.'}


def main():
    args = arguments()
    verify()
    save('original-audit.json', original_audit(), args.check)
    save('heterogeneity.json', heterogeneity(), args.check)
    save('dependence.json', dependence(), args.check)
    print('Stage47 saved width/heterogeneity/dependence audits complete; no fitting or reconstruction')


if __name__ == '__main__':
    main()
