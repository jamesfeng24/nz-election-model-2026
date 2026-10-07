"""New-row detection, inclusion rules and the next dated panel. Stdlib only (Stage35 adapter semantics, as in Stage59).

Rules separate BLOCKERS (the run refuses to publish) from REVIEW flags (published, but a human must look) and INFO notes.
"""
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from scripts.polling.national_foundation.records import record, deduplicate
from scripts.polling.national_foundation.wiki import Tables, clean, dates, pollster
from scripts.polling.panel_update.build import DUPLICATE_KEPT, DUPLICATE_DROPPED
from .common import CORE, SPAN_FACTOR, SPAN_FLOOR_DAYS, LATE_DAYS, TARGET_YEAR, read, sha, rel, ROOT

KNOWN_COLLAPSED = {DUPLICATE_DROPPED: DUPLICATE_KEPT}   # Stage59: Wikipedia April 2026 Talbot Mills copy kept as one wave
HEADER = ['Date[a]', 'Polling organisation', 'Sample size']


def wiki_rows(html_text, source_id, capture_path, capture_sha):
    """Every full-width poll row of the Wikipedia party table as a panel record; rows that cannot be mapped are returned apart."""
    parser = Tables(); parser.feed(html_text)
    tables = [t for t in parser.tables if t and t[0][:3] == HEADER and 'NAT' in t[0]]
    if len(tables) != 1:
        raise ValueError('Party table layout changed: expected exactly one table')
    header = tables[0][0]; rows, unmapped = [], []
    for number, row in enumerate(tables[0][1:], 2):
        if len(row) != len(header):
            continue                      # event rows (debates, leadership changes)
        if row[0] == header[0] or 'election result' in row[1].lower():
            continue                      # repeated header row, last-election result row
        try:
            fs = {'date': dates(row[0]), 'org': pollster(row[1])}
            n = clean(row[2]); fs['n'] = '~' if n in ('', '1,000+') else n
            for k, v in zip(header[3:-1], row[3:-1]):
                fs[{'TPM': 'MRI', 'OPP': 'TOP', 'Others': 'OTH'}.get(k, k)] = clean(v)
            r = record(TARGET_YEAR, fs, {'sourceId': source_id, 'rawPath': capture_path, 'sha256': capture_sha, 'row': number,
                                         'role': 'Wikipedia REST table row', 'sourceType': 'aggregator'})
        except (ValueError, KeyError) as exc:
            unmapped.append({'row': number, 'reason': str(exc), 'cells': row[:3]}); continue
        r['commissioner'] = row[1]
        rows.append(r)
    return rows, unmapped


def semantic(o):
    return (o['status'], o['share'], o['bounds'])


def content(r):
    """Fields a Wikipedia revision could change. 'Others' is excluded: the Stage35 base panel never carried it."""
    return ({k: semantic(v) for k, v in r['estimates'].items()}, {k: semantic(v) for k, v in r['additionalPublishedCategories'].items()}, r['sampleSize'])


def same_content(wiki, base):
    a, b = content(wiki), content(base)
    return a[0] == b[0] and a[1] == b[1] and (a[2] is None or a[2] == b[2])   # a blank sample cell takes the pinned default downstream


def span_days(r):
    s, e = r['fieldworkStartBounds'][0], r['fieldworkEndBounds'][1]
    return (date.fromisoformat(e) - date.fromisoformat(s)).days + 1


