"""Seat polls for every candidate (James, 2026-10-11): fundamentals blended with the poll's figure for each candidate.

The Stage79 / D117 rule moves only the candidate National/Labour balance and ignores a poll whose top two are not National and Labour.
This rule uses every candidate the poll publishes and we can match to a party column, in every seat. It is deliberately simple:

* Observation: the matched candidates' published shares, rescaled to sum to 1, as log-odds against the poll's leading candidate.
* Poll error: multinomial sampling variance of those log-odds, times `INFLATION`, plus the sponsor allowance of the design contract
  (labour-aligned 0.12 on Labour's own log-share), with each poll's variance divided by the square of its age factor (the 6-week
  half-life of D117/D123). Polls from different pollsters are applied one after another (inverse-variance combination for independent
  errors); of one pollster only the newest poll counts.
* Update: the model's own spread of those log-odds across the simulated elections (so its correlation with the national draw is
  kept) is combined with the poll, and every simulated election's shares for the matched candidates move by the same gain, with a
  perturbed observation per row so the spread stays correct. The gain keeps the D117 cap of 0.60. The matched candidates keep their
  combined share; unmatched candidates keep theirs. National, local-party and Maori layers, MMP and the D107 multipliers are untouched.

`INFLATION` is not the Stage79 constant (5.29, National/Labour only): re-scoring the 12 usable historical seat polls on every candidate
contrast gave an error about 3.3 times the sampling SD (`docs/stage89-seat-polls-all-candidates.md`). No bias term is applied.
"""
import numpy as np
from .common import read, fold, DESIGN
from .live import live_rows, seat_ids, canonical_names, source_key, date

INFLATION = 10.0
CAP = 0.60
HALF_LIFE_WEEKS = 6.0
ASSUMED_SAMPLE = 400
FLOOR = 1e-12

# 2026 ballot group key -> the column code of the seat-poll tables
COLUMNS = {'nationalparty': 'NAT', 'labourparty': 'LAB', 'greenparty': 'GRN', 'actnewzealand': 'ACT', 'newzealandfirstparty': 'NZF',
           'opportunity': 'TOP', 'tepatimaori': 'TPM'}


def allowance(design, group):
    table = design['pollError']['allowance']
    return table.get(group, table['all other groups'])


def usable(poll, as_of):
    """Reason a poll cannot count, else None."""
    if poll['election'] != 2026:
        return 'not a 2026 poll'
    if poll['excluded']:
        return 'excluded from the model'
    if date(poll['fieldworkEnd']) > date(as_of):
        return 'fieldwork ended after the data cutoff'
    shares = {k: float(v) for k, v in poll['candidateVotePct'].items() if k in COLUMNS.values() and float(v) > 0}
    if len(shares) < 2:
        return 'fewer than two published candidates can be matched to a party'
    return None


def combine(as_of, rows=None, design=None):
    """(polls, detail): `polls` is {seat id: [poll, ...]} oldest first (newest poll per pollster), `detail` the display rows per seat as
    `scripts.seat_polls.live.combine` gives them (status, reason, share of the combined poll). Display only: nothing in `polls` reads it."""
    design = design or read(DESIGN)
    ids = seat_ids()
    names = {i: n for n, i in canonical_names().items()}
    by_seat, detail = {}, {}
    for poll in (rows if rows is not None else live_rows()):
        if poll['election'] != 2026:
            continue
        if fold(poll['electorate']) not in ids:
            raise ValueError(f"unknown electorate in a seat poll: {poll['electorate']}")
        seat = ids[fold(poll['electorate'])]
        reason = usable(poll, as_of)
        assumed = poll['sampleSize'] is None
        detail.setdefault(seat, {})[poll['id']] = {
            'pollId': poll['id'], 'pollster': poll['pollster'], 'sponsorGroup': poll['sponsorGroup'], 'fieldworkStart': poll['fieldworkStart'],
            'fieldworkEnd': poll['fieldworkEnd'], 'sampleSize': ASSUMED_SAMPLE if assumed else poll['sampleSize'], 'sampleSizeAssumed': assumed,
            'candidateVotePct': dict(poll['candidateVotePct']), 'approximate': poll.get('approximate', []), 'evidenceGrade': poll.get('evidenceGrade'),
            'status': 'not-used' if reason else 'used', 'reason': reason, 'share': None}
        if not reason:
            by_seat.setdefault(seat, {}).setdefault(source_key(poll['pollster']), []).append(poll)
    out = {}
    for seat, sources in by_seat.items():
        chosen = []
        for entries in sources.values():
            entries.sort(key=lambda p: (p['fieldworkEnd'], p['id']))
            for older in entries[:-1]:
                detail[seat][older['id']].update(status='not-used', reason='superseded by a newer poll from the same pollster')
            chosen.append(entries[-1])
        chosen.sort(key=lambda p: (p['fieldworkEnd'], p['id']))
        precision = {}
        for p in chosen:
            age = max(0.0, (date(as_of) - date(p['fieldworkEnd'])).days / 7)
            rho = 0.5 ** (age / HALF_LIFE_WEEKS)
            precision[p['id']] = rho ** 2 / np.mean(np.diag(error_covariance(p, design)))
        total = sum(precision.values())
        for p in chosen:
            detail[seat][p['id']]['share'] = precision[p['id']] / total
        out[seat] = {'polls': chosen, 'asOf': as_of, 'electorate': names[seat]}
    order = lambda r: (r['fieldworkEnd'], r['pollId'])
    return out, {seat: sorted(polls.values(), key=order) for seat, polls in detail.items()}


def inputs(as_of, rows=None, design=None):
    return combine(as_of, rows, design)[0]


