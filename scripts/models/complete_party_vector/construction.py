"""Outcome-blind proportional compositional party-vector construction."""
import argparse
import hashlib
import math

from scripts.models.complete_party_vector.common import (
    DEST, digest, encode, read_json, verify_contract, write_or_check,
)

TOL = 1e-12


def validate_simplex(values):
    if not values or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError('Invalid nonnegative vector')
    if abs(sum(values) - 1) > TOL:
        raise ValueError('Incomplete party simplex')


def construct_vector(categories, source_local, scenario):
    """Return one coupled target-group vector; never read target local outcomes."""
    target = [c for c in categories if c['relationship'] != 'exit']
    ids = [c['categoryId'] for c in target]
    if len(set(ids)) != len(ids) or set(scenario) != set(ids) or set(source_local) != set(ids):
        raise ValueError('Ambiguous or incomplete target categories')
    validate_simplex(list(scenario.values()))
    masses = {}
    status = {}
    for category in target:
        cid = category['categoryId']
        local = source_local[cid]
        p0 = category['sourceNationalShare']
        if category['relationship'] == 'entrant':
            if local['sourceLocalStatus'] != 'entrant_no_source_category' or local['sourceLocalShare'] is not None:
                raise ValueError('Entrant has unexplained source category')
            affinity = 1.0
        elif category['relationship'] == 'continuing':
            if local['sourceLocalStatus'] not in ('observed_zero', 'observed_positive'):
                raise ValueError('Missing continuing source party row')
            p = local['sourceLocalShare']
            if p is None or not math.isfinite(p) or not 0 <= p <= 1 or p0 is None or not 0 < p0 <= 1:
                raise ValueError('Invalid continuing source party evidence')
            if (p == 0) != (local['sourceLocalStatus'] == 'observed_zero'):
                raise ValueError('Inconsistent zero status')
            affinity = p / p0
        else:
            raise ValueError('Unsupported category relation')
        masses[cid] = scenario[cid] * affinity
        status[cid] = {'relationship': category['relationship'],
                       'sourceLocalStatus': local['sourceLocalStatus'], 'affinity': affinity}
    total = sum(masses.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError('No supported target mass')
    vector = {cid: masses[cid] / total for cid in ids}
    validate_simplex(list(vector.values()))
    return vector, status


def construct_inventory(inventory):
    groups = {(r['sourceYear'], r['targetYear']): r['categories']
              for r in inventory['categoryRelationships']}
    records = []
    for row in inventory['frame']:
        pair = (row['sourceYear'], row['targetYear'])
        categories = groups[pair]
        scenario = {c['categoryId']: c['suppliedTargetNationalShare']
                    for c in categories if c['relationship'] != 'exit'}
        source = {c['categoryId']: c for c in row['sourceCategories']}
        base = {
            'sourceYear': row['sourceYear'], 'targetYear': row['targetYear'],
            'scope': row['scope'], 'contestStatus': row['contestStatus'],
            'sourceElectorateId': row['sourceElectorateId'],
            'targetElectorateId': row['targetElectorateId'],
            'informationSet': 'conditional_observed_target_national_party_support',
            'suppliedNationalScenario': dict(sorted(scenario.items())),
            'weightingAssumptions': None,
            'sourceDependencyContract': 'source-contract.json',
        }
        try:
            vector, status = construct_vector(categories, source, scenario)
        except ValueError as exc:
            base.update({'applicability': 'abstain', 'reason': str(exc),
                         'localPartyShares': None, 'sourceAffinityStatus': None})
        else:
            base.update({'applicability': 'constructed', 'reason': None,
                         'localPartyShares': dict(sorted(vector.items())),
                         'sourceAffinityStatus': dict(sorted(status.items()))})
        records.append(base)
    return {'schemaVersion': 1, 'stage': 23, 'role': 'construction_no_target_local_party_actuals',
            'frozenSpecificationSha256': digest('data/processed/models/complete-party-vector/specification.json'),
            'inventorySha256': hashlib.sha256(encode(inventory)).hexdigest(),
            'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    verify_contract()
    inventory = read_json('data/processed/models/complete-party-vector/input-inventory.json')
    output = construct_inventory(inventory)
    write_or_check('construction.json', output, args.check)
    print('Stage23 constructed:', sum(r['applicability'] == 'constructed' for r in output['records']))


if __name__ == '__main__':
    main()
