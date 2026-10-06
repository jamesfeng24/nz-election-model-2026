"""Independent arithmetic: Stage47 control equality, locations, fits, scores and decision inputs."""
import numpy as np
from scipy.special import expit
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty.metrics import crps
from scripts.uncertainty_revision.coordinates import mean_logit_location, partition
from scripts.uncertainty_expectation.simulation import component
from scripts.uncertainty_tails.metrics import record
from .common import (PREFIX, INVENTORY, SCALES, STAGE47_EVALUATION, HETEROGENEITY, STRUCTURE, RESTRICTIONS,
                     read, save, verify, arguments, design)
from .fit import location
from .simulate import scaled


def control_equality(evaluation):
    """The control must be Stage47's sealed corrected bank, seat by seat."""
    prior = read(STAGE47_EVALUATION)
    result = {}
    for layer, key in (('component', 'candidate'), ('composed', 'composed')):
        old = {r['id']: r for c in prior['cases'] if c['layer'] == key for r in c['methods']['corrected']['records']}
        worst = {'crps': 0., 'energy': 0., 'width90': 0.}
        for r in evaluation[layer]['records']['control']:
            o = old[r['id']]
            worst['crps'] = max(worst['crps'], float(np.max(np.abs(np.array(r['crpsPP']) - np.array(o['crpsPP'])))))
            worst['energy'] = max(worst['energy'], abs(r['energyPP'] - o['energyPP']))
            worst['width90'] = max(worst['width90'], float(np.max(np.abs(np.array(r['interval90']['widths']) - np.array(o['interval90']['widths'])))))
        result[layer] = {'seats': len(evaluation[layer]['records']['control']), 'maximumAbsoluteDifference': worst}
    return result


def location_checks(fits):
    """Independent hermegauss(161) check that every multiplier preserves the frozen ratio mean."""
    inventory, scales = read(INVENTORY), read(SCALES)
    nodes, weights = np.polynomial.hermite_e.hermegauss(161)
    weights = weights / np.sqrt(2 * np.pi)
    worst_gap, worst_agree = 0., 0.
    for year in (2014, 2017, 2020, 2023):
        fit = scale_for(scales, 'candidate', year)['scales']['balance']
        fold = fits['folds'][str(year)]
        index = {s: i for i, s in enumerate(fold['seatIds'])}
        for row in (r for r in inventory['candidateRecords'] if r['targetYear'] == year):
            n, l, _ = partition(row['groups'])
            p = row['mean'][n[0]] / (row['mean'][n[0]] + row['mean'][l[0]])
            for r in RESTRICTIONS:
                sd = float(np.hypot(fit['shared'], fit['seat'] * fold['multipliers'][r][index[row['targetElectorateId']]]))
                simulated = float(mean_logit_location(np.array([p]), sd)[0])
                exact = float(location(np.array([p]), np.array([sd]))[0][0])
                worst_gap = max(worst_gap, abs(float(np.sum(expit(simulated + sd * nodes) * weights)) - p))
                worst_agree = max(worst_agree, abs(simulated - exact))
    return {'maximumConditionalMeanGapPP': 100 * worst_gap, 'maximumSimulationVersusFitLocationDifference': worst_agree,
            'gatePP': design()['gatesPP']['conditionalIntegration']}


def feature_multipliers(fits):
    """Recompute every multiplier from raw feature files, independent of the fit module's arrays."""
    support = {r['id']: r['supportedR'] for r in read(HETEROGENEITY)['records']}
    proxy = {r['id']: r['sourceNonmajorSupportProxy'] for r in read(STRUCTURE)['structuralRecords']}
    worst = 0.
    for year, fold in fits['folds'].items():
        for r in RESTRICTIONS:
            a, br, bt = fold[r]['theta']
            for cid, m in zip(fold['seatIds'], fold['multipliers'][r]):
                x = a + br * ((1 - support[cid]) - fold['centers']['R']) + bt * (proxy[cid] - fold['centers']['T'])
                worst = max(worst, abs(np.exp(x) - m))
    return worst


def fit_checks(fits):
    spec = design()['equalityTolerance']
    rows = []
    for year, fold in fits['folds'].items():
        for r in ('constant', 'conditional'):
            f = fold[r]
            if 'powell' in f:
                rows.append({'year': int(year), 'restriction': r, 'objectiveDifference': f['powell']['objectiveDifference'],
                             'projectedGradientMax': f['projectedGradientMax'],
                             'centralDifferenceGradient': f['centralDifferenceGradientMaxDifference'],
                             'boundContact': any(f['boundContact']),
                             'passed': bool(f['powell']['objectiveDifference'] <= spec['objective'] and f['projectedGradientMax'] <= spec['gradient']
                                            and f['centralDifferenceGradientMaxDifference'] <= spec['gradient'])})
    return rows


def brute_crps(draws, y):
    d = np.asarray(draws)
    return float(np.mean(np.abs(d - y)) - 0.5 * np.mean(np.abs(d[:, None] - d[None, :])))


