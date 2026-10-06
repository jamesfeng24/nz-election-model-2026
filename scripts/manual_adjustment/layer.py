"""The model + James layer: apply dated seat adjustments on top of an automatic seat forecast.

Input is the automatic forecast as per-seat candidate-share draws (rows on the simplex). The layer never changes
the automatic forecast: it returns a second forecast beside it, and seats without an active entry are copied
unchanged. For an adjusted seat the targeted quantity is moved in the model's own uncertainty coordinate
(log(N/L) for the National/Labour balance, logit(share) for a party share):

    z' = zbar + delta + k (z - zbar),   k = sqrt(1 + (extra / sd_z)^2)

with `delta` solved so the mean of the targeted share moves by exactly `meanShiftPp`, and `extra` the extra sd
in percentage points converted to the coordinate with the average local slope. Hence sd(z') = sqrt(sd_z^2 +
extra^2) >= sd_z exactly: a mean shift alone never narrows the coordinate uncertainty and there is no way to
ask for less. In share space a shift toward a boundary can mechanically compress the interval (the logistic
slope is smaller there); that is reported, not hidden. An N/L shift transfers share between the two major
candidates and leaves every other candidate and the N+L mass untouched. A party-share shift rescales the other
candidates proportionally.
"""
import copy

import numpy as np

from .common import NATIONAL_KEY, LABOUR_KEY, require, canonical, sha256_text, parse_time
from .schema import active_entry

FORECAST_VERSION = 1
SIMPLEX_TOLERANCE = 1e-9


def _logit(p):
    return np.log(p) - np.log1p(-p)


def _expit(z):
    return 1.0 / (1.0 + np.exp(-z))


def check_seat(seat):
    require(isinstance(seat, dict) and {'electorateId', 'groups', 'draws'} <= set(seat), 'seat needs electorateId, groups and draws')
    draws = np.asarray(seat['draws'], dtype=float)
    require(draws.ndim == 2 and draws.shape[0] >= 2 and draws.shape[1] == len(seat['groups']),
            f'{seat["electorateId"]}: draws must be a (draws >= 2, candidates) matrix matching groups')
    require(np.isfinite(draws).all() and (draws >= 0).all() and np.all(np.abs(draws.sum(axis=1) - 1) <= SIMPLEX_TOLERANCE),
            f'{seat["electorateId"]}: every draw must be a finite share vector summing to 1')
    return draws


def _index(groups, key):
    hits = [i for i, g in enumerate(groups) if g == key]
    require(len(hits) == 1, f'party key {key!r} must appear exactly once in the seat slate, found {len(hits)}')
    return hits[0]


class _Coordinate:
    """The target quantity q, its uncertainty coordinate z and the exact inverse map for a changed z."""

    def __init__(self, draws, groups, target):
        self.draws, self.kind = draws, target['kind']
        if self.kind == 'nl_balance':
            self.n, self.l = _index(groups, NATIONAL_KEY), _index(groups, LABOUR_KEY)
            n, l = draws[:, self.n], draws[:, self.l]
            require((n > 0).all() and (l > 0).all(), 'an N/L balance adjustment needs both major candidates above zero in every draw')
            self.mass = n + l
            self.z = np.log(n) - np.log(l)
            self.share = n
        else:
            self.k = _index(groups, target['partyKey'])
            s = draws[:, self.k]
            require((s > 0).all() and (s < 1).all(), f'the party share must be strictly inside (0, 1) in every draw to adjust {target["partyKey"]}')
            self.z = _logit(s)
            self.share = s

    def slope(self):
        """Average d(share)/dz over the draws, to convert extra sd in share points to coordinate units."""
        if self.kind == 'nl_balance':
            p = _expit(self.z)
            return float(np.mean(self.mass * p * (1 - p)))
        return float(np.mean(self.share * (1 - self.share)))

    def build(self, z):
        out = self.draws.copy()
        if self.kind == 'nl_balance':
            p = _expit(z)
            out[:, self.n], out[:, self.l] = self.mass * p, self.mass * (1 - p)
        else:
            s = _expit(z)
            others = np.arange(out.shape[1]) != self.k
            out[:, others] = self.draws[:, others] * ((1 - s) / (1 - self.share))[:, None]
            out[:, self.k] = s
        return out

    def target_share(self, rebuilt):
        return rebuilt[:, self.n] if self.kind == 'nl_balance' else rebuilt[:, self.k]


def _summary(values):
    low, high = np.percentile(values, [5, 95])
    return {'mean': float(values.mean()), 'sd': float(values.std(ddof=0)), 'lower90': float(low), 'upper90': float(high)}


