"""Audited case-level external points; no posterior reconstruction or inference."""
import csv
from datetime import date, timedelta
from math import fsum, sqrt, isfinite
from .common import RAW, NATIONAL, ROOT, read, simplex, save

ALIASES = {'National': 'NAT', 'Labour': 'LAB', 'Green': 'GRN', 'ACT': 'ACT',
           'NZ First': 'NZF', 'Te Pāti Māori': 'MRI'}
NAMED = ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'MRI']
DATES = {2017: '2017-09-23', 2020: '2020-10-17', 2023: '2023-10-14'}


def validate_case(case, year, own):
    expected = (date.fromisoformat(DATES[year]) - timedelta(days=56)).isoformat()
    if (case['target'], case['horizon_weeks'], case['cutoff']) != (year, 8, expected):
        raise ValueError('External election/horizon/cutoff mismatch')
    if own['electionYear'] != year or own['horizonDays'] != 56 or own['cutoff'][:10] != expected:
        raise ValueError('Own case does not match external calendar cutoff')
    if len(set(case['parties'])) != len(case['parties']):
        raise ValueError('Duplicate external party')
    if set(case['forecast_mean']) != set(case['parties']) or set(case['outcome']) != set(case['parties']):
        raise ValueError('Incomplete external forecast/outcome schema')
    simplex(list(case['forecast_mean'].values()), 1e-6)
    simplex(list(case['outcome'].values()), 1e-6)


def named_means(case, ensemble):
    result = {}
    for name, code in ALIASES.items():
        if name not in case['parties']:
            continue
        key = 'error_pp[' + name + ']'
        if not ensemble.get(key):
            continue
        # Invert the audited case-level signed-error field, not aggregate scores.
        v = case['outcome'][name] + float(ensemble[key]) / 100
        if not isfinite(v) or not 0 <= v <= 1:
            raise ValueError('Invalid recovered named-party mean')
        result[code] = v
    return result


def coarsen_means(case):
    if not set(ALIASES) <= set(case['parties']):
        raise ValueError('Required named party folded into Other')
    result = {code: case['forecast_mean'][name] for name, code in ALIASES.items()}
    result['OTH'] = fsum(v for p, v in case['forecast_mean'].items() if p not in ALIASES)
    simplex(list(result.values()), 1e-6)
    return result


def audit():
    own = {c['electionYear']: c for c in read(NATIONAL / 'output-manifest.json')['cases']
           if c['id'].startswith('primary-') and c['horizonDays'] == 56}
    with (RAW / 'output_backtest_ensemble.csv').open() as stream:
        csv_rows = list(csv.DictReader(stream))
    cases = []
    for year in (2017, 2020, 2023):
        gauss = read(RAW / f'output_backtest_cases_gauss_{year}_h8.json')
        base = read(RAW / f'output_backtest_cases_base_{year}_h8.json')
        validate_case(gauss, year, own[year])
        validate_case(base, year, own[year])
        if base['parties'] != gauss['parties'] or base['outcome'] != gauss['outcome']:
            raise ValueError('Ensemble constructor schema/outcome disagreement')
        selected = [r for r in csv_rows if (int(r['target']), int(r['horizon_weeks']), r['variant']) == (year, 8, 'ensemble')]
        if len(selected) != 1:
            raise ValueError('Missing/duplicate requested ensemble record')
        recovered = named_means(base, selected[0])
        missing = sorted(set(NAMED) - set(recovered))
        cases.append({'year': year, 'cutoff': gauss['cutoff'], 'ownCaseId': own[year]['id'],
                      'status': 'unavailable' if missing else 'point_comparison_available',
                      'reason': 'named_party_not_separately_reported:' + ','.join(missing) if missing else None,
                      'gaussCategories': gauss['parties'], 'gaussNamedMeans': {ALIASES[p]: v for p,v in gauss['forecast_mean'].items() if p in ALIASES},
                      'gaussCoarseMeans': coarsen_means(gauss) if not missing else None,
                      'ensembleNamedMeans': recovered, 'ensembleRecovery': 'archived base outcome + ensemble case signed mean error/100',
                      'gaussDiagnostics': gauss['diagnostics'],
                      'probabilityComparison': 'unavailable_no_joint_samples_or_interval_endpoints',
                      'cutoffMatch': 'exact_NZ_calendar_day; external_hour_timezone_unarchived',
                      'archiveType': 'retrospective_backtest_not_pre_election_archive'})
    return {'stage': 37, 'cases': cases, 'requestedCases': 3, 'pointMatchedCases': sum(c['status']=='point_comparison_available' for c in cases),
            'pin': read(RAW / 'current-commit.json')['sha'], 'attribution': 'ariedotcodotnz/nz-poll-of-polls, GPL-3.0-or-later',
            'ensembleWeights': 'leave_one_election_out; later_elections_in_earlier_cases',
            'commonCategoryDistributionAvailable': False, 'newInferenceRun': False,
            'nationalSelection': None}


