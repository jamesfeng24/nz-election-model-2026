"""Source-only feature availability; no candidate predictions or outcome admission."""
from math import isfinite
from scripts.checkpoints.complete_share_features import coupled_cell_percent, coupled_row_witness
from scripts.transform.historical import key
from .registry import mapping_readiness


def neutral(reason, status='neutral_fallback'):
    return {'status':status,'reason':reason,'valueFraction':None,
            'missingContribution':'neutral_exponent_where_existing_contract_permits; not_observed_zero_strength'}


def s_feature(candidate, seat, parties, occurrences, splits):
    if not seat['exactSourceElectorateId']:
        return neutral('changed_or_uncertified_candidate_feature_transport')
    if seat['scope']=='maori':
        return neutral('missing_named_candidate_split_matrix; separate_maori_baseline_required','unavailable')
    sid=seat['exactSourceElectorateId']
    old=[o for o in occurrences if o['electorateId']==sid]
    if any(o['candidateContestStatus']!='held' for o in old):
        return neutral('cancelled_source_candidate_contest')
    party=parties[candidate['originalAffiliation']];group=party['sourceBallotGroupKey']
    if group is None:
        return neutral('no_supported_cross_election_ballot_group_continuity')
    matrices=[m for m in splits if m['electorateId']==sid]
    if len(matrices)!=1:
        return neutral('continuing_group_missing_source_table','requires_explicit_abstention')
    matrix=matrices[0]
    rows=[r for r in matrix['rows'] if key(r['partyLabel'])==group]
    # 2023 official group aliases are explicit and preserved; target names never infer row identity.
    if group=='theopportunitiespartytop':
        rows=[r for r in matrix['rows'] if r['partyLabel']=='The Opportunities Party (TOP)']
    if len(rows)!=1:
        return neutral('continuing_group_missing_or_ambiguous_source_row','requires_explicit_abstention')
    row=rows[0]
    destinations=[o for o in old if o['ballotGroupKey']==group]
    if len(destinations)>1:
        return neutral('multiple_source_group_candidates','requires_explicit_abstention')
    if not destinations:
        return neutral('source_party_without_candidate_destination')
    if row['totalPartyVotes']==0:
        return neutral('zero_mass_source_party_row_s_unavailable')
    source=destinations[0]
    try:
        printed,low,high=coupled_cell_percent(row,source['candidateOccurrenceId'])
        witnesses={end:[str(v) for v in coupled_row_witness(row,source['candidateOccurrenceId'],end)] for end in ('lower','upper')}
    except ValueError as error:
        return neutral(str(error),'requires_explicit_abstention')
    return {'status':'supported','reason':None,'valueFraction':printed/100,
        'sourceOccurrenceId':source['candidateOccurrenceId'],'sourceMatrixId':matrix['id'],
        'sourcePartyKey':group,'sourcePartyRowMass':row['totalPartyVotes'],
        'printedPercentWorkingApproximation':printed,'coupledSelectedPercentBounds':[str(low),str(high)],
        'completeRowWitnesses':witnesses,'sourceIds':matrix['sourceIds'],
        'evidenceTier':'official_rounded_source_party_row_to_candidate_destination',
        'personIdentityRequired':False,'publicationBy2026Cutoff':'retrospective_preserved2023_evidence'}


def r_feature(link, seat, residuals, strict=False):
    if not link['broadAccepted'] or strict and not link['strictAccepted']:
        return neutral('no_accepted_strict_link' if strict else 'no_accepted_direct_relationship')
    if not link['geographyCompatible'] or not seat['exactSourceElectorateId']:
        return neutral('seat_change_or_nonexact_transport_not_authorized')
    record=residuals.get(link['sourceOccurrenceId']);value=record.get('normalizedPremium') if record else None
    if record and (record['year']!=2023 or record['electorateId']!=seat['exactSourceElectorateId'] or record['candidateOccurrenceId']!=link['sourceOccurrenceId']):
        raise ValueError('Corrupt source-only residual/geography join')
    if not record or record['candidateContestStatus']!='held' or value is None or not isfinite(value):
        return neutral('source_residual_unavailable_or_cancelled')
    return {'status':'supported' if seat['scope']=='general' else 'evidence_available_separate_maori_contract_required',
        'valueFraction':value,'sourceOccurrenceId':record['candidateOccurrenceId'],
        'sourceReferenceId':record['referenceId'],'evidenceTier':link['label'],
        'sourceNormalization':'frozen2023whole_contest_reference; no2026target_reference',
        'careerHistoryRequired':False,'reason':None}


