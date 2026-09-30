"""Generate evaluation-only actuals and scores after committed construction."""

import argparse
from hashlib import sha256

from scripts.models.conditional_candidate_share.evaluate import actuals, evaluate
from scripts.models.conditional_candidate_share.inventory import DEST, ROOT, digest, encode, read
from scripts.models.conditional_candidate_share.run import ELECTION_PATHS


INPUTS = ('data/processed/models/conditional-candidate-share/construction.json',
          'data/processed/models/conditional-candidate-share/construction-manifest.json',
          *ELECTION_PATHS)


def build():
    construction = read(INPUTS[0])
    frozen = read(INPUTS[1])
    if digest(ROOT / INPUTS[0]) != frozen['constructionSha256']:
        raise ValueError('Changed committed construction before evaluation')
    elections = {int(path[-9:-5]): read(path) for path in ELECTION_PATHS}
    outcomes = actuals(construction, elections)
    diagnostics = evaluate(construction, outcomes)
    outputs = {'actuals.json': outcomes, 'diagnostics.json': diagnostics}
    outputs['evaluation-manifest.json'] = {
        'schemaVersion': 1, 'stage': 18, 'phase': 'evaluation_after_committed_construction',
        'inputSha256': {name: digest(ROOT / name) for name in INPUTS},
        'generatorSha256': {name: digest(ROOT / 'scripts/models/conditional_candidate_share' / name)
                            for name in ('evaluate.py', 'evaluation_run.py')},
        'outputSha256': {name: sha256(encode(data)).hexdigest() for name, data in outputs.items()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, data in outputs.items():
            if (DEST / name).read_bytes() != encode(data):
                raise ValueError(f'Changed Stage 18 evaluation artifact: {name}')
    else:
        for name, data in outputs.items():
            (DEST / name).write_bytes(encode(data))
    print({year: {'contests': item['allSupported']['fitted_floor']['contests'],
                  'maePP': item['allSupported']['fitted_floor']['contestEqualMaePP']}
           for year, item in outputs['diagnostics.json']['summary']['byHoldout'].items()})


if __name__ == '__main__':
    main()
