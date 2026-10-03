"""Whole ballot-group alignment; structural absence is distinct from missing data."""
from math import fsum, isfinite
from scripts.models.complete_party_vector.construction import validate_simplex


def category_audit(categories):
    ids = [c['categoryId'] for c in categories]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Duplicate/empty canonical category roster')
    result = []
    for c in categories:
        relation = c['relationship']
        source, target = c['sourcePartyKey'], c['targetPartyKey']
        if relation not in ('continuing', 'entrant', 'exit'):
            raise ValueError('Ambiguous whole-group continuity')
        if ((source is not None) != (relation != 'entrant') or
                (target is not None) != (relation != 'exit')):
            raise ValueError('Structural absence contradicts relationship')
        if not c.get('continuityEvidence'):
            raise ValueError('Missing category evidence')
        result.append({**c, 'alignmentRule': 'canonical_whole_ballot_group',
            'renamedContinuingGroup': relation == 'continuing' and source != target,
            'allianceAllocation': 'none; no_constituent_partition',
            'sourceStructuralZero': relation == 'entrant', 'targetStructuralZero': relation == 'exit'})
    for field in ('sourcePartyKey', 'targetPartyKey'):
        keys = [c[field] for c in result if c[field] is not None]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate election-local ballot-group mapping')
    return result


def align(categories, source, target):
    rows = category_audit(categories)
    expected_source = {c['categoryId'] for c in rows if c['relationship'] != 'entrant'}
    expected_target = {c['categoryId'] for c in rows if c['relationship'] != 'exit'}
    if set(source) != expected_source or set(target) != expected_target:
        raise ValueError('Missing or extra party category; cannot zero-fill')
    validate_simplex(list(source.values()))
    validate_simplex(list(target.values()))
    return ({c['categoryId']: 0.0 if c['sourceStructuralZero'] else source[c['categoryId']] for c in rows},
            {c['categoryId']: 0.0 if c['targetStructuralZero'] else target[c['categoryId']] for c in rows})


def total_variation(source, target):
    if set(source) != set(target):
        raise ValueError('Unaligned total-variation categories')
    validate_simplex(list(source.values()))
    validate_simplex(list(target.values()))
    value = .5*fsum(abs(target[k]-source[k]) for k in sorted(source))
    if not isfinite(value) or not 0 <= value <= 1+1e-12:
        raise ValueError('Invalid total variation')
    return value
