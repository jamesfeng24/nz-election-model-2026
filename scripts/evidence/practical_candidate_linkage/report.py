"""Coverage and readiness after acceptance; no effect estimation or model scores."""
from collections import Counter, defaultdict

from .components import SAME
from .names import strict_member, parse_name


def count_labels(edges):
    return dict(sorted(Counter(e['label'] for e in edges).items()))


def coverage(rows, edges, geography, groups, review, winners):
    by_seat = defaultdict(list)
    for row in rows:
        by_seat[row['electorateId']].append(row['candidateOccurrenceId'])
    frame = []
    for geo in geography:
        source_ids = [p['sourceElectorateId'] for p in geo['predecessors']]
        ids = set(by_seat[geo['targetElectorateId']]) | {cid for sid in source_ids for cid in by_seat[sid]}
        frame.append({'geographyId': geo['geographyId'], 'scope': geo['scope'],
                      'certifiedTwoSidedExact': geo['certifiedTwoSidedExact'],
                      'sourceElectorateIds': source_ids, 'targetElectorateId': geo['targetElectorateId'],
                      'candidateOccurrenceIds': sorted(ids),
                      'contestStatus': geo['contestStatus'],
                      'reason': None if geo['certifiedTwoSidedExact'] else 'nonexact_geography_no_primary_transport'})
    strata = []
    for sy, ty in sorted({(r['sourceYear'],r['targetYear']) for r in geography}):
        for scope in ('general','maori','scope_change'):
            selected = [e for e in edges if (e['sourceYear'],e['targetYear'],e['scope']) == (sy,ty,scope)]
            geo_rows = [g for g in geography if (g['sourceYear'],g['targetYear'],g['scope']) == (sy,ty,scope)]
            considered = set(cid for g in geo_rows if g['certifiedTwoSidedExact']
                             for sid in (g['dominantPredecessorId'],g['targetElectorateId']) for cid in by_seat[sid])
            accepted = [e for e in selected if e['label'] in SAME]
            primary = [e for e in accepted if e['primaryExactHeld']]
            strata.append({'transition': f'{sy}-{ty}', 'scope': scope,
                           'exactFrameOccurrencesConsidered': len(considered),
                           'proposedEdges': len(selected), 'labels': count_labels(selected),
                           'primaryBroadEdges': len(primary),
                           'primaryStrictEdges': sum(strict_member(e) for e in primary),
                           'primaryBroadLinkedOccurrences': len({cid for e in primary for cid in
                                (e['sourceOccurrenceId'],e['targetOccurrenceId'])}),
                           'ruleFlagCounts': dict(sorted(Counter(flag for e in accepted for flag in e['ruleFlags']).items())),
                           'competingEdges': sum(bool(e['competingOccurrenceIds']) for e in selected),
                           'componentConflictEdges': sum(e['ambiguityType']=='component_conflict' for e in selected)})
    party_groups, outcomes = defaultdict(list), defaultdict(list)
    indexed = {r['candidateOccurrenceId']:r for r in rows}
    for edge in edges:
        source, target = edge['sourceOccurrenceId'],edge['targetOccurrenceId']
        transition = f'{edge["sourceYear"]}-{edge["targetYear"]}'
        party_groups[transition,indexed[target]['candidateAffiliationKey']].append(edge)
        if edge['primaryExactHeld']:
            for role, cid in (('source',source),('target',target)):
                outcomes[transition,edge['scope'],role,str(winners.get(cid))].append(edge)
    occurrence_outcomes = outcome_occurrence_coverage(rows, edges, geography, winners)
    return {'byExactFrameOccurrenceOutcome': occurrence_outcomes, 'universeOccurrences':len(rows), 'frame':frame, 'byTransitionScope':strata,
            'overallLabels':count_labels(edges),
            'broadAcceptedEdges':sum(e['label'] in SAME for e in edges),
            'strictAcceptedEdges':sum(strict_member(e) for e in edges),
            'broadLinkedOccurrences':len({cid for e in edges if e['label'] in SAME for cid in
                (e['sourceOccurrenceId'],e['targetOccurrenceId'])}),
            'strictLinkedOccurrences':len({cid for e in edges if strict_member(e) for cid in
                (e['sourceOccurrenceId'],e['targetOccurrenceId'])}),
            'provisionalBroadGroups':len(groups['broad']), 'provisionalStrictGroups':len(groups['strict']),
            'exceptions':dict(sorted(Counter(r['reviewState'] for r in review).items())),
            'byTransitionAffiliation':[{'transition':t,'affiliationKey':p,'proposed':len(es),
                                       'labels':count_labels(es)} for (t,p),es in sorted(party_groups.items())],
            'byObservedRoleOutcome':[{'transition':t,'scope':s,'role':r,'winner':w,
                                      'proposedPrimaryEdges':len(es),'labels':count_labels(es)}
                                     for (t,s,r,w),es in sorted(outcomes.items())],
            'interpretation':'algorithmic_research_links_not_measured_precision_or_prospective_validation; exact_geography_selected; documentary_coverage_selected; outcomes_joined_after_acceptance'}


