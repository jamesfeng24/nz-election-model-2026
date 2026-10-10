"""Maori seats: the Stage66 default layer re-run for the polled seats; the unpolled seats use the registered Stage78 fallback.

The polled seats are those with a Maori poll in the newest Stage82 live-inputs run (Stage86, D125), not the pinned 2026-10-07 transcription: a new
Maori seat poll is a data-only addition and moves its seat from the fallback to the Stage66 layer. The calibration is unchanged.

Stage66 stores only a 500-draw preview, so the registered model is re-simulated here with the assembly's draw
count. Maori draws are independent of the national draw (Stage66 default; any coupling needs a stated correlation).
Unpolled seats follow `maori.unpolledFallbackModel` (D114, D115): `stage78-f` draws the 2023 result carried forward by party label
with Stage66's calibrated error and no seat poll (Stage78 arm F, James's choice, 2026-10-09). The fallback block is independent of the polled
block. With no model registered the unpolled seats stay `unavailable` with that reason, never a default or a guess.

Candidates carry the official roster ids (`config.candidate.features`, Stage50 part 2). A poll's candidates are matched to the roster by
surname and party; any candidate that does not match exactly one roster entry fails the build.
"""
from scripts.maori_seat_fallback.draws import f_shares
from scripts.maori_seat_layer.common import SEATS, fold
from scripts.maori_seat_layer.fit import fit
from scripts.maori_seat_layer.run import parameters
from scripts.maori_seat_layer.live import current_polls
from scripts.maori_seat_layer.simulate import simulate as simulate_layer
from .common import TARGET_FRAME, read, require, namespace_seed
from .summaries import share_summaries

FALLBACK_MODEL = 'stage78-f'
FALLBACK_SOURCE = 'Stage78 no-poll fallback: 2023 result carried forward, no seat poll (D115)'
# Stage66/Stage78 party codes -> 2026 ballot-group keys of the official roster; None is an independent or an unregistered party. Any other code fails closed.
PARTIES = {'MP': 'tepatimaori', 'LAB': 'labourparty', 'GRN': 'greenparty', 'NAT': 'nationalparty', 'NZF': 'newzealandfirstparty',
           'ALC': 'aotearoalegalisecannabisparty', 'TOP': 'opportunity', 'TTT': 'tetaitokerauparty', 'NZL': 'newzealandloyal',
           'PIC': None, 'IND': None}


def electorate_ids():
    frame = read(TARGET_FRAME)['records']
    ids = {fold(r['canonicalName']): r['targetElectorateId'] for r in frame if r['scope'] == 'maori'}
    require(len(ids) == len(SEATS) and all(fold(s) in ids for s in SEATS), 'Maori seat names do not match the 2026 frame')
    return {s: ids[fold(s)] for s in SEATS}


def roster(config, ids):
    """{seat: [{'id', 'name', 'group'}]}: the active official candidates of each Maori seat, from the configured roster."""
    require(config['roster']['snapshotId'] is not None, 'roster.snapshotId is pending: the Maori candidates need the official roster')
    by_electorate = {v: k for k, v in ids.items()}
    out = {seat: [] for seat in SEATS}
    for r in read(config['candidate']['features'])['candidateRecords']:
        seat = by_electorate.get(r['targetElectorateId'])
        if seat is not None and r['active']:
            out[seat].append({'id': r['targetOccurrenceId'], 'name': r['displayedName'], 'group': r['ballotGroupKey']})
    for seat, people in out.items():
        require(len(people) >= 2 and len({p['id'] for p in people}) == len(people), f'{seat}: the roster has fewer than two distinct candidates')
    return out


def surname(display):
    """The upper-case run at the end of an official displayed name ('Lisa TE MORENGA' -> 'TE MORENGA')."""
    tokens = display.split()
    keep = []
    for token in reversed(tokens):
        if not token.isupper():
            break
        keep.append(token)
    require(keep, f'no upper-case surname in {display!r}')
    return ' '.join(reversed(keep))


