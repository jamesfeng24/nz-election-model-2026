"""Direct provisional source relationships using frozen practical name safeguards."""
import re
from scripts.evidence.practical_candidate_linkage.names import normalize, parse_name, name_match


def parsed_target(name, historical):
    label = re.sub(r'^(?:Rt Hon\.?|Hon\.?|Dr\.?)\s+', '', name, flags=re.I)
    families = {o['parsedName']['surname'] for o in historical if o['parsedName']['status']=='parsed'
                and normalize(label).endswith(' '+o['parsedName']['surname'])}
    # Longest explicit historical family resolves compound surnames without token rearrangement.
    family = max(families, key=len) if families else None
    return parse_name(label, 'given_surname', surname=family)


def build_links(candidates, historical, aliases, frame, parties):
    source = [o for o in historical if o['year']==2023]
    seats = {s['targetElectorateId']:s for s in frame}
    continuity = {p['targetGroupKey']:p['sourceBallotGroupKey'] for p in parties}
    parsed = {c['targetOccurrenceId']:parsed_target(c['displayedName'],source) for c in candidates}
    proposals=[]
    for target in candidates:
        tid=target['targetOccurrenceId']; matching=[]
        for old in source:
            match=name_match(old['parsedName'],parsed[tid],aliases)
            if match['compatible']:
                matching.append((old,match))
        competitors=[c['targetOccurrenceId'] for c in candidates if c['active'] and c['targetOccurrenceId']!=tid
                     and name_match(parsed[c['targetOccurrenceId']],parsed[tid],aliases)['compatible']]
        reasons=[]
        if not target['active'] or target['conflict']:reasons.append('inactive_or_conflicting_target')
        if parsed[tid]['status']!='parsed':reasons.append('unresolved_name_parse')
        if len(matching)!=1:reasons.append('competing_source_occurrences' if matching else 'no_compatible_source_name_not_proof_of_replacement')
        if competitors:reasons.append('competing_target_occurrences')
        selected=matching[0][0] if len(matching)==1 else None
        if selected and selected['candidateAffiliationKey'] != continuity.get(target['originalAffiliation']):
            reasons.append('party_change_or_unsupported_continuity_exception')
        flags=matching[0][1]['flags'] if len(matching)==1 else []
        seat=seats[target['targetElectorateId']]
        # Geography is deliberately separate: accepted same-person leads may change seats.
        exact=bool(selected and seat['exactSourceElectorateId']==selected['electorateId'])
        within_predecessors=bool(selected and selected['electorateId'] in {p['sourceElectorateId'] for p in seat['predecessors']})
        accepted=not reasons
        proposals.append({'targetOccurrenceId':tid,'sourceOccurrenceId':selected['candidateOccurrenceId'] if selected else None,
            'proposedSourceOccurrenceIds':sorted(o['candidateOccurrenceId'] for o,_ in matching),
            'competingTargetOccurrenceIds':sorted(competitors),'parsedTargetName':parsed[tid],
            'label':'accepted_algorithmic_same_person' if accepted else 'unresolved_ambiguous',
            'ruleFlags':flags,'broadAccepted':accepted,'strictAccepted':accepted and flags==['exact_name'],
            'exceptionReasons':reasons,'geographyCompatible':exact,'seatChangeLead':bool(selected and not within_predecessors),
            'sourceSeatRelation':'exact_predecessor' if exact else 'supported_nonexact_predecessor' if within_predecessors else 'outside_target_predecessors' if selected else 'unknown',
            'sourceOfficialSourceIds':selected['officialSourceIds'] if selected else [],
            'targetSourceIds':sorted({c['sourceId'] for c in target['claims']}),
            'confidence':'unique_in_observed_election_wide_universe; pending_complete2026_nomination_refresh' if accepted else 'unresolved',
            'documentaryBridge':False,'careerHistoryEstablished':False,
            'historicalPublicationCertified':False,'reversible':True,'personGroupAssigned':False})
    return proposals
