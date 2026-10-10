"""Apply the frozen Stage83 rule (design plus amendment 1); thresholds and arms live in design-contract.json."""
import numpy as np
from .common import PREFIX, YEARS, DECISION_YEARS, LEVELS, ARMS, read, save, verify, arguments, design, arms

MATCHING17 = {'within': 'within17', 'within_mass': 'within_mass17', 'within_robust': 'within_robust17',
              'within_mass_robust': 'within_mass_robust17'}
MOMENT, ROBUST = ('within', 'within_mass'), ('within_robust', 'within_mass_robust')


def paired(records, arm, years):
    """(control, arm) record pairs for the seats the arm narrows (its own ordinary population) in `years`."""
    if [r['id'] for r in records[arm]] != [r['id'] for r in records['control']]:
        raise ValueError('Unequal paired Stage83 records')
    return [(c, a) for c, a in zip(records['control'], records[arm]) if a['narrowed'] and a['year'] in years]


def group_stats(side, group):
    recs = [p['groups'][group] for p in side if group in p['groups']]
    if not recs:
        return None
    flat = lambda key: [v for r in recs for v in r[key]]
    out = {'seats': len(recs), 'candidates': len(flat('covered80')), 'crpsPP': float(np.mean([r['crpsPP'] for r in recs])),
           'coverage80Prefix': float(np.mean(flat('covered80Prefix')))}
    out['intervalScorePP80'] = float(np.mean(flat('score80')))
    for level in LEVELS:
        out[f'coverage{level}'] = float(np.mean(flat(f'covered{level}')))
        out[f'widthPP{level}'] = float(np.mean(flat(f'width{level}')))
    return out


def ranking_stats(side):
    unique = [p['ranking'] for p in side if p['ranking']['uniqueWinner']]
    return {'seats': len(side), 'uniqueWinnerSeats': len(unique),
            'meanActualWinnerProbability': float(np.mean([r['actualWinnerProbability'] for r in unique])) if unique else None,
            'actualMinorWins': int(sum(r['actualWinnerIsMinor'] for r in unique)),
            'predictedMinorWinMass': float(sum(p['ranking']['minorWinMass'] for p in side)),
            'predictedMinorWinMassOnUniqueWinnerSeats': float(sum(r['minorWinMass'] for r in unique)),
            'meanLogLossFloorOne10000': float(np.mean([-np.log(max(r['actualWinnerProbability'], 1e-4)) for r in unique])) if unique else None}


def mass_stats(side):
    recs = [p['mass'] for p in side if 'mass' in p]
    return {'seats': len(recs), 'crpsPP': float(np.mean([r['crpsPP'] for r in recs])),
            **{f'coverage{l}': float(np.mean([r[f'covered{l}'] for r in recs])) for l in LEVELS}} if recs else None


def population(pairs):
    out = {'seats': len(pairs)}
    for label, index in (('control', 0), ('arm', 1)):
        side = [p[index] for p in pairs]
        out[label] = {**{g: group_stats(side, g) for g in ('national', 'labour', 'other', 'no_group')},
                      'mass': mass_stats(side), 'ranking': ranking_stats(side)}
    return out


def relative(arm, control):
    return float((arm - control) / control)


def minor_crps(pairs):
    values = [(c['groups']['other']['crpsPP'], a['groups']['other']['crpsPP']) for c, a in pairs if 'other' in c['groups']]
    return (float(np.mean([v[0] for v in values])), float(np.mean([v[1] for v in values]))) if values else (None, None)


def major_crps(side):
    return float(np.mean([np.mean([p['groups'][g]['crpsPP'] for g in ('national', 'labour') if g in p['groups']]) for p in side]))