def candidate_features(candidates, links, frame, parties, occurrences, residuals, splits):
    seats={s['targetElectorateId']:s for s in frame};relations={p['targetGroupKey']:p for p in parties}
    edges={e['targetOccurrenceId']:e for e in links};rows=[]
    for c in candidates:
        seat=seats[c['targetElectorateId']];link=edges[c['targetOccurrenceId']]
        s=s_feature(c,seat,relations,occurrences,splits) if c['originalAffiliation'] in relations else neutral('ambiguous_target_party_mapping','requires_explicit_abstention')
        rows.append({'targetOccurrenceId':c['targetOccurrenceId'],'targetElectorateId':c['targetElectorateId'],
            'activeCandidate':c['active'],'S':s,'R':r_feature(link,seat,residuals),
            'RStrict':r_feature(link,seat,residuals,True),'predictionGenerated':False})
    return rows


def seat_readiness(frame,candidates,features,complete):
    result=[]
    for seat in frame:
        known=[c for c in candidates if c['targetElectorateId']==seat['targetElectorateId']]
        active=[c for c in known if c['active']]
        f=[r for r in features if r['targetElectorateId']==seat['targetElectorateId'] and r['activeCandidate']]
        supportedS=sum(r['S']['status']=='supported' for r in f)
        supportedR=sum(r['R']['status']=='supported' for r in f)
        result.append({'targetElectorateId':seat['targetElectorateId'],'scope':seat['scope'],
            'knownActiveCandidateIds':[c['targetOccurrenceId'] for c in active],
            'knownCandidateCount':len(active),'officialNominationCount':sum(c['status']=='official_nomination' for c in active),
            'slateStatus':'official_complete' if seat['targetElectorateId'] in complete else 'incomplete_known_announcements' if active else 'unknown',
            'slateComplete':seat['targetElectorateId'] in complete,'mappingStatus':mapping_readiness(known),
            'SCounts':{'supported':supportedS,'fallbackOrUnavailable':len(f)-supportedS},
            'RCounts':{'supported':supportedR,'fallbackOrUnavailable':len(f)-supportedR},
            'strictRSupported':sum(r['RStrict']['status']=='supported' for r in f),
            'partyAffinity':seat['partyReconstruction'],
            'constructionNow':'source_party_evidence_and_partial_candidate_features; no_complete_forecast',
            'conditionalOn':['supplied_coherent_national_vector','confirmed2026_party_ballot_roster','complete_target_candidate_slate'],
            'modellingAssumptions':['neutral_entrant_geographic_profile_from_existing_rule','missing_feature_neutral_exponent']+
                ([] if seat['exactSourceElectorateId'] else ['joint_population_to_party_vote_transport; no_selected_point']),
            'unavailable':['complete_candidate_uncertainty','parameter_uncertainty']+
                ([] if seat['exactSourceElectorateId'] else ['authorized_changed_boundary_S_R_transport'])+
                (['maori_candidate_baseline_and_poll_layer'] if seat['scope']=='maori' else []),
            'smallestNextAction':'refresh_official_nominations_after8October; preserve conflicts and recheck affected links',
            'maoriPollingInterface':{'status':'separate_planned_component','nationalTPMIsCandidateSupport':False,
                'required':['actual_candidate_or_party_question','valid_vote_or_respondent_denominator','target_boundary_and_candidate_ids','fieldwork_dates','publication_dates','sample_size','polling_error','dependence_with_other_inputs'],
                'unpolledOrStaleFallback':'explicit_maori_seat_baseline_with_wider_joint_uncertainty','acquisitionStarted':False} if seat['scope']=='maori' else None})
    return result
