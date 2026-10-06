"""Join curated polls to official results: named-candidate closure, contrasts and the calibration table."""
import math
from datetime import date
from scripts.maori_seat_layer.common import (read, fold, group, SEATS, YEARS, ELECTION_DATES, HISTORICAL_POLLS, PREFIX)


def days_to_election(year, end):
    return (date.fromisoformat(ELECTION_DATES[year]) - date.fromisoformat(end)).days


def resolve(entry, official):
    """Official candidate for a poll entry: party must agree, and the surname (when given) must match; unique or fail."""
    matches = [c for c in official if c['party'] == entry['party']]
    if entry.get('name'):
        key = fold(entry['name'])
        tokens = lambda c: [fold(t) for t in c['name'].split(',')[0].replace('-', ' ').split() if len(t) > 2]
        matches = [c for c in matches if any(t and t in key for t in tokens(c))]
    if len(matches) != 1:
        raise ValueError('Cannot resolve poll candidate uniquely: %r (%d matches)' % (entry, len(matches)))
    return matches[0]


def closure(values):
    total = sum(values)
    return [v / total for v in values]


def calibration_rows():
    polls = read(HISTORICAL_POLLS)['polls']
    results = read(PREFIX + '/historical-results.json')['years']
    rows = []
    for poll in polls:
        official = results[str(poll['year'])][poll['seat']]['candidates']
        entries = [e for e in poll['candidates'] if e['pollPercent'] > 0]  # a listed 0% cannot enter a log-share model
        resolved = [resolve(e, official) for e in entries]
        names = [c['name'] for c in resolved]
        if len(set(names)) != len(names):
            raise ValueError('Duplicate resolved candidate in ' + poll['id'])
        q = closure([e['pollPercent'] for e in entries])
        votes = [c['votes'] for c in resolved]
        v = closure(votes)
        parties = [e['party'] for e in entries]
        if parties.count('MP') > 1 or parties.count('LAB') != 1:
            raise ValueError('Each calibration poll needs one LAB candidate and at most one MP candidate: ' + poll['id'])
        has_contrast = parties.count('MP') == 1
        i, j = (parties.index('MP') if has_contrast else None), parties.index('LAB')
        total = results[str(poll['year'])][poll['seat']]['validCandidateVotes']
        top = max(official, key=lambda c: c['votes'])
        rows.append({
            'id': poll['id'], 'year': poll['year'], 'seat': poll['seat'], 'pollster': poll['pollster'],
            'horizonDays': days_to_election(poll['year'], poll['fieldworkEnd']), 'dateQuality': poll['dateQuality'],
            'candidates': [{'name': c['name'], 'party': p, 'group': group(p), 'pollClosed': q[k], 'resultClosed': v[k], 'resultShare': c['votes'] / total}
                           for k, (c, p) in enumerate(zip(resolved, parties))],
            'contrastD': (math.log(v[i] / v[j]) - math.log(q[i] / q[j])) if has_contrast else None,
            'unnamedShare': 1.0 - sum(votes) / total,
            'pollLeader': resolved[max(range(len(q)), key=lambda k: q[k])]['name'],
            'actualWinner': top['name'], 'winnerNamed': top['name'] in names,
            'leaderWon': resolved[max(range(len(q)), key=lambda k: q[k])]['name'] == top['name']})
    seats = {(r['year'], r['seat']) for r in rows}
    if len(seats) != len(rows):
        raise ValueError('Calibration uses one poll per seat and election')
    return rows