def bootstrap(records, arm, spec):
    """Seats resampled with replacement within election; pooled equal-seat mean of the paired minor CRPS difference."""
    rng = np.random.default_rng(spec['seed'])
    deltas = {y: np.array([a['groups']['other']['crpsPP'] - c['groups']['other']['crpsPP']
                           for c, a in paired(records, arm, (y,)) if 'other' in c['groups']]) for y in DECISION_YEARS}
    sizes = [len(v) for v in deltas.values()]
    stat = np.empty(spec['draws'])
    for i in range(spec['draws']):
        stat[i] = np.concatenate([v[rng.integers(0, len(v), len(v))] for v in deltas.values()]).mean()
    lo, hi = np.quantile(stat, [(1 - spec['level']) / 2, 1 - (1 - spec['level']) / 2])
    return {'seatsByElection': sizes, 'pointDeltaCRPSPP': float(np.concatenate(list(deltas.values())).mean()),
            f'lower{int(spec["level"] * 100)}': float(lo), f'upper{int(spec["level"] * 100)}': float(hi)}


def judge(records, arm, rule, identity):
    """The frozen qualification checks for one arm on its own ordinary population over the decision years."""
    kind, estimator, uses_mass = ARMS[arm]
    pairs = paired(records, arm, DECISION_YEARS)
    pop = population(pairs)
    arm_minor, control_minor = pop['arm']['other'], pop['control']['other']
    c_crps, a_crps = minor_crps(pairs)
    change = relative(a_crps, c_crps)
    by_year = {}
    for y in DECISION_YEARS:
        cy, ay = minor_crps(paired(records, arm, (y,)))
        by_year[str(y)] = {'controlCRPSPP': cy, 'armCRPSPP': ay, 'relativeChange': relative(ay, cy)}
    band = rule['minorCoverage80']['band']
    nearer = abs(arm_minor['coverage80'] - 0.8) < abs(control_minor['coverage80'] - 0.8)
    guard = rule['majorGuard']
    major = {}
    for g in ('national', 'labour'):
        a80, c80 = pop['arm'][g]['coverage80'], pop['control'][g]['coverage80']
        major[g] = {'coverage80': a80, 'controlCoverage80': c80,
                    'passed': bool(a80 >= guard['coverage80FloorAbsolute'] and c80 - a80 <= guard['coverage80MaxDropFromControl'] + 1e-12)}
    major_change = relative(major_crps([a for _, a in pairs]), major_crps([c for c, _ in pairs]))
    checks = {
        'minorCoverage80InBand': bool(band[0] <= arm_minor['coverage80'] <= band[1]),
        'minorCoverage80NearerNominal': bool(nearer),
        'minorCoverage90AtLeastFloor': bool(arm_minor['coverage90'] >= rule['minorCoverage90Floor']),
        'minorCRPSPooledChangeAtMost': bool(change <= rule['minorCRPS']['pooledRelativeChangeAtMost'] + 1e-12),
        'minorCRPSNegativeFolds': bool(sum(v['relativeChange'] < 0 for v in by_year.values()) >= rule['minorCRPS']['minimumFoldsNegative']),
        'majorGuardCoverage': all(v['passed'] for v in major.values()),
        'majorGuardCRPS': bool(major_change <= guard['pooledCRPSRelativeChangeAtMost'] + 1e-12),
        'flaggedSeatsIdenticalToControl': bool(identity[arm] <= 1e-12),
        'precisionPrefixCoverage80': bool(abs(arm_minor['coverage80Prefix'] - arm_minor['coverage80']) <= rule['precision_tolerance'])}
    if uses_mass:
        mb = rule['massCoverage80Band']['band']
        checks['massCoverage80InBand'] = bool(mb[0] <= pop['arm']['mass']['coverage80'] <= mb[1])
    return {'arm': arm, 'kind': kind, 'estimator': estimator, 'usesMass': uses_mass, 'seats': pop['seats'],
            'minorCRPSPP': {'control': c_crps, 'arm': a_crps, 'pooledRelativeChange': change, 'byElection': by_year},
            'majorGuard': {'byCandidate': major, 'pooledCRPSRelativeChange': major_change},
            'checks': checks, 'passedAllChecksExceptSensitivity17': all(checks.values()), 'population': pop}


