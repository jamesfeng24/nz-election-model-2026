"""Outcome-free occurrence adapters, context checks and election-wide competitors."""
from collections import defaultdict
from itertools import product

from .common import unique
from .names import parse_name, name_match


def adapt_occurrences(records, ballot_groups=None):
    original_count = len(records)
    records = unique(records, 'candidateOccurrenceId')
    fields = ('candidateOccurrenceId', 'year', 'electorateId', 'electorateName',
              'electorateType', 'sourceCandidateName', 'sourceAffiliation',
              'candidateAffiliationKey', 'partyKey', 'candidateContestStatus')
    rows = []
    for cid, source in sorted(records.items()):
        row = {field: source[field] for field in fields}
        row['parsedName'] = parse_name(source['sourceCandidateName'])
        row['sharedBallotGroup'] = bool(ballot_groups is not None and cid in ballot_groups and ballot_groups[cid]['shared'])
        row['ballotGroupKey'] = (ballot_groups[cid]['partyKey'] if ballot_groups is not None and cid in ballot_groups
                                else source['partyKey'] if source['eligible'] else None)
        row['ballotGroupMapping'] = ('validated_Stage22_election_local_mapping' if ballot_groups is not None and cid in ballot_groups
                                     else 'Stage7_exact_within_election_mapping' if source['eligible'] else
                                     'no_exact_party_group_mapping')
        row['officialSourceIds'] = sorted(set(source['provenance']['sourceIds']))
        row['occurrenceEvidence'] = 'official_election_local_candidature_only'
        row['historicalFactYear'] = row['year']
        row['publicationByForecastCutoff'] = 'unknown'
        rows.append(row)
    return rows, original_count - len(rows)


def continuity_index(records):
    result = {}
    for row in records:
        if row.get('target'):
            key = row['sourceYear'], row['targetYear'], row['target']['sourceKey']
            if key in result:
                raise ValueError('Ambiguous party continuity')
            result[key] = row
    return result


def party_context(source, target, continuity):
    if source.get('sharedBallotGroup') or target.get('sharedBallotGroup'):
        return False, 'shared_group_not_constituent_continuity'
    if source['candidateAffiliationKey'] == target['candidateAffiliationKey'] == 'independent' and source['ballotGroupKey'] is None and target['ballotGroupKey'] is None:
        return True, 'independent_no_party_context'
    relation = continuity.get((source['year'], target['year'], target['ballotGroupKey']))
    if not relation or relation['status'] != 'eligible' or not relation['source']:
        return False, 'party_change_or_unknown_continuity'
    if relation['source']['sourceKey'] != source['ballotGroupKey']:
        return False, 'party_change_or_unknown_continuity'
    return True, ('documented_party_continuity_same_original_affiliation'
                  if source['candidateAffiliationKey'] == target['candidateAffiliationKey']
                  else 'documented_single_party_label_continuity')


def election_competitors(rows, aliases):
    """Ignore party and geographic filters when finding name competitors."""
    years = defaultdict(list)
    for row in rows:
        years[row['year']].append(row)
    result = {}
    for row in rows:
        matches = {}
        for year, others in sorted(years.items()):
            matches[year] = [other['candidateOccurrenceId'] for other in others
                if name_match(row['parsedName'], other['parsedName'], aliases)['compatible']]
        result[row['candidateOccurrenceId']] = matches
    return result


def inherited_leads(links):
    groups = defaultdict(list)
    for link in links:
        groups[link['personId']].append(link['candidateOccurrenceId'])
    return groups


