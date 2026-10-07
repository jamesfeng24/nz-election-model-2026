"""Stage75: refit the S+R candidate-mean model on every completed election and recentre the 2026 features.

python -m scripts.candidate_fit_2026.run [--check]

The fit is the Stage33 primary design (`baseline_plus_S_plus_R`, broad view, printed rounding, constructed party
input), unchanged in every respect except the training set: the latest saved fold's training contests plus its own
2023 evaluation contests. Before fitting, the builder must reproduce the saved 2023-target fit's signature exactly,
which proves the payload (arrays, actuals, centring) is the Stage33 one. The 2026 Stage42 continuous features are
re-centred on the new training-only means from their stored components (exact; the old centring is reproduced first).
"""
import argparse
from math import fsum
from scripts.balance_scale.common import equivalent
from scripts.models.joint_candidate_share.numerics import calculate
from scripts.uncertainty_revision.common import ROOT, encode
from .common import (CONSTRUCTION, FEATURES, FIT, LIVE_BRANCH, LIVE_YEAR, METHOD, PREFIX, READINESS, design, job,
                     live_fold, read, rows_for)

TOLERANCE = 1e-12


def saved_latest():
    return next(f for f in read(CONSTRUCTION)['folds'] if f['branch'] == 'primary' and f['targetYear'] == 2023)


def verify_builder(latest, records):
    signature = job(latest, rows_for(latest['trainingIds'], records))['signature']
    if signature != saved_latest()['fits'][METHOD]['fitId']:
        raise ValueError('Builder does not reproduce the saved Stage33 2023-target fit payload')
    return signature


def fit():
    latest, records = design()
    reproduced = verify_builder(latest, records)
    fold, rows = live_fold(latest, records)
    result = calculate(job(fold, rows))
    if result['fit'].get('status') != 'fitted':
        raise ValueError('Live fit did not converge: ' + str(result['fit']))
    old = saved_latest()['fits'][METHOD]['parameters']
    new = result['fit']
    years = sorted({r['targetYear'] for r in rows})
    entry = {**{k: v for k, v in fold.items() if k not in ('trainingIds', 'trainingCandidateIds')},
             'trainingContests': len(fold['trainingIds']), 'trainingCandidates': len(fold['trainingCandidateIds']),
             'trainingTargetYears': years, 'trainingIds': fold['trainingIds'],
             'fits': {METHOD: {'fitId': result['signature'], 'parameters': new}}}
    return {'stage': 75, 'method': METHOD,
            'rule': 'Stage33 primary S+R design and fitter unchanged; training = latest saved fold training + its 2023 evaluation contests',
            'builderReproducesSavedFit': reproduced,
            'folds': [entry],
            'comparison': {'previous': {'fitId': saved_latest()['fits'][METHOD]['fitId'], 'trainingContests': len(saved_latest()['trainingIds']),
                                        'trainingOnlyMeans': saved_latest()['trainingOnlyMeans'], 'coefficients': old['coefficients'],
                                        'kappa': old['kappa']},
                           'live': {'fitId': result['signature'], 'trainingContests': len(fold['trainingIds']),
                                    'trainingOnlyMeans': fold['trainingOnlyMeans'], 'coefficients': new['coefficients'],
                                    'kappa': new['kappa']}},
            'uncertainty': 'unchanged: the Stage45/72 scales measure out-of-time error, the error a 2026 prediction makes'}


def contribution(record, center):
    """Stage42 `weighted` rule from stored components: supported terms weight*(value-center), missing terms zero."""
    terms = [c['weight'] * (c['valueFraction'] - center) for c in record['components'] if c['valueFraction'] is not None]
    return fsum(terms)


def recentre(fit_value):
    readiness = read(READINESS)
    old = readiness['developmentCenterReference']['trainingOnlyMeans']
    new = fit_value['folds'][0]['trainingOnlyMeans']
    candidates = {}
    for c in readiness['candidateRecords']:
        values = {}
        for name, mean in (('S', 'S'), ('R', 'R')):
            record = c['continuous'][name]
            if abs(contribution(record, old[mean]) - record['contribution']) > TOLERANCE:
                raise ValueError(f"{c['targetOccurrenceId']}: stored {name} contribution not reproduced")
            values[name] = contribution(record, new[mean])
            values[name + 'SupportedWeight'] = record['supportedWeight']
        candidates[c['targetOccurrenceId']] = values
    return {'stage': 75, 'source': READINESS, 'previousTrainingOnlyMeans': old, 'trainingOnlyMeans': new,
            'fitId': fit_value['folds'][0]['fits'][METHOD]['fitId'],
            'rule': 'Stage42 weighted contribution recomputed from stored components with the live training-only means',
            'candidates': candidates}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    check = parser.parse_args().check
    value = fit()
    features = recentre(value)
    for path, data in ((FIT, value), (FEATURES, features)):
        if check:
            if not equivalent(read(path), data, 1e-9):
                raise SystemExit('Stale ' + path)
        else:
            (ROOT / PREFIX).mkdir(parents=True, exist_ok=True)
            (ROOT / path).write_bytes(encode(data))
    live = value['comparison']['live']
    print('Stage75', 'reproduced' if check else 'written', live['coefficients'], live['kappa'])


if __name__ == '__main__':
    main()
