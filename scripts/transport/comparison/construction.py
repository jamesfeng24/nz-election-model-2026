"""Apply independently saved fits to centered continuous source components."""
import argparse
from decimal import Decimal, localcontext
from math import isfinite
from scripts.transport.continuous.features import weighted
from .common import BRANCHES, MODELS, PREFIX, read, save, verify


def shares(base, features, parameters):
    theta = parameters['theta']
    if parameters['status'] != 'fitted' or len(theta) not in (1, 2):
        raise ValueError('Saved S or joint fit unavailable')
    if not .0001 <= parameters['kappa'] <= .1 or any(not isfinite(t) or abs(t) > 4 for t in theta):
        raise ValueError('Frozen parameter bounds')
    if not base or len(base) != len(features):
        raise ValueError('Incomplete slate')
    with localcontext() as context:
        context.prec = 50
        weights = []
        for b, x in zip(base, features):
            if not isfinite(b) or not 0 <= b <= 1 or len(x) != len(theta) or not all(isfinite(v) for v in x):
                raise ValueError('Invalid fixed inputs')
            movement = sum((Decimal(str(t)) * Decimal(str(v)) for t, v in zip(theta, x)), Decimal(0))
            weights.append((Decimal(str(b)) + Decimal(str(parameters['kappa']))) * movement.exp())
        total = sum(weights)
        result = [float(w / total) for w in weights]
    if abs(sum(result) - 1) > 1e-12 or any(not isfinite(v) or v < 0 for v in result):
        raise ValueError('Complete slate simplex failure')
    return result


def centered(candidate, means, branch):
    names = ('S',) if branch == 'S' else ('S', 'R')
    result = []
    for name in names:
        key = 'RStrict' if name == 'R' and branch == 'joint_strict' else name
        feature = candidate['continuous'][key]
        value = weighted(feature['components'], means[name])['contribution']
        # Every selected mean must match the saved Stage42 preprocessing.
        if abs(value - feature['contribution']) > 1e-12:
            raise ValueError('Centered source feature reproduction failed')
        result.append(value)
    return result


def build(inventory=None, manifest=None, saved=None, reference=None):
    inventory = read('data/processed/continuous-transport/inventory.json') if inventory is None else inventory
    manifest = read(PREFIX + '/sample-manifest.json') if manifest is None else manifest
    saved = read('data/processed/models/joint-candidate-share/construction.json') if saved is None else saved
    reference = read('data/processed/continuous-transport/construction.json') if reference is None else reference
    folds = []
    for sample in manifest['folds']:
        earlier = next(f for f in saved['folds'] if f['id'] == sample['savedFoldId'])
        if earlier['branch'] != 'primary' or earlier['protocol'] != 'expanding_window':
            raise ValueError('Wrong saved fit branch/chronology')
        if earlier['trainingOnlyMeans'] != sample['trainingOnlyMeans'] or earlier['trainingIds'] != sample['trainingIds']:
            raise ValueError('Changed training/preprocessing')
        if any(int(i.split('-')[2]) >= sample['targetYear'] for i in sample['trainingIds']):
            raise ValueError('Target/later training outcome')
        for model, key in MODELS.items():
            if earlier['fits'][key] != sample['fits'][model]:
                raise ValueError('Changed independently saved fit')
        rows = [r for r in inventory['records'] if r['targetYear'] == sample['targetYear']]
        if [r['targetElectorateId'] for r in rows] != sample['comparisonIds'] or [c['targetOccurrenceId'] for r in rows for c in r['candidates']] != sample['candidateIds']:
            raise ValueError('Frozen complete common IDs changed')
        predictions = {}
        for branch in BRANCHES:
            fit = sample['fits']['S' if branch == 'S' else 'joint']
            predictions[branch] = []
            for row in rows:
                cs = row['candidates']
                ids = [c['targetOccurrenceId'] for c in cs]
                if len(ids) != len(set(ids)):
                    raise ValueError('Duplicate candidate')
                x = [centered(c, sample['trainingOnlyMeans'], branch) for c in cs]
                q = shares([c['observedPartySupport'] for c in cs], x, fit['parameters'])
                predictions[branch].append({'targetElectorateId': row['targetElectorateId'],
                    'candidateShares': dict(zip(ids, q)), 'centeredContributions': dict(zip(ids, x))})
        old = next(f for f in reference['folds'] if f['targetYear'] == sample['targetYear'])
        for branch, old_branch in (('joint', 'continuous'), ('joint_strict', 'continuous_strict')):
            previous = old['predictions'][old_branch]
            if [p['targetElectorateId'] for p in previous] != sample['comparisonIds']:
                raise ValueError('Stage42 reproduction contest IDs differ')
            for new, prior in zip(predictions[branch], previous):
                if new['candidateShares'].keys() != prior['candidateShares'].keys() or max(abs(v - prior['candidateShares'][c]) for c, v in new['candidateShares'].items()) > 1e-12:
                    raise ValueError('Stage42 joint prediction reproduction failed')
        folds.append({'targetYear': sample['targetYear'], 'savedFoldId': sample['savedFoldId'],
            'fits': sample['fits'], 'trainingOnlyMeans': sample['trainingOnlyMeans'], 'trainingIds': sample['trainingIds'],
            'predictions': predictions, 'stage42JointReproductionWithin1eMinus12': True,
            'fittingPerformed': False, 'heldoutCandidateOutcomesConsumed': False})
    return {'stage': 43, 'folds': folds, 'operationalSelection': None,
        'informationSet': 'fixed primary constructed-input-trained fits; observed target local party inputs; retrospective slates'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    verify()
    save('construction.json', build(), args.check)
    print('Stage43 fixed predictions reproduced and sealed; no fitting/scoring')


if __name__ == '__main__':
    main()
