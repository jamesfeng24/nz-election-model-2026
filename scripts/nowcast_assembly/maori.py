"""Maori seats: the Stage66 default layer re-run for the polled seats; unpolled seats follow config only.

Stage66 stores only a 500-draw preview, so the registered model is re-simulated here with the assembly's draw
count. Maori draws are independent of the national draw (Stage66 default; any coupling needs a stated correlation).
Unpolled seats have no estimate: while `maori.unpolledSeats` is pending they are `unavailable`, never a fallback.
"""
from scripts.maori_seat_layer.common import SEATS, fold
from scripts.maori_seat_layer.fit import fit
from scripts.maori_seat_layer.run import parameters
from scripts.maori_seat_layer.simulate import current_polls, simulate as simulate_layer
from .common import TARGET_FRAME, read, require, namespace_seed
from .summaries import share_summaries

# Stage66 party codes -> 2026 ballot-group keys; IND is an independent (no party). Any other code fails closed.
PARTIES = {'MP': 'tepatimaori', 'LAB': 'labourparty', 'GRN': 'greenparty', 'NAT': 'nationalparty',
           'NZF': 'newzealandfirstparty', 'IND': None}


def electorate_ids():
    frame = read(TARGET_FRAME)['records']
    ids = {fold(r['canonicalName']): r['targetElectorateId'] for r in frame if r['scope'] == 'maori'}
    require(len(ids) == len(SEATS) and all(fold(s) in ids for s in SEATS), 'Maori seat names do not match the 2026 frame')
    return {s: ids[fold(s)] for s in SEATS}


def simulate(config, count):
    """Return {electorateId: record}; records are simulated (winner party per draw) or unavailable with a reason."""
    require(config['maori']['layer'] == 'stage66-default', 'only the Stage66 default Maori layer is registered')
    ids = electorate_ids()
    polls, _, _ = current_polls()
    fitted = fit()[0]['fit']
    sim = simulate_layer(polls, parameters(fitted), count, namespace_seed(config['simulation']['seedNamespace'], 'maori'))
    out = {}
    for seat in SEATS:
        if seat in sim['seats']:
            s = sim['seats'][seat]
            codes = [c['party'] for c in s['poll']['candidates']]
            require(all(code in PARTIES for code in codes), f'{seat}: unmapped Maori candidate party code')
            candidates = [f'{ids[seat]}-poll-candidate-{fold(c["name"])}' for c in s['poll']['candidates']]
            require(len(set(candidates)) == len(candidates), f'{seat}: duplicate poll candidate key')
            out[ids[seat]] = {'status': 'simulated', 'class': 'maori-layer', 'source': f"Stage66 default; poll {s['poll']['id']}",
                              'candidates': candidates, 'candidateNames': [c['name'] for c in s['poll']['candidates']],
                              'candidateParty': [PARTIES[code] for code in codes],
                              'candidateShares': share_summaries(candidates, s['share']),
                              'winnerParty': [PARTIES[codes[int(i)]] for i in s['winner']],
                              'winnerCandidate': [candidates[int(i)] for i in s['winner']]}
        else:
            reason = 'unpolled; maori.unpolledSeats is pending James' if config['maori']['unpolledSeats'] is None \
                else 'unpolled; no registered fallback implementation'
            out[ids[seat]] = {'status': 'unavailable', 'reason': reason}
    return out
