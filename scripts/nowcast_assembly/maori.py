"""Maori seats: the Stage66 default layer re-run for the polled seats; the unpolled seats use the registered Stage78 fallback.

The polled seats are those with a Maori poll, ending by the data cutoff, in the Stage82 live-inputs run that `seatPolls.electorateRun` pins (Stage86,
D125; audit J2), not the 2026-10-07 transcription: a new Maori seat poll is a data-only addition and moves its seat from the fallback to the
Stage66 layer once its run is adopted. The calibration is unchanged.

Stage66 stores only a 500-draw preview, so the registered model is re-simulated here with the assembly's draw
count. Maori draws are independent of the national draw (Stage66 default; any coupling needs a stated correlation).
Unpolled seats follow `maori.unpolledFallbackModel` (D114, D115): `stage78-f` draws the 2023 result carried forward by party label
with Stage66's calibrated error and no seat poll (Stage78 arm F, James's choice, 2026-10-09). The fallback block is independent of the polled
block. With no model registered the unpolled seats stay `unavailable` with that reason, never a default or a guess.

Candidates carry the official roster ids (`config.candidate.features`, Stage50 part 2). A poll's candidates are matched to the roster by
surname and party; any candidate that does not match exactly one roster entry fails the build.
"""
import numpy as np
from scripts.maori_seat_calibration.inflation import arm_p
from scripts.maori_seat_calibration.readout import simulate as stage71_simulate
from scripts.maori_seat_fallback.draws import f_shares
from scripts.maori_seat_layer.common import SEATS, fold
from scripts.maori_seat_layer.fit import fit
from scripts.maori_seat_layer.run import parameters
from scripts.maori_seat_layer import live as maori_live
from scripts.polling import electorate_live
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


def with_unpolled_candidates(roster_people, matched, shares):
    """Every official candidate of a polled seat, not only those with a poll share (Stage86, D125).

    Stage66 simulates the candidates the poll names and keeps the rest as one unnamed remainder `w` per draw (1 minus the named shares), which by
    its definition goes to candidates outside the named set. The official roster names them, so each rostered candidate without a poll share
    gets an equal part of `w` in every draw (the poll gives no basis for any other split; placeholder allocation, stated in the docs). Stage66
    never lets a candidate outside the poll win, so the winners stay those of the named candidates. Returns (people, shares, named count).
    """
    missing = [p for p in roster_people if p['id'] not in {m['id'] for m in matched}]
    if not missing:
        return matched, shares, len(matched)
    remainder = np.clip(1.0 - shares.sum(axis=1), 0.0, None)
    extra = np.repeat((remainder / len(missing))[:, None], len(missing), axis=1)
    return matched + missing, np.hstack([shares, extra]), len(matched)


def record(source, people, shares, extra=None, named=None):
    """A simulated seat record from roster entries (in order) and their shares (draws x candidates); winners are among the first `named` columns."""
    ids = [p['id'] for p in people]
    return {'status': 'simulated', 'class': 'maori-layer', 'source': source, **(extra or {}),
            'candidates': ids, 'candidateNames': [p['name'] for p in people], 'candidateParty': [p['group'] for p in people],
            'candidateShares': share_summaries(ids, shares),
            'winners': [int(i) for i in shares[:, :named].argmax(axis=1)]}


def inflation_winners(polls, count, namespace):
    """{seat: winner index per draw} of the polled seats under Stage71's arm P (audit J1, D127): the same polls and Stage66 control fit with
    sigma^2 and tau^2 multiplied by a lambda drawn per draw from Stage71's bootstrap, simulated by Stage71's readout simulator on its own seed
    streams. Indices follow the poll's candidate order, which is the order of the record's named candidates. Only the winners are kept: the
    published shares and the MMP layer stay on the Stage66 control (C), so P is the other end of the labelled range, never a second law."""
    if not polls:
        return {}
    est, lam = arm_p()
    pick = np.random.default_rng(namespace_seed(namespace, 'maori-inflation-lambda')).integers(0, len(lam), count)
    # The unnamed-remainder list only advances each seat's stream after its winners are drawn, so a placeholder leaves the winners unchanged.
    sim = stage71_simulate(polls, est, lam[pick], 0.0, [0.0], namespace_seed(namespace, 'maori-inflation'), count)
    return {seat: s['winner'] for seat, s in sim['seats'].items()}


def simulate(config, count):
    """Return {electorateId: record}; records are simulated (winner party per draw) or unavailable with a reason."""
    require(config['maori']['layer'] == 'stage66-default', 'only the Stage66 default Maori layer is registered')
    require(config['maori']['presentation'] == 'labelled-range', 'only the labelled C-P range presentation is registered (D114, D127)')
    fallback = config['maori']['unpolledFallbackModel']
    require(fallback in (None, FALLBACK_MODEL), f'unregistered Maori fallback model: {fallback}')
    require(fallback is None or config['maori']['unpolledSeats'] == 'labelled-fallback', 'a fallback model needs maori.unpolledSeats = labelled-fallback')
    ids = electorate_ids()
    people = roster(config, ids)
    run, sha = electorate_live.pinned(config)
    polls, _ = maori_live.current_polls(resolver(people), maori_live.live_polls(run, sha), electorate_live.forecast_cutoff(config))
    fitted = fit()[0]['fit']
    sim = simulate_layer(polls, parameters(fitted), count, namespace_seed(config['simulation']['seedNamespace'], 'maori'))
    inflated = inflation_winners(polls, count, config['simulation']['seedNamespace'])
    unpolled = [seat for seat in SEATS if seat not in sim['seats']]
    drawn = (f_shares(unpolled, count, namespace_seed(config['simulation']['seedNamespace'], 'maori-fallback'))
             if fallback is not None and unpolled else {})
    out = {}
    for seat in SEATS:
        if seat in sim['seats']:
            s = sim['seats'][seat]
            matched = [match(seat, c['name'], c['party'], people[seat]) for c in s['poll']['candidates']]
            require(len({p['id'] for p in matched}) == len(matched), f'{seat}: two poll candidates match one roster candidate')
            everyone, shares, named = with_unpolled_candidates(people[seat], matched, s['share'])
            extra = {'pollFieldworkEnd': s['poll']['fieldworkEnd']}
            if seat in inflated:
                extra['inflationWinners'] = [int(i) for i in inflated[seat]]
            out[ids[seat]] = record(f"Stage66 default; poll {s['poll']['id']}", everyone, shares, extra, named)
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
