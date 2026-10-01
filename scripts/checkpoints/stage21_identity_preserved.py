"""Reassess selected relationship cases from preserved adjudication channels."""

import argparse
from hashlib import sha256

from scripts.checkpoints.stage21_identity_pilot import DEST, ROOT, digest, encode, read


INPUTS = (
    'data/processed/checkpoints/stage21-identity-pilot/claim-ledger.json',
    'data/processed/checkpoints/stage21-identity-pilot/acquisition-plan.json',
    'data/processed/models/candidate-persistence/person-links.json',
    'data/processed/models/replacement-candidate/person-links.json',
    'data/processed/models/replacement-candidate/inventory.json',
    'data/processed/models/freshman-incumbency/tenure-evidence.json',
    'data/processed/checkpoints/identity-evidence-pass/final/occurrence-evidence.json',
    'data/processed/checkpoints/identity-evidence-pass/final/relations.json',
)


def build():
    ledger, plan, stage8, stage10, stage10_inventory, tenure, stage13, stage13_relations = map(read, INPUTS)
    by8 = {r['candidateOccurrenceId']: r for r in stage8['links']}
    by10 = {r['candidateOccurrenceId']: r for r in stage10['links']}
    by10_event = {r['eventId']: r for r in stage10_inventory['records']}
    by13 = {r['candidateOccurrenceId']: r for r in stage13['records']}
    by_relation = {(r['sourceOccurrenceId'], r['targetOccurrenceId']): r
                   for r in stage13_relations['records']}
    by_profile = {r['sourceId']: r for r in tenure['profiles']}
    by_case = {r['caseId']: r for r in ledger['cases']}
    rows = []
    for case_id in plan['selection']['selectedCaseIds']:
        case = by_case[case_id]
        source_id, target_id = case['sourceOccurrenceId'], case['targetOccurrenceId']
        previous = case['existingEvidence']
        old_event = by10_event.get(case_id, {})
        relevant_profile_ids = sorted({profile_id for profile_id in (
            old_event.get('sourceProfileId'), old_event.get('incomingProfileId'),
            (by10.get(source_id) or {}).get('sourceId'),
            (by10.get(target_id) or {}).get('sourceId'))
            if profile_id in by_profile})
        relation = by_relation.get((source_id, target_id))
        stage13_source, stage13_target = by13.get(source_id), by13.get(target_id)
        rows.append({
            'caseId': case_id,
            'sourceOfficialCandidatureIds': case['sourceOfficialIds'],
            'targetOfficialCandidatureIds': case['targetOfficialIds'],
            'sourceStage8': {'confidence': (by8.get(source_id) or {}).get('status', 'unresolved'),
                             'method': (by8.get(source_id) or {}).get('method'),
                             'anchorOccurrenceIds': [r['candidateOccurrenceId'] for r in
                                                     (by8.get(source_id) or {}).get('evidence', {}).get('anchorOccurrences', [])]},
            'targetStage8': {'confidence': (by8.get(target_id) or {}).get('status', 'unresolved'),
                             'method': (by8.get(target_id) or {}).get('method'),
                             'anchorOccurrenceIds': [r['candidateOccurrenceId'] for r in
                                                     (by8.get(target_id) or {}).get('evidence', {}).get('anchorOccurrences', [])]},
            'stage10OccurrenceRoutes': [by10[occurrence_id] for occurrence_id
                                        in (source_id, target_id) if occurrence_id in by10],
            'stage13PrimarySourceOccurrence': (stage13_source or {}).get('primaryOccurrenceConfidence'),
            'stage13PrimaryTargetOccurrence': (stage13_target or {}).get('primaryOccurrenceConfidence'),
            'stage13PrimaryRelation': relation['verifiedRelation'] if relation else None,
            'preservedProfileIds': relevant_profile_ids,
            'preservedProfileServiceRows': {profile_id: by_profile[profile_id]['serviceRows']
                                            for profile_id in relevant_profile_ids},
            'priorStage10Class': previous['stage10Event'],
            'relationshipFinding': 'unresolved_explicit_cross_occurrence_bridge',
            'why': case['whyExistingEvidenceIsInsufficient'],
            'careerFinding': 'retain_prior_dated_service_if_supported;_otherwise_unknown;_no_complete_career_inference',
            'timing': 'official_election_fact_precedes_target;_profile_or_prior_review_retrieval_retrospective;_historical_publication_by_target_cutoff_unverified',
        })
    output = {'schemaVersion': 1, 'stage': 21, 'phase': 'uniform_selected_case_preserved_review',
              'reviewedCases': len(rows), 'records': rows,
              'interpretation': 'Preserved official candidature confirms each occurrence; inherited profile/name chains and direct one-occurrence facts do not by themselves bridge exact source and target nominations.'}
    return {'preserved-review.json': output,
            'preserved-review-manifest.json': {
                'schemaVersion': 1, 'stage': 21,
                'inputSha256': {path: digest(path) for path in INPUTS},
                'generatorSha256': digest('scripts/checkpoints/stage21_identity_preserved.py'),
                'outputSha256': sha256(encode(output)).hexdigest()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    for name, output in outputs.items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != encode(output):
                raise ValueError(f'Changed Stage21 preserved review: {name}')
        else:
            path.write_bytes(encode(output))
    print({'reviewedCases': outputs['preserved-review.json']['reviewedCases']})


if __name__ == '__main__':
    main()
