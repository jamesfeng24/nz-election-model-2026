"""Validate occurrence-specific Stage 10 identity adjudications and source timing."""

from html.parser import HTMLParser

from scripts.models.freshman_incumbency.inventory import _source_date
from scripts.transform.historical import key


def verify_identity_snapshot(registry, snapshot):
    """Pin only consumed identity records; tolerate unrelated registry additions."""
    live = registry['sources']
    ids = [row['id'] for row in live]
    if len(ids) != len(set(ids)):
        raise ValueError('Ambiguous source ID in registry')
    by_id = {row['id']: row for row in live}
    required = snapshot['sources']
    if len(required) != len({row['id'] for row in required}):
        raise ValueError('Duplicate required identity source ID')
    for record in required:
        expected = {key: value for key, value in record.items() if key != 'publishedDate'}
        if by_id.get(record['id']) != expected:
            raise ValueError('Changed or deleted required identity source record')


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        if value.strip():
            self.parts.append(value.strip())


def _contains(root, record, phrase):
    parser = _VisibleText()
    parser.feed((root / record['rawPath']).read_text(errors='replace'))
    return phrase.casefold() in ' '.join(parser.parts).casefold()


def validate_adjudications(root, plan, adjudications, occurrences, source_records,
                          tenure_sources, profiles, links):
    """Reject unsupported routes, dangling occurrences and evidence after target day."""
    planned = {row['eventId']: row for row in plan['records']}
    by_occurrence = {row['candidateOccurrenceId']: row for row in occurrences}
    by_link = {row['candidateOccurrenceId']: row for row in links}
    by_source = {row['id']: row for row in (*source_records, *tenure_sources)}
    by_profile = {row['sourceId']: row for row in profiles}
    result = {}
    for row in adjudications['records']:
        event_id = row['eventId']
        if event_id in result or event_id not in planned or not planned[event_id]['externalPriority']:
            raise ValueError('Duplicate or undeclared Stage 10 identity adjudication')
        source_id, target_id = event_id.split('->')
        if source_id not in by_occurrence or target_id not in by_occurrence:
            raise ValueError('Dangling Stage 10 identity occurrence')
        source, target = by_occurrence[source_id], by_occurrence[target_id]
        if (source['year'] != row['sourceYear'] or target['year'] != row['targetYear'] or
                source['electorateName'] != row['electorateName'] or
                target['electorateName'] != row['electorateName']):
            raise ValueError('Stage 10 evidence attached to wrong occurrence')
        target_date = _source_date(target['year'])
        if not (row['sourceFactDate'] <= _source_date(source['year']) and
                row['targetFactDate'] < target_date):
            raise ValueError('Identity route uses a target/later historical fact')
        if row['targetOutcomeDependent']:
            raise ValueError('Outcome-dependent evidence cannot be accepted')
        if row['role'] == 'primary':
            surname, given = target['sourceCandidateName'].split(',', 1)
            proof_tokens = row['targetNameProof'].split()
            if key(proof_tokens[-1]) != key(surname) or key(proof_tokens[0]) not in key(given):
                raise ValueError('Primary target proof lacks an occurrence-specific name join')
        for prefix in ('source', 'target'):
            evidence_id = row[prefix + 'EvidenceId']
            link = by_link.get(source_id if prefix == 'source' else target_id)
            if evidence_id.startswith('parliament:'):
                if (link is None or link.get('personId') != evidence_id or
                        link.get('status') != 'confirmed' or
                        not any(anchor['candidateOccurrenceId'] ==
                                (source_id if prefix == 'source' else target_id)
                                for anchor in link['evidence']['anchorOccurrences'])):
                    raise ValueError('Missing direct inherited occurrence anchor')
                continue
            record = by_source.get(evidence_id)
            if record is None:
                raise ValueError('Unregistered Stage 10 identity evidence')
            if row[prefix + 'RetrievalAt'] != record['retrievedAt']:
                raise ValueError('Changed Stage 10 evidence retrieval date')
            published = (by_profile[evidence_id]['publishedDate'] if evidence_id in by_profile
                         else record.get('publishedDate'))
            if row[prefix + 'PublicationDate'] != published:
                raise ValueError('Changed Stage 10 evidence publication date')
            if evidence_id in by_profile:
                profile = by_profile[evidence_id]
                if not any(service['serviceKind'] == 'electorate' and
                           key(service['electorateName']) == key(row['electorateName']) and
                           service['startDate'] <= row[prefix + 'FactDate'] and
                           (service['endDate'] is None or service['endDate'] >= row[prefix + 'FactDate'])
                           for service in profile['serviceRows']):
                    raise ValueError('No dated electorate service for identity route')
            elif not _contains(root, record, row[prefix + 'NameProof']):
                raise ValueError('Name proof absent from registered source')
            if evidence_id not in by_profile and row['electorateName'].casefold() not in (
                    root / record['rawPath']).read_text(errors='replace').casefold():
                raise ValueError('Electorate absent from identity evidence')
            if prefix == 'target' and row['targetRoute'].startswith('pre_result_party'):
                if published is None or not (row['targetFactDate'] <= published < target_date):
                    raise ValueError('Party candidate statement was not pre-result')
        if row['sourceNameProof'] == row['targetNameProof']:
            raise ValueError('Distinct people not corroborated')
        if row['role'] not in ('primary', 'by_election_successor', 'retrospective_alias'):
            raise ValueError('Unknown Stage 10 replacement role')
        if row['role'] == 'primary' and row['targetOccurrenceConfidence'] != 'confirmed':
            raise ValueError('Primary replacement requires occurrence corroboration')
        alias_id = row.get('aliasEvidenceId')
        if alias_id:
            alias_record = by_source.get(alias_id)
            if (row['role'] != 'retrospective_alias' or alias_record is None or
                    len(row.get('aliasNames', [])) != 2 or
                    not all(name.casefold() in (root / alias_record['rawPath']).read_text(
                        errors='replace').casefold()
                            for name in row['aliasNames'])):
                raise ValueError('Unsupported retrospective alias bridge')
        if row.get('laterOutcomeCoverageDependent') and row['role'] == 'primary':
            raise ValueError('Later-success-covered alias entered primary cohort')
        result[event_id] = row
    return result


