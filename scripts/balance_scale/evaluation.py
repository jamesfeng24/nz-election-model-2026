"""Score the three restrictions on identical common-stream records; no adoption."""
import numpy as np
from scripts.uncertainty.construction import scale_for
from .common import PREFIX, INVENTORY, SCALES, RESTRICTIONS, read, save, verify, arguments, design
from .data import YEARS
from .simulate import component_seat, composed_seat, national_inputs
from .summary import by_population


def representative_ids(rows):
    return [rows[i]['targetElectorateId'] for i in sorted({0, len(rows) // 2, len(rows) - 1})]


def multipliers_for(fits, year):
    fold = fits['folds'][str(year)]
    index = {s: i for i, s in enumerate(fold['seatIds'])}
    return lambda cid: {r: fold['multipliers'][r][index[cid]] for r in RESTRICTIONS}


def components(inventory, scales, fits, spec):
    records = {r: [] for r in RESTRICTIONS}
    representatives, gaps = [], []
    for year in YEARS:
        rows = sorted([r for r in inventory['candidateRecords'] if r['targetYear'] == year], key=lambda r: r['targetElectorateId'])
        fit = scale_for(scales, 'candidate', year)['scales']
        mult = multipliers_for(fits, year)
        rep = set(representative_ids(rows))
        for row in rows:
            cid = row['targetElectorateId']
            found, gap = component_seat(row, fit, mult(cid), spec['components']['draws'], spec['decision']['resolutionPrefixDraws'],
                                        spec['components']['doubling'] if cid in rep else None)
            for r in RESTRICTIONS:
                records[r].append(found[r])
            gaps.append({'id': cid, **{r: v for r, v in gap.items()}})
        print('Stage48 component', year, len(rows), flush=True)
    return records, gaps


def composed(inventory, scales, fits, spec):
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    records = {r: [] for r in RESTRICTIONS}
    checks, representatives = [], []
    frame, caps = spec['composed']['draws'], spec['composed']['representativeDraws']
    for year in design()['decisionYears']:
        rows = sorted([r for r in inventory['candidateRecords'] if r['targetYear'] == year], key=lambda r: r['targetElectorateId'])
        pfit = scale_for(scales, 'local_party', year)['scales']
        fit = scale_for(scales, 'candidate', year)['scales']
        mult = multipliers_for(fits, year)
        first = parties[rows[0]['targetElectorateId']]
        national = national_inputs(year, first, frame)
        rep = representative_ids(rows)
        edge = {rows[0]['targetElectorateId'], rows[-1]['targetElectorateId']}
        for row in rows:
            cid = row['targetElectorateId']
            found, check = composed_seat(row, parties[cid], national, pfit, fit, mult(cid), frame, None, cid in edge)
            for r in RESTRICTIONS:
                records[r].append(found[r])
            checks.append({'id': cid, **check})
        big = national_inputs(year, first, max(caps))
        for cid in rep:
            row = next(x for x in rows if x['targetElectorateId'] == cid)
            found, _ = composed_seat(row, parties[cid], big, pfit, fit, mult(cid), len(big), caps)
            representatives.append({'id': cid, 'year': year, **{r: found[r]['doubling'] for r in RESTRICTIONS}})
        print('Stage48 composed', year, len(rows), flush=True)
    return records, checks, representatives


def doubling(entries, counts, gates, restrictions=RESTRICTIONS):
    """Maximum change between consecutive counts across representative seats and candidates."""
    mapping = {'means': 'mean', 'crps': 'crps', 'energy': 'energy', 'width50': 'width50', 'width80': 'width80', 'width90': 'width90'}
    result = {}
    for r in restrictions:
        rounds = []
        for earlier, later in zip(counts[:-1], counts[1:]):
            change = {}
            for field, gate in mapping.items():
                values = []
                for e in entries:
                    a = np.atleast_1d(e[r][str(later)]['meansPP' if field == 'means' else field])
                    b = np.atleast_1d(e[r][str(earlier)]['meansPP' if field == 'means' else field])
                    values.append(float(np.max(np.abs(a - b))))
                change[gate] = max(values)
            rounds.append({'earlier': earlier, 'later': later, 'changesPP': change,
                           'passed': {k: change[k] <= gates[k] for k in change}, 'allPassed': all(change[k] <= gates[k] for k in change)})
        result[r] = rounds
    return result


def flatten(value):
    if isinstance(value, dict):
        return [x for k, v in value.items() if k != 'id' for x in flatten(v)]
    if isinstance(value, list):
        return [x for v in value for x in flatten(v)]
    return [float(value)] if isinstance(value, (int, float)) and not isinstance(value, bool) else []


def build():
    spec = design()
    inventory, scales, fits = read(INVENTORY), read(SCALES), read(PREFIX + '/fit.json')
    comp_records, comp_gaps = components(inventory, scales, fits, spec)
    comp_summary = by_population(comp_records)
    rep_entries = [{r: x['doubling'] for r, x in zip(RESTRICTIONS, (rec_c, rec_k, rec_f))}
                   for rec_c, rec_k, rec_f in zip(*[[x for x in comp_records[r] if 'doubling' in x] for r in RESTRICTIONS])]
    comp_precision = doubling(rep_entries, spec['components']['doubling'], spec['gatesPP'])
    cmp_records, cmp_checks, cmp_rep = composed(inventory, scales, fits, spec)
    cmp_summary = by_population(cmp_records)
    cmp_precision = doubling(cmp_rep, spec['composed']['representativeDraws'], spec['gatesPP'])
    strip = lambda recs: {r: [{k: v for k, v in x.items() if k != 'doubling'} for x in recs[r]] for r in RESTRICTIONS}
    return {'stage': 48, 'status': 'scored after the design freeze; no adoption',
            'component': {'draws': spec['components']['draws'], 'records': strip(comp_records), 'summary': comp_summary,
                          'drawGaps': comp_gaps,
                          'maximumDrawGapAcrossRestrictions': max(max(g[r]['otherMaxAbs'], g[r]['majorMassMaxAbs']) for g in comp_gaps for r in RESTRICTIONS[1:]),
                          'maximumFiniteMeanDeviationPP': {r: max(x['finiteMeanDeviationPP'] for x in comp_records[r]) for r in RESTRICTIONS},
                          'representativeDoubling': comp_precision},
            'composed': {'draws': spec['composed']['draws'], 'records': strip(cmp_records), 'summary': cmp_summary,
                         'equalityChecks': cmp_checks,
                         'maximumEqualityGap': max(flatten(cmp_checks)),
                         'representativeDoubling': cmp_precision,
                         'precisionNote': 'Stage47 composed precision gates are unmet for the control; no fine superiority claim.'}}


def main():
    args = arguments()
    verify()
    save('evaluation.json', build(), args.check)
    print('Stage48 scores complete' if not args.check else 'Stage48 scores reproduced')


if __name__ == '__main__':
    main()
