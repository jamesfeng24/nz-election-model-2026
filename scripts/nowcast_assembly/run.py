"""Stage73 runner.

python -m scripts.nowcast_assembly.run [--check] [--workers N]
    Development gate on the live inputs: builds the bank at the development draw count and writes only the gate
    report (statuses, blockers, checks, reconciliation diagnostic, bank digest), never the bank or a forecast.
python -m scripts.nowcast_assembly.run --require-complete --draws N --bank PATH [--workers N]
    Production: refuses unless the config is complete and every gate check passes, then writes the bank to PATH.
"""
import argparse
import os
from scripts.nowcast_config.validate import check_config, ConfigError
from .assemble import assemble, gate, bank_digest
from .common import CONFIG, OUTPUT, ROOT, read, encode, require, AssemblyError
from scripts.balance_scale.common import equivalent

DEVELOPMENT_DRAWS = 64


def development_report(config, workers):
    bank = assemble(config, DEVELOPMENT_DRAWS, workers=workers)
    passed, checks = gate(bank, config)
    blockers = {}
    for seat in bank['seats']:
        if seat['status'] == 'unavailable':
            blockers.setdefault(seat['reason'], []).append(seat['electorateId'])
    return {'stage': 73, 'label': 'DEVELOPMENT gate on live inputs at a development draw count; no bank, no forecast',
            'configVersion': bank['configVersion'], 'draws': bank['draws'], 'provenance': bank['provenance'],
            'publishable': passed, 'checks': checks,
            'seatStatus': {s['electorateId']: s['status'] for s in bank['seats']},
            'blockers': [{'reason': r, 'seats': len(v), 'electorateIds': v} for r, v in sorted(blockers.items())],
            'diagnostics': bank['diagnostics'], 'bankDigest': bank_digest(bank)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--draws', type=int)
    parser.add_argument('--bank')
    parser.add_argument('--workers', type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    config = read(CONFIG)
    if args.require_complete:
        try:
            check_config(config, require_complete=True)
        except ConfigError as error:
            raise SystemExit(f'REFUSED: {error}')
        require(args.draws == config['simulation']['draws'] and args.bank, '--draws must equal simulation.draws and --bank is required')
        bank = assemble(config, args.draws, workers=args.workers)
        passed, checks = gate(bank, config)
        if not passed:
            raise SystemExit('REFUSED: ' + '; '.join(f"{c['check']}: {c['detail']}" for c in checks if not c['passed']))
        (ROOT / args.bank).write_bytes(encode(bank))
        print('bank written', args.bank, bank_digest(bank))
        return
    value = development_report(config, args.workers)
    if args.check:
        if not equivalent(read(OUTPUT), value, 1e-9):
            raise SystemExit('Stale ' + OUTPUT)
        print('Stage73 development gate reproduced')
        return
    (ROOT / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / OUTPUT).write_bytes(encode(value))
    print('Stage73 development gate written; publishable:', value['publishable'])


if __name__ == '__main__':
    try:
        main()
    except AssemblyError as error:
        raise SystemExit(f'INVALID: {error}')
