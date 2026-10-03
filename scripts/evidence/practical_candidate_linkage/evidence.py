"""Carry verified earlier evidence as references, never winner-chain confirmation."""
from .common import DISTINCT, LINKS, HISTORY, PROFILES, STAGE13, STAGE21, read


def preserved_claims():
    claims = []
    for row in read(DISTINCT)['records']:
        evidence = row.get('adjudication')
        if evidence is None:
            continue
        source, target = row['eventId'].split('->')
        if not evidence.get('distinctPersonEvidence'):
            raise ValueError('Inherited distinct claim lacks independent occurrence routes')
        claims.append({'sourceOccurrenceId': source, 'targetOccurrenceId': target,
                       'label': 'documentary_distinct_people',
                       'evidenceArtifact': DISTINCT, 'evidencePointer': row['eventId'],
                       'evidence': evidence,
                       'availability': 'retrospective_selected_Stage10_evidence; original_fact_publication_retrieval_dates_retained',
                       'limitation': 'not_new_adjudication; departure_and_incoming_career_not_established'})
    return claims


def inherited_audit(rows):
    links = {r['candidateOccurrenceId']: r for r in read(LINKS)['links']}
    histories = {r['candidateOccurrenceId']: r for r in read(HISTORY)['records']}
    audit = []
    for row in rows:
        cid = row['candidateOccurrenceId']
        link, history = links.get(cid), histories.get(cid)
        audit.append({'candidateOccurrenceId': cid,
                      'inheritedPersonId': link['personId'] if link else None,
                      'inheritedConfidence': link['status'] if link else 'unresolved',
                      'inheritedMethod': link['method'] if link else None,
                      'personExistenceEvidence': link.get('personExistenceStatus') if link else 'unknown',
                      'careerHistoryEvidence': history,
                      'interpretation': 'audit_only; none_of_these_labels_establish_documentary_relationship',
                      'profileHistoryArtifact': PROFILES,
                      'earlierRelationArtifacts': [STAGE13, STAGE21]})
    return audit
