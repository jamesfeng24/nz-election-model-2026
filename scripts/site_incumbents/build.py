"""Stage84 public-site incumbents: which 2026 candidate is the sitting MP for the seat.

A candidate is marked the incumbent when the preserved official current-MP index (New Zealand Parliament, listed on
2026-09-23) shows the same person as an electorate MP for the seat that supplies most of the 2026 seat's population
(the seat itself, or its largest predecessor where the boundaries moved). List MPs and electorate MPs who stand in a
different seat are not marked: the site says "incumbent" only where a voter would. MPs for an electorate who match no
candidate in the successor seat are reported in `unmatchedElectorateMps` for review, never guessed.

    python3 -m scripts.site_incumbents.build
    python3 -m scripts.site_incumbents.build --check
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MPS = ROOT / 'data/raw/identity-parliament-current.html'
NOMINATIONS = ROOT / 'data/processed/nominations-2026/2026-10-10/features-raw.json'
OUT = ROOT / 'data/processed/site-incumbents/2026-10-10/incumbents.json'
SOURCE = {'label': 'New Zealand Parliament, current MPs', 'url': 'https://www3.parliament.nz/en/mps-and-electorates/members-of-parliament/', 'asOf': '2026-09-23'}


def fold(text: str) -> str:
    """Lower case, no macrons, letters and single spaces only."""
    text = unicodedata.normalize('NFD', html.unescape(text)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]+', ' ', text).strip()


def current_electorate_mps() -> list[dict]:
    """Every MP the index lists with an electorate (not 'List'): name as 'Given Surname' parts, party, electorate."""
    text = MPS.read_text(encoding='utf-8', errors='ignore')
    out = []
    for row in re.findall(r'<tr class="list__row[^"]*">(.*?)</tr>', text, flags=re.S):
        name = re.search(r'class="list__cell-heading theme__link" title="([^"]+)"', row)
        cells = [html.unescape(c).strip() for c in re.findall(r'<div class="list__cell-text">\s*(.*?)\s*</div>', row, flags=re.S)]
        if not name or len(cells) != 2 or cells[1] == 'List':
            continue
        surname, _, given = html.unescape(name.group(1)).partition(',')
        out.append({'name': f'{given.strip()} {surname.strip()}'.strip(), 'surname': fold(surname), 'given': fold(given), 'party': cells[0], 'electorate': cells[1]})
    return out


def same_person(mp: dict, candidate_name: str) -> bool:
    """Same surname and a compatible first name (equal, or one a prefix of the other: Chris / Christopher)."""
    words = candidate_name.split()
    upper = [w for w in words if w.isupper() and len(w) > 1]                 # the nomination lists the surname in capitals
    surname = fold(' '.join(upper)) if upper else fold(words[-1]) if words else ''
    given = fold(' '.join(w for w in words if w not in upper))
    first, mp_first = (given.split() or [''])[0], (mp['given'].split() or [''])[0]
    if surname != mp['surname'] or not first or not mp_first:
        return False
    return first == mp_first or (min(len(first), len(mp_first)) >= 3 and (first.startswith(mp_first) or mp_first.startswith(first)))


def build() -> dict:
    mps = current_electorate_mps()
    nominations = json.loads(NOMINATIONS.read_text(encoding='utf-8'))
    seats = {s['targetElectorateId']: s for s in nominations['seatRecords']}
    incumbents, matched = [], set()
    for record in nominations['candidateRecords']:
        seat = seats[record['targetElectorateId']]
        geo = seat['geography']
        preds = geo.get('predecessors') or []
        if not preds:                                                          # a seat with no predecessor has no incumbent
            continue
        source = max(preds, key=lambda p: p['jointPopulationEdgeBounds'][0])['sourceName']
        for mp in mps:
            if fold(mp['electorate']) == fold(source) and same_person(mp, record['displayedName']):
                matched.add(mp['name'])
                incumbents.append({'targetElectorateId': record['targetElectorateId'], 'targetOccurrenceId': record['targetOccurrenceId'],
                                   'candidateName': record['displayedName'], 'seat': seat['officialName'], 'mp': mp['name'], 'party': mp['party'],
                                   'mpElectorate': source, 'sameSeat': fold(source) == fold(seat['officialName'])})
    incumbents.sort(key=lambda r: (r['targetElectorateId'], r['targetOccurrenceId']))
    unmatched = sorted(({'mp': mp['name'], 'party': mp['party'], 'electorate': mp['electorate']} for mp in mps if mp['name'] not in matched), key=lambda r: r['electorate'])
    return {'schemaVersion': 1, 'source': SOURCE, 'rule': "Electorate MP in the current-MP index whose current electorate is the largest predecessor of the 2026 seat (by population), standing there under the same name",
            'incumbents': incumbents, 'unmatchedElectorateMps': unmatched,
            'inputs': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (MPS, NOMINATIONS)}}


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + '\n'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    data = build()
    text = render(data)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            print(f'MISMATCH: {OUT.relative_to(ROOT)} differs from a fresh derivation', file=sys.stderr)
            return 1
        print(f'ok: {OUT.relative_to(ROOT)} reproduced')
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['incumbents'])} incumbents, {len(data['unmatchedElectorateMps'])} electorate MPs not matched")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
