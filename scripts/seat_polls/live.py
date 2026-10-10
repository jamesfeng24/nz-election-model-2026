"""Stage79 2026 poll inputs: eligible polls per general seat, merged by source, aged to the data cutoff.

Fails closed: a seat with polls from more than one source is not defined by the frozen design and raises.
"""
import datetime
from . import model
from .common import ROOT, read, fold, parameters, POLLS, DESIGN, PREFIX
from .data import derived

TARGET_FRAME = 'data/processed/forecast-readiness/snapshots/2026-10-05/target-frame.json'
FIT = PREFIX + '/fit.json'


def seat_ids():
    return {fold(r['canonicalName']): r['targetElectorateId'] for r in read(TARGET_FRAME)['records'] if r['scope'] == 'general'}


def date(text):
    return datetime.date.fromisoformat(text)


def inputs(as_of, fit=None, design=None, rows=None):
    """{seat id: {'value', 'variance', 'rho', 'ageWeeks', 'pollIds', ...}} for polls with fieldwork ending on or before `as_of`."""
    design = design or read(DESIGN)
    fit = fit or read(FIT)
    p = parameters(design)
    ids = seat_ids()
    by_seat = {}
    for poll in (rows if rows is not None else read(POLLS)['polls']):
        if poll['election'] != 2026 or poll['excluded']:
            continue
        d = derived(poll, design)
        if not d['eligible'] or date(poll['fieldworkEnd']) > date(as_of):
            continue
        seat = ids[fold(poll['electorate'])]
        allowance = design['pollError']['allowance'].get(poll['sponsorGroup'], design['pollError']['allowance']['all other groups'])
        variance = fit['inflation'] * d['samplingVariance'] + allowance ** 2
        by_seat.setdefault(seat, []).append({'poll': poll, 'value': d['value'], 'variance': variance})
    out = {}
    for seat, entries in by_seat.items():
        entries.sort(key=lambda e: e['poll']['fieldworkEnd'])
        sources = {e['poll']['pollster'] for e in entries}
        if len(sources) > 1:
            raise ValueError(f'{seat}: polls from more than one source are not defined by the Stage79 design')
        for a, b in zip(entries, entries[1:]):
            if (date(b['poll']['fieldworkStart']) - date(a['poll']['fieldworkEnd'])).days > p['mergeDays']:
                raise ValueError(f'{seat}: two polls of one source more than {p["mergeDays"]} days apart are not defined by the design')
        value, variance = model.merge_same_source([(e['value'], e['variance']) for e in entries], p['later'])
        end = max(date(e['poll']['fieldworkEnd']) for e in entries)
        age = (date(as_of) - end).days / 7
        out[seat] = {'value': value, 'variance': variance, 'ageWeeks': age, 'rho': model.age_factor(age, p['halfLifeWeeks']),
                     'cap': p['cap'], 'pollIds': [e['poll']['id'] for e in entries], 'electorate': entries[0]['poll']['electorate']}
    return out
