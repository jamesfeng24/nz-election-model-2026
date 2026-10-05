"""Lightweight sealed Stage39 integrity, distinct from full --check reconstruction."""
import argparse
import hashlib
from math import isfinite, prod

from .ci_selection import ROOT, load_registry, fingerprint_errors


def simplex(values):
    if len(values) < 2 or any(not isfinite(v) or not 0 <= v <= 1 for v in values) or abs(sum(values)-1) > 1e-12:
        raise ValueError('Invalid complete Stage39 simplex')


def verify():
    registry = load_registry()
    errors = fingerprint_errors(registry)
    if errors:
        raise ValueError('Stage39 dependencies not previously validated: ' + '; '.join(errors[:5]))
    from scripts.polling.candidate_integration.common import OUT, DESIGN, METHODS, POLICIES, read, verify_inputs, verify_phase, preserve
    from scripts.polling.candidate_integration.construction import signature
    verify_inputs()
    verify_phase('construction')
    verify_phase('evaluation')
    preserved = preserve()
    inventory, construction = read(OUT/'inventory.json'), read(OUT/'construction.json')
    slates_by_seat = {r['targetElectorateId']: {c['targetOccurrenceId'] for c in r['candidates']}
                      for r in read(DESIGN/'inventory.json')['contestRecords']}
    if construction['signature'] != signature(256) or construction['heldoutOutcomesUsed'] or construction['operationalSelection'] is not None:
        raise ValueError('Invalid sealed Stage39 information set/signature')
    if len(inventory['cases']) != 3 or len(construction['cases']) != 6:
        raise ValueError('Missing Stage39 cases')
    by_year = {c['year']: c for c in inventory['cases']}
    seen, vectors, candidates = set(), 0, 0
    for case in construction['cases']:
        key = case['year'], case['policy']
        if key in seen or case['policy'] not in POLICIES or case['abstentions']:
            raise ValueError('Duplicate/invalid Stage39 case')
        seen.add(key)
        source = by_year[case['year']]
        if case['expectedIds'] != source['evaluationIds'] or case['candidateIds'] != source['evaluationCandidateIds']:
            raise ValueError('Stage39 exact sample changed')
        if [r['targetElectorateId'] for r in case['records']] != case['expectedIds']:
            raise ValueError('Stage39 complete contest order changed')
        fine = read(OUT/case['nationalArtifact'])
        if fine['drawIds'] != source['nationalDrawIds'] or fine['ballotGroupKeys'] != [r['ballotGroupKey'] for r in source['roster']]:
            raise ValueError('Stage39 national draw identity/schema changed')
        if len(fine['arrays']) != prod(source['chainShape'][:2]) or len(fine['arrays']) != len(fine['drawIds']):
            raise ValueError('Incomplete Stage39 national draws')
        for values in fine['arrays']:
            simplex(values)
            vectors += 1
        for record in case['records']:
            slates = [set(record['methods'][method]['candidateShares']) for method in METHODS]
            if slates[0] != slates_by_seat[record['targetElectorateId']] or any(slate != slates[0] for slate in slates[1:]):
                raise ValueError('Incomplete paired Stage39 candidate slate')
            for method in METHODS:
                output = record['methods'][method]
                simplex(list(output['candidateShares'].values()))
                if output['fitId'] != source['fits'][method]['fitId']:
                    raise ValueError('Wrong frozen Stage39 fit')
                if set(output['nationalInputOnlyConditionalIntervals']) != slates[0]:
                    raise ValueError('Incomplete Stage39 marginal intervals')
                for intervals in output['nationalInputOnlyConditionalIntervals'].values():
                    for low, high in intervals.values():
                        if not isfinite(low) or not isfinite(high) or not 0 <= low <= high <= 1:
                            raise ValueError('Invalid Stage39 marginal intervals')
                candidates += len(slates[0])
        # Local candidate caches are optional derived files; a present cache must be exact.
        for cache in case['candidateDrawCaches'].values():
            path = ROOT/cache['path']
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != cache['sha256']:
                raise ValueError('Corrupt optional Stage39 candidate cache')
    expected = {(year, policy) for year in by_year for policy in POLICIES}
    if seen != expected:
        raise ValueError('Missing policy case')
    return {'preservedFiles': preserved, 'nationalVectors': vectors, 'candidateCoordinates': candidates,
            'predictionReconstruction': False, 'inference': False, 'validatedHead': registry['attestation']['head']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', required=True)
    parser.parse_args()
    print('Stage39 lightweight sealed integrity:', verify())


if __name__ == '__main__':
    main()
