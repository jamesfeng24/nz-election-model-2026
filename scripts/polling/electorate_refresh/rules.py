"""Stage82: identity, blocker, review and info rules for electorate polls read from Wikipedia (stdlib only).

Blockers stop the run for a human: unknown seat, a published row that changed or disappeared, fieldwork after the run date, impossible
shares. Review flags are published but flagged: a new pollster, an approximate cell, an independent column, a sponsored-story source, a poll
that lists little of the vote. Info: primary verification pending (these rows are Wikipedia aggregator evidence only, never verified here)."""
import hashlib
import json
import re
import unicodedata
from datetime import date

MAORI_SEATS = ('Hauraki-Waikato', 'Ikaroa-Rāwhiti', 'Tāmaki Makaurau', 'Te Tai Hauāuru', 'Te Tai Tokerau', 'Te Tai Tonga', 'Waiariki')
CYCLE_YEAR = 2026
LATE_DAYS = 14
LOW_LISTED_PCT = 60


def seat_key(name):
    t = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().casefold()
    t = re.sub(r'[^a-z0-9]+', ' ', t).strip()
    return re.sub(r'^mount\b', 'mt', t)


def pollster_key(name):
    return re.sub(r'[^a-z0-9]+', '', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().casefold())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def resolve_seats(labels):
    """{seat_key: official label}; two labels with one key would make matching ambiguous."""
    out = {}
    for label in labels:
        k = seat_key(label)
        if out.setdefault(k, label) != label:
            raise ValueError('Ambiguous seat key ' + k)
    return out


def build_record(raw, seats, run_date):
    """(record, blockers) for one parsed poll. The record is what is stored; contentSha256 covers everything a reader could dispute."""
    blockers = []
    label = seats.get(seat_key(raw['seatName']))
    tag = {'seat': raw['seatName'], 'fieldwork': raw['fieldwork']['raw'], 'pollster': raw['pollster']}
    if label is None:
        blockers.append({**tag, 'kind': 'unknown_seat', 'action': 'not an electorate on the official 2026 list; a human must add an alias or reject the row'})
        return None, blockers
    is_maori = label in MAORI_SEATS
    if (raw['kind'] == 'maori') != is_maori:
        blockers.append({**tag, 'kind': 'seat_kind_mismatch', 'seatLabel': label, 'action': 'section heading and the official electorate type disagree'})
    fw = raw['fieldwork']
    if fw['end'] > run_date:
        blockers.append({**tag, 'kind': 'fieldwork_ends_after_run_date', 'action': 'impossible for a published poll'})
    if not fw['start'].startswith(str(CYCLE_YEAR)):
        blockers.append({**tag, 'kind': 'fieldwork_outside_cycle', 'action': 'this table is the 2026 cycle'})
    core = {'seat': label, 'kind': raw['kind'], 'fieldwork': {'start': fw['start'], 'end': fw['end']}, 'pollsterKey': pollster_key(raw['pollster']),
            'sampleSize': raw['sampleSize'], 'electorate': raw['electorate'], 'partyVote': raw['partyVote'], 'flags': raw['flags']}
    pid = 'nz-seatpoll-' + digest([label, fw['start'], fw['end'], core['pollsterKey']])[:20]
    rec = {'id': pid, 'seat': label, 'seatPublishedAs': raw['seatName'], 'type': raw['kind'], 'fieldwork': fw, 'pollster': raw['pollster'],
           'sampleSize': raw['sampleSize'], 'electorateVotePct': raw['electorate'], 'electorateVoteFlags': raw['flags']['electorate'],
           'partyVotePct': raw['partyVote'], 'partyVoteFlags': raw['flags']['partyVote'], 'partyVoteUsed': False,
           'references': [r['url'] for r in raw['references'] if r['url']], 'evidenceGrade': 'aggregator_only',
           'contentSha256': digest(core)}
    return rec, blockers


def evaluate(base, raws, seats, run_date):
    """(added records, blockers, reviews, infos) comparing the page with the previous cumulative polls."""
    blockers, reviews, infos, current = [], [], [], {}
    for raw in raws:
        rec, bl = build_record(raw, seats, run_date)
        blockers.extend(bl)
        if rec is None:
            continue
        if rec['id'] in current:
            blockers.append({'seat': rec['seat'], 'fieldwork': raw['fieldwork']['raw'], 'pollster': raw['pollster'], 'kind': 'duplicate_poll', 'action': 'two rows share seat, pollster and fieldwork'})
        current[rec['id']] = rec
    old = {r['id']: r for r in base}
    for pid, r in old.items():
        tag = {'id': pid, 'seat': r['seat'], 'fieldwork': r['fieldwork']['raw'], 'pollster': r['pollster']}
        if pid not in current:
            blockers.append({**tag, 'kind': 'removed_row', 'action': 'a published poll disappeared from the page; decide whether it was withdrawn or vandalised'})
        elif current[pid]['contentSha256'] != r['contentSha256']:
            now = current[pid]
            blockers.append({**tag, 'kind': 'revised_row', 'before': {'electorate': r['electorateVotePct'], 'partyVote': r['partyVotePct'], 'n': r['sampleSize']},
                             'after': {'electorate': now['electorateVotePct'], 'partyVote': now['partyVotePct'], 'n': now['sampleSize']},
                             'action': 'a published poll was edited on Wikipedia; a human decides which version stands'})
    added = [current[p] for p in current if p not in old]
    known_pollsters = {pollster_key(r['pollster']) for r in base}
    for r in added:
        tag = {'id': r['id'], 'seat': r['seat'], 'fieldwork': r['fieldwork']['raw'], 'pollster': r['pollster']}
        if base and pollster_key(r['pollster']) not in known_pollsters:
            reviews.append({**tag, 'kind': 'new_pollster', 'action': 'first seat poll from this pollster: confirm identity and method'})
        if r['electorateVoteFlags']:
            reviews.append({**tag, 'kind': 'approximate_value', 'detail': r['electorateVoteFlags'], 'action': 'published as "~"; stored as the number with an approximate flag'})
        if 'IND' in r['electorateVotePct']:
            reviews.append({**tag, 'kind': 'independent_column', 'detail': r['electorateVotePct']['IND'], 'action': 'an independent has a share; the candidate is not named in the table'})
        if any('sponsored' in (u or '').lower() for u in r['references']):
            reviews.append({**tag, 'kind': 'sponsored_source', 'action': 'the cited page is a sponsored story, not an independent report'})
        listed = sum(r['electorateVotePct'].values())
        if listed < LOW_LISTED_PCT:
            reviews.append({**tag, 'kind': 'low_listed_share', 'detail': round(listed, 1), 'action': 'the listed parties total under 60%'})
        if r['sampleSize'] is None:
            infos.append({**tag, 'kind': 'sample_size_missing', 'note': 'blank sample cell'})
        if (date.fromisoformat(run_date) - date.fromisoformat(r['fieldwork']['end'])).days > LATE_DAYS:
            infos.append({**tag, 'kind': 'late_addition', 'note': f'fieldwork ended more than {LATE_DAYS} days before the run date'})
        infos.append({**tag, 'kind': 'primary_verification_pending', 'note': 'Wikipedia aggregator evidence only; no primary release checked'})
    return added, blockers, reviews, infos


def next_polls(base, added, run_date):
    rows = [dict(r) for r in base] + [{**r, 'firstSeen': run_date} for r in added]
    return sorted(rows, key=lambda r: (r['fieldwork']['end'], r['seat'], r['id']))
