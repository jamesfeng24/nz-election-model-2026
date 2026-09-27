"""Generate or check evaluation-only actuals and conditional interval diagnostics."""

import argparse
from hashlib import sha256

from scripts.models.conditional_candidate_ledger.evaluate import evaluate, observed_results
from scripts.models.conditional_candidate_ledger.run import DEST, ROOT, digest, encode, read
from scripts.models.conditional_candidate_ledger.sources import TARGET_YEARS


EVALUATION_INPUTS = (
    'data/processed/models/conditional-candidate-ledger/ledgers.json',
    'data/processed/models/conditional-candidate-ledger/source-pools.json',
    'data/processed/models/conditional-candidate-ledger/construction-manifest.json',
    *(f'data/processed/elections/{year}.json' for year in TARGET_YEARS),
)
CODE = ('feasibility.py', 'evaluate.py', 'evaluation_run.py')


def build():
    construction = read(EVALUATION_INPUTS[0])
    pools = read(EVALUATION_INPUTS[1])
    frozen = read(EVALUATION_INPUTS[2])
    for name in EVALUATION_INPUTS[:2]:
        if digest(ROOT / name) != frozen['outputSha256'][name.rsplit('/', 1)[-1]]:
            raise ValueError('Changed saved construction before evaluation')
    elections = {year: read(f'data/processed/elections/{year}.json')
                 for year in TARGET_YEARS}
    actuals = observed_results(construction, elections)
    diagnostics = evaluate(construction, actuals, pools)
    outputs = {'actuals.json': actuals, 'diagnostics.json': diagnostics}
    outputs['evaluation-manifest.json'] = {
        'schemaVersion': 1, 'stage': 15, 'phase': 'evaluation_after_committed_construction',
        'inputSha256': {name: digest(ROOT / name) for name in EVALUATION_INPUTS},
        'codeSha256': {f'scripts/models/conditional_candidate_ledger/{name}':
                       digest(ROOT / 'scripts/models/conditional_candidate_ledger' / name)
                       for name in CODE},
        'outputSha256': {name: sha256(encode(value)).hexdigest()
                         for name, value in outputs.items()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, value in outputs.items():
            if (DEST / name).read_bytes() != encode(value):
                raise ValueError(f'Changed Stage 15 evaluation output: {name}')
    else:
        for name, value in outputs.items():
            (DEST / name).write_bytes(encode(value))
    print('Stage 15 conditional evaluation: 191 held general contests; no operational selection')


if __name__ == '__main__':
    main()