def readiness(edges, occurrences, tenure):
    by_id = {r['candidateOccurrenceId']:r for r in occurrences}
    tenure_by_pair = {r['pairId']:r for r in tenure}
    records = []
    for edge in edges:
        if not edge['primaryExactHeld']:
            continue
        source, target = by_id[edge['sourceOccurrenceId']],by_id[edge['targetOccurrenceId']]
        linked = edge['label'] in SAME
        residuals = all(r.get('normalizedPremium') is not None for r in (source,target))
        history = tenure_by_pair.get(edge['edgeId'])
        records.append({'edgeId':edge['edgeId'],'transition':f'{edge["sourceYear"]}-{edge["targetYear"]}',
                        'scope':edge['scope'],'broadSamePerson':linked,'strictSamePerson':strict_member(edge),
                        'persistenceEvidenceReady':linked and residuals,
                        'strictPersistenceEvidenceReady':strict_member(edge) and residuals,
                        'persistenceReason': 'available_for_separate_retrospective_research' if linked and residuals else
                            'missing_residual' if linked else 'relationship_not_accepted',
                        'existingTenureReview': {'artifact':'data/processed/models/freshman-incumbency/inventory.json',
                             'pairId':history['pairId'],'category':history['tenureCategory'],
                             'primaryEligible':history['primaryEligible']} if history else None,
                        'freshmanExistingEvidenceReady':linked and residuals and bool(history and history['primaryEligible']),
                        'freshmanLimitation':'only_previously_reviewed_selected_tenure; no_new_career_classification_or_as_of_claim',
                        'replacementDistinctEvidenceReady':edge['label']=='documentary_distinct_people',
                        'replacementLimitation':'no_nonmatch_inference; retained_by_election_roles_and_selected_source_coverage; departure_and_incoming_history_separate'})
    groups=[]
    for transition,scope in sorted({(r['transition'],r['scope']) for r in records}):
        selected=[r for r in records if (r['transition'],r['scope'])==(transition,scope)]
        groups.append({'transition':transition,'scope':scope,'pairQuestions':len(selected),
                       **{field:sum(r[field] for r in selected) for field in
                          ('broadSamePerson','strictSamePerson','persistenceEvidenceReady','strictPersistenceEvidenceReady','freshmanExistingEvidenceReady','replacementDistinctEvidenceReady')}})
    return {'records':records,'byTransitionScope':groups,
            'notModelAuthorization':True,'operationalSelections':'unchanged_null_or_unresolved',
            'nextTask':'registered_identity_free_exact_geography_retests; linkage_exceptions_do_not_block'}


def table(edges):
    lines=['# Stage26 proposed relationship review table',
           '', 'Automated rule assessment; not independent documentary validation. Manual exceptions are in review.json.',
           '', 'Timing: historical occurrence years are fact years; all adjudication is retrospective and publication by the historical cutoff is unknown. Exact documentary dates/passages are retained in documentary-claims.json; raw/source hashes are in input-contract.json.',
           '', '| Edge IDs | Source → target names | Parsed tokens | Affiliation | Ballot groups / context | Label / flags | Reason / competitors | Primary exact held |',
           '|---|---|---|---|---|---|---|---|']
    def cell(value):
        return str(value).replace('|','\\|').replace('\n',' ')
    for e in edges:
        lines.append('| '+' | '.join(cell(v) for v in (e['edgeId'],e['sourceOriginalName']+' → '+e['targetOriginalName'],
            str(parse_name(e['sourceOriginalName']))+' → '+str(parse_name(e['targetOriginalName'])),
            e['sourceOriginalAffiliation']+' → '+e['targetOriginalAffiliation'],
            str(e['sourcePartyBallotGroup'])+' → '+str(e['targetPartyBallotGroup'])+' / '+e['contextAssessment'],e['label']+' / '+','.join(e['ruleFlags']),
            str(e['ambiguityType'])+' / '+','.join(e['competingOccurrenceIds']),e['primaryExactHeld']))+' |')
    return ('\n'.join(lines)+'\n').encode()


def outcome_occurrence_coverage(rows, edges, geography, winners):
    """Count unique occurrences, including those with no proposed/accepted edge."""
    by_seat = defaultdict(list)
    for row in rows:
        by_seat[row['electorateId']].append(row['candidateOccurrenceId'])
    buckets = defaultdict(set)
    linked = defaultdict(set)
    strict_linked = defaultdict(set)
    for geo in geography:
        if not geo['certifiedTwoSidedExact']:
            continue
        transition = f"{geo['sourceYear']}-{geo['targetYear']}"
        for role, seat in (('source', geo['dominantPredecessorId']), ('target', geo['targetElectorateId'])):
            for cid in by_seat[seat]:
                buckets[transition, geo['scope'], role, str(winners.get(cid))].add(cid)
    for edge in edges:
        if edge['label'] not in SAME or not edge['primaryExactHeld']:
            continue
        transition = f"{edge['sourceYear']}-{edge['targetYear']}"
        for role, cid in (('source', edge['sourceOccurrenceId']), ('target', edge['targetOccurrenceId'])):
            linked[transition, edge['scope'], role, str(winners.get(cid))].add(cid)
            if strict_member(edge):
                strict_linked[transition, edge['scope'], role, str(winners.get(cid))].add(cid)
    return [{'transition': t, 'scope': s, 'role': r, 'observedWinner': w,
             'occurrences': len(ids), 'broadLinkedOccurrences': len(linked[t,s,r,w]), 'strictLinkedOccurrences': len(strict_linked[t,s,r,w])}
            for (t,s,r,w), ids in sorted(buckets.items())]
