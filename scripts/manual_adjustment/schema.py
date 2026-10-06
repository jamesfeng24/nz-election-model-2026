"""Versioned seat adjustment files (the model + James layer input).

One file per seat, `data/manual-adjustments/<electionId>/<electorateId>.json`, holding an append-only list of
dated entries. Entries are never edited or deleted: a change is a new entry that names the one it supersedes,
and each entry carries a digest chained to the previous one, so a retrospective edit is detected. An adjustment
can move a mean and can ADD uncertainty; no field exists that could remove any (the coordinate standard
deviation after the layer is sqrt(automatic^2 + extra^2), see layer.py). Invalid input raises AdjustmentError.
"""
import re
from pathlib import Path

from .common import (ROOT, ELECTION_ID, NATIONAL_KEY, LABOUR_KEY, AdjustmentError, require, canonical, sha256_text,
                      parse_time, number, one_line, exact_keys, read_json)

SCHEMA_VERSION = 1
ADJUSTMENT_ROOT = 'data/manual-adjustments'
TARGET_FRAME = 'data/processed/forecast-readiness/snapshots/2026-10-05/target-frame.json'
PARTY_RELATIONSHIPS = 'data/processed/forecast-readiness/snapshots/2026-10-05/party-relationships.json'
MAX_SHIFT_PP = 25.0
MAX_EXTRA_SD_PP = 25.0
HEX64 = re.compile(r'^[a-f0-9]{64}$')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
FILE_KEYS = ('schemaVersion', 'electionId', 'electorateId', 'entries')
ENTRY_KEYS = ('entryId', 'supersedes', 'author', 'recordedAt', 'expiresAt', 'reason', 'sources', 'exceptionalSeat',
              'adjustment', 'unadjusted', 'previousDigest', 'digest')


def seat_frame():
    """The 2026 target seats by electorate type: {'general': set, 'maori': set}."""
    frame = {'general': set(), 'maori': set()}
    for record in read_json(ROOT / TARGET_FRAME)['records']:
        frame[record['scope']].add(record['targetElectorateId'])
    return frame


def party_keys():
    """Ballot group keys that exist for 2026 (plus the two major parties the layer addresses by name)."""
    keys = {r['targetGroupKey'] for r in read_json(ROOT / PARTY_RELATIONSHIPS)['records'] if r.get('targetGroupKey')}
    return keys | {NATIONAL_KEY, LABOUR_KEY}


def entry_digest(entry):
    """SHA-256 of the canonical entry without its own digest; `previousDigest` is inside, so entries chain."""
    return sha256_text(canonical({k: v for k, v in entry.items() if k != 'digest'}))


def _source(source, field):
    exact_keys(source, ('description', 'date', 'url'), field)
    one_line(source['description'], field + '.description')
    require(isinstance(source['date'], str) and DATE.match(source['date']), f'{field}.date must be YYYY-MM-DD')
    parse_time(source['date'] + 'T00:00:00+00:00', field + '.date')
    if source['url'] is not None:
        one_line(source['url'], field + '.url', maximum=500)
        require(source['url'].startswith(('https://', 'http://')), f'{field}.url must be an http(s) URL or null')


def _target(target, field, keys):
    require(isinstance(target, dict) and target.get('kind') in ('nl_balance', 'party_share'),
            f'{field}.kind must be "nl_balance" or "party_share"')
    if target['kind'] == 'nl_balance':
        exact_keys(target, ('kind',), field)
    else:
        exact_keys(target, ('kind', 'partyKey'), field)
        require(target['partyKey'] in keys, f'{field}.partyKey {target["partyKey"]!r} is not a 2026 party group key')


