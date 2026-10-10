"""Stage85 per-seat evidence: display data for the seat pages, derived from inputs the bank already used.

One record per simulated seat: its D107 uncertainty class and multipliers, the 2023 party-vote baseline it started from (general
seats), the seat polls that were found with the share each took of the combined poll and how much each moved the model, and the
size of the poll update. Nothing here feeds a forecast number; it is computed after the seats are simulated and is left out of the
bank digest (`assemble.bank_digest`), so adding or changing it never changes a bank's simulated content.

Polls: a general seat's `weight` is exactly its contribution to the updated National/Labour balance. The update is linear in the
combined poll, centre = model + k (poll - model) with k = rho * w, and the combined poll is the share-weighted mean of the polls, so
poll i moves the centre by `weight` = k * share_i of the gap to its own value and the model keeps 1 - k (`pollUpdate.modelWeight`).
A Maori seat's poll is the one input of the Stage66 layer, so it has no share or weight.
"""
from scripts.maori_seat_layer.simulate import current_polls
from scripts.seat_polls import live as seat_polls
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
    note = None if update else 'the seat has no National or no Labour candidate, so the poll could not update the balance'
    return {'electorateId': seat, 'uncertaintyClass': record['class'],
            'multipliers': {'balance': record['multiplier'], 'within': record['withinMultiplier'], 'mass': record['massMultiplier']},
            'baseline': {'basis': BASELINE_BASIS, 'partyVote': party_vote(row, keys, groups, continuing)},
            'pollUpdate': None if update is None else {
                'pollBalance': update['pollValue'], 'modelBalance': update['modelCentre'], 'updatedBalance': update['modelCentre'] + update['shift'],
                'ageWeeks': update['ageWeeks'], 'ageFactor': update['rho'], 'pollWeight': update['weight'], 'effectiveWeight': scale,
                'modelWeight': 1 - scale, 'modelSD': update['modelSD'], 'posteriorSD': update['posteriorSD']},
            'polls': [poll_row(p, update is not None, scale, note) for p in polls]}


def maori_polls(seat_name, record):
    """The Maori layer's poll rows for one seat: the latest poll is the input, earlier ones are listed as superseded. A seat without a
    poll has none. The polls are read the way the layer reads them (`current_polls`); the latest must be the poll the record used."""
    if 'pollFieldworkEnd' not in record:
        return []
    latest, superseded, data = current_polls()
    require(seat_name in latest and latest[seat_name]['fieldworkEnd'] == record['pollFieldworkEnd'],
            f'{seat_name}: the bank record does not match the current Maori poll')
    rows = []
    for poll in [p for p in data['polls'] if p['seat'] == seat_name]:
        used = poll['id'] == latest[seat_name]['id']
        rows.append({'pollId': poll['id'], 'pollster': poll.get('pollster'), 'sponsorGroup': None,
                     'fieldworkStart': poll['fieldworkStart'], 'fieldworkEnd': poll['fieldworkEnd'],
                     'sampleSize': poll.get('sampleSize'), 'sampleSizeAssumed': False,
                     'candidateVotePct': [{'party': c['party'], 'pct': float(c['pollPercent']), 'name': c['name']} for c in poll['candidates']],
                     'approximate': [], 'evidenceGrade': None, 'status': 'used' if used else 'not-used',
                     'reason': None if used else 'superseded by a newer poll for the seat', 'shareOfPoll': None, 'weight': None})
    return sorted(rows, key=lambda r: (r['fieldworkEnd'], r['pollId']))


def build(config, bank_seats, keys, groups, base, continuing, as_of, synthetic_maori):
    """Evidence for every simulated seat of `bank_seats` ({seat: record}). `synthetic_maori`: injected Maori records have no poll."""
    _, polls = (seat_polls.combine(as_of) if config.get('seatPolls', {}).get('enabled') else ({}, {}))
    names = {} if synthetic_maori else {v: k for k, v in maori.electorate_ids().items()}
    out = []
    for seat, record in bank_seats.items():
        if record['status'] != 'simulated':
            continue
        if record['class'] == 'maori-layer':
            out.append({'electorateId': seat, 'uncertaintyClass': 'maori-layer', 'multipliers': None, 'baseline': None, 'pollUpdate': None,
                        'polls': [] if synthetic_maori else maori_polls(names[seat], record)})
        else:
            out.append(general_seat(seat, record, base[seat], keys, groups, continuing, polls.get(seat, [])))
    return out
