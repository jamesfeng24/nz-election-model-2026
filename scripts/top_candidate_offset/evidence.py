"""D132 evidence: electorate-to-party vote ratios of third parties outside flagged seats and seat wins, 2017-2023.

python -m scripts.top_candidate_offset.evidence [--check]

A ratio is a candidate's share of the valid candidate votes over the same party's share of the valid party votes in the
same seat. Seats flagged exceptional in the Stage67 audit (a stand-in for two-tick campaigns, which are not recorded) and
seats where the party's candidate won are removed. Descriptive only: nothing here is fitted, scored or adopted; the
-0.35 offset is James's judgement (D132).
"""
import argparse
import collections
import json
import math
import statistics
from pathlib import Path
from scripts.balance_scale.common import equivalent

ROOT = Path(__file__).resolve().parents[2]
HISTORY = 'data/processed/historical/2008-2023/'
FLAGS = 'data/processed/exceptional-balance-scale/design-contract.json'
OUTPUT = 'data/processed/top-candidate-offset/evidence.json'
KEYS = {'NZF': 'newzealandfirstparty', 'ACT': 'actnewzealand', 'GRN': 'greenparty', 'TOP': 'theopportunitiespartytop'}
BINS = ((0, .04), (.04, .07), (.07, .10), (.10, 1))


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def records(party, candidates, party_votes, names, flags, totals, years):
    out = []
    for r in candidates:
        if r['partyKey'] != KEYS[party] or r['year'] not in years:
            continue
        seat = r['electorateId']
        candidate_total, party_total = totals
        if not (candidate_total[seat] and party_total[seat]):
            continue
        share = party_votes.get((seat, KEYS[party]), 0) / party_total[seat]
        if share <= 0 or names[seat] in flags.get(str(r['year']), []) or r.get('elected'):
            continue
        out.append((r['year'], names[seat], r['votes'] / candidate_total[seat], share))
    return out


def summary(rows):
    if not rows:
        return None
    return {'n': len(rows), 'ratioOfSums': round(sum(c for *_, c, p in rows) / sum(p for *_, c, p in rows), 4),
            'medianRatio': round(statistics.median(c / p for *_, c, p in rows), 4),
            'meanPartySharePct': round(100 * statistics.mean(p for *_, c, p in rows), 2)}


def slope(rows_by_party):
    """Slope of the change in log candidate share on the change in log party share, same seat and party, three years apart."""
    index = {(nm, y): (c, p) for y, nm, c, p in rows_by_party}
    xs, ys = [], []
    for (nm, y), (c, p) in index.items():
        before = index.get((nm, y - 3))
        if before:
            xs.append(math.log(p / before[1]))
            ys.append(math.log(c / before[0]))
    if len(xs) < 4:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    return {'n': len(xs), 'slope': round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs), 4),
            'meanLogPartyChange': round(mx, 4), 'meanLogCandidateChange': round(my, 4)}


def build():
    candidates = read(HISTORY + 'candidate-votes.json')['records']
    parties = read(HISTORY + 'party-votes.json')['records']
    names = {r['id']: r.get('name') for r in read(HISTORY + 'electorates.json')['records']}
    flags = read(FLAGS)['flags']['primary']
    candidate_total, party_total = collections.defaultdict(int), collections.defaultdict(int)
    for r in candidates:
        candidate_total[r['electorateId']] += r['votes']
    for r in parties:
        party_total[r['electorateId']] += r['votes']
    party_votes = {(r['electorateId'], r['partyKey']): r['votes'] for r in parties}
    out = {}
    for party in KEYS:
        rows = records(party, candidates, party_votes, names, flags, (candidate_total, party_total), (2017, 2020, 2023))
        wider = records(party, candidates, party_votes, names, flags, (candidate_total, party_total), (2014, 2017, 2020, 2023))
        out[party] = {'all': summary(rows), 'byPartyShare': {f'{int(lo * 100)}-{int(hi * 100)}%': summary([x for x in rows if lo <= x[3] < hi])
                                                           for lo, hi in BINS},
                      'byYear': {str(y): summary([x for x in rows if x[0] == y]) for y in (2017, 2020, 2023)},
                      'changeBetweenElections': slope(wider)}
    return {'stage': 'D132', 'label': 'DESCRIPTIVE evidence for the TOP candidate-weight offset; nothing fitted or scored',
            'definition': 'candidate share of candidate votes divided by the same party\'s share of party votes in the seat; flagged seats (Stage67 audit) and seats the party\'s candidate won are removed',
            'years': [2017, 2020, 2023], 'parties': out}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    value = build()
    if parser.parse_args().check:
        if not equivalent(read(OUTPUT), value, 1e-9):
            raise SystemExit('Stale ' + OUTPUT)
        print('D132 evidence reproduced')
        return
    (ROOT / OUTPUT).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    print('D132 evidence written')


if __name__ == '__main__':
    main()