def sensitivity(results, arm):
    other = results[MATCHING17[arm]]
    pop = other['population']
    ok = other['minorCRPSPP']['pooledRelativeChange'] < 0 and \
        abs(pop['arm']['other']['coverage80'] - 0.8) < abs(pop['control']['other']['coverage80'] - 0.8)
    return {'matching': MATCHING17[arm], 'pooledMinorCRPSRelativeChange': other['minorCRPSPP']['pooledRelativeChange'],
            'minorCoverage80': pop['arm']['other']['coverage80'], 'controlMinorCoverage80': pop['control']['other']['coverage80'],
            'passed': bool(ok)}


def choose(results, group):
    qualified = [a for a in group if results[a]['qualifies']]
    if len(qualified) == 2:
        mass, plain = group[1], group[0]
        gain = relative(results[mass]['minorCRPSPP']['arm'], results[plain]['minorCRPSPP']['arm'])
        return mass if gain <= -0.01 else plain
    return qualified[0] if qualified else None


def build():
    spec = design()
    rule = spec['decision']['qualifies']
    rule = {**rule, 'precision_tolerance': 0.005, 'minorCoverage80': rule['minorCoverage80']}
    evaluation = read(PREFIX + '/evaluation.json')
    records = evaluation['records']
    identity = evaluation['flaggedSeatMaximumAbsoluteDifferenceFromControl']
    results = {a: judge(records, a, rule, identity) for a in arms() if a != 'control'}
    for arm in spec['decision']['candidateArms']:
        results[arm]['sensitivity17'] = sensitivity(results, arm)
        results[arm]['qualifies'] = bool(results[arm]['passedAllChecksExceptSensitivity17'] and results[arm]['sensitivity17']['passed'])
    for arm in results:
        results[arm].setdefault('qualifies', None)
    step = None
    chosen = choose(results, MOMENT)
    if chosen:
        step = 'moment'
    else:
        chosen = choose(results, ROBUST)
        step = 'robust' if chosen else None
    if chosen:
        finding = f'recommend_{chosen}_for_james_signoff'
    else:
        changes = [results[a]['minorCRPSPP']['pooledRelativeChange'] for a in spec['decision']['candidateArms']]
        # robust arms were added by amendment 1; the label uses every registered candidate arm
        changes += [results[a]['minorCRPSPP']['pooledRelativeChange'] for a in ROBUST if a not in spec['decision']['candidateArms']]
        if all(v > 0 for v in changes):
            finding = 'keep_control_worse'
        elif all(abs(v) < 0.01 for v in changes):
            finding = 'keep_control_negligible'
        else:
            finding = 'keep_control_mixed'
    reports = {}
    for label, years in (('decision', DECISION_YEARS), *[(str(y), (y,)) for y in YEARS]):
        reports[label] = {a: population(paired(records, a, years)) for a in arms() if a != 'control' and paired(records, a, years)}
    boot = {a: bootstrap(records, a, spec['decision']['bootstrap']) for a in spec['decision']['candidateArms'] +
            [x for x in ROBUST if x not in spec['decision']['candidateArms']]}
    return {'stage': 83, 'decisionNumber': spec.get('decisionNumber'), 'finding': finding, 'selectedStep': step, 'selectedArm': chosen,
            'candidates': results, 'bootstrapMinorCRPS90': boot, 'populationsByElection': reports,
            'flaggedSeatMaximumAbsoluteDifferenceFromControl': identity, 'leak': spec['descriptive']['leak'],
            'operationalAdoption': None}


def main():
    args = arguments()
    verify()
    save('decision.json', build(), args.check, tolerance=1e-9)
    print('Stage83 decision ' + ('reproduced' if args.check else 'written'))


if __name__ == '__main__':
    main()