def _unadjusted(value, field, adjustment):
    exact_keys(value, ('forecastId', 'snapshotSha256', 'candidateShares'), field)
    one_line(value['forecastId'], field + '.forecastId')
    require(isinstance(value['snapshotSha256'], str) and HEX64.match(value['snapshotSha256']),
            f'{field}.snapshotSha256 must be a lowercase SHA-256 hex digest of the automatic forecast file')
    shares = value['candidateShares']
    require(isinstance(shares, dict) and shares, f'{field}.candidateShares must be a non-empty object')
    for key, share in shares.items():
        number(share, f'{field}.candidateShares.{key}', 0.0, 1.0)
    require(abs(sum(shares.values()) - 1.0) <= 1e-6, f'{field}.candidateShares must sum to 1 (the full candidate slate)')
    if adjustment is None:
        return
    target, shift = adjustment['target'], adjustment['meanShiftPp'] / 100
    if target['kind'] == 'nl_balance':
        require(NATIONAL_KEY in shares and LABOUR_KEY in shares,
                f'{field}.candidateShares needs {NATIONAL_KEY} and {LABOUR_KEY} for an N/L balance adjustment')
        # A transfer of `shift` from Labour to National (negative: the reverse) must stay inside both shares.
        require(-shares[NATIONAL_KEY] < shift < shares[LABOUR_KEY],
                f'meanShiftPp {adjustment["meanShiftPp"]} would take a National/Labour share below zero')
    else:
        key = target['partyKey']
        require(key in shares, f'{field}.candidateShares has no share for the targeted party {key!r}')
        require(0.0 < shares[key] + shift < 1.0, f'meanShiftPp {adjustment["meanShiftPp"]} takes {key} outside 0-100%')


def _adjustment(adjustment, field, keys):
    if adjustment is None:
        return
    exact_keys(adjustment, ('target', 'meanShiftPp', 'extraSdPp'), field)
    _target(adjustment['target'], field + '.target', keys)
    shift = number(adjustment['meanShiftPp'], field + '.meanShiftPp', -MAX_SHIFT_PP, MAX_SHIFT_PP)
    extra = number(adjustment['extraSdPp'], field + '.extraSdPp', 0.0, MAX_EXTRA_SD_PP)
    require(shift != 0 or extra > 0, f'{field} changes nothing (zero shift and zero extra sd): use null for a flag-only entry')


def validate_entry(entry, index, electorate_id, keys):
    field = f'entries[{index}]'
    exact_keys(entry, ENTRY_KEYS, field)
    require(entry['entryId'] == f'{electorate_id}#{index + 1:03d}', f'{field}.entryId must be {electorate_id}#{index + 1:03d}')
    one_line(entry['author'], field + '.author', maximum=100)
    recorded, expires = parse_time(entry['recordedAt'], field + '.recordedAt'), parse_time(entry['expiresAt'], field + '.expiresAt')
    require(expires > recorded, f'{field}.expiresAt must be after recordedAt (every adjustment is dated and expires)')
    one_line(entry['reason'], field + '.reason', maximum=300, minimum=10)
    require(isinstance(entry['sources'], list) and entry['sources'], f'{field}.sources needs at least one dated source')
    for i, source in enumerate(entry['sources']):
        _source(source, f'{field}.sources[{i}]')
    flag = entry['exceptionalSeat']
    exact_keys(flag, ('flag', 'reason'), field + '.exceptionalSeat')
    require(isinstance(flag['flag'], bool), f'{field}.exceptionalSeat.flag must be true or false')
    if flag['flag']:
        one_line(flag['reason'], field + '.exceptionalSeat.reason', maximum=300, minimum=10)
    else:
        require(flag['reason'] is None, f'{field}.exceptionalSeat.reason must be null when the seat is not flagged')
    _adjustment(entry['adjustment'], field + '.adjustment', keys)
    if entry['adjustment'] is not None and entry['adjustment']['meanShiftPp'] != 0:
        require(flag['flag'], f'{field}: a seat with a mean shift is by definition not ordinary; set exceptionalSeat.flag true '
                              'with a reason (an adjusted seat never inherits the ordinary-seat scale)')
    _unadjusted(entry['unadjusted'], field + '.unadjusted', entry['adjustment'])
    return recorded, expires


