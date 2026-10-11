"""Stage85 per-seat evidence: display data for the seat pages, derived from inputs the bank already used.

One record per simulated seat: its D107 uncertainty class and multipliers, the 2023 party-vote baseline it started from (general
seats), the seat polls that were found with the share each took of the combined poll and how much each moved the model, and the
size of the poll update. Nothing here feeds a forecast number; it is computed after the seats are simulated and is left out of the
bank digest (`assemble.bank_digest`), so adding or changing it never changes a bank's simulated content.

Polls: a general seat's `weight` is exactly its contribution to the updated National/Labour balance. The update is linear in the
combined poll, centre = model + k (poll - model) with k = rho * w, and the combined poll is the share-weighted mean of the polls, so
poll i moves the centre by `weight` = k * share_i of the gap to its own value and the model keeps 1 - k (`pollUpdate.modelWeight`).
A Maori seat's latest poll (from the Stage82 live file since Stage86) is the one input of the Stage66 layer, so it has no share or weight.
"""
from scripts.maori_seat_layer import live as maori_live
from scripts.maori_seat_layer.live import live_polls
from scripts.seat_polls import live as seat_polls, candidates as candidate_polls
from scripts.polling import electorate_live
from . import maori
from .common import OTHER, require

BASELINE_BASIS = '2023 party vote on the 2026 boundaries'


def party_vote(row, keys, groups, continuing):
    """The seat's 2023 party-vote baseline by national group; groups outside the core parties are summed into the other bucket."""
    require(abs(sum(row) - 1) < 1e-9, 'evidence baseline is not a simplex')
    out = {g: 0.0 for g in groups}
    for key, share in zip(keys, row):
        out[continuing.get(key) if continuing.get(key) in out else OTHER] += float(share)
    return [{'partyId': g, 'share': out[g]} for g in groups]


def poll_row(poll, applied, weight_scale, note=None):
    used = poll['status'] == 'used' and applied
    reason = poll['reason'] if poll['status'] == 'not-used' else (None if applied else note)
    return {'pollId': poll['pollId'], 'pollster': poll['pollster'], 'sponsorGroup': poll['sponsorGroup'],
            'fieldworkStart': poll['fieldworkStart'], 'fieldworkEnd': poll['fieldworkEnd'],
            'sampleSize': poll['sampleSize'], 'sampleSizeAssumed': poll['sampleSizeAssumed'],
            'candidateVotePct': [{'party': k, 'pct': float(v)} for k, v in sorted(poll['candidateVotePct'].items())],
            'approximate': poll['approximate'], 'evidenceGrade': poll['evidenceGrade'],
            'status': 'used' if used else 'not-used', 'reason': reason,
            'shareOfPoll': poll['share'] if used else None, 'weight': poll['share'] * weight_scale if used else None}


def general_seat(seat, record, row, keys, groups, continuing, polls):
    update = record.get('seatPoll')
    scale = update['rho'] * update['weight'] if update else 0.0
    note = None if update else 'the poll could not be applied to this seat (no National or no Labour candidate to summarise, or fewer than two matched candidates)'
    return {'electorateId': seat, 'uncertaintyClass': record['class'],
            'multipliers': {'balance': record['multiplier'], 'within': record['withinMultiplier'], 'mass': record['massMultiplier']},
            'baseline': {'basis': BASELINE_BASIS, 'partyVote': party_vote(row, keys, groups, continuing)},
            'pollUpdate': None if update is None else {
                'pollBalance': update['pollValue'], 'modelBalance': update['modelCentre'], 'updatedBalance': update['modelCentre'] + update['shift'],
                'ageWeeks': update['ageWeeks'], 'ageFactor': update['rho'], 'pollWeight': update['weight'], 'effectiveWeight': scale,
                'modelWeight': 1 - scale, 'modelSD': update['modelSD'], 'posteriorSD': update['posteriorSD']},
            'polls': [poll_row(p, update is not None, scale, note) for p in polls]}


def maori_polls(seat_name, record, polls=None, as_of=None):
    """The Maori layer's poll rows for one seat, read from the Stage82 live file the way the layer reads it (Stage86, D125): the latest poll by
    fieldwork end, among those ending by `as_of` (the data cutoff, audit J2), is the input; earlier ones are listed as superseded and later
    ones as after the cutoff. Shares are the published electorate-vote percentages excluding undecided respondents, by the poll's own party
    labels. The input must be the poll the record used; a seat on the fallback has no rows. `polls` overrides the file (tests)."""
    if 'pollFieldworkEnd' not in record:
        return []
    mine = sorted((p for p in (live_polls() if polls is None else polls) if maori_live.seat_name(p['seat']) == seat_name),
                  key=lambda p: (p['fieldwork']['end'], p['id']))
    eligible = [p for p in mine if as_of is None or p['fieldwork']['end'] <= as_of]
    used = eligible[-1] if eligible else None
    require(used is not None and used['fieldwork']['end'] == record['pollFieldworkEnd'], f'{seat_name}: the bank record does not match the current Maori poll')

    def reason(poll):
        if poll is used:
            return None
        return 'superseded by a newer poll for the seat' if poll in eligible else 'fieldwork ended after the data cutoff'
    return [{'pollId': poll['id'], 'pollster': poll.get('pollster'), 'sponsorGroup': None,
             'fieldworkStart': poll['fieldwork']['start'], 'fieldworkEnd': poll['fieldwork']['end'],
             'sampleSize': poll.get('sampleSize'), 'sampleSizeAssumed': False,
             'candidateVotePct': [{'party': k, 'pct': float(v)} for k, v in sorted(poll['electorateVotePct'].items())],
             'approximate': sorted(k for k, v in poll.get('electorateVoteFlags', {}).items() if v == 'approx'),
             'evidenceGrade': poll.get('evidenceGrade'), 'status': 'used' if poll is used else 'not-used',
             'reason': reason(poll), 'shareOfPoll': None, 'weight': None}
            for poll in mine]


def build(config, bank_seats, keys, groups, base, continuing, as_of, synthetic_maori):
    """Evidence for every simulated seat of `bank_seats` ({seat: record}). `synthetic_maori`: injected Maori records have no poll."""
    run, sha = electorate_live.pinned(config)
    module = candidate_polls if config.get('seatPolls', {}).get('rule', 'balance') == 'all-candidates' else seat_polls
    _, polls = (module.combine(as_of, rows=seat_polls.live_rows(run, sha)) if config.get('seatPolls', {}).get('enabled') else ({}, {}))
    names = {} if synthetic_maori else {v: k for k, v in maori.electorate_ids().items()}
    out = []
    for seat, record in bank_seats.items():
        if record['status'] != 'simulated':
            continue
        if record['class'] == 'maori-layer':
            out.append({'electorateId': seat, 'uncertaintyClass': 'maori-layer', 'multipliers': None, 'baseline': None, 'pollUpdate': None,
                        'polls': [] if synthetic_maori else maori_polls(names[seat], record, live_polls(run, sha), as_of)})
        else:
            out.append(general_seat(seat, record, base[seat], keys, groups, continuing, polls.get(seat, [])))
    return out
