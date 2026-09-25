"""Reproduce the pre-acquisition fixed-cohort evidence and search ledger."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = Path('data/processed/checkpoints/identity-evidence-pass')
COHORT = Path('data/processed/checkpoints/evidence-repair/cohort-inventory.json')
OCCURRENCES = Path('data/processed/models/candidate-overperformance/occurrences.json')
STAGE8 = Path('data/processed/models/candidate-persistence/person-links.json')
STAGE9 = Path('data/processed/models/freshman-incumbency/tenure-evidence.json')
STAGE10 = Path('data/processed/models/replacement-candidate/person-links.json')
REGISTRY = Path('data/sources.json')
PRESERVED = BASE / 'preserved-audit.json'
LEDGER = BASE / 'search-ledger.json'
SNAPSHOT = Path('data/source-plans/stage13-preserved-candidacy-sources.json')
IDENTITY_SNAPSHOT = Path('data/source-plans/stage13-preserved-identity-sources.json')
IDENTITY_PLANS = (Path('data/source-plans/candidate-persistence-sources.json'),
                  Path('data/source-plans/freshman-incumbency-tenure-sources.json'),
                  Path('data/source-plans/stage10-identity-sources.json'))
SEED = 'nz-election-model-2026-identity-acquisition-v1'
INPUTS = (COHORT, OCCURRENCES, STAGE8, STAGE9, STAGE10)


def _read(path):
    raw = (ROOT / path).read_bytes()
    return json.loads(raw), sha256(raw).hexdigest()


def ordered_occurrences(cohort):
    """Return the complete fixed sample without reading winner or identity fields."""
    ids = [candidate_id for seat in cohort['frame'] if seat['selected']
           for candidate_id in seat['sourceOccurrenceIds'] + seat['targetOccurrenceIds']]
    if len(ids) != 415 or len(set(ids)) != 415:
        raise ValueError('Fixed cohort must contain 415 distinct occurrences')
    return sorted(ids, key=lambda candidate_id: (
        sha256(f'{SEED}|{candidate_id}'.encode()).hexdigest(), candidate_id))


def _indexes(occurrences, stage8, stage10):
    by_occurrence = {row['candidateOccurrenceId']: row for row in occurrences['records']}
    if len(by_occurrence) != len(occurrences['records']):
        raise ValueError('Duplicate source occurrence')
    by_stage8 = {row['candidateOccurrenceId']: row for row in stage8['links']}
    by_stage10 = {row['candidateOccurrenceId']: row for row in stage10['links']}
    if len(by_stage8) != len(stage8['links']) or len(by_stage10) != len(stage10['links']):
        raise ValueError('Duplicate inherited identity link')
    return by_occurrence, by_stage8, by_stage10


def _stage8_route(link, occurrence_id):
    if link is None:
        return {'confidence': 'unresolved', 'personId': None,
                'personExistence': 'unknown', 'route': 'none', 'sourceIds': [],
                'factDate': None, 'publicationDate': None, 'retrievedAt': None,
                'outcomeCoverage': 'unknown'}
    evidence = link['evidence']
    anchors = evidence.get('anchorOccurrences', [])
    direct = (link['status'] == 'confirmed' and evidence.get('directOccurrenceEvidence') is True
              and any(anchor['candidateOccurrenceId'] == occurrence_id for anchor in anchors))
    if link['status'] == 'confirmed' and not direct:
        raise ValueError(f'Unsupported inherited confirmed link: {occurrence_id}')
    fact_date = next((anchor['electionDate'] for anchor in anchors
                      if anchor['candidateOccurrenceId'] == occurrence_id), None)
    return {'confidence': 'confirmed' if direct else 'probable',
            'personId': link['personId'], 'personExistence': link['personExistenceStatus'],
            'route': link['method'], 'sourceIds': [evidence['sourceId']] if evidence.get('sourceId') else [],
            'factDate': fact_date, 'publicationDate': evidence.get('evidencePublishedAt'),
            'retrievedAt': evidence.get('evidenceRetrievedAt'),
            'outcomeCoverage': 'retrospective_winner_anchor' if direct else 'chain_projection_or_unknown'}


def _stage10_route(link):
    if link is None:
        return None
    return {'confidence': link['occurrenceConfidence'], 'personId': link['personId'],
            'personExistence': link['personExistenceStatus'], 'route': link['method'],
            'sourceIds': [link['sourceId']], 'factDate': link['historicalFactDate'],
            'publicationDate': link['publicationDate'], 'retrievedAt': link['retrievalAt'],
            'outcomeCoverage': 'retrospective_or_review_selected'}


def _reassess(stage8_route, stage10_route):
    routes = [route for route in (stage8_route, stage10_route) if route and route['confidence'] != 'unresolved']
    confirmed = [route for route in routes if route['confidence'] == 'confirmed']
    if len({route['personId'] for route in confirmed}) > 1:
        return 'unresolved', None, 'conflicting_confirmed_person_ids'
    if confirmed:
        return 'confirmed', confirmed[0]['personId'], 'direct_occurrence_route'
    if not routes:
        return 'unresolved', None, 'no_cross_election_corroboration'
    if len({route['personId'] for route in routes}) > 1:
        return 'unresolved', None, 'conflicting_probable_person_ids'
    return 'probable', routes[0]['personId'], 'projection_only'


def build_preserved_audit(cohort, occurrences, stage8, stage9, stage10, hashes):
    """Audit all sampled candidacies uniformly, keeping inherited claims separate."""
    order = ordered_occurrences(cohort)
    by_occurrence, by_stage8, by_stage10 = _indexes(occurrences, stage8, stage10)
    source_ids = set()
    rows = []
    roles = {}
    for seat in cohort['frame']:
        if seat['selected']:
            roles.update({candidate_id: ('source' if candidate_id in seat['sourceOccurrenceIds'] else 'target',
                                         seat['sourceYear'], seat['targetYear'], seat['scope'])
                          for candidate_id in seat['sourceOccurrenceIds'] + seat['targetOccurrenceIds']})
    profile_urls = {profile['sourceUrl']: profile for profile in stage9['profiles']}
    profiles_by_id = {profile['sourceId']: profile for profile in stage9['profiles']}
    for rank, occurrence_id in enumerate(order, 1):
        occurrence = by_occurrence[occurrence_id]
        source_ids.update(occurrence['provenance']['sourceIds'])
        inherited8 = by_stage8.get(occurrence_id)
        inherited10 = by_stage10.get(occurrence_id)
        route8 = _stage8_route(inherited8, occurrence_id)
        route10 = _stage10_route(inherited10)
        confidence, person_id, reason = _reassess(route8, route10)
        profile = profile_urls.get(inherited8['evidence'].get('sourceUrl')) if inherited8 else None
        if profile is None and inherited10:
            profile = profiles_by_id.get(inherited10['sourceId'])
        career = {'status': profile['tenureEvidenceStatus'], 'sourceId': profile['sourceId'],
                  'serviceRows': profile['serviceRows'], 'publishedDate': profile['publishedDate'],
                  'retrievedAt': profile['retrievedAt']} if profile and confidence == 'confirmed' else {
                      'status': 'unknown', 'sourceId': None, 'serviceRows': [],
                      'publishedDate': None, 'retrievedAt': None}
        role, source_year, target_year, scope = roles[occurrence_id]
        rows.append({'order': rank, 'candidateOccurrenceId': occurrence_id,
                     'sourceYear': source_year, 'targetYear': target_year, 'role': role,
                     'scope': scope, 'sourceCandidateName': occurrence['sourceCandidateName'],
                     'electorateName': occurrence['electorateName'],
                     'sourceAffiliation': occurrence['sourceAffiliation'],
                     'preservedCandidacySourceIds': sorted(occurrence['provenance']['sourceIds']),
                     'inheritedEvidence': {'stage8': route8, 'stage10': route10},
                     'reassessedOccurrenceConfidence': confidence, 'reassessedPersonId': person_id,
                     'reassessmentReason': reason, 'careerHistory': career,
                     'newPassEvidence': [], 'prospectiveAvailability': 'unverified_cutoff'})
    return ({'schemaVersion': 1, 'stage': 13, 'phase': 'before_external_acquisition',
             'orderSeed': SEED, 'inputHashes': hashes, 'records': rows,
             'summary': dict(sorted(Counter(row['reassessedOccurrenceConfidence'] for row in rows).items()))},
            source_ids)


def build_ledger(audit):
    return {'schemaVersion': 1, 'stage': 13, 'phase': 'before_external_acquisition',
            'orderSeed': SEED, 'maxNewUniqueResources': 60,
            'maxAuthoritativeSearchesPerUnresolvedOccurrence': 2,
            'records': [{'order': row['order'], 'candidateOccurrenceId': row['candidateOccurrenceId'],
                         'state': 'pending', 'searchAttempts': [], 'resourceIds': []}
                        for row in audit['records']]}


def build_snapshot(source_ids, registry):
    live = registry['sources']
    by_id = {row['id']: row for row in live}
    if len(by_id) != len(live) or not source_ids <= set(by_id):
        raise ValueError('Duplicate or missing preserved candidacy source ID')
    records = [by_id[source_id] for source_id in sorted(source_ids)]
    return {'schemaVersion': 1, 'stage': 13, 'purpose': 'preserved cohort candidature',
            'requiredSourceRecords': records}


def verify_snapshot(snapshot, registry):
    live = registry['sources']
    by_id = {row['id']: row for row in live}
    pinned = snapshot['requiredSourceRecords']
    if len(by_id) != len(live) or len({row['id'] for row in pinned}) != len(pinned):
        raise ValueError('Ambiguous source ID')
    for row in pinned:
        if by_id.get(row['id']) != row:
            raise ValueError('Changed or removed required source record')
        raw = (ROOT / row['rawPath']).read_bytes()
        if sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Changed required raw source bytes')


def build_identity_snapshot(audit, plans):
    required_ids = {source_id for row in audit['records']
                    for route in row['inheritedEvidence'].values() if route
                    for source_id in route['sourceIds'] if not source_id.startswith('parliament:')}
    required_ids.update(row['careerHistory']['sourceId'] for row in audit['records']
                        if row['careerHistory']['sourceId'])
    by_id = {}
    for plan in plans:
        for record in plan['sources']:
            if record['id'] in by_id:
                raise ValueError('Duplicate inherited identity source ID')
            by_id[record['id']] = record
    if not required_ids <= set(by_id):
        raise ValueError('Missing inherited identity source record')
    return {'schemaVersion': 1, 'stage': 13,
            'purpose': 'selected inherited identity evidence only',
            'requiredSourceRecords': [by_id[source_id] for source_id in sorted(required_ids)]}


def verify_identity_snapshot(snapshot, plans):
    live = [record for plan in plans for record in plan['sources']]
    by_id = {record['id']: record for record in live}
    pinned = snapshot['requiredSourceRecords']
    if len(live) != len(by_id) or len(pinned) != len({row['id'] for row in pinned}):
        raise ValueError('Ambiguous inherited identity source ID')
    for record in pinned:
        if by_id.get(record['id']) != record:
            raise ValueError('Changed or missing inherited identity source record')
        if sha256((ROOT / record['rawPath']).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Changed inherited identity raw bytes')


def _encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    values = {}
    hashes = {}
    for path in INPUTS:
        values[path], hashes[str(path)] = _read(path)
    registry, _ = _read(REGISTRY)
    identity_plans = []
    for path in IDENTITY_PLANS:
        plan, hashes[str(path)] = _read(path)
        identity_plans.append(plan)
    audit, source_ids = build_preserved_audit(*(values[path] for path in INPUTS), hashes)
    outputs = {PRESERVED: audit, LEDGER: build_ledger(audit),
               SNAPSHOT: build_snapshot(source_ids, registry),
               IDENTITY_SNAPSHOT: build_identity_snapshot(audit, identity_plans)}
    if args.check:
        verify_snapshot(outputs[SNAPSHOT], registry)
        verify_identity_snapshot(outputs[IDENTITY_SNAPSHOT], identity_plans)
        for path, value in outputs.items():
            if not (ROOT / path).is_file() or (ROOT / path).read_bytes() != _encoded(value):
                raise SystemExit(f'Changed pre-acquisition checkpoint: {path}')
        print('Pre-acquisition evidence, search ledger and source bytes match')
    else:
        for path, value in outputs.items():
            destination = ROOT / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(_encoded(value))
        verify_snapshot(outputs[SNAPSHOT], registry)
        verify_identity_snapshot(outputs[IDENTITY_SNAPSHOT], identity_plans)


if __name__ == '__main__':
    main()
