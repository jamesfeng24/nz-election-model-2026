"""Stage84 public-site evidence: the polls the forecast rests on, and the national model's weekly trend.

Reads the preserved weekly-refresh outputs (panel, estimate, dataset) and the preserved seat-poll files, and writes one
deterministic JSON file that the release publisher embeds in the forecast snapshot (`--evidence`). Nothing is fitted and
no number is invented: poll figures are copied as published, missing values stay null, and a seat poll names its source
page only where a registry records its address.

    python3 -m scripts.site_evidence.build --refresh data/processed/polling/weekly-refresh/2026-10-07
    python3 -m scripts.site_evidence.build --refresh data/processed/polling/weekly-refresh/2026-10-07 --check
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / 'data' / 'processed' / 'site-evidence'
SCHEMA_VERSION = 1
ELECTION_2023 = '2023-10-15'

# Panel category codes to export party ids (config/nowcast-2026.json and the draw-bank directory).
PARTY_IDS = {'NAT': 'nationalparty', 'LAB': 'labourparty', 'GRN': 'greenparty', 'ACT': 'actnewzealand', 'NZF': 'newzealandfirstparty',
             'TPM': 'tepatimaori', 'MRI': 'tepatimaori', 'TOP': 'opportunity', 'OTH': 'other'}
POLL_ORDER = ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'MRI', 'TOP']
# Used only for a poll the Wikipedia table no longer carries (a collapsed duplicate); every other poll keeps the table's own label.
POLLSTER_NAMES = {'Verian lineage': 'Verian', 'Talbot Mills/UMR': 'Talbot Mills'}
WIKIPEDIA_TITLE = 'Opinion_polling_for_the_2026_New_Zealand_general_election'
SEAT_POLL_FILES = [
    ('data/processed/polling/electorate-polls-2026/polls.json', 'general-article'),
    ('data/source-plans/maori-seat-layer/polls-2026.json', 'maori-used'),
    ('data/processed/polling/maori-seat-polls-2026-10/polls.json', 'maori-not-adopted'),
]
CANDIDATE = re.compile(r'^(?P<name>.+?)\s*\((?P<party>[A-Za-z]+)\)$')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def registry_urls() -> dict[str, tuple[str | None, str | None]]:
    """raw path and source id to (url, organisation) from every dated source registry; `data/sources.json` is read only."""
    index: dict[str, tuple[str | None, str | None]] = {}
    files = sorted(glob.glob(str(ROOT / 'data/processed/**/source-registry*.json'), recursive=True))
    for file in files + [str(ROOT / 'data/sources.json')]:
        data = load(Path(file))
        for source in data['sources'] if isinstance(data, dict) else data:
            for key in (source.get('rawPath'), source.get('id')):
                if key and key not in index:
                    index[key] = (source.get('url'), source.get('organisation'))
    return index


def number(value) -> float | None:
    return None if value is None else float(value)


FAMILY = {'Verian lineage': 'Verian', 'Talbot Mills/UMR': 'Talbot Mills'}


def valid_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def midpoint(start: str, end: str) -> str:
    """The fieldwork midpoint the model's dataset uses; a start with no stated day falls back to the end date."""
    a, b = valid_date(start), valid_date(end)
    assert b is not None, f'fieldwork end {end!r} is not a date'
    return (a + (b - a) / 2).isoformat() if a is not None else b.isoformat()


def used_flags(panel: dict, dataset: dict) -> dict[str, bool]:
    """Which 2026-cycle panel records are in the model's dataset, matched by pollster family and fieldwork midpoint."""
    left = Counter((pid.split('|')[0], pid.split('|')[1]) for pid, mid in zip(dataset['poll_ids'], dataset['mid_dates']) if mid >= ELECTION_2023)
    flags = {}
    for r in panel['records']:
        if r['cycle'] != 2026:
            continue
        key = (FAMILY.get(r['pollster'], r['pollster']), midpoint(r['fieldworkRaw'][0], r['fieldworkRaw'][-1]))
        flags[r['id']] = left[key] > 0
        if flags[r['id']]:
            left[key] -= 1
    assert sum(left.values()) == 0, f'dataset polls with no panel record: {dict(+left)}'
    return flags


