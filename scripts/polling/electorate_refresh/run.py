"""Stage82: electorate polls from the Wikipedia opinion-polling page into a dated, append-only live-inputs file (stdlib only; needs network
unless --use-existing-capture).

  python3 -m scripts.polling.electorate_refresh.run [--date YYYY-MM-DD] [--use-existing-capture]
  python3 -m scripts.polling.electorate_refresh.run --check

The page is the same capture the national refresh reads (data/raw/polling/weekly-refresh/<date>/, written by `weekly_refresh.capture`); this step
fetches it first and the national step then reuses it with --use-existing-capture, so both read one revision. If an electorate poll was added, nothing
else changed. Output on a change: data/processed/polling/electorate-live/<date>/ (cumulative polls.json = previous + additions, changes, review,
registry, seat list, manifest), a byte copy of the capture under data/raw/polling/electorate-live/<date>/, index.json and one handoff fragment.
Earlier dates are never edited. Nothing here is read by any model layer: wiring is a separate, authorised stage. No refit is implied: a data change only.
Exit 0: ELECTORATE_NO_CHANGE or ELECTORATE_UPDATED. Exit 2: ELECTORATE_BLOCKED (blocked.json and review.json written, nothing published)."""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.polling.weekly_refresh import capture
from scripts.polling.weekly_refresh.common import CAPTURE, ELECTION_DAY, FRAGMENTS, RAW as NATIONAL_RAW, ROOT, TIMEZONE, read, rel, sha, write
from . import parse, rules

RAW = ROOT / 'data/raw/polling/electorate-live'
OUT = ROOT / 'data/processed/polling/electorate-live'
INDEX = OUT / 'index.json'
NOMINATIONS = ROOT / 'data/processed/nominations-2026'
PROCESSING = 'scripts/polling/electorate_refresh/run.py'
EXIT_BLOCKED = 2
LICENCE = 'Wikipedia text is CC BY-SA; bytes preserved unchanged for research provenance. Poll figures originate from the named pollsters and press reports.'
RAW_FILES = (CAPTURE, CAPTURE + '.headers', 'fetch-log.tsv')


def nz_today():
    return datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()


def load_index():
    return read(INDEX) if INDEX.exists() else {'schemaVersion': 1, 'runs': []}


def latest_polls():
    runs = load_index()['runs']
    return (read(OUT / runs[-1]['date'] / 'polls.json')['polls'], runs[-1]['date']) if runs else ([], None)


def seat_universe():
    """Official 2026 electorate labels from the newest preserved nomination table (a name list only; no candidate is read)."""
    tables = sorted(NOMINATIONS.glob('*/official-table.json'))
    if not tables:
        raise FileNotFoundError('No official nomination table to take the electorate names from')
    path = tables[-1]
    labels = sorted({r['electorateLabel'] for r in read(path)['rows']})
    return labels, {'source': rel(path), 'sha256': sha(path), 'count': len(labels)}


def process(base, html, run_date, labels):
    """Pure step: (status, added, blockers, reviews, infos). status is 'blocked', 'unchanged' or 'updated'."""
    seats = rules.resolve_seats(labels)
    try:
        raws = parse.parse_page(html)
    except parse.Block as b:
        return 'blocked', [], [{'kind': b.kind, **b.detail, 'action': 'the page layout is not one this reader understands; a human must extend or fix the reader'}], [], []
    added, blockers, reviews, infos = rules.evaluate(base, raws, seats, run_date)
    status = 'blocked' if blockers else ('updated' if added else 'unchanged')
    return status, added, blockers, reviews, infos


def registry(run_date, rev, last_modified, retrieved):
    srcs = []
    for name, role in ((RAW_FILES[0], 'table'), (RAW_FILES[1], 'response headers'), (RAW_FILES[2], 'fetch log')):
        srcs.append({'dateOrElection': f'2026 general election cycle; electorate poll refresh {run_date}', 'id': f'polling-electorate-live-{run_date}-{name}', 'licence': LICENCE,
                     'limitations': ['Aggregator transcription; fieldwork dates, sample sizes and shares unverified against primary releases.',
                                     f'Wikipedia revision {rev}, last modified {last_modified}; {role}'],
                     'organisation': 'Wikipedia (REST HTML, Opinion polling for the 2026 New Zealand general election, Electorate polling)', 'processingScript': PROCESSING,
                     'rawPath': rel(RAW / run_date / name), 'resource': name, 'retrievedAt': retrieved, 'schemaVersion': 1, 'sha256': sha(RAW / run_date / name),
                     'url': 'https://en.wikipedia.org/api/rest_v1/page/html/Opinion_polling_for_the_2026_New_Zealand_general_election'})
    return {'schemaVersion': 1, 'note': 'Dated registry for this electorate poll refresh; data/sources.json is frozen and not edited.', 'sources': srcs}


def manifest(d):
    return {'schemaVersion': 1, 'sha256': {str(p.relative_to(d)): sha(p) for p in sorted(d.rglob('*')) if p.is_file() and p.name != 'manifest.json'}}


def write_fragment(run_date, added, total, rev, reviews):
    line = ', '.join(sorted({f"{r['seat']} ({r['pollster']})" for r in added}))
    text = (f'<!-- fold: changelog -->\n## Electorate poll refresh {run_date}\n\n- {len(added)} new electorate poll(s) added to the dated live-inputs file '
            f'`data/processed/polling/electorate-live/{run_date}/polls.json` ({total} in total) from Wikipedia revision {rev}: {line}. '
            f'{len(reviews)} item(s) flagged for human review. Wikipedia aggregator evidence only; not read by any model layer. Data change only, no refit.\n')
    FRAGMENTS.mkdir(exist_ok=True)
    (FRAGMENTS / f'{run_date}-electorate-poll-refresh.md').write_text(text)


