"""Stage86 (D125): the 2026 Maori seat polls from the Stage82 live-inputs file, in the shape the Stage66 simulation reads.

The nowcast assembly used to read the pinned transcription `data/source-plans/maori-seat-layer/polls-2026.json`. It now reads the run of
`data/processed/polling/electorate-live/` that `seatPolls.electorateRun` pins (append-only, hash-checked against `index.json`; audit J2), up to
the data cutoff as for the general seats, so a new Maori seat poll is a data-only addition once that run is adopted:
the Stage66 calibration and the Stage71 and Stage78 decisions are untouched and nothing is refitted. The pinned file still serves the recorded
Stage66, Stage71 and Stage78 artifacts (a 2026-10-07 snapshot of three seats); the assembly no longer reads it.

Differences from the pinned form, all deliberate:
- The live file has party shares, not candidate names, so each poll party is resolved to exactly one active official candidate of the seat by
  ballot group (an independent column resolves only when the seat has exactly one independent). The caller supplies that resolver.
- Shares are the published electorate-vote percentages excluding undecided respondents, rounded to whole numbers. The Stage66 simulation closes
  the shares over the named candidates, so the excluded undecided and "other" shares do not matter; the rounding does, slightly.
- As in Stage66, the latest poll per seat by fieldwork end is used; earlier polls of a seat are returned as superseded, never dropped silently.
Fails closed: a hash mismatch, an unknown seat or party label, an unresolvable candidate or fewer than two candidates raises.
"""
from scripts.maori_seat_layer.common import SEATS, fold
from scripts.polling import electorate_live

# Live column labels (the Stage82 parser stores OPP as TOP) -> Stage66 and assembly party codes. "Others" (stored as OTH) is not a named candidate and is not read.
PARTY_CODES = {'TPM': 'MP', 'LAB': 'LAB', 'GRN': 'GRN', 'NAT': 'NAT', 'NZF': 'NZF', 'TOP': 'TOP', 'IND': 'IND'}
NOT_A_CANDIDATE = ('OTH', 'Others')


def live_polls(run=None, sha256=None):
    """The Maori polls of a Stage82 run: the pinned run `run` (date), else the newest (empty when there is no run). The file must match its
    index entry and, when given, the pinned hash."""
    return [p for p in electorate_live.polls(run, sha256) if p['type'] == 'maori']


def seat_name(published):
    found = [s for s in SEATS if fold(s) == fold(published)]
    if len(found) != 1:
        raise ValueError('Unknown Maori seat in a live poll: ' + published)
    return found[0]


def poll_record(poll, resolve):
    """Stage66 poll record from one live row: candidates in descending share (ties by party code), as the pinned file lists them."""
    seat = seat_name(poll['seat'])
    candidates = []
    for label, share in sorted(poll['electorateVotePct'].items(), key=lambda kv: (-kv[1], kv[0])):
        if label in NOT_A_CANDIDATE:
            continue
        if label not in PARTY_CODES:
            raise ValueError(f"{seat}: unmapped party column {label!r} in poll {poll['id']}")
        if not share > 0:
            raise ValueError(f"{seat}: non-positive share for {label} in poll {poll['id']}")
        code = PARTY_CODES[label]
        candidates.append({'name': resolve(seat, code), 'party': code, 'pollPercent': share})
    if len(candidates) < 2:
        raise ValueError('A seat poll needs at least two candidates: ' + poll['id'])
    if len({fold(c['name']) for c in candidates}) != len(candidates):
        raise ValueError('Duplicate candidate in ' + poll['id'])
    return {'id': poll['id'], 'seat': seat, 'pollster': poll['pollster'], 'fieldworkStart': poll['fieldwork']['start'],
            'fieldworkEnd': poll['fieldwork']['end'], 'sampleSize': poll['sampleSize'], 'candidates': candidates}


def current_polls(resolve, polls=None, as_of=None):
    """(latest poll per seat, superseded poll ids), the first element in the form `maori_seat_layer.simulate.simulate` reads.

    `resolve(seat, party_code)` returns the displayed name of the one official candidate; `polls` overrides the file (tests). With `as_of`
    (ISO date) a poll whose fieldwork ended after it is not read, as for the general seats (audit J2).
    """
    latest, superseded = {}, []
    eligible = [p for p in (live_polls() if polls is None else polls) if as_of is None or p['fieldwork']['end'] <= as_of]
    for poll in sorted(eligible, key=lambda p: (p['fieldwork']['end'], p['id'])):
        record = poll_record(poll, resolve)
        if record['seat'] in latest:
            superseded.append(latest[record['seat']]['id'])
        latest[record['seat']] = record
    return latest, superseded