def generate(rows, geography, continuity_rows, links, claims, aliases):
    indexed = unique(rows, 'candidateOccurrenceId')
    by_year, by_seat = defaultdict(list), defaultdict(list)
    for row in rows:
        by_year[row['year']].append(row)
        by_seat[row['electorateId']].append(row)
    transitions = sorted({(r['sourceYear'], r['targetYear']) for r in geography})
    exact = {(r['dominantPredecessorId'], r['targetElectorateId']): r for r in geography
             if r['certifiedTwoSidedExact']}
    candidates = defaultdict(set)
    for (source_id, target_id), geo in exact.items():
        for source, target in product(by_seat[source_id], by_seat[target_id]):
            sn, tn = source['parsedName'], target['parsedName']
            if (source['candidateAffiliationKey'] == target['candidateAffiliationKey'] or
                (sn['status'] == tn['status'] == 'parsed' and sn['surname'] == tn['surname'])):
                candidates[source['candidateOccurrenceId'], target['candidateOccurrenceId']].add('exact_seat_context_question')
    competitors = election_competitors(rows, aliases)
    for source in rows:
        for sy, ty in transitions:
            if sy != source['year']:
                continue
            for target_id in competitors[source['candidateOccurrenceId']].get(ty, []):
                candidates[source['candidateOccurrenceId'], target_id].add('electionwide_name_lead')
    for ids in inherited_leads(links).values():
        for sid, tid in product(ids, ids):
            if sid in indexed and tid in indexed and (indexed[sid]['year'], indexed[tid]['year']) in transitions:
                candidates[sid, tid].add('inherited_person_ID_lead_not_proof')
    for claim in claims:
        if claim['sourceOccurrenceId'] in indexed and claim['targetOccurrenceId'] in indexed:
            candidates[claim['sourceOccurrenceId'], claim['targetOccurrenceId']].add('preserved_explicit_claim')
    continuity = continuity_index(continuity_rows)
    by_claim = {(c['sourceOccurrenceId'], c['targetOccurrenceId']): c for c in claims}
    edges = []
    for (sid, tid), routes in sorted(candidates.items()):
        source, target = indexed[sid], indexed[tid]
        geo = exact.get((source['electorateId'], target['electorateId']))
        names = name_match(source['parsedName'], target['parsedName'], aliases)
        context, context_reason = party_context(source, target, continuity)
        competing = sorted(set(competitors[sid].get(target['year'], [])) - {tid} |
                           (set(competitors[tid].get(source['year'], [])) - {sid}) |
                           (set(competitors[sid].get(source['year'], [])) - {sid}) |
                           (set(competitors[tid].get(target['year'], [])) - {tid}))
        claim = by_claim.get((sid, tid))
        reason = (names['reason'] if not names['compatible'] else
                  'competing_matches' if competing else
                  context_reason if not context else
                  'seat_change_or_nonexact_geography' if geo is None else
                  'cancelled_or_missing_contest' if any(r['candidateContestStatus'] != 'held' for r in (source, target)) else None)
        label = 'unresolved_ambiguous' if reason else 'accepted_algorithmic_same_person'
        if claim:
            label = claim['label']
            reason = None if label == 'documentary_same_person' else 'preserved_distinct_person_evidence'
        edge = {'edgeId': sid+'->'+tid, 'sourceOccurrenceId': sid, 'targetOccurrenceId': tid,
                'sourceYear': source['year'], 'targetYear': target['year'],
                'scope': source['electorateType'] if source['electorateType'] == target['electorateType'] else 'scope_change',
                'sourceOriginalName': source['sourceCandidateName'], 'targetOriginalName': target['sourceCandidateName'],
                'sourceOriginalAffiliation': source['sourceAffiliation'], 'targetOriginalAffiliation': target['sourceAffiliation'],
                'sourcePartyBallotGroup': source['ballotGroupKey'], 'targetPartyBallotGroup': target['ballotGroupKey'],
                'sourceElectorateId': source['electorateId'], 'targetElectorateId': target['electorateId'],
                'primaryGeographyId': geo['geographyId'] if geo else None,
                'primaryExactHeld': geo is not None and all(r['candidateContestStatus'] == 'held' for r in (source,target)),
                'proposalRoutes': sorted(routes), 'nameAssessment': names,
                'contextAssessment': context_reason, 'competingOccurrenceIds': competing,
                'ruleFlags': names['flags'], 'label': label, 'ambiguityType': reason,
                'relationshipEvidence': [claim] if claim else [],
                'officialSourceIds': sorted(set(source['officialSourceIds']+target['officialSourceIds'])),
                'historicalFactYears': [source['year'],target['year']],
                'publicationByForecastCutoff': 'unknown', 'adjudicationTiming': 'retrospective_stage26',
                'careerCompleteness': 'not_established_by_linkage', 'reversible': True}
        edges.append(edge)
    return edges