def score_checks(evaluation, fits):
    """Regenerate selected seats and recompute major CRPS by an independent pairwise formula."""
    inventory, scales = read(INVENTORY), read(SCALES)
    out, worst = [], 0.
    for year in (2017, 2023):
        rows = sorted([r for r in inventory['candidateRecords'] if r['targetYear'] == year], key=lambda r: r['targetElectorateId'])
        fit = scale_for(scales, 'candidate', year)['scales']
        fold = fits['folds'][str(year)]
        for row in (rows[0], rows[-1]):
            i = fold['seatIds'].index(row['targetElectorateId'])
            for r in ('control', 'conditional'):
                q, _ = component(row, scaled(fit, fold['multipliers'][r][i]), design()['components']['draws'])
                major = [k for k, g in enumerate(row['groups']) if g in ('national', 'labour')]
                independent = float(np.mean([brute_crps(100 * q[:2048, k], 100 * row['actual'][k]) for k in major]))
                vectorised = float(np.mean(crps(100 * q[:2048][:, major], 100 * np.asarray(row['actual'])[major])))
                saved = next(x for x in evaluation['component']['records'][r] if x['id'] == row['targetElectorateId'])
                recomputed = float(np.mean([saved['crpsPP'][k] for k in major]))
                regenerated = float(np.mean(crps(100 * q[:, major], 100 * np.asarray(row['actual'])[major])))
                worst = max(worst, abs(independent - vectorised), abs(recomputed - regenerated))
                out.append({'id': row['targetElectorateId'], 'restriction': r, 'pairwiseVersusVectorisedPP': abs(independent - vectorised),
                            'savedVersusRegeneratedPP': abs(recomputed - regenerated)})
    return {'seats': out, 'maximumDifferencePP': worst}


def decision_arithmetic(evaluation, decision):
    """Plain-loop recomputation of the primary pooled differences."""
    out = {}
    for name, (x, y) in {'constant_vs_control': ('constant', 'control'), 'conditional_vs_constant': ('conditional', 'constant')}.items():
        for layer in ('component', 'composed'):
            total, count = 0., 0
            for a, b in zip(evaluation[layer]['records'][x], evaluation[layer]['records'][y]):
                if a['year'] == 2014:
                    continue
                major = [k for k, g in enumerate(a['groups']) if g in ('national', 'labour')]
                total += sum(a['crpsPP'][k] for k in major) / len(major) - sum(b['crpsPP'][k] for k in major) / len(major)
                count += 1
            out[f'{layer}:{name}'] = {'plainLoop': total / count, 'saved': decision[layer][name]['deltaMajorCRPSPP'],
                                      'difference': abs(total / count - decision[layer][name]['deltaMajorCRPSPP'])}
    return out


def identity_2014(evaluation):
    rows = {r: [x for x in evaluation['component']['records'][r] if x['year'] == 2014] for r in RESTRICTIONS}
    return {'seats': len(rows['control']), 'restrictionsIdentical': all(
        rows[r][i]['crpsPP'] == rows['control'][i]['crpsPP'] and rows[r][i]['energyPP'] == rows['control'][i]['energyPP']
        for r in RESTRICTIONS[1:] for i in range(len(rows['control'])))}


def build():
    evaluation, fits, decision = read(PREFIX + '/evaluation.json'), read(PREFIX + '/fit.json'), read(PREFIX + '/decision.json')
    tolerance = design()['equalityTolerance']
    result = {'stage': 48, 'controlEqualsStage47Corrected': control_equality(evaluation),
              'locationChecks': location_checks(fits), 'multiplierRecomputationMaxDifference': feature_multipliers(fits),
              'fitChecks': fit_checks(fits), 'scoreChecks': score_checks(evaluation, fits),
              'decisionArithmetic': decision_arithmetic(evaluation, decision), 'identity2014': identity_2014(evaluation),
              'reusedRemainderMaximumGap': evaluation['composed']['maximumEqualityGap'],
              'drawGapAcrossRestrictions': evaluation['component']['maximumDrawGapAcrossRestrictions']}
    result['passed'] = bool(
        all(v['maximumAbsoluteDifference'][k] <= 1e-9 for v in result['controlEqualsStage47Corrected'].values() for k in v['maximumAbsoluteDifference'])
        and result['locationChecks']['maximumConditionalMeanGapPP'] <= result['locationChecks']['gatePP']
        and result['locationChecks']['maximumSimulationVersusFitLocationDifference'] <= tolerance['locationAgreement']
        and result['multiplierRecomputationMaxDifference'] <= 1e-12 and all(f['passed'] for f in result['fitChecks'])
        and result['scoreChecks']['maximumDifferencePP'] <= 1e-9
        and all(v['difference'] <= 1e-12 for v in result['decisionArithmetic'].values())
        and result['identity2014']['restrictionsIdentical']
        and result['reusedRemainderMaximumGap'] <= tolerance['reusedRemainder'] and result['drawGapAcrossRestrictions'] <= tolerance['reusedRemainder'])
    return result


def main():
    args = arguments()
    verify()
    value = build()
    if not value['passed']:
        raise ValueError('Stage48 independent verification failed')
    save('verification.json', value, args.check)
    print('Stage48 independent verification passed')


if __name__ == '__main__':
    main()