def run(run_date, use_existing=False, html_path=None):
    if datetime.fromisoformat(run_date).date() >= ELECTION_DAY:
        raise ValueError('The refresh ends before election day (7 Nov 2026)')
    out = OUT / run_date
    if out.exists():
        raise FileExistsError('Run directory exists; earlier runs are never edited: ' + str(out))
    src = NATIONAL_RAW / run_date
    if not use_existing:
        capture.fetch(run_date)
    cap = src / CAPTURE
    if not cap.exists():
        raise FileNotFoundError(str(cap))
    rev, last_modified = capture.revision(run_date)
    html = cap.read_text(encoding='utf-8')
    base, base_date = latest_polls()
    labels, universe = seat_universe()
    status, added, blockers, reviews, infos = process(base, html, run_date, labels)
    review = {'schemaVersion': 1, 'refreshDate': run_date, 'blockers': blockers, 'reviews': reviews, 'infos': infos}
    if status == 'unchanged':
        print('ELECTORATE_NO_CHANGE', run_date, 'wikipedia revision', rev, len(base), 'polls held')
        return 0
    raw = RAW / run_date
    if raw.exists():
        raise FileExistsError('Raw directory exists; earlier captures are never overwritten: ' + str(raw))
    raw.mkdir(parents=True)
    for name in RAW_FILES:
        shutil.copyfile(src / name, raw / name)
    retrieved = (raw / 'fetch-log.tsv').read_text().splitlines()[-1].split('\t')[0]
    out.mkdir(parents=True)
    write(out / 'review.json', review)
    write(out / 'source-registry.json', registry(run_date, rev, last_modified, retrieved))
    write(out / 'seats.json', {'schemaVersion': 1, 'universe': universe, 'labels': labels})
    if status == 'blocked':
        write(out / 'blocked.json', {'schemaVersion': 1, 'refreshDate': run_date, 'reason': 'electorate-poll rules', 'review': review,
                                     'note': 'No electorate poll was published for this date. The raw capture is preserved.'})
        print('ELECTORATE_BLOCKED', json.dumps(blockers)[:2000], file=sys.stderr)
        return EXIT_BLOCKED
    polls = rules.next_polls(base, added, run_date)
    write(out / 'polls.json', {'schemaVersion': 1, 'refreshDate': run_date, 'wikipediaRevision': rev, 'evidenceGrade': 'aggregator_only',
                               'note': 'Cumulative: the previous file plus the additions in changes.json. Not read by any model layer. Party-vote rows are stored but unused.',
                               'basePolls': rel(OUT / base_date / 'polls.json') if base_date else None, 'polls': polls})
    write(out / 'changes.json', {'schemaVersion': 1, 'refreshDate': run_date, 'baseDate': base_date, 'baseCount': len(base), 'added': added})
    write(out / 'manifest.json', manifest(out))
    idx = load_index()
    idx['runs'].append({'date': run_date, 'wikipediaRevision': rev, 'pollCount': len(polls), 'added': len(added), 'pollsSha256': sha(out / 'polls.json'),
                        'manifestSha256': sha(out / 'manifest.json'), 'humanReviewRequired': bool(reviews)})
    write(INDEX, idx)
    write_fragment(run_date, added, len(polls), rev, reviews)
    print('ELECTORATE_UPDATED', run_date, len(added), 'new,', len(polls), 'held, review flags', len(reviews))
    return 0


def check():
    """Verify every committed run from the raw captures alone: hashes, the append-only chain and a full re-derivation (stdlib; no network)."""
    seen, prev = [], []
    for entry in load_index()['runs']:
        d, day = OUT / entry['date'], entry['date']
        man = read(d / 'manifest.json')
        for name, h in man['sha256'].items():
            if sha(d / name) != h:
                raise ValueError(f'Changed file {day}/{name}')
        if sha(d / 'manifest.json') != entry['manifestSha256'] or sha(d / 'polls.json') != entry['pollsSha256']:
            raise ValueError('Index does not match run ' + day)
        for r in read(d / 'source-registry.json')['sources']:
            if sha(ROOT / r['rawPath']) != r['sha256']:
                raise ValueError('Changed registered source ' + r['rawPath'])
        if read(d / 'review.json')['blockers'] or (d / 'blocked.json').exists():
            raise ValueError('Published run carries blockers ' + day)
        rev = entry['wikipediaRevision']
        headers = (RAW / day / (CAPTURE + '.headers')).read_text()
        if f'content-revision-id: {rev}' not in headers.lower():
            raise ValueError('Revision id does not match the preserved headers ' + day)
        status, added, blockers, _, _ = process(prev, (RAW / day / CAPTURE).read_text(encoding='utf-8'), day, read(d / 'seats.json')['labels'])
        stored = read(d / 'polls.json')['polls']
        if status != 'updated' or blockers or stored != rules.next_polls(prev, added, day) or read(d / 'changes.json')['added'] != added:
            raise ValueError('Run not reproduced from its capture ' + day)
        old = {r['id']: r for r in prev}
        if any(old[i] != next(r for r in stored if r['id'] == i) for i in old):
            raise ValueError('An earlier poll was edited ' + day)
        prev = stored; seen.append(day)
    return seen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--date', default=None, help='run date (NZ civil date), default today in Pacific/Auckland')
    ap.add_argument('--use-existing-capture', action='store_true', help='reuse data/raw/polling/weekly-refresh/<date>/ already on disk')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    if a.check:
        print('ok', check()); return 0
    return run(a.date or nz_today(), a.use_existing_capture)


if __name__ == '__main__':
    sys.exit(main())
