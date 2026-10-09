"""Stage79 runner: transcription check, leave-one-seat-election-out scoring, the frozen finding, the 2026 fit and the registry.

python -m scripts.seat_polls.run [--check]
"""
import argparse
from . import data, historical, model, score
from .common import ROOT, RAW, POLLS, DESIGN, DESIGN_DOC, INVENTORY, SCALES, REGISTRY, read, save, digest, parameters

ORGANISATION = 'Wikipedia'
LIMITATION = ('Electorate-poll compilation (secondary, volunteer-edited), aggregator_only; transcribed into data/source-plans/seat-polls/polls.json and '
              'checked against these bytes. James confirmed on 2026-10-09 that the 2026 numbers match the underlying articles. Not a primary release.')


def registry():
    rows = [line.split('\t') for line in (ROOT / RAW / 'fetch-log.tsv').read_text().splitlines()]
    sources = []
    for stamp, status, name, url, size in sorted(rows, key=lambda r: r[2]):
        entry = {'id': 'stage79-' + name, 'organisation': ORGANISATION, 'url': url, 'dateOrElection': 'General-electorate polls ' + name.split('-')[-1].split('.')[0],
                 'resource': name, 'retrievedAt': stamp, 'status': status, 'processingScript': 'scripts/seat_polls/run.py',
                 'limitations': [LIMITATION], 'schemaVersion': 1,
                 'licence': 'Wikipedia text CC BY-SA; preserved unchanged for research provenance only, not redistributed in application results.'}
        if status.startswith('200'):
            entry.update({'rawPath': RAW + '/' + name, 'sha256': digest(RAW + '/' + name), 'bytes': int(size)})
        else:
            entry.update({'rawPath': None, 'sha256': None, 'bytes': 0, 'limitations': [LIMITATION, 'Not retrieved (rate-limited); the 2011 election precedes the out-of-sample seat replay (2014 onwards), so it is not needed.']})
        sources.append(entry)
    return {'schemaVersion': 1, 'note': 'Dated standalone registry for Stage79. data/sources.json is frozen and untouched.', 'sources': sources}


def build():
    design = read(DESIGN)
    rows = data.polls()
    data.verify_transcription(rows)
    units = historical.historical_units(design)
    ok = [u for u in units if u['status'] == 'ok']
    eligible = [u for u in ok if u['eligible']]
    if not eligible:
        raise ValueError('no eligible historical polls')
    arms = {'primary': score.run_arm(eligible, eligible, design),
            'S1_dropAssumedSampleSize': score.run_arm(eligible, eligible, design, drop_assumed=True),
            'S2_noInflation': score.run_arm(eligible, eligible, design, fixed_one=True),
            'S3_inflationFromAllNationalLabourPolls': score.run_arm(eligible, ok, design)}
    decisions = {name: score.decide(arm, design) for name, arm in arms.items()}
    primary = arms['primary']
    decomposition = {'both': 0.0, 'centreOnly': 0.0, 'varianceOnly': 0.0}
    for r in primary['records']:
        z, mu, s2, pc, pv = r['actual'], r['modelCentre'], r['modelSD'] ** 2, r['posteriorCentre'], r['posteriorSD'] ** 2
        base = model.log_density(z, mu, s2)
        decomposition['both'] += model.log_density(z, pc, pv) - base
        decomposition['centreOnly'] += model.log_density(z, pc, s2) - base
        decomposition['varianceOnly'] += model.log_density(z, mu, pv) - base
    zs = [(r['actual'] - r['modelCentre']) / r['modelSD'] for r in primary['records']]
    inflation = model.fit_inflation([u['value'] - u['actual'] for u in eligible], [u['samplingVariance'] for u in eligible])
    p = parameters(design)
    polls = [{**data.derived(x, design), **({k: v for k, v in next((u for u in units if u['id'] == x['id']), {}).items()
                                              if k in ('status', 'seatId', 'exceptional', 'centre', 'sigma2', 'actual')})} for x in rows]
    summary = {'finding': decisions['primary']['finding'],
               'eligibleHistoricalPolls': len(eligible), 'seatElections': primary['seatElections'],
               'polledHistoricalWithNationalAndLabour': len(ok), 'ineligibleHistorical': sorted(u['id'] for u in ok if not u['eligible']),
               'totalLogScoreGain': primary['totalLogScoreGain'], 'coverage80ModelPlusPoll': primary['coverage']['80']['modelPlusPoll'],
               'coverage80Model': primary['coverage']['80']['model'], 'pollsImproved': primary['improved'], 'pollsWorsened': primary['worsened'],
               'sensitivityFindings': {k: v['finding'] for k, v in decisions.items() if k != 'primary'},
               'sensitivityGains': {k: arms[k]['totalLogScoreGain'] for k in arms if k != 'primary'},
               'logScoreGainDecomposition': decomposition, 'modelAloneRmsZ': float(sum(z * z for z in zs) / len(zs)) ** 0.5,
               'qualifier': 'exploratory sample: nine polls in seven seat-elections; the gain depends on 2020 polls whose sample size is assumed (S1 drops them)'}
    return {'polls.json': {'schemaVersion': 1, 'polls': polls},
            'scores.json': {'schemaVersion': 1, 'stage': 79, 'arms': arms},
            'findings.json': {'schemaVersion': 1, 'stage': 79, 'decisions': decisions, 'summary': summary},
            'fit.json': {'schemaVersion': 1, 'stage': 79, 'inflation': inflation, 'fittedOn': sorted(u['id'] for u in eligible),
                         'pollErrorRms': float((sum((u['value'] - u['actual']) ** 2 for u in eligible) / len(eligible)) ** 0.5),
                         'parameters': p, 'note': 'c for the 2026 layer: fitted on every eligible historical poll (no hold-out). Used only if the finding is adopt and seatPolls.enabled is true.'},
            'source-registry.json': registry()}


def manifest(names):
    inputs = [DESIGN_DOC, DESIGN, POLLS, RAW + '/fetch-log.tsv', INVENTORY, SCALES, historical.FLAGS,
              'scripts/uncertainty_revision/coordinates.py']
    return {'schemaVersion': 1, 'inputHashes': {p: digest(p) for p in inputs}, 'dataSourcesJsonTouched': False,
            'frozenStagesModified': False, 'outputs': sorted(names)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    artifacts = build()
    for name, value in artifacts.items():
        save(name, value, args.check)
    save('manifest.json', manifest(list(artifacts)), args.check)
    print('Stage79 check ok' if args.check else 'wrote %d artifacts' % (len(artifacts) + 1))


if __name__ == '__main__':
    main()
