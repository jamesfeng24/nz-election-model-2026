"""Apply the frozen Stage67 rule (design plus amendment 1); thresholds, floors and arms live in design-contract.json."""
import numpy as np
from scripts.balance_shrink.summary import summarize
from scripts.balance_shrink.decision import compare, classify, seat_deltas, bootstrap_indices, bootstrap_interval
from .common import PREFIX, YEARS, DECISION_YEARS, LEVELS, read, save, verify, arguments, design, arms

GROUPS = {'ordinary': lambda r: not r['exceptional'], 'exceptional': lambda r: r['exceptional'],
          'ordinary17': lambda r: not r['exceptional17'], 'exceptional17': lambda r: r['exceptional17']}


def populations(records):
    order = arms()
    ids = [r['id'] for r in records['control']]
    if any([r['id'] for r in records[a]] != ids for a in order):
        raise ValueError('Unequal paired Stage67 records')
    keep = {'allSeats': lambda r: True, 'decisionSeats': lambda r: r['year'] != 2014}
    keep.update({str(y): (lambda y: lambda r: r['year'] == y)(y) for y in YEARS})
    for g, test in GROUPS.items():
        keep[f'{g}:decision'] = (lambda t: lambda r: r['year'] != 2014 and t(r))(test)
        keep.update({f'{g}:{y}': (lambda t, y: lambda r: r['year'] == y and t(r))(test, y) for y in YEARS})
    out = {}
    for name, test in keep.items():
        chosen = {a: [r for r in records[a] if test(r)] for a in order}
        out[name] = {a: summarize(v) for a, v in chosen.items()} if chosen['control'] else {}
    return out


def doubling_passed(evaluation, arm):
    return all(r['allPassed'] for r in evaluation['representativeDoubling'][arm])


def floors(summary, arm, spec):
    rows, passed = {}, True
    for group, scope in (('ordinary', [f'ordinary:{y}' for y in DECISION_YEARS]), ('exceptional', ['exceptional:decision'])):
        rule = spec[group]
        for population in scope:
            for level in spec['levels']:
                nominal = level / 100
                value = summary[population][arm]['majorIntervals'][str(level)]['coverage']
                reference = summary[population]['free']['majorIntervals'][str(level)]['coverage']
                threshold = min(nominal - rule['nominalMargin'], reference - rule['alreadyUndercoveringMargin'])
                ok = bool(value >= threshold - 1e-12)
                passed = passed and ok
                rows[f'{population}:{level}'] = {'coverage': value, 'freeCoverage': reference, 'threshold': threshold, 'passed': ok}
    return {'passed': passed, 'rows': rows}


def select(results, head_to_head):
    qualified = [a for a in ('twogroup', 'twogroup_exc1') if results[a]['qualifies']]
    if len(qualified) == 2:
        return 'recommend_twogroup_for_james_signoff' if head_to_head['label'] == 'IMPROVES' else 'recommend_twogroup_exc1_for_james_signoff'
    if len(qualified) == 1:
        return f'recommend_{qualified[0]}_for_james_signoff'
    labels = {results[a]['label'] for a in ('twogroup', 'twogroup_exc1')}
    if 'IMPROVES' in labels:
        return 'floor_blocked_report_to_james'
    if labels == {'NEGLIGIBLE'}:
        return 'negligible_keep_single_scale'
    if labels == {'WORSE'}:
        return 'worse_keep_single_scale'
    return 'mixed_report_to_james'


def build():
    spec = design()
    rule, decision = spec['decision']['improves'], spec['decision']
    evaluation = read(PREFIX + '/evaluation.json')
    records = evaluation['records']
    summary = populations(records)
    indices, sizes = bootstrap_indices(records, decision['bootstrap'])
    interval = lambda x, y: bootstrap_interval(seat_deltas(records, x, y), indices, sizes, decision['bootstrap'])
    results = {}
    for arm in ('twogroup', 'twogroup_exc1', 'twogroup17'):
        c = compare(summary, arm, 'free', rule, records)
        label = classify(c, rule, doubling_passed(evaluation, arm))
        f = floors(summary, arm, decision['groupCoverageFloors'])
        results[arm] = {'versusFree': c, 'label': label, 'groupFloors': f, 'bootstrapDeltaCRPS90': interval(arm, 'free'),
                        'qualifies': arm != 'twogroup17' and label == 'IMPROVES' and f['passed'],
                        'versusControl': {'deltaMajorCRPSPP': summary['decisionSeats'][arm]['majorCRPSPP'] - summary['decisionSeats']['control']['majorCRPSPP'],
                                          'bootstrapDeltaCRPS90': interval(arm, 'control')}}
    h2h = compare(summary, 'twogroup', 'twogroup_exc1', rule, records)
    head = {'comparison': h2h, 'label': classify(h2h, rule, doubling_passed(evaluation, 'twogroup') and doubling_passed(evaluation, 'twogroup_exc1')),
            'bootstrapDeltaCRPS90': interval('twogroup', 'twogroup_exc1')}
    finding = select(results, head)
    sensitive = (results['twogroup']['versusFree']['deltaMajorCRPSPP'] < 0 <= results['twogroup17']['versusFree']['deltaMajorCRPSPP'])
    report17 = {pop: {a: {'majorCRPSPP': summary[pop][a]['majorCRPSPP'], 'seats': summary[pop][a]['seats'],
                          **{f'coverage{l}': summary[pop][a]['majorIntervals'][str(l)]['coverage'] for l in LEVELS},
                          **{f'width{l}PP': summary[pop][a]['majorIntervals'][str(l)]['widthPP'] for l in LEVELS}}
                      for a in ('control', 'free', 'twogroup17')}
                for pop in [f'{g}:{s}' for g in ('ordinary17', 'exceptional17') for s in ('decision', *map(str, DECISION_YEARS))]}
    return {'stage': 67, 'decisionNumber': spec.get('decisionNumber'), 'finding': finding,
            'flagSelectionSensitive': bool(sensitive), 'candidates': results, 'twogroupVersusExc1': head,
            'twogroup17GroupReport': report17, 'summary': summary,
            'maximumDrawGapAcrossArms': evaluation['maximumDrawGapAcrossArms'],
            'leak': spec['descriptive']['leak'], 'operationalAdoption': None}


def main():
    args = arguments()
    verify()
    save('decision.json', build(), args.check)
    print('Stage67 decision ' + ('reproduced' if args.check else 'written'))


if __name__ == '__main__':
    main()