def adjust_seat(seat, adjustment):
    """Return (new draws, report) for one seat; `seat` and its arrays are never modified."""
    draws = check_seat(seat)
    groups = list(seat['groups'])
    coordinate = _Coordinate(draws, groups, adjustment['target'])
    z, shift, extra = coordinate.z, adjustment['meanShiftPp'] / 100, adjustment['extraSdPp'] / 100
    centre, sd = float(z.mean()), float(z.std(ddof=0))
    inflation = 1.0
    if extra > 0:
        require(sd > 0, f'{seat["electorateId"]}: draws have zero spread in the adjustment coordinate; extra uncertainty is undefined')
        inflation = float(np.sqrt(1 + (extra / coordinate.slope() / sd) ** 2))
    spread = centre + inflation * (z - centre)
    goal = float(coordinate.share.mean()) + shift

    def moved(delta):
        return float(coordinate.target_share(coordinate.build(spread + delta)).mean())

    if shift == 0 and extra == 0:
        delta = 0.0
    else:
        low, high = -40.0, 40.0
        require(moved(low) < goal < moved(high),
                f'{seat["electorateId"]}: a mean shift of {adjustment["meanShiftPp"]}pp is not reachable with these draws')
        for _ in range(300):
            delta = (low + high) / 2
            low, high = (delta, high) if moved(delta) < goal else (low, delta)
            if high - low < 1e-14:
                break
        delta = (low + high) / 2
    new = coordinate.build(spread + delta)
    require(np.isfinite(new).all() and (new >= 0).all() and np.all(np.abs(new.sum(axis=1) - 1) <= SIMPLEX_TOLERANCE),
            'adjusted draws left the simplex (internal error)')
    achieved = float(coordinate.target_share(new).mean() - coordinate.share.mean())
    require(abs(achieved - shift) <= 1e-9, f'internal error: mean shift achieved {achieved * 100:.9f}pp, asked {shift * 100:.9f}pp')
    new_z = _Coordinate(new, groups, adjustment['target']).z
    sd_after = float(new_z.std(ddof=0))
    require(sd_after >= sd - 1e-12, 'internal error: the layer narrowed the coordinate uncertainty')
    touched = [coordinate.n, coordinate.l] if coordinate.kind == 'nl_balance' else [coordinate.k]
    rest = [i for i in range(draws.shape[1]) if i not in touched]
    other_change = float(100 * np.max(np.abs(new.mean(axis=0)[rest] - draws.mean(axis=0)[rest]))) if rest else 0.0
    report = {'target': adjustment['target'], 'requestedMeanShiftPp': adjustment['meanShiftPp'], 'achievedMeanShiftPp': achieved * 100,
              'extraSdPp': adjustment['extraSdPp'],
              'coordinate': {'name': 'log(N/L)' if coordinate.kind == 'nl_balance' else 'logit(party share)',
                             'sdBefore': sd, 'sdAfter': sd_after, 'sdExpected': float(np.sqrt(sd ** 2 + (extra / coordinate.slope()) ** 2)) if extra > 0 else sd},
              'targetedShare': {'before': _summary(coordinate.share), 'after': _summary(coordinate.target_share(new))},
              'maxOtherCandidateMeanChangePp': other_change}
    report['shareWidth90Ratio'] = ((report['targetedShare']['after']['upper90'] - report['targetedShare']['after']['lower90']) /
                                    (report['targetedShare']['before']['upper90'] - report['targetedShare']['before']['lower90']))
    return new, report


def drift_pp(entry, groups, draws):
    """How far the automatic mean shares have moved since the entry recorded its `unadjusted` shares (info, pp)."""
    mean, drift = draws.mean(axis=0), {}
    for key, recorded in entry['unadjusted']['candidateShares'].items():
        hits = [i for i, g in enumerate(groups) if g == key]
        if len(hits) == 1:
            drift[key] = float(100 * (mean[hits[0]] - recorded))
    return drift


def apply_layer(forecast, documents, as_of):
    """The model + James forecast beside the untouched automatic one.

    `documents` is {electorateId: adjustment file}. Entries recorded after `as_of`, expired ones and superseded ones
    are ignored, so replaying an earlier date reproduces what James had entered then. Seats flagged exceptional (with
    or without a numeric adjustment) are listed so the calibration set can leave them out."""
    when = parse_time(as_of, 'as_of')
    require(isinstance(forecast, dict) and forecast.get('schemaVersion') == FORECAST_VERSION and
            forecast.get('kind') == 'automatic-seat-forecast', 'forecast must be an automatic-seat-forecast v1 document')
    automatic_hash = sha256_text(canonical(forecast))
    pristine = copy.deepcopy(forecast)
    seats = {s['electorateId']: s for s in forecast['seats']}
    require(len(seats) == len(forecast['seats']), 'duplicate electorateId in the automatic forecast')
    unknown = sorted(set(documents) - set(seats))
    require(not unknown, f'adjustment files for seats absent from the automatic forecast: {unknown}')
    output, applied, flagged = [], [], []
    for seat in forecast['seats']:
        entry = active_entry(documents[seat['electorateId']], when) if seat['electorateId'] in documents else None
        if entry is None:
            output.append(copy.deepcopy(seat))
            continue
        row = {k: v for k, v in seat.items() if k != 'draws'}
        info = {'electorateId': seat['electorateId'], 'entryId': entry['entryId'], 'digest': entry['digest'], 'author': entry['author'],
                'recordedAt': entry['recordedAt'], 'expiresAt': entry['expiresAt'], 'reason': entry['reason'],
                'exceptionalSeat': entry['exceptionalSeat'], 'sources': entry['sources']}
        if entry['adjustment'] is None:
            row['draws'] = copy.deepcopy(seat['draws'])
        else:
            new, report = adjust_seat(seat, entry['adjustment'])
            row['draws'] = new.tolist()
            info['report'] = report
            info['automaticDriftSinceEntryPp'] = drift_pp(entry, seat['groups'], check_seat(seat))
        row['adjustment'] = info
        output.append(row)
        applied.append(info)
        if entry['exceptionalSeat']['flag']:
            flagged.append(seat['electorateId'])
    require(forecast == pristine, 'internal error: the automatic forecast was modified')
    return {'schemaVersion': FORECAST_VERSION, 'kind': 'model-plus-james-seat-forecast', 'electionId': forecast['electionId'],
            'automaticForecastId': forecast['forecastId'], 'automaticSha256': automatic_hash, 'asOf': as_of,
            'synthetic': forecast.get('synthetic', False), 'adjustedSeats': applied, 'exceptionalSeats': sorted(flagged),
            'seats': output}
