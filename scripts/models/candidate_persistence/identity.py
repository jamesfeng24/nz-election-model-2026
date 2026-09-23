"""Auditable links from immutable candidate occurrences to people."""

from collections import Counter, defaultdict


STATUSES = frozenset({
    'continuing_incumbent', 'first_term_incumbent', 'returning_former_incumbent',
    'replacement_candidate', 'returning_challenger', 'genuinely_new_candidate',
    'list_only_history', 'unknown',
})


def _occurrence_index(occurrences):
    indexed = {}
    for row in occurrences:
        candidate_id = row['candidateOccurrenceId']
        if candidate_id in indexed:
            raise ValueError(f'Duplicate occurrence ID: {candidate_id}')
        if row.get('personId') is not None:
            raise ValueError(f'Source person ID must remain null: {candidate_id}')
        if type(row['year']) is not int or not row['sourceCandidateName'] or not row['electorateName']:
            raise ValueError(f'Invalid occurrence identity fields: {candidate_id}')
        if row['electorateType'] not in ('general', 'maori') or not row['candidateAffiliationKey']:
            raise ValueError(f'Invalid occurrence context: {candidate_id}')
        indexed[candidate_id] = row
    return indexed


def _official_index(official_members, occurrences):
    indexed = {}
    for record in official_members:
        candidate_id = record['candidateOccurrenceId']
        if candidate_id not in occurrences or candidate_id in indexed:
            raise ValueError(f'Unknown or duplicate official occurrence: {candidate_id}')
        person_id, source_url = record.get('personId'), record.get('sourceUrl')
        if (type(person_id) is not str or not person_id or type(source_url) is not str
                or not source_url.startswith(('https://', 'http://'))):
            raise ValueError(f'Official identity lacks person ID or source URL: {candidate_id}')
        if type(record.get('directOccurrenceEvidence')) is not bool:
            raise ValueError(f'Official occurrence lacks direct-evidence flag: {candidate_id}')
        source_name = record.get('sourceName')
        if source_name and source_name != occurrences[candidate_id]['sourceCandidateName'] and not record.get('aliasEvidence'):
            raise ValueError(f'Official name differs without alias evidence: {candidate_id}')
        status = record.get('status', 'unknown')
        if status not in STATUSES:
            raise ValueError(f'Unsupported candidate status: {status}')
        if status in ('first_term_incumbent', 'genuinely_new_candidate') and not record.get('priorServiceEvidence'):
            raise ValueError(f'Career-start status lacks prior-service evidence: {candidate_id}')
        if record.get('leadership') not in (None, True, False):
            raise ValueError(f'Invalid leadership evidence: {candidate_id}')
        indexed[candidate_id] = record
    by_person_year = defaultdict(list)
    for candidate_id, record in indexed.items():
        by_person_year[(record['personId'], occurrences[candidate_id]['year'])].append(candidate_id)
    duplicates = {key: ids for key, ids in by_person_year.items() if len(ids) > 1}
    if duplicates:
        raise ValueError(f'Official person has simultaneous occurrences: {duplicates}')
    return indexed


def _chain_key(row):
    return (row['sourceCandidateName'], row['candidateAffiliationKey'],
            row['electorateName'], row['electorateType'])


def _probable_chains(occurrences, official):
    by_name = defaultdict(list)
    by_chain = defaultdict(list)
    for row in occurrences.values():
        by_name[row['sourceCandidateName']].append(row)
        by_chain[_chain_key(row)].append(row)
    ambiguous_names = {
        name for name, rows in by_name.items()
        if len({row['year'] for row in rows}) != len(rows)
    }
    chains = {}
    for key, rows in by_chain.items():
        if len(rows) < 2 or key[0] in ambiguous_names:
            continue
        ids = sorted(row['candidateOccurrenceId'] for row in rows)
        confirmed_ids = {official[candidate_id]['personId'] for candidate_id in ids if candidate_id in official}
        if len(confirmed_ids) > 1:
            raise ValueError(f'Conflicting official people in exact-name chain: {ids}')
        person_id = next(iter(confirmed_ids)) if confirmed_ids else f'person:occurrence:{ids[0]}'
        chains[key] = (person_id, ids)
    return chains, ambiguous_names


def _evidence(row, method, official=None, chain_ids=None):
    evidence = {'sourceOccurrenceId': row['candidateOccurrenceId'],
                'sourceName': row['sourceCandidateName'],
                'sourceAffiliation': row['sourceAffiliation'],
                'sourceElectorate': row['electorateName'],
                'sourceIds': sorted(row.get('provenance', {}).get('sourceIds', []))}
    if official is not None:
        evidence['sourceUrl'] = official['sourceUrl']
        if official.get('sourceId'):
            evidence['sourceId'] = official['sourceId']
        if official.get('sourceName'):
            evidence['officialSourceName'] = official['sourceName']
        if official.get('aliasEvidence'):
            evidence['aliasEvidence'] = official['aliasEvidence']
        if official.get('winnerOccurrenceIds'):
            evidence['winnerOccurrenceIds'] = official['winnerOccurrenceIds']
        evidence['anchorOccurrences'] = official.get('anchorOccurrences', [])
        evidence['directOccurrenceEvidence'] = official['directOccurrenceEvidence']
        evidence['evidenceRetrievedAt'] = official.get('evidenceRetrievedAt')
        evidence['evidencePublishedAt'] = official.get('evidencePublishedAt')
        if official.get('serviceText'):
            evidence['serviceText'] = official['serviceText']
    else:
        evidence['corroboratingOccurrenceIds'] = [candidate_id for candidate_id in chain_ids
                                                 if candidate_id != row['candidateOccurrenceId']]
        evidence['anchorOccurrences'] = []
        evidence['evidenceRetrievedAt'] = None
        evidence['evidencePublishedAt'] = None
    return evidence