def match(seat, name, code, people):
    """The one roster entry whose surname ends the poll name and whose ballot group is the code's group."""
    require(code in PARTIES, f'{seat}: unmapped Maori party code {code}')
    found = [p for p in people if fold(name).endswith(fold(surname(p['name']))) and p['group'] == PARTIES[code]]
    require(len(found) == 1, f'{seat}: {name} ({code}) matches {len(found)} roster candidates')
    return found[0]


def resolver(people):
    """`resolve(seat, party_code)` for the live poll reader: the displayed name of the one active official candidate whose ballot group is the
    code's group (an independent column resolves only when the seat's roster has exactly one independent), else the build fails."""
    def resolve(seat, code):
        require(code in PARTIES, f'{seat}: unmapped Maori party code {code}')
        found = [p for p in people[seat] if p['group'] == PARTIES[code]]
        require(len(found) == 1, f'{seat}: a {code} poll share matches {len(found)} official candidates')
        return found[0]['name']
    return resolve


def record(source, people, shares, extra=None):
    """A simulated seat record from roster entries (in order) and their closed shares (draws x candidates)."""
    ids = [p['id'] for p in people]
    return {'status': 'simulated', 'class': 'maori-layer', 'source': source, **(extra or {}),
            'candidates': ids, 'candidateNames': [p['name'] for p in people], 'candidateParty': [p['group'] for p in people],
            'candidateShares': share_summaries(ids, shares), 'winners': [int(i) for i in shares.argmax(axis=1)]}


def simulate(config, count):
    """Return {electorateId: record}; records are simulated (winner party per draw) or unavailable with a reason."""
    require(config['maori']['layer'] == 'stage66-default', 'only the Stage66 default Maori layer is registered')
    fallback = config['maori']['unpolledFallbackModel']
    require(fallback in (None, FALLBACK_MODEL), f'unregistered Maori fallback model: {fallback}')
    require(fallback is None or config['maori']['unpolledSeats'] == 'labelled-fallback', 'a fallback model needs maori.unpolledSeats = labelled-fallback')
    ids = electorate_ids()
    people = roster(config, ids)
    polls, _ = current_polls(resolver(people))
    fitted = fit()[0]['fit']
    sim = simulate_layer(polls, parameters(fitted), count, namespace_seed(config['simulation']['seedNamespace'], 'maori'))
    unpolled = [seat for seat in SEATS if seat not in sim['seats']]
    drawn = (f_shares(unpolled, count, namespace_seed(config['simulation']['seedNamespace'], 'maori-fallback'))
             if fallback is not None and unpolled else {})
    out = {}
    for seat in SEATS:
        if seat in sim['seats']:
            s = sim['seats'][seat]
            matched = [match(seat, c['name'], c['party'], people[seat]) for c in s['poll']['candidates']]
            require(len({p['id'] for p in matched}) == len(matched), f'{seat}: two poll candidates match one roster candidate')
            out[ids[seat]] = record(f"Stage66 default; poll {s['poll']['id']}", matched, s['share'], {'pollFieldworkEnd': s['poll']['fieldworkEnd']})
        elif seat in drawn:
            inp, shares = drawn[seat]
            slate = []
            for name, code in zip(inp['names'], inp['codes']):
                found = [p for p in people[seat] if fold(p['name']) == fold(name)]
                require(len(found) == 1, f'{seat}: fallback candidate {name} matches {len(found)} roster candidates')
                require(code in PARTIES and found[0]['group'] == PARTIES[code], f'{seat}: {name} has code {code} but roster group {found[0]["group"]}')
                slate.append(found[0])
            require(len(slate) == len(people[seat]), f'{seat}: the fallback slate and the roster differ')
            out[ids[seat]] = record(FALLBACK_SOURCE, slate, shares)
        else:
            decision = config['maori']['unpolledSeats']
            reason = ('unpolled; maori.unpolledSeats is pending James' if decision is None
                      else 'unpolled; withheld by decision (D114)' if decision == 'withhold'
                      else 'unpolled; labelled fallback chosen (D114) but no fallback model is registered yet (maori.unpolledFallbackModel)')
            out[ids[seat]] = {'status': 'unavailable', 'reason': reason}
    return out