def validate_file(document, keys=None, frame=None):
    """Validate one seat file; returns its entries' effective intervals as [(entryId, start, end)] or raises."""
    keys = party_keys() if keys is None else keys
    frame = seat_frame() if frame is None else frame
    exact_keys(document, FILE_KEYS, 'adjustment file')
    require(document['schemaVersion'] == SCHEMA_VERSION, f'schemaVersion must be {SCHEMA_VERSION} (loaders reject unknown versions)')
    require(document['electionId'] == ELECTION_ID, f'electionId must be {ELECTION_ID}')
    seat = document['electorateId']
    require(seat not in frame['maori'], f'{seat} is a Māori electorate: Māori seats are modelled completely separately and take no adjustment here')
    require(seat in frame['general'], f'{seat} is not a 2026 general electorate id')
    entries = document['entries']
    require(isinstance(entries, list) and entries, 'entries must be a non-empty list (an empty file should not exist)')
    ends, superseded, last_recorded = [], set(), None
    for index, entry in enumerate(entries):
        recorded, expires = validate_entry(entry, index, seat, keys)
        require(last_recorded is None or recorded > last_recorded, f'entries[{index}].recordedAt must be later than the previous entry (append-only history)')
        require(entry['previousDigest'] == (entries[index - 1]['digest'] if index else None),
                f'entries[{index}].previousDigest does not match the previous entry: history was reordered or edited')
        require(entry['digest'] == entry_digest(entry),
                f'entries[{index}] digest mismatch: the entry was edited after it was recorded (append a new entry instead)')
        target = entry['supersedes']
        known = {e['entryId'] for e in entries[:index]}
        require(target is None or target in known, f'entries[{index}].supersedes must name an earlier entry')
        require(target not in superseded, f'entries[{index}] supersedes {target}, which is already superseded')
        for other, (name, start, end) in enumerate(ends):
            if name != target and recorded < end:
                raise AdjustmentError(f'entries[{index}] is recorded while {name} is still active; it must supersede {name} explicitly')
        if target is not None:
            superseded.add(target)
            slot = next(i for i, (name, _, _) in enumerate(ends) if name == target)
            name, start, end = ends[slot]
            ends[slot] = (name, start, min(end, recorded))
        ends.append((entry['entryId'], recorded, expires))
        last_recorded = recorded
    return ends


def active_entry(document, as_of):
    """The one entry in force at `as_of` (recorded then, not expired, not superseded), or None."""
    when = parse_time(as_of, 'as_of') if isinstance(as_of, str) else as_of
    by_id = {e['entryId']: e for e in document['entries']}
    found = [name for name, start, end in validate_file(document) if start <= when < end]
    require(len(found) <= 1, 'internal error: more than one active entry')
    return by_id[found[0]] if found else None


def new_entry(document, electorate_id, fields):
    """Append helper: `fields` holds everything the author supplies; ids, supersession default, chain and digest are added.

    Returns the file document with the entry appended and validated (the input is not modified)."""
    exact_keys(fields, ('author', 'recordedAt', 'expiresAt', 'reason', 'sources', 'exceptionalSeat', 'adjustment', 'unadjusted')
               + (('supersedes',) if 'supersedes' in fields else ()), 'new entry')
    base = {'schemaVersion': SCHEMA_VERSION, 'electionId': ELECTION_ID, 'electorateId': electorate_id, 'entries': []}
    document = {**base, 'entries': list((document or base)['entries'])}
    previous = document['entries'][-1] if document['entries'] else None
    entry = {'entryId': f'{electorate_id}#{len(document["entries"]) + 1:03d}', 'supersedes': fields.get('supersedes'),
             **{k: fields[k] for k in ('author', 'recordedAt', 'expiresAt', 'reason', 'sources', 'exceptionalSeat', 'adjustment', 'unadjusted')},
             'previousDigest': previous['digest'] if previous else None, 'digest': ''}
    validate_entry(entry, len(document['entries']), electorate_id, party_keys())  # field errors surface before hashing
    entry['digest'] = entry_digest(entry)
    document['entries'].append(entry)
    validate_file(document)
    return document


def seat_path(electorate_id, root=None):
    return Path(root or ROOT / ADJUSTMENT_ROOT) / ELECTION_ID / f'{electorate_id}.json'


def load_directory(root=None):
    """Validate every seat file under the adjustment root; returns {electorateId: document}."""
    base = Path(root or ROOT / ADJUSTMENT_ROOT) / ELECTION_ID
    keys, frame, documents = party_keys(), seat_frame(), {}
    for path in sorted(base.glob('*.json')) if base.exists() else []:
        document = read_json(path)
        require(path.stem == document.get('electorateId'), f'{path.name}: file name must equal electorateId')
        validate_file(document, keys, frame)
        documents[document['electorateId']] = document
    return documents