def build_person_links(adjudications, inherited_links, occurrences):
    """Extend occurrence links without rewriting the frozen Stage 8 person layer."""
    inherited = {row['candidateOccurrenceId']: row for row in inherited_links}
    valid_ids = {row['candidateOccurrenceId'] for row in occurrences}
    links = {}
    for event_id, evidence in sorted(adjudications.items()):
        source_id, target_id = event_id.split('->')
        for prefix, occurrence_id in (('source', source_id), ('target', target_id)):
            if occurrence_id not in valid_ids:
                raise ValueError('Dangling Stage 10 occurrence link')
            inherited_link = inherited.get(occurrence_id)
            person_id = (inherited_link['personId'] if inherited_link and
                         inherited_link['personId'] else
                         f'person:stage10:occurrence:{occurrence_id}')
            proposed = {
                'candidateOccurrenceId': occurrence_id, 'personId': person_id,
                'occurrenceConfidence': evidence[prefix + 'OccurrenceConfidence'],
                'personExistenceStatus': 'independently_corroborated',
                'method': evidence[prefix + 'Route'],
                'sourceId': evidence[prefix + 'EvidenceId'],
                'historicalFactDate': evidence[prefix + 'FactDate'],
                'publicationDate': evidence[prefix + 'PublicationDate'],
                'retrievalAt': evidence[prefix + 'RetrievalAt'],
                'adjudicationRole': evidence['role'],
                'careerHistoryStatus': 'separate_dated_tenure_overlay_or_unknown',
            }
            if occurrence_id in links and links[occurrence_id] != proposed:
                raise ValueError('Conflicting Stage 10 occurrence links')
            links[occurrence_id] = proposed
        if links[source_id]['personId'] == links[target_id]['personId']:
            raise ValueError('Distinct-person adjudication resolves to same person ID')
    return {'schemaVersion': 1, 'links': [links[key] for key in sorted(links)]}
