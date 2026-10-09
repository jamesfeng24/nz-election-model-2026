"""The 2026 slates of the seven Maori electorates from the Stage50 official table, mapped to party codes (fail closed on an unknown label)."""
from scripts.maori_seat_fallback import history
from scripts.maori_seat_fallback.common import read, fold, INPUTS, SEATS


def label_codes():
    return read(INPUTS)['labelCodes']


def slates():
    """{seat: [{'name', 'label', 'party'}]} in official-table order; every seat must be present."""
    inputs = read(INPUTS)
    codes = inputs['labelCodes']
    table = read(inputs['officialTable'])['rows']
    by_key = {fold(s): s for s in SEATS}
    out = {s: [] for s in SEATS}
    for r in table:
        seat = by_key.get(fold(r['electorateLabel']))
        if seat is None:
            continue
        if r['affiliationLabel'] not in codes:
            raise ValueError('Unmapped 2026 affiliation label in %s: %r' % (seat, r['affiliationLabel']))
        out[seat].append({'name': r['displayName'], 'label': r['affiliationLabel'], 'party': codes[r['affiliationLabel']]})
    empty = [s for s, v in out.items() if len(v) < 2]
    if empty:
        raise ValueError('Official table lacks a slate for: ' + ', '.join(empty))
    return out


def split_for(seat, slate, res=None):
    """The registered split incumbent for the seat (or None), checked against the previous election's result."""
    res = res or history.results()
    for rec in read(INPUTS)['splitIncumbents']:
        if rec['seat'] != seat:
            continue
        names = [c['name'] for c in slate]
        if rec['displayName'] not in names:
            raise ValueError('Split incumbent is not on the %s slate: %s' % (seat, rec['displayName']))
        prior = [c for c in res[2023][seat]['candidates'] if c['party'] == rec['fromCode']]
        if len(prior) != 1 or fold(prior[0]['name'].split(',')[0]) != fold(rec['priorCandidateSurname']):
            raise ValueError('The 2023 %s candidate in %s is not %s' % (rec['fromCode'], seat, rec['priorCandidateSurname']))
        if next(c for c in slate if c['name'] == rec['displayName'])['party'] != rec['candidateCode']:
            raise ValueError('Split incumbent code differs from the official affiliation')
        return {'name': rec['displayName'], 'fromCode': rec['fromCode']}
    return None


def seat_inputs(seat, slate, res=None):
    res = res or history.results()
    return history.build_inputs(res[2023][seat]['candidates'], slate, split=split_for(seat, slate, res))