def evaluate(base_records, wiki, unmapped, run_date):
    """Compare the new capture with the previous panel. Returns (added records, changes, blockers, reviews, infos)."""
    run = date.fromisoformat(run_date)
    base = {r['id']: r for r in base_records if r['cycle'] == TARGET_YEAR}
    wid = {r['id']: r for r in wiki}
    blockers, reviews, infos, added = [], [], [], []
    for u in unmapped:
        blockers.append({'kind': 'unmapped_row', 'detail': u, 'action': 'new pollster name or unreadable date; a human must extend the adapter or the pollster map'})
    for i, r in wid.items():
        if i in KNOWN_COLLAPSED:
            continue
        if i in base:
            if not same_content(r, base[i]):
                blockers.append({'kind': 'revised_row', 'id': i, 'fieldwork': r['fieldworkRaw'], 'pollster': r['pollsterCode'],
                                 'action': 'an already-published wave changed on Wikipedia; a human decides whether the panel follows'})
        else:
            added.append(r)
    for i, r in base.items():
        if i not in wid and i not in KNOWN_COLLAPSED.values():
            blockers.append({'kind': 'removed_row', 'id': i, 'fieldwork': r['fieldworkRaw'], 'pollster': r['pollsterCode'],
                             'action': 'a panel wave no longer appears on Wikipedia; a human decides'})
    history = {}
    for r in base.values():
        history.setdefault(r['pollsterCode'], []).append(r)
    for r in added:
        tag = {'id': r['id'], 'pollster': r['pollsterCode'], 'fieldwork': r['fieldworkRaw']}
        end = date.fromisoformat(r['fieldworkEndBounds'][1]); start = date.fromisoformat(r['fieldworkStartBounds'][0])
        if end > run:
            blockers.append({**tag, 'kind': 'fieldwork_ends_after_run_date', 'action': 'impossible for a published poll'})
        if r['status'] != 'usable_partial':
            blockers.append({**tag, 'kind': 'published_shares_incompatible', 'detail': r['status'], 'action': 'lower bounds sum above 100%'})
        if any(v['status'] == 'rounded' and not 0 <= v['share'] <= 0.7 for v in r['estimates'].values()):
            blockers.append({**tag, 'kind': 'implausible_share', 'action': 'a party share outside 0-70%'})
        prior = history.get(r['pollsterCode'], [])
        if not prior:
            reviews.append({**tag, 'kind': 'new_pollster', 'action': 'first poll from this pollster in the 2026 cycle: confirm identity, method and the pinned pollster map'})
        else:
            longest = max(span_days(p) for p in prior)
            if span_days(r) > max(SPAN_FLOOR_DAYS, SPAN_FACTOR * longest):
                reviews.append({**tag, 'kind': 'odd_field_dates', 'detail': f'span {span_days(r)} days vs longest earlier {longest}',
                                'action': 'fieldwork span unusually long for this pollster; verify against the primary release'})
        if len(r['fieldworkRaw']) == 1:
            reviews.append({**tag, 'kind': 'odd_field_dates', 'detail': 'single date, no fieldwork range', 'action': 'a single date may be a release date, not fieldwork'})
        if any('00' == d[-2:] for d in r['fieldworkRaw']):
            reviews.append({**tag, 'kind': 'odd_field_dates', 'detail': 'unknown day', 'action': 'fieldwork day unknown'})
        missing = [k for k in CORE if r['estimates'][k]['status'] == 'not_reported']
        if missing:
            reviews.append({**tag, 'kind': 'missing_party_shares', 'detail': missing, 'action': 'core party share not published; unreported is missing, not zero'})
        total = sum(v['share'] * 100 for v in r['estimates'].values() if v['share'] is not None) + (r['publishedOther']['share'] or 0) * 100
        if r['publishedOther']['share'] is not None and not 97 <= total <= 103:
            reviews.append({**tag, 'kind': 'shares_do_not_sum', 'detail': round(total, 1), 'action': 'published shares plus Others outside 97-103%'})
        if r['sampleSize'] is None:
            infos.append({**tag, 'kind': 'sample_size_missing', 'note': 'blank sample cell; the pinned pollster default applies downstream'})
        if (run - end).days > LATE_DAYS:
            infos.append({**tag, 'kind': 'late_addition', 'note': f'fieldwork ended {(run - end).days} days before the run date (publication lag)'})
        if r['commissioner'].startswith(('Labour–', 'National–')):
            infos.append({**tag, 'kind': 'sponsored_release', 'note': 'excluded by the pinned configuration (sponsored-release rule)'})
        infos.append({**tag, 'kind': 'primary_verification_pending', 'note': 'Wikipedia aggregator evidence only; no primary release checked'})
    return added, blockers, reviews, infos


def next_panel(base_path, added, run_date, capture_rel, capture_sha, revision):
    base_bytes = Path(base_path).read_bytes()
    base = json.loads(base_bytes)
    new = []
    for r in added:
        r = json.loads(json.dumps(r))
        r['evidenceGrade'] = 'aggregator_only'
        r['panelUpdateNote'] = f'Added by the {run_date} weekly refresh from Wikipedia revision {revision}; primary-release verification pending.'
        new.append(r)
    records, dups = deduplicate(base['records'] + new)
    if dups:
        raise ValueError('Added wave collides with an existing wave: ' + json.dumps(dups))
    ids = [r['id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate ids')
    panel = {'schemaVersion': 1, 'basePanel': rel(base_path), 'basePanelSha256': hashlib.sha256(base_bytes).hexdigest(),
             'refreshDate': run_date, 'records': records}
    changes = {'schemaVersion': 1, 'refreshDate': run_date, 'wikipediaRevision': revision, 'capture': {'rawPath': capture_rel, 'sha256': capture_sha},
               'baseWaves': len(base['records']), 'updatedWaves': len(records),
               'added': [{'id': r['id'], 'pollsterCode': r['pollsterCode'], 'commissioner': r['commissioner'], 'fieldworkRaw': r['fieldworkRaw'],
                          'sampleSize': r['sampleSize'], 'shares': {k: v['published'] for k, v in r['estimates'].items() if v['status'] != 'not_reported'},
                          'others': r['publishedOther']['published']} for r in new]}
    return panel, changes
