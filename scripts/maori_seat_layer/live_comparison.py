"""Stage86 (D125) reproducible comparison: the Stage66 default layer on the pinned 2026-10-07 transcription versus the Stage82 live file.

python3 -m scripts.maori_seat_layer.live_comparison [DRAWS]

Same seed, same calibration, same per-seat random streams; only the poll inputs differ. Prints, per seat, the poll shares as closed over the named
candidates and the win probabilities under each source, and for a seat the live file polls but the pinned file does not (Waiariki) the Stage78
arm F fallback it replaces. Reporting only; writes nothing.
"""
import sys
import numpy as np
from scripts.maori_seat_fallback.draws import f_shares
from scripts.maori_seat_layer import live, simulate as S
from scripts.maori_seat_layer.common import SEATS
from scripts.maori_seat_layer.fit import fit
from scripts.maori_seat_layer.run import parameters
from scripts.nowcast_assembly import maori
from scripts.nowcast_assembly.common import CONFIG, read, namespace_seed


def win_probabilities(sim, seat, draws):
    candidates = sim['seats'][seat]['poll']['candidates']
    wins = np.bincount(sim['seats'][seat]['winner'], minlength=len(candidates)) / draws
    return {c['party']: float(w) for c, w in zip(candidates, wins)}


def closed(poll):
    total = sum(c['pollPercent'] for c in poll['candidates'])
    return {c['party']: c['pollPercent'] / total for c in poll['candidates']}


def compare(draws):
    config = read(CONFIG)
    people = maori.roster(config, maori.electorate_ids())
    pinned, _, _ = S.current_polls()
    current, _ = live.current_polls(maori.resolver(people))
    params = parameters(fit()[0]['fit'])
    seed = namespace_seed(config['simulation']['seedNamespace'], 'maori')
    sims = {'pinned': S.simulate(pinned, params, draws, seed), 'live': S.simulate(current, params, draws, seed)}
    fallback = f_shares([s for s in SEATS if s not in pinned], draws, namespace_seed(config['simulation']['seedNamespace'], 'maori-fallback'))
    rows = {}
    for seat in SEATS:
        row = {}
        for label, polls in (('pinned', pinned), ('live', current)):
            if seat in polls:
                row[label] = {'closedShares': closed(polls[seat]), 'win': win_probabilities(sims[label], seat, draws)}
        if seat not in pinned and seat in fallback:
            inputs, shares = fallback[seat]
            wins = np.bincount(shares.argmax(axis=1), minlength=len(inputs['names'])) / draws
            row['fallbackF'] = {'win': {code: float(w) for code, w in zip(inputs['codes'], wins)}}
        rows[seat] = row
    return rows


def main():
    draws = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    for seat, row in compare(draws).items():
        print(seat)
        for label, value in row.items():
            parts = ', '.join(f'{k} {v:.3f}' for k, v in value['win'].items() if v >= 0.0005)
            shares = ('; closed poll shares ' + ', '.join(f'{k} {v:.3f}' for k, v in value['closedShares'].items())) if 'closedShares' in value else ''
            print(f'  {label:9s} win: {parts}{shares}')


if __name__ == '__main__':
    main()
