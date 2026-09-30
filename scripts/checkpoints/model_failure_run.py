"""Generate deterministic exploratory summaries from pinned frozen predictions."""

import argparse
from hashlib import sha256

from scripts.checkpoints.model_failure_inventory import DEST, digest, encode, read
from scripts.checkpoints.model_failure_diagnostics import build
from scripts.checkpoints.model_failure_plots import build as build_plots


INVENTORY = 'data/processed/checkpoints/model-failure-diagnostics/diagnostic-inventory.json'
CODE = ('model_failure_inventory.py', 'model_failure_diagnostics.py',
        'model_failure_plots.py', 'model_failure_run.py')


def outputs():
    inventory = read(INVENTORY)
    pinned = read('data/processed/checkpoints/model-failure-diagnostics/inventory-manifest.json')
    if digest(INVENTORY) != pinned['outputSha256']['diagnostic-inventory.json']:
        raise ValueError('Changed pre-diagnostic inventory')
    diagnostic = build(inventory)
    json_outputs = {'paired-diagnostics.json': diagnostic}
    plots = build_plots(diagnostic['rows'])
    manifest = {'schemaVersion': 1, 'stage': 19,
                'role': 'frozen_prediction_exploratory_diagnostics_no_new_fit',
                'inventorySha256': digest(INVENTORY),
                'generatorSha256': {name: digest('scripts/checkpoints/' + name)
                                    for name in CODE},
                'outputSha256': {name: sha256(encode(value)).hexdigest()
                                 for name, value in json_outputs.items()},
                'plotSha256': {name: sha256(value).hexdigest()
                               for name, value in plots.items()}}
    json_outputs['diagnostic-manifest.json'] = manifest
    return json_outputs, plots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    json_outputs, plots = outputs()
    for name, data in json_outputs.items():
        path = DEST / name
        expected = encode(data)
        if args.check:
            if path.read_bytes() != expected:
                raise ValueError(f'Changed Stage19 diagnostic: {name}')
        else:
            path.write_bytes(expected)
    for name, data in plots.items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != data:
                raise ValueError(f'Changed Stage19 plot: {name}')
        else:
            path.write_bytes(data)
    print(json_outputs['paired-diagnostics.json']['coverage'])


if __name__ == '__main__':
    main()
