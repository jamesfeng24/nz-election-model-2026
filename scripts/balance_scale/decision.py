"""Apply the frozen decision rule; the rule and thresholds live in design-contract.json."""
import numpy as np
from .common import PREFIX, RESTRICTIONS, read, save, verify, arguments, design

NAMES = {'constant_vs_control': ('constant', 'control'), 'conditional_vs_constant': ('conditional', 'constant'),
         'conditional_vs_control': ('conditional', 'control')}


def sign(x):
    return 0 if x == 0 else 1 if x > 0 else -1


def compare(section, x, y, rule, years=(2017, 2020, 2023)):
    pop = section['summary']['fittedFolds']
    levels = rule['intervalScoreLevels']
    delta_crps = pop[x]['majorCRPSPP'] - pop[y]['majorCRPSPP']
    delta_is = float(np.mean([pop[x]['majorIntervals'][str(l)]['intervalScorePP'] - pop[y]['majorIntervals'][str(l)]['intervalScorePP'] for l in levels]))
    guard = {str(l): {'coverageX': pop[x]['majorIntervals'][str(l)]['coverage'], 'coverageY': pop[y]['majorIntervals'][str(l)]['coverage'],
                      'passed': abs(pop[x]['majorIntervals'][str(l)]['coverage'] - l / 100)
                                <= abs(pop[y]['majorIntervals'][str(l)]['coverage'] - l / 100) + rule['coverageGuardAbsolute']}
             for l in levels}
    delta_energy = pop[x]['energyPP'] - pop[y]['energyPP']
    folds = {str(y_): section['summary'][str(y_)][x]['majorCRPSPP'] - section['summary'][str(y_)][y]['majorCRPSPP'] for y_ in years}
    out = {'deltaMajorCRPSPP': float(delta_crps), 'deltaMajorIntervalScorePP': delta_is, 'coverageGuard': guard,
           'deltaEnergyPP': float(delta_energy), 'foldDeltaMajorCRPSPP': folds,
           'foldsNegative': int(sum(v < 0 for v in folds.values()))}
    if 'records' in section and 'majorCRPSPrefix' in section['records'][x][0]:
        fitted = [i for i, r in enumerate(section['records'][x]) if r['year'] != 2014]
        prefix = float(np.mean([section['records'][x][i]['majorCRPSPrefix'] - section['records'][y][i]['majorCRPSPrefix'] for i in fitted]))
        out['resolution'] = {'prefixDraws': rule['resolutionPrefixDraws'], 'deltaAtPrefixPP': prefix,
                             'differencePP': abs(prefix - delta_crps), 'passed': abs(prefix - delta_crps) <= rule['resolutionTolerancePP']}
    return out


def classify(c, rule):
    resolved = c.get('resolution', {'passed': True})['passed']
    material = rule['crpsMaterialityPP']
    improves = (resolved and c['deltaMajorCRPSPP'] <= -material and c['deltaMajorIntervalScorePP'] <= 0
                and all(g['passed'] for g in c['coverageGuard'].values()) and c['deltaEnergyPP'] <= rule['energyGuardPP']
                and c['foldsNegative'] >= rule['minimumFoldsNegative'])
    if improves:
        return 'IMPROVES'
    if resolved and c['deltaMajorCRPSPP'] >= material:
        return 'WORSE'
    if resolved and abs(c['deltaMajorCRPSPP']) < material:
        return 'NEGLIGIBLE'
    return 'MIXED'


def finding(kc, fk, fc):
    if 'MIXED' in (kc, fk):
        return 'mixed'
    if kc == 'IMPROVES' and fk == 'IMPROVES':
        return 'global scale change and predictable heteroskedasticity'
    if kc == 'IMPROVES':
        return 'constant only'
    if fk == 'IMPROVES':
        return 'conditional only' if fc == 'IMPROVES' else 'mixed'
    return 'neither'


def build():
    evaluation = read(PREFIX + '/evaluation.json')
    rule = design()['decision']
    result = {'stage': 48, 'rule': rule, 'operationalAdoption': None}
    for layer in ('component', 'composed'):
        section = evaluation[layer]
        comparisons = {}
        for name, (x, y) in NAMES.items():
            c = compare(section, x, y, rule)
            c['classification'] = classify(c, rule) if layer == 'component' else None
            comparisons[name] = c
        result[layer] = comparisons
    comp = result['component']
    result['finding'] = finding(comp['constant_vs_control']['classification'], comp['conditional_vs_constant']['classification'],
                                comp['conditional_vs_control']['classification'])
    flags = {}
    for name in ('constant_vs_control', 'conditional_vs_constant'):
        a, b = comp[name]['deltaMajorCRPSPP'], result['composed'][name]['deltaMajorCRPSPP']
        flags[name] = {'component': a, 'composed': b,
                       'flag': bool(abs(b) >= rule['composedSignFlagPP'] and sign(a) != sign(b)),
                       'meaning': 'composed sign disagreement of at least the flag size; supporting only, composed gates unmet'}
    result['composedSignFlags'] = flags
    result['allSeatsDeltaMajorCRPSPP'] = {name: evaluation['component']['summary']['allSeats'][x]['majorCRPSPP']
                                           - evaluation['component']['summary']['allSeats'][y]['majorCRPSPP'] for name, (x, y) in NAMES.items()}
    gate = design()['gatesPP']
    precision = evaluation['component']['representativeDoubling']
    result['numerical'] = {'componentDoublingAllPassed': {r: all(x['allPassed'] for x in precision[r]) for r in RESTRICTIONS},
                           'componentMaximumDoublingChangePP': {r: precision[r][-1]['changesPP'] for r in RESTRICTIONS},
                           'composedDoublingAllPassed': {r: all(x['allPassed'] for x in evaluation['composed']['representativeDoubling'][r]) for r in RESTRICTIONS},
                           'maximumDrawGapAcrossRestrictions': evaluation['component']['maximumDrawGapAcrossRestrictions'],
                           'maximumFiniteMeanDeviationPP': evaluation['component']['maximumFiniteMeanDeviationPP'],
                           'meanDeviationGatePP': gate['mean']}
    return result


def main():
    args = arguments()
    verify()
    save('decision.json', build(), args.check)
    print('Stage48 frozen decision rule applied' if not args.check else 'Stage48 decision reproduced')


if __name__ == '__main__':
    main()
