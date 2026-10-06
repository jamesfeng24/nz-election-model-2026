"""Stage72: the 2026 uncertainty scales, by the frozen Stage45 rule applied with target 2026.

python -m scripts.nowcast_config.scales [--check]

No new estimator, fit or score: `scripts.uncertainty_revision.estimation.fit` is called unchanged on the unchanged
Stage44 inventory and Stage45 priors, and the result must equal Stage45's own all-election `descriptive` fit. The
D107 multipliers are applied as arithmetic to the candidate seat balance scale only.
"""
import argparse
import json
import math
from scripts.balance_scale.common import equivalent
from scripts.uncertainty_revision.common import ROOT, read, encode
from scripts.uncertainty_revision.estimation import fit

OUTPUT = 'data/processed/nowcast-config/scales-2026.json'
CONFIG = 'config/nowcast-2026.json'
INVENTORY = 'data/processed/uncertainty/inventory.json'
STAGE45 = 'data/processed/uncertainty-revision/scales.json'
LAYERS = (('local_party', 'partyRecords'), ('candidate', 'candidateRecords'))


def build():
    inventory, stage45 = read(INVENTORY), read(STAGE45)['descriptive']
    multipliers = read(CONFIG)['uncertainty']['candidateBalanceSeatMultiplier']
    layers = {}
    for layer, key in LAYERS:
        result = fit(inventory[key], layer, 2026)
        reference = {k: v for k, v in stage45[layer].items() if k != 'targetYear'}
        if not equivalent(reference, {k: v for k, v in result.items() if k != 'targetYear'}, 1e-12):
            raise ValueError(f'2026 {layer} fold differs from the Stage45 all-election fit')
        layers[layer] = {'trainingYears': result['trainingYears'], 'scales': result['scales'],
                         'contributions': result['contributions'], 'status': result['status']}
    balance = layers['candidate']['scales']['balance']
    effective = {kind: {'seat': balance['seat'] * m, 'shared': balance['shared'],
                        'total': math.hypot(balance['seat'] * m, balance['shared']), 'multiplier': m}
                 for kind, m in multipliers.items()}
    return {'stage': 72, 'targetYear': 2026, 'rule': 'Stage45 fit(rows, layer, 2026), unchanged; equals the Stage45 all-election descriptive fit',
            'layers': layers,
            'candidateBalanceByClass': {'decision': 'D107', 'appliesTo': 'candidate N/L balance seat scale only; shared scale, means and other coordinates unchanged',
                                        **effective},
            'evidence': 'development-informed and flag-selection-sensitive (D101, D107); not a validated calibration',
            'equalsStage45Descriptive': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    check = parser.parse_args().check
    value = build()
    if check:
        if not equivalent(read(OUTPUT), value, 1e-12):
            raise SystemExit('Stale ' + OUTPUT)
        print('Stage72 2026 scales reproduced')
        return
    (ROOT / OUTPUT).write_bytes(encode(value))
    print('Stage72 2026 scales written')


if __name__ == '__main__':
    main()
