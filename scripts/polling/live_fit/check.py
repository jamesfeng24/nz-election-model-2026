"""Stage62 committed-artifact checks: numpy and stdlib only, never infers. Run: python3 -m scripts.polling.live_fit.check"""
import argparse
import math
import numpy as np
from .common import ROOT, OUT, EXT, ARMS, ENV_CHECK, read, sha
from .summarize import ORDER, build, scan
from scripts.polling.external_comparison.archive import check_diagnostics
from scripts.polling.external_comparison.common import validate_inputs as validate_stage38_inputs

EXPECTED_DRAWS = 8000


def check_inputs():
    contract = read(OUT / 'input-contract.json')
    for path, h in {**contract['sha256'], **contract['numericalCode']}.items():
        if sha(ROOT / path) != h:
            raise ValueError('Changed Stage62 input or frozen code ' + path)
    for rel, h in contract['datasets'].items():
        if sha(OUT / rel) != h:
            raise ValueError('Changed dataset ' + rel)
    for ext, h in contract['stage38Dataset2017'].items():
        if sha(EXT / f'datasets/2017.{ext}') != h:
            raise ValueError('Changed Stage38 2017 dataset')
    validate_stage38_inputs()
    rec = read(OUT / 'reconciliation.json')
    if not all(rec['assertions'].values()):
        raise ValueError('Stage59-correction assertions failed')
    if rec['panelSha256'] != contract['sha256']['data/processed/polling/panel-update-2026-10/panel.json']:
        raise ValueError('Reconciliation was built against a different panel')
    return rec


def inspect_arm(arm):
    attempts = []
    accepted = None
    for attempt in (1, 2):
        p = OUT / f'fits/{arm}/attempt{attempt}.json'
        if not p.exists():
            continue
        record = read(p); attempts.append(record)
        if 'diagnostics' in record:
            diag_path = OUT / f'fits/{arm}/attempt{attempt}-diagnostics.json.gz'
            if sha(diag_path) != record['diagnosticsSha256']:
                raise ValueError('Changed diagnostics ' + arm)
            check_diagnostics({'diagnostics': read(diag_path), 'status': record['status']})
        if record.get('npzSha256'):
            archive = p.with_suffix('.npz')
            if sha(archive) != record['npzSha256']:
                raise ValueError('Changed draw archive ' + arm)
            with np.load(archive, allow_pickle=False) as a:
                for key in ('electionDay', 'lastDataSupport'):
                    x = a[key]
                    if list(x.shape) != record['savedDrawChainShape'] or not np.isfinite(x).all() or (x < 0).any() or not np.allclose(x.sum(-1), 1, atol=1e-10, rtol=0):
                        raise ValueError('Invalid joint draws ' + arm + ' ' + key)
                if not np.allclose(a['electionDay'].mean((0, 1)), record['expectedElectionDay'], atol=1e-12, rtol=0):
                    raise ValueError('Wrong election-week mean ' + arm)
                if int(a['extra__diverging'].sum()) != record['diagnostics']['divergences']:
                    raise ValueError('Divergence count mismatch ' + arm)
                for key in a.files:
                    if not np.isfinite(a[key]).all():
                        raise ValueError('Non-finite saved array ' + arm + ' ' + key)
            if len(set(record['drawIds'])) != EXPECTED_DRAWS:
                raise ValueError('Invalid draw IDs ' + arm)
        if record['status'] == 'accepted':
            accepted = attempt; break
    return {'arm': arm, 'accepted': accepted, 'attempts': len(attempts)}


def run():
    rec = check_inputs()
    inspected = [inspect_arm(a) for a in [ENV_CHECK] + ORDER]
    summaries, comparison, env = build(check=True)
    for path in sorted((OUT / 'summary').glob('*.json')):
        scan(read(path))
    return rec, inspected, env


if __name__ == '__main__':
    argparse.ArgumentParser().parse_args()
    rec, inspected, env = run()
    print('ok', {i['arm']: i['accepted'] for i in inspected}, 'environment check', env['status'])
