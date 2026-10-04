"""Regenerate Stage37 companions without fitting or candidate calculations."""
import argparse
from .common import save, verify_inputs
from .inventory import build
from .allocation import run as allocate
from .external import audit, evaluate


def run(check=False, construction_only=False):
    verify_inputs()
    inventory = build()
    save('inventory.json', inventory, check)
    allocation = allocate(inventory, check)
    external = audit()
    save('external-inventory.json', external, check)
    if not construction_only:
        evaluate(external, check)
    print('Stage37:', len(allocation['cases']), 'conditional allocation cases;', external['pointMatchedCases'], '/3 point-matched external cases; no inference/candidate replay')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--construction-only', action='store_true')
    args = parser.parse_args()
    run(args.check, args.construction_only)
