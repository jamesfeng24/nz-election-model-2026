"""Official Maori-seat results as carry-forward inputs: transitions, party-label matching, contrasts and entrant pools."""
import math
from collections import Counter
from scripts.maori_seat_fallback.common import read, RESULTS, SEATS, ESTABLISHED_DEFAULT

TRANSITIONS = ((2014, 2017), (2017, 2020), (2020, 2023))
PREVIOUS = {b: a for a, b in TRANSITIONS}


def prev_year(year):
    return PREVIOUS[year]


def results():
    """{year: {seat: {'candidates': [...], 'winner': name}}} with integer years."""
    return {int(y): seats for y, seats in read(RESULTS)['years'].items()}


def codes(cands):
    return Counter(c['party'] for c in cands)


def build_inputs(prev, new, established=ESTABLISHED_DEFAULT, split=None):
    """Carry-forward structure for one seat.

    prev: previous election's candidates (name, party, share). new: this election's slate (name, party).
    A candidate is matched when its code is established and exactly one candidate has that code in each election.
    split: {'name', 'fromCode'} marks one new candidate whose baseline is a fraction phi of the fromCode baseline, taken
    from the matched fromCode candidate, which keeps the remaining 1 - phi.
    """
    pc, nc = codes(prev), codes(new)
    prev_share = {c['party']: c['share'] for c in prev if pc[c['party']] == 1}
    out = {'names': [c['name'] for c in new], 'codes': [c['party'] for c in new], 'base': [], 'entrant': [], 'mp': [], 'split': None}
    for i, c in enumerate(new):
        matched = c['party'] in established and pc[c['party']] == 1 and nc[c['party']] == 1
        out['base'].append(math.log(prev_share[c['party']]) if matched else None)
        out['entrant'].append(None if matched else ('established' if c['party'] in established else 'other'))
        out['mp'].append(bool(matched and c['party'] == 'MP'))
    if split is not None:
        j = out['names'].index(split['name'])
        src = [i for i, c in enumerate(new) if c['party'] == split['fromCode']]
        if len(src) != 1 or out['base'][src[0]] is None or out['base'][j] is not None:
            raise ValueError('Split incumbent needs one matched %s candidate and an unmatched split candidate' % split['fromCode'])
        out['split'] = {'toIndex': j, 'fromIndex': src[0], 'prevLog': out['base'][src[0]]}
        out['entrant'][j] = None
    return out


def prev_log_odds(prev):
    """log(MP share / LAB share) of the previous election, or None unless exactly one MP and one LAB candidate."""
    pc = codes(prev)
    if pc['MP'] != 1 or pc['LAB'] != 1:
        return None
    s = {c['party']: c['share'] for c in prev}
    return math.log(s['MP'] / s['LAB'])


def contrast_rows(res=None):
    """One row per (transition, seat) with exactly one MP and one LAB candidate in both elections: D and the cell's identifiers."""
    res = res or results()
    rows = []
    for a, b in TRANSITIONS:
        for seat in SEATS:
            old, new = res[a][seat]['candidates'], res[b][seat]['candidates']
            lo, ln = prev_log_odds(old), prev_log_odds(new)
            if lo is None or ln is None:
                continue
            rows.append({'year': b, 'seat': seat, 'contrastD': ln - lo})
    return rows


def groups_for(rows, years):
    out = {}
    for r in rows:
        if r['year'] in years:
            out.setdefault(r['year'], []).append(r['contrastD'])
    return out


def entrant_pools(years, res=None):
    """Realised closed shares of entrants in the given target years, in two pools. Sorted, so the pool is order-free."""
    res = res or results()
    pools = {'established': [], 'other': []}
    for a, b in TRANSITIONS:
        if b not in years:
            continue
        for seat in SEATS:
            inp = build_inputs(res[a][seat]['candidates'], res[b][seat]['candidates'])
            for cls, c in zip(inp['entrant'], res[b][seat]['candidates']):
                if cls is not None:
                    pools[cls].append(c['share'])
    return {k: sorted(v) for k, v in pools.items()}


def other_contrast_ratio(years, s2, res=None):
    """Second moment of log-odds errors against Labour for matched candidates outside the MP and LAB groups, against 2 sigma^2."""
    res = res or results()
    errs = []
    for a, b in TRANSITIONS:
        if b not in years:
            continue
        for seat in SEATS:
            old, new = res[a][seat]['candidates'], res[b][seat]['candidates']
            inp = build_inputs(old, new)
            if 'LAB' not in inp['codes'] or inp['base'][inp['codes'].index('LAB')] is None:
                continue
            lab = inp['codes'].index('LAB')
            for i, c in enumerate(new):
                if inp['base'][i] is not None and c['party'] not in ('MP', 'LAB'):
                    errs.append((math.log(c['share'] / new[lab]['share']) - (inp['base'][i] - inp['base'][lab])))
    rms2 = sum(e * e for e in errs) / len(errs) if errs else None
    return {'count': len(errs), 'meanError': (sum(errs) / len(errs)) if errs else None, 'rms2': rms2,
            'ratioTo2Sigma2': (rms2 / (2 * s2)) if errs and s2 > 0 else None}
