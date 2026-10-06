"""Official Maori electorate candidate results 2014-2023, read from the preserved Electoral Commission files."""
import argparse
import csv
import io
from scripts.maori_seat_layer.common import ROOT, SEATS, YEARS, PARTY_CODES, fold, save, digest

FILES = {2014: ('2014/e9/csv/e9_part8_cand_{n}.csv', range(65, 72)),
         2017: ('2017/statistics/csv/candidate-votes-by-voting-place-{n}.csv', range(65, 72)),
         2020: ('2020/statistics/csv/candidate-votes-by-voting-place-{n}.csv', range(66, 73)),
         2023: ('2023/statistics/csv/candidate-votes-by-voting-place-{n}.csv', range(66, 73))}
MARKER = 'Electorate Candidate Valid Votes'


def parse(path, year):
    text = (ROOT / 'data/raw/elections' / path).read_text(encoding='utf-8-sig')
    rows = list(csv.reader(io.StringIO(text)))
    seat = rows[1][0].rsplit(' ', 1)[0]
    start = next(i for i, r in enumerate(rows) if r and r[0] == MARKER)
    candidates = []
    for r in rows[start + 1:]:
        if len(r) < 3 or not r[0]:
            break
        candidates.append({'name': r[0], 'partyLabel': r[1], 'party': PARTY_CODES.get(r[1], 'OTH'), 'votes': int(r[2])})
    total = sum(c['votes'] for c in candidates)
    for c in candidates:
        c['share'] = c['votes'] / total
    winner = max(candidates, key=lambda c: c['votes'])
    return seat, {'validCandidateVotes': total, 'winner': winner['name'], 'candidates': candidates}


def build():
    out = {}
    for year in YEARS:
        pattern, numbers = FILES[year]
        for n in numbers:
            seat, record = parse(pattern.format(n=n), year)
            out.setdefault(str(year), {})[seat] = record
        if sorted(out[str(year)]) != sorted(SEATS):
            raise ValueError('Maori seat inventory mismatch in %d: %s' % (year, sorted(out[str(year)])))
    return {'schemaVersion': 1, 'source': 'Electoral Commission candidate votes by voting place (data/raw/elections), electorate summary block',
            'years': out}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    save('historical-results.json', build(), args.check)
    print('Stage66 historical Maori seat results ok' if args.check else 'wrote historical-results.json')


if __name__ == '__main__':
    main()
