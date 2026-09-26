"""Uniform preserved Parliament-profile candidates omitted by the initial audit."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from scripts.checkpoints.identity_evidence_pass import OCCURRENCES, PRESERVED, ROOT, STAGE9
from scripts.models.freshman_incumbency.inventory import find_profile
from scripts.transform.historical import key


OUTPUT = Path('data/processed/checkpoints/identity-evidence-pass/preserved-profile-supplement.json')
PLAN = Path('data/source-plans/freshman-incumbency-tenure-sources.json')
SOURCE_SNAPSHOT = Path('data/source-plans/stage13-profile-supplement-sources.json')


def _read(path):
    raw = (ROOT / path).read_bytes()
    return json.loads(raw), sha256(raw).hexdigest()


def _first_given(name):
    return name.split(',', 1)[1].strip().split()[0] if ',' in name else ''


def build_supplement(audit, occurrences, profiles, hashes):
    by_id = {row['candidateOccurrenceId']: row for row in occurrences['records']}
    records = []
    for row in audit['records']:
        occurrence = by_id[row['candidateOccurrenceId']]
        matches = find_profile(occurrence, profiles['profiles'])
        candidates = []
        for profile, service_rows in matches:
            exact_first = key(_first_given(occurrence['sourceCandidateName'])) == key(
                _first_given(profile['displayName']))
            candidates.append({'sourceId': profile['sourceId'],
                               'profileDisplayName': profile['displayName'],
                               'serviceRowsAtElection': service_rows,
                               'exactFirstName': exact_first,
                               'publicationDate': profile['publishedDate'],
                               'retrievedAt': profile['retrievedAt'],
                               'route': 'unique_seat_date_and_exact_given_name' if exact_first else
                               'unique_seat_date_but_alias_unproved'})
        status = ('no_candidate' if not candidates else 'ambiguous_multiple_profiles'
                  if len(candidates) > 1 else 'direct_retrospective_profile_candidate'
                  if candidates[0]['exactFirstName'] else 'alias_unresolved')
        records.append({'candidateOccurrenceId': row['candidateOccurrenceId'],
                        'order': row['order'], 'status': status,
                        'profileCandidates': candidates,
                        'inheritedAuditConfidence': row['reassessedOccurrenceConfidence']})
    return {'schemaVersion': 1, 'stage': 13, 'status': 'post-initial-audit_preserved-evidence-supplement',
            'reason': 'Initial audit attached Stage9 profiles only through inherited Stage8/10 links; this searches the same preserved profiles uniformly for all 415 by seat/date, then separates exact given-name proof from nickname/alias uncertainty. It changes no cohort or search order.',
            'inputHashes': hashes, 'records': records,
            'summary': dict(sorted(Counter(row['status'] for row in records).items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    inputs = {}
    hashes = {}
    for path in (PRESERVED, OCCURRENCES, STAGE9, PLAN):
        inputs[path], hashes[str(path)] = _read(path)
    result = build_supplement(inputs[PRESERVED], inputs[OCCURRENCES], inputs[STAGE9], hashes)
    encoded = (json.dumps(result, indent=2, ensure_ascii=False) + '\n').encode()
    source_ids = {candidate['sourceId'] for row in result['records']
                  for candidate in row['profileCandidates']}
    source_by_id = {row['id']: row for row in inputs[PLAN]['sources']}
    if len(source_by_id) != len(inputs[PLAN]['sources']) or not source_ids <= set(source_by_id):
        raise ValueError('Missing or duplicate profile source')
    snapshot = {'schemaVersion': 1, 'stage': 13,
                'purpose': 'uniform preserved profile supplement',
                'requiredSourceRecords': [source_by_id[source_id] for source_id in sorted(source_ids)]}
    snapshot_bytes = (json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n').encode()
    for record in snapshot['requiredSourceRecords']:
        if sha256((ROOT / record['rawPath']).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Changed preserved profile raw bytes')
    destination = ROOT / OUTPUT
    if args.check:
        if not destination.is_file() or destination.read_bytes() != encoded:
            raise SystemExit('Preserved profile supplement changed')
        if not (ROOT / SOURCE_SNAPSHOT).is_file() or (ROOT / SOURCE_SNAPSHOT).read_bytes() != snapshot_bytes:
            raise SystemExit('Preserved profile source snapshot changed')
        print('Preserved profile supplement matches')
    else:
        destination.write_bytes(encoded)
        (ROOT / SOURCE_SNAPSHOT).write_bytes(snapshot_bytes)


if __name__ == '__main__':
    main()
