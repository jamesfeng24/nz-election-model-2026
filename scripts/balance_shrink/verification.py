"""Independent arithmetic: Stage48 equality, fits, locations, scores, 2014 identity, exclusion and decision inputs."""
import numpy as np
from scipy.special import expit
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty.metrics import crps
from scripts.uncertainty_revision.coordinates import mean_logit_location, partition
from scripts.uncertainty_expectation.simulation import component
from scripts.balance_scale.fit import location
from scripts.balance_scale.simulate import scaled
from .common import (PREFIX, INVENTORY, SCALES, STAGE48_EVALUATION, STAGE48_FIT, YEARS, LEVELS, read, save, verify, arguments, design, arms)
from .evaluation import candidate_rows


def stage48_equality(evaluation):
    """The control must equal Stage48's control, and the penalised reference Stage48's constant arm, seat by seat."""
    old = read(STAGE48_EVALUATION)['component']['records']
    result = {}
    for arm, source in (('control', 'control'), ('penalised', 'constant')):
        worst = {'crps': 0., 'energy': 0., 'width': 0., 'score': 0., 'coverage': 0}
        for new, o in zip(evaluation['records'][arm], old[source]):
            if new['id'] != o['id']:
                raise ValueError('Stage48 seat order differs')
            n = [o['groups'].index('national'), o['groups'].index('labour')]
            worst['crps'] = max(worst['crps'], max(abs(a - o['crpsPP'][i]) for a, i in zip(new['crpsPP'], n)))
            worst['energy'] = max(worst['energy'], abs(new['energyPP'] - o['energyPP']))
            for level in LEVELS:
                block, ob = new['intervals'][str(level)], o[f'interval{level}']
                worst['width'] = max(worst['width'], max(abs(a - ob['widths'][i]) for a, i in zip(block['widths'], n)))
                worst['score'] = max(worst['score'], max(abs(a - ob['scores'][i]) for a, i in zip(block['scores'], n)))
                worst['coverage'] += sum(a != ob['covered'][i] for a, i in zip(block['covered'], n))
        result[arm] = {'seats': len(evaluation['records'][arm]), 'maximumAbsoluteDifference': worst, 'comparedWith': 'Stage48 ' + source}
    return result


def fit_checks(fits):
    spec = design()
    stage48 = read(STAGE48_FIT)['folds']
    rows = []
    for year, fold in fits['folds'].items():
        if fold['trainingYears']:
            f = fold['free']
            rows.append({'year': int(year), 'objectiveDifference': f['powell']['objectiveDifference'], 'projectedGradientMax': f['projectedGradientMax'],
                         'centralDifferenceGradient': f['centralDifferenceGradientMaxDifference'], 'boundContact': f['boundContact'],
                         'agreementWithStage48DescriptiveA': abs(f['a'] - stage48[year]['unpenalisedConstant']['a']),
                         'penalisedMultiplierAgreement': abs(fold['multipliers']['penalised'] - float(np.exp(stage48[year]['constant']['theta'][0]))),
                         'passed': bool(f['powell']['objectiveDifference'] <= 1e-6 and f['projectedGradientMax'] <= 1e-6
                                        and f['centralDifferenceGradientMaxDifference'] <= 1e-6 and not f['boundContact']
                                        and abs(f['a'] - stage48[year]['unpenalisedConstant']['a']) <= spec['fit']['agreementWithStage48DescriptiveValue'])})
    refit = fits['descriptive2026Refit']['fit']
    rows.append({'year': 2026, 'objectiveDifference': refit['powell']['objectiveDifference'], 'projectedGradientMax': refit['projectedGradientMax'],
                 'centralDifferenceGradient': refit['centralDifferenceGradientMaxDifference'], 'boundContact': refit['boundContact'],
                 'passed': bool(refit['powell']['objectiveDifference'] <= 1e-6 and refit['projectedGradientMax'] <= 1e-6
                                and refit['centralDifferenceGradientMaxDifference'] <= 1e-6 and not refit['boundContact'])})
    return rows


