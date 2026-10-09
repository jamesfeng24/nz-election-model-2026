"""Stage79 development readout: the six eligible 2026 polled seats with and without the poll update, under both D107 classes.

INTERNAL development output on the live inputs (national draws, Stage50 official slates, Stage75 candidate fit). The D107
classification does not exist yet, so each seat is shown under both classes. Nothing is adopted or published.

python -m scripts.seat_polls.readout [--draws 2048] [--check]
"""
import argparse
import numpy as np
from scripts.nowcast_assembly import assemble as A, fastmath, general, national, streams
from scripts.nowcast_assembly.common import CONFIG, read, encode, ROOT
from scripts.balance_scale.common import equivalent
from . import live
from .common import PREFIX

OUTPUT = PREFIX + '/readout-2026.json'


def build(draws):
    config = read(CONFIG)
    inputs = live.inputs(config['national']['dataCutoff'])
    shares, ids, groups = national.load(config, draws)
    keys, national2023, base = general.baseline(config)
    continuing = general.relationships(config)
    fine = general.fine_national(shares, groups, keys, national2023, continuing)
    parameters, _ = general.fold_parameters(config)
    scale_file = read(config['uncertainty']['scales'])
    party_scales, candidate_scales = scale_file['layers']['local_party']['scales'], scale_file['layers']['candidate']['scales']
    slates, reason = A.live_slates(config)
    multipliers = config['uncertainty']['candidateBalanceSeatMultiplier']
    seats = sorted(inputs)
    party = {s: general.party_row(s, keys, base[s], national2023, continuing) for s in seats}
    candidate = {s: general.candidate_row(s, slates[s], party[s], parameters) for s in seats}
    names = {s: {c['id']: c['name'] for c in slates[s]} for s in seats}
    out = {}
    with streams.substituted(list(party.values()) + list(candidate.values()), draws, config['simulation']['seedNamespace']), fastmath.accelerated():
        for seat in seats:
            entry = {'electorate': inputs[seat]['electorate'], 'poll': {k: v for k, v in inputs[seat].items() if k != 'electorate'}, 'classes': {}}
            for kind, multiplier in multipliers.items():
                arms = {}
                for arm, poll in (('modelAlone', None), ('modelPlusPoll', inputs[seat])):
                    _, q, record = general.simulate_with_poll(party[seat], candidate[seat], fine, party_scales, candidate_scales, multiplier, poll)
                    winner = np.bincount(q.argmax(axis=1), minlength=q.shape[1]) / draws
                    cand = candidate[seat]
                    n, l = cand['groups'].index('national'), cand['groups'].index('labour')
                    balance = np.log(q[:, n] / q[:, l])
                    arms[arm] = {'winProbability': {names[seat][i]: float(w) for i, w in zip(cand['ids'], winner) if w > 0},
                                 'nationalWins': float(winner[n]), 'labourWins': float(winner[l]),
                                 'balance': {'mean': float(balance.mean()), 'p10': float(np.quantile(balance, .1)), 'p90': float(np.quantile(balance, .9))},
                                 'nationalShareMean': float(q[:, n].mean()), 'labourShareMean': float(q[:, l].mean()), 'update': record}
                entry['classes'][kind] = arms
            out[seat] = entry
    return {'schemaVersion': 1, 'stage': 79, 'label': 'INTERNAL development output; nothing adopted; the D107 classification does not exist yet, so both classes are shown',
            'draws': draws, 'dataCutoff': config['national']['dataCutoff'], 'nationalDrawIds': ids[:3] + ['...'], 'seats': out,
            'ineligible2026': 'Auckland Central and Wellington Bays (Green-led polls) are context only (design amendment A2)'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draws', type=int, default=2048)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    value = build(args.draws)
    if args.check:
        if not equivalent(read(OUTPUT), value, 1e-9):
            raise SystemExit('Stale ' + OUTPUT)
        print('Stage79 readout reproduced')
    else:
        (ROOT / OUTPUT).write_bytes(encode(value))
        print('Stage79 readout written')


if __name__ == '__main__':
    main()
