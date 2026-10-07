"""SYNTHETIC FIXTURE: a complete draw bank for the Python -> TypeScript contract test (Stage74).

python -m scripts.nowcast_assembly.fixture [--check]

The bank runs the real Stage73 engine on the live national draws and baseline. The slates, classification and Maori
winners are invented, so the bank is marked `synthetic-fixture`, uses `synthetic-` candidate ids and is read only by
tests (never imported by the site). It is not a nowcast.
"""
import argparse
import numpy as np
from scripts.balance_scale.common import equivalent
from scripts.manual_adjustment.schema import seat_frame
from . import assemble as A, summaries
from .common import CONFIG, ROOT, read, encode

OUTPUT = 'data/fixtures/synthetic/nowcast-draw-bank.json'
COUNT = 32
PARTIES = ('nationalparty', 'labourparty', 'greenparty', None)


def build():
    frame = seat_frame()
    general, maori = sorted(frame['general']), sorted(frame['maori'])
    slates = {seat: [{'id': f'synthetic-{seat}-{i}', 'group': g, 'name': f'Synthetic candidate {i}', 'S': 0.0, 'R': 0.0}
                     for i, g in enumerate(PARTIES)] for seat in general}
    classes = {seat: 'exceptional' if i % 8 == 0 else 'ordinary' for i, seat in enumerate(general)}

    def record(k, seat):
        ids, parties = [f'synthetic-{seat}-a', f'synthetic-{seat}-b'], ['labourparty', 'tepatimaori']
        win = [(d + k) % 3 == 0 for d in range(COUNT)]
        shares = np.array([[0.6, 0.4] if w else [0.4, 0.6] for w in win])
        return {'status': 'simulated', 'class': 'maori-layer', 'source': 'synthetic-fixture', 'candidates': ids,
                'candidateNames': ['Synthetic A', 'Synthetic B'], 'candidateParty': parties,
                'candidateShares': summaries.share_summaries(ids, shares),
                'winnerParty': [parties[0] if w else parties[1] for w in win], 'winnerCandidate': [ids[0] if w else ids[1] for w in win]}
    bank = A.assemble(read(CONFIG), COUNT, slates=slates, classification=classes,
                      maori_records={seat: record(k, seat) for k, seat in enumerate(maori)}, workers=2)
    bank['label'] = 'SYNTHETIC FIXTURE: invented slates, classification and Maori winners on live national draws; not a nowcast'
    return bank


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    value = build()
    if parser.parse_args().check:
        if not equivalent(read(OUTPUT), value, 1e-9):
            raise SystemExit('Stale ' + OUTPUT)
        print('Stage74 synthetic bank fixture reproduced')
        return
    (ROOT / OUTPUT).write_bytes(encode(value))
    print('Stage74 synthetic bank fixture written')


if __name__ == '__main__':
    main()