def multiplier_checks(evaluation, fits):
    worst = 0.
    for arm in arms():
        for r in evaluation['records'][arm]:
            worst = max(worst, abs(r['multiplier'] - fits['folds'][str(r['year'])]['multipliers'][arm]))
    grid = {a: v['multiplier'] for a, v in design()['arms'].items() if isinstance(v['multiplier'], float)}
    for year, fold in fits['folds'].items():
        for a, m in grid.items():
            worst = max(worst, abs(fold['multipliers'][a] - m))
    return worst


def location_checks(fits):
    """Independent hermegauss(161) check that every multiplier preserves the frozen ratio mean (gate 0.05pp)."""
    nodes, weights = np.polynomial.hermite_e.hermegauss(161)
    weights = weights / np.sqrt(2 * np.pi)
    scales = read(SCALES)
    worst_gap, worst_agree = 0., 0.
    for year in YEARS:
        fit = scale_for(scales, 'candidate', year)['scales']['balance']
        rows = candidate_rows(year)
        p = np.array([r['mean'][partition(r['groups'])[0][0]] / (r['mean'][partition(r['groups'])[0][0]] + r['mean'][partition(r['groups'])[1][0]]) for r in rows])
        for arm in arms():
            sd = float(np.hypot(fit['shared'], fit['seat'] * fits['folds'][str(year)]['multipliers'][arm]))
            simulated = mean_logit_location(p, sd)
            exact = location(p, np.full(len(p), sd))[0]
            gap = np.abs(expit(simulated[:, None] + sd * nodes[None, :]) @ weights - p)
            worst_gap = max(worst_gap, float(gap.max()))
            worst_agree = max(worst_agree, float(np.abs(simulated - exact).max()))
    return {'maximumConditionalMeanGapPP': 100 * worst_gap, 'maximumSimulationVersusFitLocationDifference': worst_agree,
            'gatePP': design()['decision']['improves']['doublingGatesPP']['mean']}


def brute_crps(draws, y):
    d = np.asarray(draws)
    return float(np.mean(np.abs(d - y)) - 0.5 * np.mean(np.abs(d[:, None] - d[None, :])))


def score_checks(evaluation, fits):
    """Regenerate selected seats and recompute major CRPS by an independent pairwise formula."""
    scales = read(SCALES)
    out, worst = [], 0.
    for year in (2017, 2023):
        rows = candidate_rows(year)
        fit = scale_for(scales, 'candidate', year)['scales']
        for row in (rows[0], rows[-1]):
            for arm in ('grid85', 'free'):
                m = fits['folds'][str(year)]['multipliers'][arm]
                q, _ = component(row, scaled(fit, m), design()['components']['draws'])
                major = [k for k, g in enumerate(row['groups']) if g in ('national', 'labour')]
                actual = 100 * np.asarray(row['actual'])
                independent = float(np.mean([brute_crps(100 * q[:2048, k], actual[k]) for k in major]))
                vectorised = float(np.mean(crps(100 * q[:2048][:, major], actual[major])))
                saved = next(x for x in evaluation['records'][arm] if x['id'] == row['targetElectorateId'])
                regenerated = float(np.mean(crps(100 * q[:, major], actual[major])))
                worst = max(worst, abs(independent - vectorised), abs(float(np.mean(saved['crpsPP'])) - regenerated))
                out.append({'id': row['targetElectorateId'], 'arm': arm, 'pairwiseVersusVectorisedPP': abs(independent - vectorised),
                            'savedVersusRegeneratedPP': abs(float(np.mean(saved['crpsPP'])) - regenerated)})
    return {'seats': out, 'maximumDifferencePP': worst}


