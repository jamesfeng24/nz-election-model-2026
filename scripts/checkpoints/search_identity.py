"""Prepare and validate fixed-order authoritative search batches."""

import argparse
import json
from pathlib import Path

from scripts.checkpoints.identity_evidence_pass import BASE, LEDGER, PRESERVED, ROOT
from scripts.checkpoints.profile_supplement import OUTPUT as PROFILE_SUPPLEMENT


BATCHES = BASE / 'search-batches'
ACTIVE = BASE / 'search-attempts.json'


def queries(row):
    parts = row['sourceCandidateName'].split(',', 1)
    if len(parts) != 2:
        raise ValueError('Candidate name lacks preserved surname/given split')
    name = f'{parts[1].strip()} {parts[0].strip()}'
    year = row['sourceYear'] if row['role'] == 'source' else row['targetYear']
    return (f'"{name}" "{row["electorateName"]}" {year} site:elections.nz OR site:parliament.nz',
            f'"{name}" "{row["electorateName"]}" {year} "{row["sourceAffiliation"]}" candidate')


def batch_requests(audit, initial, supplement, start, count):
    if start < 1 or count < 1 or start + count - 1 > 415:
        raise ValueError('Out-of-range fixed cohort search batch')
    requests = []
    profile_by_id = {row['candidateOccurrenceId']: row for row in supplement['records']}
    for row, item in zip(audit['records'][start - 1:start + count - 1],
                         initial['records'][start - 1:start + count - 1]):
        if row['order'] != item['order'] or row['candidateOccurrenceId'] != item['candidateOccurrenceId']:
            raise ValueError('Changed initial occurrence order')
        profile = profile_by_id.get(row['candidateOccurrenceId'])
        if profile is None:
            raise ValueError('Missing uniform preserved profile review')
        direct = (row['reassessedOccurrenceConfidence'] == 'confirmed' or
                  profile['status'] == 'direct_retrospective_profile_candidate')
        requests.append({'order': row['order'], 'candidateOccurrenceId': row['candidateOccurrenceId'],
                         'preservedDirectEvidence': direct,
                         'queries': list(queries(row))})
    return requests


def merge_batches(initial, batches):
    """Replay immutable search batches and reject skips, duplicates or >2 attempts."""
    ledger = json.loads(json.dumps(initial))
    next_order = 1
    for batch in sorted(batches, key=lambda item: item['startOrder']):
        if batch['startOrder'] != next_order:
            raise ValueError('Search batch skipped or duplicated an occurrence')
        for item in batch['records']:
            target = ledger['records'][next_order - 1]
            if item['order'] != next_order or item['candidateOccurrenceId'] != target['candidateOccurrenceId']:
                raise ValueError('Search attempt order or occurrence changed')
            if len(item['searchAttempts']) > 2:
                raise ValueError('More than two searches for occurrence')
            for number, attempt in enumerate(item['searchAttempts'], 1):
                if (attempt['number'] != number or not attempt['query'] or
                        (not attempt.get('searchedAt') and
                         attempt.get('timingStatus') != 'exact_time_unknown_preflight')):
                    raise ValueError('Incomplete search attempt')
            target['searchAttempts'] = item['searchAttempts']
            target['state'] = item['state']
            target['resourceIds'] = item.get('resourceIds', [])
            next_order += 1
    ledger['phase'] = 'external_search_in_progress'
    ledger['nextOrder'] = next_order
    return ledger


def _encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=int)
    parser.add_argument('--count', type=int)
    parser.add_argument('--merge', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    initial = json.loads((ROOT / LEDGER).read_text())
    if args.merge or args.check:
        paths = sorted((ROOT / BATCHES).glob('*.json')) if (ROOT / BATCHES).exists() else []
        batches = [json.loads(path.read_text()) for path in paths]
        merged = merge_batches(initial, batches)
        output = ROOT / ACTIVE
        if args.check:
            if not output.is_file() or output.read_bytes() != _encoded(merged):
                raise SystemExit('Search-attempt ledger differs from saved batches')
            print(f'Search ledger matches {len(paths)} batches; next order {merged["nextOrder"]}')
        else:
            output.write_bytes(_encoded(merged))
        return
    if args.start is None or args.count is None:
        parser.error('--start and --count required for query request')
    audit = json.loads((ROOT / PRESERVED).read_text())
    supplement = json.loads((ROOT / PROFILE_SUPPLEMENT).read_text())
    print(json.dumps(batch_requests(audit, initial, supplement, args.start, args.count), ensure_ascii=False))


if __name__ == '__main__':
    main()