def matched(poll):
    """Poll columns we can match, as {code: published percent}, in a stable order."""
    return {k: float(poll['candidateVotePct'][k]) for k in sorted(poll['candidateVotePct'])
            if k in COLUMNS.values() and float(poll['candidateVotePct'][k]) > 0}


def error_covariance(poll, design, reference=None):
    """Covariance of the poll's matched log-odds against `reference` (default: the leader), in the order of `matched(poll)` without it."""
    shares = matched(poll)
    n = ASSUMED_SAMPLE if poll['sampleSize'] is None else poll['sampleSize']
    leader = reference or max(shares, key=shares.get)
    d = {k: INFLATION / (n * v / 100) + (allowance(design, poll['sponsorGroup']) ** 2 if k == 'LAB' else 0.0) for k, v in shares.items()}
    others = [k for k in shares if k != leader]
    return np.diag([d[k] for k in others]) + d[leader]


def balance(q, parties):
    """log(National / Labour) per row, or None when the seat has no candidate of one of them."""
    if 'nationalparty' not in parties or 'labourparty' not in parties:
        return None
    return np.log(np.maximum(q[:, parties.index('nationalparty')], FLOOR) / np.maximum(q[:, parties.index('labourparty')], FLOOR))


def apply(q, parties, seat_polls, shared_balance_sd, seed, design=None):
    """(updated shares, record) for one seat. `q` [rows, candidates]; `parties` the candidates' 2026 group keys (None for no group).
    The record has the Stage79 `seatPoll` shape (a summary on the National/Labour balance), so the bank schema and the seat evidence are unchanged."""
    design = design or read(DESIGN)
    q = np.asarray(q, dtype=float)
    rng = np.random.default_rng(seed)
    code_of = {i: COLUMNS.get(g) for i, g in enumerate(parties)}
    out = q.copy()
    polls = []
    for poll in seat_polls['polls']:
        shares = matched(poll)
        index = [i for i, c in code_of.items() if c in shares]
        if len(index) < 2:
            continue
        codes = [code_of[i] for i in index]
        shares = {c: shares[c] for c in codes}
        leader = max(shares, key=shares.get)
        ref = codes.index(leader)
        rest = [j for j in range(len(codes)) if j != ref]
        y = np.log(np.array([shares[codes[j]] for j in rest]) / shares[leader])
        z = np.log(np.maximum(out[:, index], FLOOR))
        mass = out[:, index].sum(axis=1)
        x = (z - z[:, [ref]])[:, rest]
        sigma = np.atleast_2d(np.cov(x.T))
        age = max(0.0, (date(seat_polls['asOf']) - date(poll['fieldworkEnd'])).days / 7)
        rho = 0.5 ** (age / HALF_LIFE_WEEKS)
        v = error_covariance({**poll, 'candidateVotePct': {c: shares[c] for c in codes}}, design, leader)
        v_aged = v / rho ** 2
        gain = sigma @ np.linalg.inv(sigma + v_aged)
        gain *= min(1.0, CAP / float(np.max(np.linalg.eigvals(gain).real)))
        noise = rng.multivariate_normal(np.zeros(len(rest)), v_aged, size=len(x))
        new = x + (y + noise - x) @ gain.T
        logit = np.zeros((len(x), len(codes)))
        logit[:, rest] = new
        w = np.exp(logit)
        out[:, index] = w / w.sum(axis=1, keepdims=True) * mass[:, None]
        polls.append(poll)
    if not polls:
        return q, None
    before, after = balance(q, parties), balance(out, parties)
    ages = [max(0.0, (date(seat_polls['asOf']) - date(p['fieldworkEnd'])).days / 7) for p in polls]
    rho = 0.5 ** (min(ages) / HALF_LIFE_WEEKS)
    if before is None:
        return out, None  # no National or no Labour candidate: the shares moved, but there is no balance to summarise for the evidence
    model_centre, updated = float(before.mean()), float(after.mean())
    poll_value, poll_variance = nl_summary(polls, design, seat_polls['asOf'], model_centre, updated)
    gap = poll_value - model_centre
    effective = 0.0 if abs(gap) < 1e-9 else min(max((updated - model_centre) / gap, 0.0), 1.0)
    return out, {'pollIds': [p['id'] for p in polls], 'pollValue': poll_value, 'pollVariance': poll_variance, 'ageWeeks': min(ages),
                 'rho': rho, 'weight': min(1.0, effective / rho) if rho > 0 else 0.0, 'modelCentre': model_centre,
                 'modelSD': float(before.std()), 'shift': updated - model_centre, 'posteriorSD': max(float(after.std()), 1e-6),
                 'sharedSD': float(shared_balance_sd)}


def nl_summary(polls, design, as_of, fallback_centre, fallback_updated):
    """The polls' own log(National/Labour) and its variance (inverse-variance over the polls that publish both), for the seat evidence
    display only. With no poll publishing both, the updated model value stands in and the variance is large (the display shows no gap)."""
    values, precisions = [], []
    for poll in polls:
        shares = matched(poll)
        if 'NAT' not in shares or 'LAB' not in shares:
            continue
        n = ASSUMED_SAMPLE if poll['sampleSize'] is None else poll['sampleSize']
        variance = INFLATION * (1 / (n * shares['NAT'] / 100) + 1 / (n * shares['LAB'] / 100)) + allowance(design, poll['sponsorGroup']) ** 2
        values.append(float(np.log(shares['NAT'] / shares['LAB'])))
        precisions.append(1 / variance)
    if not values:
        return fallback_updated, 1.0
    precision = sum(precisions)
    return sum(v * p for v, p in zip(values, precisions)) / precision, 1 / precision
