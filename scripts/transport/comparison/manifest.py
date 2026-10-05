"""Deterministic contract selection and sealed implementation fingerprints."""
import argparse
from .common import ROOT, PREFIX, MODELS, read, save, digest, verify


def samples():
    saved = read('data/processed/models/joint-candidate-share/construction.json')
    reference = read('data/processed/continuous-transport/sample-manifest.json')
    inventory = read('data/processed/continuous-transport/inventory.json')
    folds = []
    for sample in reference['folds']:
        earlier = next(f for f in saved['folds'] if f['id'] == sample['savedFoldId'])
        if earlier['branch'] != 'primary' or earlier['protocol'] != 'expanding_window':
            raise ValueError('Incorrect primary chronological fit')
        if earlier['trainingOnlyMeans'] != sample['trainingOnlyMeans']:
            raise ValueError('Inherited centering disagreement')
        if any(int(i.split('-')[2]) >= sample['targetYear'] for i in earlier['trainingIds']):
            raise ValueError('Target/later training')
        folds.append({k: sample[k] for k in ('targetYear', 'savedFoldId', 'trainingIds', 'trainingOnlyMeans', 'comparisonIds', 'candidateIds', 'exclusiveTierCounts')} |
            {'fits': {m: earlier['fits'][key] for m, key in MODELS.items()}, 'sourceYear': earlier['sourceYear'],
             'trainingTransitionEnvironments': earlier['trainingTransitionEnvironments']})
    return {'stage': 43, 'folds': folds, 'fullFrame': inventory['fullFrame'], 'eligibilityReusedWithoutOutcomeSelection': True}


def build():
    paths = [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'scripts/transport/comparison').glob('*.py'))]
    paths += ['scripts/transport/continuous/features.py', 'scripts/transport/common.py',
              'scripts/models/joint_candidate_share/metrics.py', 'scripts/checkpoints/stage24_evaluation.py',
              'docs/stage43-comparison-contract.md', 'docs/stage43-comparison-findings.md',
              'scripts/tests/test_stage43_comparison.py']
    outputs = [str(p.relative_to(ROOT)) for p in sorted((ROOT / PREFIX).glob('*.json')) if p.name != 'implementation-manifest.json']
    return {'stage': 43, 'codeAndSpecificationHashes': {p: digest(p) for p in sorted(paths)},
        'outputHashes': {p: digest(p) for p in outputs},
        'reproduction': 'construction, evaluation, verification, report, manifest --check',
        'fittingPerformed': False, 'newSources': 0, 'operationalSelection': None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    count = verify()
    save('sample-manifest.json', samples(), True)
    save('implementation-manifest.json', build(), args.check)
    print('Stage43 manifest/IDs verified; prior data byte-identical:', count)


if __name__ == '__main__':
    main()
