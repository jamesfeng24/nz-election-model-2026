"""Synthetic prior implications only, never calibration evidence."""
import numpy as np
from .common import PREFIX, read, save, arguments
from .simulation import component


def build():
    priors = read(PREFIX + '/specification.json')['priors']
    fixtures = [
        ('competitive_two', [.51, .49], ['national', 'labour']),
        ('multi_party', [.4, .35, .15, .08, .02], ['national', 'labour', 'other', 'other', 'no_group']),
        ('small_options', [.45, .4, .1, .04, .009, .001], ['national', 'labour', 'other', 'other', 'other', 'no_group']),
        ('missing_labour', [.55, .3, .1, .05], ['national', 'other', 'other', 'no_group']),
        ('no_majors', [.5, .3, .2], ['other', 'other', 'no_group'])]
    results = []
    for layer, scales in priors.items():
        for name, mean, groups in fixtures:
            row = {'layer': layer, 'targetYear': 0, 'targetElectorateId': 'synthetic:' + name,
                   'ids': [str(i) for i in range(len(mean))], 'groups': groups, 'mean': mean,
                   'ballotGroupKeys': [str(i) for i in range(len(mean))],
                   'features': [{'group': str(i)} for i in range(len(mean))]}
            q, metadata = component(row, scales, 8000)
            results.append({'layer': layer, 'fixture': name, 'mean': mean, 'groups': groups,
                            'expectedPP': (100 * q.mean(axis=0)).tolist(),
                            'interval90PP': (100 * np.quantile(q, [.05, .95], axis=0)).tolist(),
                            'metadata': metadata, 'syntheticOnly': True})
    return {'stage': 45, 'fixtures': results, 'calibrationEvidence': False}


def main():
    args = arguments(); save('prior-implications.json', build(), args.check)
    print('Stage45 synthetic prior implications reproduced')


if __name__ == '__main__':
    main()