def wikipedia_labels(capture: dict) -> dict[str, str]:
    """Panel record id to the poll's name as the Wikipedia table prints it (for example "Taxpayers' Union–Curia"), from the preserved capture."""
    from scripts.polling.weekly_refresh.delta import wiki_rows
    path = ROOT / capture['rawPath']
    assert sha256(path) == capture['sha256'], 'the preserved Wikipedia capture does not match the fit\'s recorded hash'
    rows, unmapped = wiki_rows(path.read_text(encoding='utf-8'), 'site-evidence', capture['rawPath'], capture['sha256'])
    assert not unmapped, 'unmapped Wikipedia rows'
    return {r['id']: r['commissioner'].strip() for r in rows}


def national_polls(panel: dict, used: dict[str, bool], labels: dict[str, str]) -> list[dict]:
    out = []
    for r in panel['records']:
        if r['cycle'] != 2026:
            continue
        start, end = r['fieldworkRaw'][0], r['fieldworkRaw'][-1]
        start = start if valid_date(start) and start != end else None
        shares = []
        for code in POLL_ORDER:
            est = r['estimates'][code]
            reported = est['status'] != 'not_reported' and est.get('share') is not None
            shares.append({'partyId': PARTY_IDS[code], 'percent': round(100 * est['share'], 3) if reported else None,
                           'approximate': str(est.get('published', '')).startswith('~')})
        other = r.get('publishedOther') or {}
        shares.append({'partyId': 'other', 'percent': round(100 * other['share'], 3) if other.get('share') is not None else None,
                       'approximate': str(other.get('published', '')).startswith('~') and other.get('share') is not None})
        out.append({'id': r['id'], 'pollster': labels.get(r['id']) or POLLSTER_NAMES.get(r['pollster'], r['pollster']), 'commissioner': None,
                    'fieldworkStart': start, 'fieldworkEnd': end, 'sampleSize': r.get('sampleSize'),
                    'shares': shares, 'publisherUrl': None, 'usedInModel': used[r['id']],
                    'note': None if used[r['id']] else "Listed by Wikipedia but not in the model's data set"})
    out.sort(key=lambda p: (p['fieldworkEnd'], p['id']), reverse=True)
    return out


def trend(estimate: dict, dataset: dict) -> dict:
    path = estimate['pathWeekly']
    n = len(path['meanPP'])
    start = dataset['last_data_t'] - n + 1
    weeks = dataset['weeks'][start:start + n]
    assert len(weeks) == n and weeks[-1] == estimate['lastDataWeek'], 'path weeks do not end at the last data week'
    codes = estimate['codes']
    parties = []
    for i, code in enumerate(codes):
        parties.append({'partyId': PARTY_IDS[code], 'mean': [row[i] for row in path['meanPP']],
                        'lower90': [row[i] for row in path['q05PP']], 'upper90': [row[i] for row in path['q95PP']]})
    return {'basis': "The national model's weekly estimate of true support, from the 2023 election result to the week of the last poll data. "
                     'It is built from the polls and is not an average of them. The band is the 90% range.',
            'weeks': weeks, 'parties': parties}


def candidate_results(poll: dict, kind: str) -> list[dict]:
    if kind == 'general-article':
        results = []
        for label, percent in poll['candidateVotePct'].items():
            m = CANDIDATE.match(label)
            results.append({'name': m['name'] if m else label, 'party': m['party'] if m else None, 'percent': percent})
        return sorted(results, key=lambda r: -r['percent'])
    return [{'name': c['name'], 'party': c['party'], 'percent': c['pollPercent']} for c in poll['candidates']]