def point_score(pred, actual, categories):
    if len(set(categories)) != len(categories) or not set(categories) <= set(pred) & set(actual):
        raise ValueError('Incomplete/duplicate scoring categories')
    errors = {p: 100 * (pred[p] - actual[p]) for p in categories}
    return {'maePP': fsum(abs(v) for v in errors.values()) / len(errors),
            'rmsePP': sqrt(fsum(v*v for v in errors.values()) / len(errors)),
            'biasPP': fsum(errors.values()) / len(errors), 'partyErrorPP': errors,
            'categoryCount': len(categories), 'denominator': 'original_national_valid_party_share; no_subset_renormalization'}


def pooled(rows, categories):
    if not rows:
        return None
    errors = [r['partyErrorPP'][p] for r in rows for p in categories]
    return {'maePP': fsum(abs(v) for v in errors) / len(errors),
            'rmsePP': sqrt(fsum(v*v for v in errors) / len(errors)),
            'partyBiasPP': {p: fsum(r['partyErrorPP'][p] for r in rows) / len(rows) for p in categories},
            'elections': len(rows), 'electionWeight': 1 / len(rows)}


def evaluate(inventory, check=False):
    manifest = {c['id']: c for c in read(NATIONAL / 'output-manifest.json')['cases']}
    benchmark = {c['id']: c for c in read(NATIONAL / 'benchmark.json')['cases']}
    actuals = {r['year']: r['shares'] for r in read(ROOT / 'data/processed/polling/national-foundation/official-results-isolated.json')['records']}
    rows = []
    for c in inventory['cases']:
        if c['status'] != 'point_comparison_available':
            rows.append({'year': c['year'], 'status': c['status'], 'reason': c['reason']})
            continue
        m = manifest[c['ownCaseId']];b = benchmark[c['ownCaseId']]
        model = dict(zip(m['categories'], m['expectedElectionDay']))
        model['OTH'] += model.pop('TOP', 0)
        avg = dict(zip(b['categories'], b['shares']))
        actual = dict(actuals[c['year']]);actual['OTH'] += actual.pop('TOP', 0)
        vectors = {'own_model': model, 'own_average': avg, 'external_gauss': c['gaussCoarseMeans'], 'external_ensemble': c['ensembleNamedMeans']}
        named = {s: point_score(v, actual, NAMED) for s,v in vectors.items()}
        full = {s: point_score(v, actual, NAMED+['OTH']) for s,v in vectors.items() if s!='external_ensemble'}
        rows.append({'year': c['year'], 'status': 'scored_points_only', 'namedSix': named, 'completeCoarseSeven': full})
    pools = {}
    for group, cats in (('namedSix', NAMED), ('completeCoarseSeven', NAMED+['OTH'])):
        systems = ('own_model','own_average','external_gauss','external_ensemble') if group=='namedSix' else ('own_model','own_average','external_gauss')
        pools[group] = {s: pooled([r[group][s] for r in rows if group in r], cats) for s in systems}
    output = {'stage':37, 'cases':rows, 'supportedSubsetPooled':pools,
              'fullRequestedThreeCaseComparison':'unavailable_2020_MRI_folded_into_Other',
              'probabilisticScores':'unavailable_for_external; not reconstructed from sd/PIT/headline',
              'forecastOrigin':'retrospective_system_comparison_with_different_inputs', 'operationalSelection':None}
    save('external-evaluation.json', output, check)
    return output
