"""Stage81 runner.

python -m scripts.party_vote_elasticity.run [--check] [--stage backtest|readout|all]
    backtest: closed-vector scores of the four arms on the Stage5 general-seat records, the frozen rule and the bootstrap.
    readout:  the 2026 general-seat readout per arm (deterministic at the national mean, and a development-size run of the
              live layer with common random numbers). The readout needs the backtest's retained set.
"""
import argparse
import itertools
import numpy as np
from scripts.nowcast_assembly.common import CONFIG
from . import backtest, preview2026, rule
from .common import read, save, digest, file_sha, DESIGN, PRIMARY, SECONDARY, ARMS, RECORDS, PREFIX


def scores(contract):
    out = {'schemaVersion': 1, 'transitions': {}, 'losses': {}}
    losses = {}
    for t in PRIMARY + SECONDARY:
        result, data = backtest.score_transition(*t)
        key = f'{t[0]}-{t[1]}'
        out['transitions'][key] = result
        if t in PRIMARY:
            preds = backtest.predictions(data, 'lower')
            losses[key] = {a: backtest.per_seat_losses(data, preds[a], 'lower') for a in ARMS}
    return out, losses


def pooled(block, arms=ARMS):
    keys = [f'{a}-{b}' for a, b in PRIMARY]
    return {a: {'M1': float(np.mean([block[k]['bounds']['lower']['arms'][a]['M1']['mae'] for k in keys])),
                'M2': float(np.mean([block[k]['bounds']['lower']['arms'][a]['M2']['macroMinorMae'] for k in keys])),
                'M4': float(np.mean([block[k]['bounds']['lower']['arms'][a]['M4']['macroPartyMae'] for k in keys])),
                'M5': float(np.mean([block[k]['bounds']['lower']['arms'][a]['M5']['clrMeanSquaredPerCategory'] for k in keys]))} for a in arms}


def findings(contract, sc, losses, invariance=None):
    keys = [f'{a}-{b}' for a, b in PRIMARY]
    thresholds = contract['adoptionRule']['thresholdsPP']
    verdict = rule.classify(sc['transitions'], keys, list(ARMS), thresholds, invariance)
    b = contract['metrics']['bootstrap']
    ranked = sorted(ARMS, key=lambda a: verdict['pooledM1'][a])
    best, runner = ranked[0], ranked[1]
    pair = {f'{x} minus {y}': {m: backtest.bootstrap(losses, b['resamples'], b['seed'], m, x, y) for m in ('M1', 'M2')}
            for x, y in itertools.combinations(ARMS, 2)}
    interval = backtest.bootstrap(losses, b['resamples'], b['seed'], 'M1', best, runner)
    verdict.update({'pooledPrimary': pooled(sc['transitions']), 'bestOnM1': best, 'runnerUpOnM1': runner,
                    'bestVersusRunnerUpM1': interval, 'qualifier': 'clear' if interval['q95'] < 0 or interval['q05'] > 0 else 'weak',
                    'pairedBootstrap': pair, 'invariance': invariance})
    return verdict


def readout_summary(readout):
    names = {r['targetElectorateId']: r['canonicalName'] for r in read('data/processed/forecast-readiness/snapshots/2026-10-05/target-frame.json')['records']}
    sim = readout['simulated']
    out = {'draws': readout['draws'], 'label': readout['label'], 'settings': {}}
    for label, v in sim.items():
        seats = v['seats']
        north = next(s for s in seats if names[s] == 'Northland')
        total = {}
        for s in seats.values():
            for party, p in s.items():
                if party != '_candidates':
                    total[party] = total.get(party, 0.0) + p
        out['settings'][label] = {'expectedGeneralElectorates': {k: round(x, 3) for k, x in sorted(total.items())},
                                  'northland': {k: round(x, 3) for k, x in seats[north].items() if k != '_candidates'},
                                  'reconciliationMaxAbsGapPP': v['reconciliationMaxAbsGapPP']}
    spread = []
    for s in sim['P']['seats']:
        probs = {k: sim[k]['seats'][s].get('nationalparty', 0.0) for k in sim if k != 'default'}
        spread.append((max(probs.values()) - min(probs.values()), names[s], probs))
    out['mostArmSensitiveSeatsNationalWinProbability'] = [{'seat': n, 'range': round(r, 3), 'byArm': {k: round(x, 3) for k, x in p.items()}}
                                                          for r, n, p in sorted(spread, reverse=True)[:10]]
    out['defaultEqualsProportional'] = all(sim['default']['seats'][s] == sim['P']['seats'][s] for s in sim['P']['seats'])
    out['nationalAheadOnPartyVoteAtNationalMean'] = {a: v['seatsNationalAheadOfLabour'] for a, v in readout['deterministic']['arms'].items()}
    return out


def final(contract, check):
    sc = read(PREFIX + '/scores.json')
    readout = read(PREFIX + '/readout-2026.json')
    from .backtest import bootstrap  # noqa: F401  (losses are rebuilt below to keep the bootstrap in findings())
    _, losses = scores(contract)
    verdict = findings(contract, sc, losses, readout['deterministic']['invariance'])
    verdict['readout2026'] = readout_summary(readout)
    verdict['sourceHashes'] = {'records': file_sha(RECORDS), 'design': file_sha(DESIGN), 'classificationCopy': file_sha(preview2026.CLASSIFICATION)}
    save('findings.json', verdict, check)
    files = ['design-contract.json', 'scores.json', 'findings-backtest.json', 'readout-2026.json', 'findings.json']
    manifest = {'schemaVersion': 1, 'stage': 81, 'files': {f: file_sha(PREFIX + '/' + f) for f in files},
                'code': {f: file_sha('scripts/party_vote_elasticity/' + f) for f in ('transforms.py', 'backtest.py', 'rule.py', 'run.py', 'preview2026.py', 'common.py')}}
    if check:
        saved = read(PREFIX + '/manifest.json')
        stale = [f for f, h in manifest['files'].items() if saved['files'].get(f) != h]
        if stale:
            raise SystemExit('Stale Stage81 manifest entries: ' + ', '.join(stale))
    else:
        save('manifest.json', manifest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--stage', default='backtest', choices=('backtest', 'readout', 'findings'))
    parser.add_argument('--draws', type=int, default=512)
    args = parser.parse_args()
    contract = read(DESIGN)
    config = read(CONFIG)
    inputs = {'records': file_sha(RECORDS)}
    assert inputs['records'] == contract['inputs']['records']['sha256'], 'Stage5 records changed'
    if args.stage == 'backtest':
        sc, losses = scores(contract)
        save('scores.json', sc, args.check)
        f = findings(contract, sc, losses)
        save('findings-backtest.json', f, args.check)
        print('backtest class before the 2026 override:', f['ruleClassBeforeOverride'], 'retained', f['retainedArms'])
    if args.stage == 'readout':
        keep = read(PREFIX + '/findings-backtest.json')['retainedArms']
        det = preview2026.deterministic(config, list(ARMS))
        labels = {'default': None, **{a: a for a in ARMS}}
        if len(keep) >= 2:
            labels['mixture'] = keep
        sim = preview2026.simulated(config, labels, count=args.draws)
        save('readout-2026.json', {'schemaVersion': 1, 'deterministic': det, 'simulated': sim, 'retainedForMixture': keep,
                                    'draws': args.draws, 'label': 'development-size general-seat run; Maori seats not run'}, args.check, 1e-9)
    if args.stage == 'findings':
        final(contract, args.check)
    print('ok')


if __name__ == '__main__':
    main()
