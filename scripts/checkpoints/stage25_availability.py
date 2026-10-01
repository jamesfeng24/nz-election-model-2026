"""Outcome-blind evidence availability linked to Stage 25 geography."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.checkpoints.complete_share_features import coupled_cell_percent, source_rows
from scripts.checkpoints.stage25_geography import ROOT, DEST, read, encode, write_or_check


GEOGRAPHY = 'data/processed/checkpoints/stage25-historical-geography/geography.json'
MAPPING = 'data/processed/checkpoints/stage22-shared-group-prefit/amended-mapping.json'
CONTINUITY = 'data/processed/models/party-vote-transform/party-continuity.json'
LINKS = 'data/processed/models/candidate-persistence/person-links.json'
ELECTIONS = {year: f'data/processed/elections/{year}.json' for year in (2008, 2011, 2014, 2017, 2020, 2023)}
SPLITS = {year: f'data/processed/split-votes/{year}.json' for year in ELECTIONS}
INPUTS = (GEOGRAPHY, MAPPING, CONTINUITY, LINKS, *ELECTIONS.values(), *SPLITS.values())


def index(rows, field):
    result = {row[field]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f'Duplicate {field}')
    return result


def source_contract(elections, splits):
    ids = set()
    for year, document in elections.items():
        ids.update(document['sourceIds'])
        for matrix in splits[year]['matrices']:
            ids.update(matrix['sourceIds'])
    registered = index(read('data/sources.json')['sources'], 'id')
    records = []
    for source_id in sorted(ids):
        source = registered.get(source_id)
        if source is None:
            raise ValueError(f'Missing required source {source_id}')
        path = ROOT / source['rawPath']
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError(f'Changed required raw source {source_id}')
        records.append(source)
    return {'schemaVersion': 1, 'stage': 25, 'requiredSources': records,
            'contract': 'required_registry_records_and_raw_bytes_only; unrelated additions allowed'}


def verify_contract(saved):
    registered = index(read('data/sources.json')['sources'], 'id')
    for source in saved['requiredSources']:
        if registered.get(source['id']) != source:
            raise ValueError(f'Changed or deleted required source record {source["id"]}')
        path = ROOT / source['rawPath']
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError(f'Changed required raw source {source["id"]}')


def mapped_contests(mapping):
    rows = list(mapping['trainingGeneralContests'])
    rows.extend(row for row in mapping['frame'] if row['scope'] == 'general')
    unique = {}
    for row in rows:
        seat_id = row.get('electorateId', row.get('targetElectorateId'))
        lookup = row.get('year', row.get('targetYear')), seat_id
        if lookup in unique and unique[lookup] != row:
            # A frame record and a training record can describe the same seat.
            if unique[lookup]['status'] != row['status'] or unique[lookup]['candidates'] != row['candidates']:
                raise ValueError('Conflicting election-local candidate mapping')
        else:
            unique[lookup] = row
    return unique


def target_candidates(mapping, target_seat):
    if mapping is None or mapping['status'] != 'complete' or target_seat is None:
        return None, 'missing_or_incomplete_target_candidate_mapping'
    observed_ids = {candidate['id'] for candidate in target_seat['candidates']}
    classified = mapping['candidates']
    if {candidate['candidateOccurrenceId'] for candidate in classified} != observed_ids:
        return None, 'mapped_slate_disagrees_with_official_candidacy'
    if not classified:
        return None, 'no_standing_candidates'
    party_keys = {party['partyKey'] for party in target_seat['parties']}
    used = set()
    for candidate in classified:
        party = candidate['partyKey']
        if candidate['noRegisteredPartyGroup']:
            if party is not None:
                return None, 'contradictory_no_party_group_mapping'
        elif party not in party_keys or party in used:
            return None, 'missing_or_duplicate_target_party_group'
        else:
            used.add(party)
    return classified, None


def source_feature(candidate, source_seat, matrix, continuity, source_year, target_year):
    """Inspect permitted source facts only; never read a target result or identity label."""
    if candidate['noRegisteredPartyGroup']:
        return {'sStatus': 'neutral_fallback_no_party_group', 'vStatus': 'neutral_fallback_no_party_group'}
    relation = continuity.get((source_year, target_year, candidate['partyKey']))
    if relation is None:
        return {'sStatus': 'unresolved_party_continuity', 'vStatus': 'unresolved_party_continuity'}
    if relation['status'] == 'entrant':
        return {'sStatus': 'neutral_fallback_documented_entrant', 'vStatus': 'neutral_fallback_documented_entrant'}
    if relation['status'] != 'eligible' or not relation['source']:
        return {'sStatus': 'unresolved_party_continuity', 'vStatus': 'unresolved_party_continuity'}
    party_key = relation['source']['sourceKey']
    source_parties = index(source_seat['parties'], 'partyKey')
    if party_key not in source_parties:
        return {'sStatus': 'missing_source_party_row', 'vStatus': 'missing_source_party_row'}
    prior = [person for person in source_seat['candidates'] if person['partyKey'] == party_key]
    if len(prior) != 1:
        reason = 'missing_source_destination' if not prior else 'ambiguous_source_destination'
        return {'sStatus': reason, 'vStatus': reason}
    if not source_seat['validCandidateVotes'] or not source_seat['validPartyVotes']:
        return {'sStatus': 'missing_source_denominator', 'vStatus': 'missing_source_denominator'}
    result = {'sStatus': 'missing_source_split_table', 'vStatus': 'supported_source_gap',
              'sourceCandidateId': prior[0]['id'], 'sourcePartyKey': party_key,
              'sourceCandidateShare': prior[0]['votes'] / source_seat['validCandidateVotes'],
              'sourcePartyShare': source_parties[party_key]['votes'] / source_seat['validPartyVotes']}
    result['v0'] = result['sourceCandidateShare'] - result['sourcePartyShare']
    if matrix is None:
        return result
    try:
        rows = source_rows(matrix, source_seat)
        party_row = rows[party_key]
        if party_row['totalPartyVotes'] == 0:
            result['sStatus'] = 'zero_mass_source_row'
        else:
            printed, lower, upper = coupled_cell_percent(party_row, prior[0]['id'])
            result['sStatus'] = 'supported_rounded_source_split'
            result['s0Printed'] = printed / 100
            result['s0CoupledLower'] = str(lower / 100)
            result['s0CoupledUpper'] = str(upper / 100)
            result['sourcePartyRowMass'] = party_row['totalPartyVotes']
    except (ValueError, KeyError):
        result['sStatus'] = 'incomplete_or_ambiguous_source_split'
    return result


def build(geography=None, mapping=None, elections=None, splits=None, continuity_rows=None, links=None):
    geography = geography or read(GEOGRAPHY)
    mapping = mapping or read(MAPPING)
    elections = elections or {year: read(path) for year, path in ELECTIONS.items()}
    splits = splits or {year: read(path) for year, path in SPLITS.items()}
    continuity_rows = continuity_rows or read(CONTINUITY)['records']
    links = links or read(LINKS)['links']
    seats = {year: index(elections[year]['electorates'], 'id') for year in ELECTIONS}
    matrices = {year: index(splits[year]['matrices'], 'electorateId') for year in SPLITS}
    mapped = mapped_contests(mapping)
    continuity = {}
    for relation in continuity_rows:
        target = relation.get('target')
        if target:
            lookup = (relation['sourceYear'], relation['targetYear'], target['sourceKey'])
            if lookup in continuity:
                raise ValueError('Ambiguous target party continuity')
            continuity[lookup] = relation
    identity = index(links, 'candidateOccurrenceId')
    records = []
    for geo in geography['records']:
        target_year, target_id = geo['targetYear'], geo['targetElectorateId']
        source_year, source_id = geo['sourceYear'], geo['dominantPredecessorId']
        scope = geo['scope']
        row = {'geographyId': geo['geographyId'], 'sourceYear': source_year,
               'targetYear': target_year, 'scope': scope,
               'sourceElectorateId': source_id, 'targetElectorateId': target_id,
               'originalFrame': geo['originalFrame'],
               'geographyTier': geo['exclusiveTier'],
               'primaryExactGeography': geo['certifiedTwoSidedExact'],
               'candidateMappingStatus': 'not_a_general_candidate_mapping',
               'candidateOccurrenceIds': [], 'candidateFeatures': [],
               'natLab': [], 'completeShare': {'status': 'coverage_only_maori'},
               'sOnly': {'status': 'coverage_only_maori'},
               'partyVector': {'status': 'coverage_only_maori'},
               'splitTicket': {'status': 'coverage_only_maori'},
               'identityEvidence': {'sourceOccurrenceConfidence': {'confirmed': 0, 'probable': 0, 'unresolved': 0},
                                    'targetOccurrenceConfidence': {'confirmed': 0, 'probable': 0, 'unresolved': 0},
                                    'crossElectionRelation': 'not_adjudicated_here',
                                    'careerHistoryCompleteness': 'not_assessed_here'},
               'approximateTransportInventory': None,
               'identityDependentStudies': 'evidence_audit_only_no_inferred_new_relation'}
        if scope != 'general':
            records.append(row)
            continue
        target = seats[target_year].get(target_id)
        source = seats[source_year].get(source_id) if source_id else None
        mapped_target = mapped.get((target_year, target_id))
        classified, reason = target_candidates(mapped_target, target)
        row['candidateMappingStatus'] = reason or 'complete'
        if target:
            row['candidateOccurrenceIds'] = [candidate['id'] for candidate in target['candidates']]
        if source:
            for candidate in source['candidates']:
                confidence = identity.get(candidate['id'], {}).get('status', 'unresolved')
                row['identityEvidence']['sourceOccurrenceConfidence'][confidence] += 1
        if not geo['certifiedTwoSidedExact']:
            row['approximateTransportInventory'] = {
                'targetOverlap95': geo['targetOverlap95'], 'targetOverlap90': geo['targetOverlap90'],
                'twoSided95': geo['twoSided95'], 'twoSided90': geo['twoSided90'],
                'dominantSourceTablePresent': source is not None,
                'targetPartyTablePresent': target is not None,
                'targetCandidateMappingComplete': classified is not None,
                'sourceSplitTablePresent': source_id in matrices[source_year],
                'targetSplitTablePresent': target_id in matrices[target_year],
                'candidateVotesTransported': False,
                'status': 'inventory_only_requires_separate_approximate_rule'}
        for candidate_id in row['candidateOccurrenceIds']:
            confidence = identity.get(candidate_id, {}).get('status', 'unresolved')
            row['identityEvidence']['targetOccurrenceConfidence'][confidence] += 1
        if not geo['certifiedTwoSidedExact']:
            reason = 'not_certified_two_sided_exact'
        elif source is None or target is None:
            reason = 'missing_source_or_target_party_seat_table'
        elif classified is None:
            reason = reason
        else:
            reason = None
        if reason:
            row['completeShare'] = {'status': 'abstain', 'reason': reason}
            row['sOnly'] = {'status': 'abstain', 'reason': reason}
            row['partyVector'] = {'status': 'abstain', 'reason': reason}
            row['splitTicket'] = {'status': 'abstain', 'reason': reason}
            for party in ('nationalparty', 'labourparty'):
                row['natLab'].append({'partyKey': party, 'status': 'abstain', 'reason': reason})
            records.append(row)
            continue
        row['completeShare'] = {'status': 'available', 'candidateCount': len(classified),
                                'noPartyGroupCandidates': sum(c['noRegisteredPartyGroup'] for c in classified)}
        category_relations = []
        source_party_keys = {party['partyKey'] for party in source['parties']}
        for party in target['parties']:
            relation = continuity.get((source_year, target_year, party['partyKey']))
            status = relation['status'] if relation else 'missing_relation'
            if status == 'eligible' and relation['source']['sourceKey'] not in source_party_keys:
                status = 'missing_source_category'
            category_relations.append({'targetPartyKey': party['partyKey'],
                                       'relationship': status,
                                       'sourcePartyKey': relation['source']['sourceKey'] if relation and relation['source'] else None})
        categories_supported = all(r['relationship'] in ('eligible', 'entrant') for r in category_relations)
        national_present = bool(elections[target_year]['nationalControls']['parties'])
        row['partyVector'] = {'status': ('source_and_target_party_categories_present'
                                         if categories_supported and national_present else 'ambiguous_or_missing_category_relation'),
                              'sourceCategoryCount': len(source['parties']),
                              'targetCategoryCount': len(target['parties']),
                              'targetCategoryRelationships': category_relations,
                              'nationalScenarioPresent': national_present,
                              'constructionDeferred': True}
        source_matrix = matrices[source_year].get(source_id)
        target_matrix = matrices[target_year].get(target_id)
        row['splitTicket'] = {'status': ('source_and_target_tables_present' if source_matrix and target_matrix
                                         else 'missing_source_or_target_matrix'),
                              'sourceMatrixId': source_matrix['id'] if source_matrix else None,
                              'targetMatrixId': target_matrix['id'] if target_matrix else None,
                              'outcome': 'matched_party_ballot_component_not_complete_candidate_share'}
        for candidate in classified:
            feature = source_feature(candidate, source, source_matrix, continuity, source_year, target_year)
            row['candidateFeatures'].append({'targetOccurrenceId': candidate['candidateOccurrenceId'],
                'targetPartyGroup': candidate['partyKey'], 'mappingStatus': candidate['mappingStatus'],
                **feature})
        fatal = {'unresolved_party_continuity', 'missing_source_party_row',
                 'ambiguous_source_destination', 'missing_source_denominator',
                 'missing_source_split_table', 'incomplete_or_ambiguous_source_split'}
        blocked = sorted({feature['sStatus'] for feature in row['candidateFeatures']
                          if feature['sStatus'] in fatal})
        row['sOnly'] = {'status': 'abstain' if blocked else 'available',
                        'reasons': blocked,
                        'supportedCandidates': sum(f['sStatus'] == 'supported_rounded_source_split'
                                                   for f in row['candidateFeatures']),
                        'neutralFallbackCandidates': sum(f['sStatus'].startswith('neutral_fallback') or
                                                         f['sStatus'] in ('missing_source_destination',
                                                                          'zero_mass_source_row')
                                                         for f in row['candidateFeatures'])}
        row['splitTicket']['supportedMatchedCategories'] = sum(
            f['sStatus'] == 'supported_rounded_source_split' for f in row['candidateFeatures'])
        row['splitTicket']['interpretation'] = (
            'category_support_inventory_not_a_complete_candidate_vote_view')
        for party in ('nationalparty', 'labourparty'):
            previous = [c for c in source['candidates'] if c['partyKey'] == party]
            current = [c for c in classified if c['partyKey'] == party]
            relation = continuity.get((source_year, target_year, party))
            eligible = len(previous) == 1 and len(current) == 1 and relation is not None and relation['status'] == 'eligible'
            row['natLab'].append({'partyKey': party, 'status': 'available' if eligible else 'abstain',
                'recordId': f'{geo["geographyId"]}:{party}',
                'sourceVictory': source['winnerCandidateId'] == previous[0]['id'] if len(previous) == 1 else None,
                'reason': None if eligible else 'missing_unique_party_candidate_or_continuity'})
        records.append(row)
    if len(records) != len(geography['records']):
        raise ValueError('Availability incomplete')
    summary = []
    for year in sorted({row['targetYear'] for row in records}):
        group = [row for row in records if row['targetYear'] == year]
        summary.append({'targetYear': year, 'targets': len(group),
                        'strictExactGeneral': sum(r['primaryExactGeography'] and r['scope'] == 'general' for r in group),
                        'completeShareAvailable': sum(r['completeShare']['status'] == 'available' for r in group),
                        'sOnlyAvailable': sum(r['sOnly']['status'] == 'available' for r in group),
                        'partyVectorInputsPresent': sum(r['partyVector']['status'] == 'source_and_target_party_categories_present' for r in group),
                        'sourceSplitTablesPresent': sum(r['splitTicket']['status'] == 'source_and_target_tables_present' for r in group),
                        'natLabPairs': sum(p['status'] == 'available' for r in group for p in r['natLab']),
                        'supportedS': sum(f['sStatus'] == 'supported_rounded_source_split' for r in group for f in r['candidateFeatures']),
                        'supportedV': sum(f['vStatus'] == 'supported_source_gap' for r in group for f in r['candidateFeatures'])})
    return {'schemaVersion': 1, 'stage': 25, 'role': 'outcome_blind_linked_availability',
            'records': records, 'summary': summary}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    elections = {year: read(path) for year, path in ELECTIONS.items()}
    splits = {year: read(path) for year, path in SPLITS.items()}
    contract = source_contract(elections, splits)
    if args.check:
        saved = read('data/processed/checkpoints/stage25-historical-geography/source-contract.json')
        if saved != contract:
            raise ValueError('Changed required Stage25 source contract')
        verify_contract(saved)
    else:
        write_or_check('source-contract.json', contract, False)
    output = build(elections=elections, splits=splits)
    write_or_check('availability.json', output, args.check)
    manifest = {'schemaVersion': 1, 'stage': 25,
                'inputSha256': {path: sha256((ROOT / path).read_bytes()).hexdigest() for path in INPUTS},
                'outputSha256': sha256(encode(output)).hexdigest(),
                'sourceContractSha256': sha256(encode(contract)).hexdigest()}
    write_or_check('availability-manifest.json', manifest, args.check)
    print(json.dumps(output['summary']))


if __name__ == '__main__':
    main()