def decision_arithmetic(evaluation, decision):
    """Plain-loop recomputation of every pooled primary difference."""
    out = {}
    for arm in arms()[1:]:
        total, count = 0., 0
        for a, b in zip(evaluation['records'][arm], evaluation['records']['control']):
            if a['year'] == 2014:
                continue
            total += (a['crpsPP'][0] + a['crpsPP'][1]) / 2 - (b['crpsPP'][0] + b['crpsPP'][1]) / 2
            count += 1
        out[arm] = {'plainLoop': total / count, 'saved': decision['comparisons'][arm]['deltaMajorCRPSPP'],
                    'difference': abs(total / count - decision['comparisons'][arm]['deltaMajorCRPSPP'])}
    return out


def identity_2014(evaluation):
    rows = {a: [x for x in evaluation['records'][a] if x['year'] == 2014] for a in arms()}
    same = lambda a: all(rows[a][i]['crpsPP'] == rows['control'][i]['crpsPP'] and rows[a][i]['energyPP'] == rows['control'][i]['energyPP']
                         for i in range(len(rows['control'])))
    return {'seats': len(rows['control']), 'freeIdenticalToControl': same('free'), 'penalisedIdenticalToControl': same('penalised'),
            'gridArmsDifferFromControl': all(not same(a) for a in ('grid95', 'grid90', 'grid85', 'grid80'))}


def exclusion_check(evaluation):
    """Maori electorates are excluded by electorate type: every record scored is a general electorate."""
    records = read(INVENTORY)['candidateRecords']
    scopes = sorted({r['scope'] for r in records})
    scored = sum(evaluation['seatsByElection'].values())
    return {'inventoryScopes': scopes, 'nonGeneralRecordsInInventory': sum(r['scope'] != 'general' for r in records),
            'seatsScored': scored, 'seatsByElection': evaluation['seatsByElection'],
            'passed': bool(scopes == ['general'] and scored == len(records) == sum(evaluation['seatsByElection'].values()))}


def build():
    evaluation, fits, decision = read(PREFIX + '/evaluation.json'), read(PREFIX + '/fit.json'), read(PREFIX + '/decision.json')
    tolerance = design()['equalityTolerance']
    result = {'stage': 60, 'equalsStage48': stage48_equality(evaluation), 'fitChecks': fit_checks(fits),
              'multiplierMaxDifference': multiplier_checks(evaluation, fits), 'locationChecks': location_checks(fits),
              'scoreChecks': score_checks(evaluation, fits), 'decisionArithmetic': decision_arithmetic(evaluation, decision),
              'identity2014': identity_2014(evaluation), 'exclusion': exclusion_check(evaluation),
              'drawGapAcrossArms': evaluation['maximumDrawGapAcrossArms']}
    eq = result['equalsStage48']
    result['passed'] = bool(
        all(v['maximumAbsoluteDifference'][k] <= tolerance['controlVersusStage48'] for v in eq.values() for k in ('crps', 'energy', 'width', 'score'))
        and all(v['maximumAbsoluteDifference']['coverage'] == 0 for v in eq.values())
        and all(f['passed'] for f in result['fitChecks']) and result['multiplierMaxDifference'] <= tolerance['multiplierRecomputation']
        and result['locationChecks']['maximumConditionalMeanGapPP'] <= result['locationChecks']['gatePP']
        and result['locationChecks']['maximumSimulationVersusFitLocationDifference'] <= 1e-9
        and result['scoreChecks']['maximumDifferencePP'] <= 1e-9
        and all(v['difference'] <= 1e-12 for v in result['decisionArithmetic'].values())
        and all(result['identity2014'][k] for k in ('freeIdenticalToControl', 'penalisedIdenticalToControl', 'gridArmsDifferFromControl'))
        and result['exclusion']['passed'] and result['drawGapAcrossArms'] <= 1e-12)
    return result


def main():
    args = arguments()
    verify()
    value = build()
    if not value['passed']:
        raise ValueError('Stage60 independent verification failed')
    save('verification.json', value, args.check)
    print('Stage60 independent verification passed')


if __name__ == '__main__':
    main()