def seat_polls(urls: dict) -> list[dict]:
    out = []
    for file, kind in SEAT_POLL_FILES:
        for poll in load(ROOT / file)['polls']:
            if kind == 'general-article':
                seat, fw, published = poll['electorate'], poll.get('fieldwork'), None
                if not fw:
                    reported = re.search(r'reported (\d{4}-\d{2}-\d{2})', poll.get('fieldworkNote') or '')
                    assert reported, f"{seat}: a poll with no fieldwork dates needs a stated publication date"
                    published = reported.group(1)
                sources = [{'label': urls.get(s, (None, s))[1] or s, 'url': urls.get(s, (None, None))[0]} for s in poll['sources']]
                moe, commissioner = poll.get('marginOfError'), poll.get('commissioner')
                note = '; '.join(filter(None, [poll.get('fieldworkNote'), poll.get('candidateVoteUndecidedTreatment')]))
                used = False
            else:
                seat, fw, published = poll['seat'], [poll['fieldworkStart'], poll['fieldworkEnd']], poll.get('published')
                sources = [{'label': urls.get(s, (None, s))[1] or s, 'url': urls.get(s, (None, None))[0]} for s in poll['sourceFiles']]
                moe, commissioner = poll.get('marginOfErrorPercent'), None
                note = poll.get('notes') or ''
                used = kind == 'maori-used'
            out.append({'electorateName': seat, 'pollster': poll['pollster'], 'commissioner': commissioner,
                        'fieldworkStart': fw[0] if fw else None, 'fieldworkEnd': fw[-1] if fw else None, 'published': published,
                        'sampleSize': poll.get('sampleSize'), 'marginOfError': moe, 'results': candidate_results(poll, kind),
                        'usedInModel': used, 'note': note or None, 'sources': sources})
    out.sort(key=lambda p: (p['electorateName'], p['fieldworkEnd'] or ''))
    return out


def build(refresh_dir: Path) -> dict:
    panel, estimate, dataset = (load(refresh_dir / f) for f in ('panel.json', 'estimate.json', 'dataset.json'))
    capture = estimate['capture']
    inputs = {rel(refresh_dir / f): sha256(refresh_dir / f) for f in ('panel.json', 'estimate.json', 'dataset.json')}
    for file, _ in SEAT_POLL_FILES:
        inputs[file] = sha256(ROOT / file)
    used = used_flags(panel, dataset)
    polls = national_polls(panel, used, wikipedia_labels(capture))
    inputs[capture['rawPath']] = capture['sha256']
    assert sum(p['usedInModel'] for p in polls) == estimate['polls2026'], 'the polls marked used are not the polls the fit used'
    return {
        'schemaVersion': SCHEMA_VERSION, 'refreshDate': panel['refreshDate'], 'dataCutoff': estimate['dataCutoff'],
        'modelStateAsOf': estimate['modelStateAsOf'],
        'source': {'label': 'Wikipedia, Opinion polling for the 2026 New Zealand general election (volunteer-edited aggregator; text CC BY-SA)',
                   'url': f"https://en.wikipedia.org/w/index.php?title={WIKIPEDIA_TITLE}&oldid={capture['revision']}",
                   'revision': str(capture['revision']), 'retrieved': capture['lastModified']},
        'nationalPolls': polls, 'trend': trend(estimate, dataset), 'seatPolls': seat_polls(registry_urls()), 'inputs': inputs,
    }


def render(evidence: dict) -> str:
    return json.dumps(evidence, ensure_ascii=False, indent=1, sort_keys=True) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--refresh', required=True, help='a weekly-refresh directory, for example data/processed/polling/weekly-refresh/2026-10-07')
    parser.add_argument('--check', action='store_true', help='re-derive and compare with the saved file instead of writing')
    args = parser.parse_args(argv)
    refresh = (ROOT / args.refresh).resolve()
    evidence = build(refresh)
    target = OUT_DIR / evidence['refreshDate'] / 'evidence.json'
    text = render(evidence)
    if args.check:
        if not target.exists() or target.read_text(encoding='utf-8') != text:
            print(f'MISMATCH: {rel(target)} is missing or differs from a fresh derivation', file=sys.stderr)
            return 1
        print(f'ok: {rel(target)} reproduced ({len(evidence["nationalPolls"])} national polls, {len(evidence["seatPolls"])} seat polls)')
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')
    print(f'wrote {rel(target)} ({len(evidence["nationalPolls"])} national polls, {len(evidence["seatPolls"])} seat polls)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
