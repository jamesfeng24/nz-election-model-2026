"""Stage78 runner: calibration, held-out scoring of F, FC and FP, the frozen finding rules, the 2026 fallback readout, preview and manifest."""
import argparse
import math
import numpy as np
from scripts.maori_seat_fallback import forecast, history, model, score
from scripts.maori_seat_fallback.common import read, save, digest, DESIGN, DESIGN_DOC, INPUTS, SEATS


def election_means(rows):
    out = {}
    for y, g in history.groups_for(rows, {2017, 2020, 2023}).items():
        mean = sum(g) / len(g)
        out[str(y)] = {'contrasts': len(g), 'meanD': mean, 'sdD': math.sqrt(sum((d - mean) ** 2 for d in g) / (len(g) - 1))}
    return out


def calibration(res):
    rows = history.contrast_rows(res)
    est = model.estimate(history.groups_for(rows, {2017, 2020, 2023}))
    return {'schemaVersion': 1, 'fit': dict(est, sigma=math.sqrt(est['sigma2']), tau=math.sqrt(est['tau2']), electionMeans=election_means(rows),
                                             otherContrasts=history.other_contrast_ratio({2017, 2020, 2023}, est['sigma2'], res),
                                             entrantPools=history.entrant_pools({2017, 2020, 2023}, res)),
            'contrasts': rows}


def scheme_block(res, contract, scheme):
    fits, records = score.score_scheme(res, contract, scheme, contract['bootstrapReplicates'], contract['seed'], contract['draws'])
    years = sorted(fits)
    block = {'foldsScored': years, 'fits': {str(e): f for e, f in fits.items()}, 'pooled': {}, 'byFold': {}, 'comparisons': {}, 'contests': {}}
    for arm, recs in records.items():
        block['pooled'][arm] = score.metrics(recs)
        block['byFold'][arm] = {str(e): score.metrics(score.by_year(recs, e)) for e in years}
        block['contests'][arm] = [{k: v for k, v in r.items() if k in ('year', 'seat', 'probActual', 'logScore', 'brierMulti', 'favouriteProb', 'favouriteWon', 'subsets')}
                                  for r in recs]
    for arm in ('FC', 'FP'):
        block['comparisons'][arm + ' against F'] = score.paired_bootstrap(records['F'], records[arm], contract['pairedBootstrapResamples'], contract['seed'])
    return block, records


def findings(contract, loeo, chrono):
    z, dev = contract['calibration']['zThreshold'], contract['calibration']['coverageDeviationMax']
    swing = {}
    for arm in ('FC', 'FP'):
        swing[arm] = score.swing_rule(loeo['pooled']['F'], loeo['pooled'][arm],
                                      {e: loeo['byFold']['F'][e] for e in loeo['byFold']['F']}, {e: loeo['byFold'][arm][e] for e in loeo['byFold'][arm]},
                                      loeo['comparisons'][arm + ' against F'], contract['minimumFoldsLogScoreBetter'])
    registered = score.registration(swing['FC']['class'], swing['FP']['class'])
    calib = {arm: {'leaveOneElectionOut': score.calibration_class(loeo['pooled'][arm], z, dev),
                   'chronological2023': score.calibration_class(chrono['pooled'][arm], z, dev)} for arm in score.ARMS}
    reported = {'F': ['F'], 'FC_to_FP': ['FC', 'FP'], 'none_report_to_james': ['F', 'FC', 'FP']}[registered]
    classes = {calib[a]['leaveOneElectionOut'] for a in reported}
    chrono_classes = {calib[a]['chronological2023'] for a in reported}
    choice = read(INPUTS)['registration']
    return {'schemaVersion': 1, 'swingRule': swing, 'registered': registered, 'registeredByJames': choice, 'calibrationClass': calib, 'reportedArms': reported,
            'headlineCalibration': sorted(classes), 'chronologicalCalibration': sorted(chrono_classes),
            'chronologicalAgrees': classes == chrono_classes}


def preview(contract, sim, size):
    arms = {}
    for arm, seats in sim['arms'].items():
        arms[arm] = {seat: {'candidates': sim['inputs'][seat]['names'], 'parties': sim['inputs'][seat]['codes'],
                            'winnerIndex': [int(i) for i in np.argmax(sh[:size], axis=1)],
                            'share': [[round(float(x), 6) for x in row] for row in sh[:size]]} for seat, sh in seats.items()}
    return {'schemaVersion': 1, 'label': 'PREVIEW of the first %d deterministic draws of the Stage78 no-poll fallback; not a forecast release' % size,
            'seed': contract['seed'], 'draws': size, 'unpolledSeats': list(forecast.UNPOLLED), 'arms': arms}


def build():
    contract = read(DESIGN)
    res = history.results()
    cal = calibration(res)
    loeo, _ = scheme_block(res, contract, 'leaveOneElectionOut')
    chrono, _ = scheme_block(res, contract, 'chronological')
    finds = findings(contract, loeo, chrono)
    fc, sim = forecast.build(contract)
    fc.update({'schemaVersion': 1, 'label': 'INTERNAL development output; labelled fallback for seats without a poll; not a forecast of record',
               'registered': finds['registered'], 'registeredByJames': finds['registeredByJames'], 'calibrationClass': finds['calibrationClass']})
    summary = {'schemaVersion': 1, 'registered': finds['registered'], 'registeredByJames': finds['registeredByJames'], 'swingClasses': {a: finds['swingRule'][a]['class'] for a in ('FC', 'FP')},
               'swingQualifiers': {a: finds['swingRule'][a]['evidenceQualifier'] for a in ('FC', 'FP')},
               'calibrationClass': finds['calibrationClass'], 'chronologicalAgrees': finds['chronologicalAgrees'],
               'sigma': cal['fit']['sigma'], 'tau': cal['fit']['tau'], 'contrasts': cal['fit']['contrasts'],
               'leaveOneElectionOutPooled': loeo['pooled'], 'chronologicalPooled': chrono['pooled'],
               'winProbabilities2026': {arm: {seat: {c['name']: c['winProbability'] for c in v['candidates']} for seat, v in a['seats'].items()}
                                        for arm, a in fc['arms'].items()},
               'flaggedSensitivityShifts': {n: s['flaggedShiftOver0.10'] for n, s in fc['sensitivities'].items()}}
    return {'calibration.json': cal, 'scores.json': {'schemaVersion': 1, 'leaveOneElectionOut': loeo, 'chronological': chrono},
            'findings.json': finds, 'forecast-2026.json': fc, 'draw-bank-preview.json': preview(contract, sim, contract['previewDraws']), 'summary.json': summary}


def manifest(names):
    contract = read(DESIGN)
    inputs = [DESIGN_DOC, DESIGN, INPUTS] + [p for p in contract['inputs'] if p != INPUTS]
    return {'schemaVersion': 1, 'inputHashes': {p: digest(p) for p in inputs}, 'stage66Modified': False, 'stage71Modified': False,
            'configTouched': False, 'assemblyTouched': False, 'dataSourcesJsonTouched': False, 'newResources': 0, 'outputs': sorted(names)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    artifacts = build()
    for name, value in artifacts.items():
        save(name, value, args.check, 2e-6 if name == 'draw-bank-preview.json' else 1e-8)
    save('manifest.json', manifest(list(artifacts)), args.check)
    print('Stage78 check ok' if args.check else 'wrote %d artifacts' % len(artifacts))


if __name__ == '__main__':
    main()
