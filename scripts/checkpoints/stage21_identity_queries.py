"""Materialize the fixed pilot's two permitted targeted query templates."""

import argparse
from hashlib import sha256

from scripts.checkpoints.stage21_identity_pilot import DEST, digest, encode, read


CLAIMS = 'data/processed/checkpoints/stage21-identity-pilot/claim-ledger.json'
PLAN = 'data/processed/checkpoints/stage21-identity-pilot/acquisition-plan.json'
OCCURRENCES = 'data/processed/models/candidate-overperformance/occurrences.json'


def _display(label):
    surname, given = label.split(',', 1)
    return given.strip().split()[0] + ' ' + surname.strip()


def build():
    claims, plan, occurrences = read(CLAIMS), read(PLAN), read(OCCURRENCES)
    by_case = {row['caseId']: row for row in claims['cases']}
    by_id = {row['candidateOccurrenceId']: row for row in occurrences['records']}
    queries = []
    for case_id in plan['selection']['selectedCaseIds']:
        case = by_case[case_id]
        seat = by_id[case['sourceOccurrenceId']]['electorateName']
        source, target = _display(case['sourceOriginalName']), _display(case['targetOriginalName'])
        if case['ambiguityType'].startswith('different_label'):
            first = f'"{source}" "{target}" "{seat}" election candidate'
        else:
            first = f'"{target}" "{seat}" {case["sourceYear"]} {case["targetYear"]} candidate'
        second = (f'"{target}" "{seat}" {case["sourceYear"]} {case["targetYear"]} '
                  f'{case["partyKey"]} selected former candidate name history')
        queries.append({'caseId': case_id, 'sourceName': source, 'targetName': target,
                        'seat': seat, 'query1': first, 'query2IfNeeded': second,
                        'status': 'planned_not_attempted'})
    output = {'schemaVersion': 1, 'stage': 21, 'records': queries,
              'rule': 'Fixed templates from committed plan; query2 only if relationship remains unresolved after query1; no third query.'}
    return {'targeted-query-plan.json': output,
            'targeted-query-plan-manifest.json': {
                'schemaVersion': 1, 'stage': 21,
                'inputSha256': {path: digest(path) for path in (CLAIMS, PLAN, OCCURRENCES)},
                'generatorSha256': digest('scripts/checkpoints/stage21_identity_queries.py'),
                'outputSha256': sha256(encode(output)).hexdigest()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, value in build().items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != encode(value):
                raise ValueError(f'Changed Stage21 query plan: {name}')
        else:
            path.write_bytes(encode(value))
    print('24 fixed targeted query pairs reproducible')


if __name__ == '__main__':
    main()