def _links(occurrences, official, chains, ambiguous_names):
    links, unresolved = [], []
    for candidate_id, row in sorted(occurrences.items()):
        if candidate_id in official:
            record = official[candidate_id]
            direct = record['directOccurrenceEvidence']
            links.append({'candidateOccurrenceId': candidate_id, 'personId': record['personId'],
                          'status': 'confirmed' if direct else 'probable',
                          'personExistenceStatus': 'official_profile_corroborated',
                          'method': 'official_profile_observed_winner' if direct else
                          'profile_anchored_exact_chain_projection',
                          'evidence': _evidence(row, 'official_profile', official=record)})
        elif _chain_key(row) in chains:
            person_id, chain_ids = chains[_chain_key(row)]
            links.append({'candidateOccurrenceId': candidate_id, 'personId': person_id,
                          'status': 'probable', 'method': 'exact_full_name_party_seat_chain',
                          'personExistenceStatus': 'unverified_chain',
                          'evidence': _evidence(row, 'exact_full_name_party_seat_chain', chain_ids=chain_ids)})
        else:
            reason = 'same_election_name_collision' if row['sourceCandidateName'] in ambiguous_names else 'insufficient_identity_evidence'
            unresolved.append({'candidateOccurrenceId': candidate_id, 'status': 'unresolved',
                               'reason': reason, 'sourceName': row['sourceCandidateName'],
                               'personExistenceStatus': 'unknown', 'anchorOccurrences': [],
                               'evidenceRetrievedAt': None, 'evidencePublishedAt': None})
    return links, unresolved


def _validate_links(links, occurrences):
    by_person_year = defaultdict(list)
    for link in links:
        candidate_id = link['candidateOccurrenceId']
        by_person_year[(link['personId'], occurrences[candidate_id]['year'])].append(candidate_id)
    duplicates = {key: ids for key, ids in by_person_year.items() if len(ids) > 1}
    if duplicates:
        raise ValueError(f'Person has simultaneous occurrences: {duplicates}')


def _persons(links, occurrences):
    grouped = defaultdict(list)
    for link in links:
        grouped[link['personId']].append(link)
    persons = []
    for person_id, linked in sorted(grouped.items()):
        ids = sorted(link['candidateOccurrenceId'] for link in linked)
        persons.append({'personId': person_id, 'candidateOccurrenceIds': ids,
                        'sourceNameAliases': sorted({occurrences[candidate_id]['sourceCandidateName'] for candidate_id in ids}),
                        'identityStatus': 'confirmed' if any(link['status'] == 'confirmed' for link in linked) else 'probable'})
    return persons


def _history(occurrences, links, official):
    by_person = defaultdict(list)
    for link in links:
        candidate_id = link['candidateOccurrenceId']
        by_person[link['personId']].append(occurrences[candidate_id])
    prior_by_id = {}
    for rows in by_person.values():
        rows.sort(key=lambda row: (row['year'], row['candidateOccurrenceId']))
        for index, row in enumerate(rows):
            prior_by_id[row['candidateOccurrenceId']] = [earlier['candidateOccurrenceId'] for earlier in rows[:index]]
    result = []
    for candidate_id, row in sorted(occurrences.items()):
        evidence = official.get(candidate_id, {})
        if evidence and not evidence['directOccurrenceEvidence']:
            evidence = {}
        status = evidence.get('status', 'unknown')
        prior_service = evidence.get('priorServiceEvidence')
        result.append({'candidateOccurrenceId': candidate_id, 'year': row['year'],
                       'status': status, 'priorLinkedOccurrenceIds': prior_by_id.get(candidate_id, []),
                       'priorParliamentaryTenure': evidence.get('priorParliamentaryTenure', 'unknown'),
                       'careerHistoryEvidenceStatus': 'documented_continuous_service' if prior_service else 'unknown',
                       'leftCensored': prior_service is None,
                       'leadership': evidence.get('leadership'),
                       'evidence': {'sourceUrl': evidence['sourceUrl'], 'priorServiceEvidence': prior_service}
                       if evidence else None})
    return result


def build_identity(occurrences: list[dict], official_members: list[dict] | None = None) -> dict:
    """Link corroborated occurrences and retain explicit identity/status uncertainty."""
    indexed = _occurrence_index(occurrences)
    official = _official_index(official_members or [], indexed)
    chains, ambiguous_names = _probable_chains(indexed, official)
    links, unresolved = _links(indexed, official, chains, ambiguous_names)
    _validate_links(links, indexed)
    persons = _persons(links, indexed)
    history = _history(indexed, links, official)
    counts = Counter(link['status'] for link in links)
    coverage = {'occurrenceCount': len(indexed), 'confirmedCount': counts['confirmed'],
                'probableCount': counts['probable'], 'unresolvedCount': len(unresolved),
                'personCount': len(persons),
                'unresolvedReasons': dict(sorted(Counter(item['reason'] for item in unresolved).items()))}
    return {'links': links, 'unresolved': unresolved, 'persons': persons,
            'historyStatus': history, 'coverage': coverage}
