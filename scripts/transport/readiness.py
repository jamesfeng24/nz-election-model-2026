"""New2026 source-geography/feature companion; never normalize partial candidate slates."""
import argparse
from collections import Counter
from copy import deepcopy
from scripts.readiness.features import s_feature, r_feature, neutral
from .common import read, save, verify_inputs, preserve, PREFIX, SNAPSHOT, LINKS
from .geography import canonical_2026, admitted, classification, all_rows, relationship_records


def source_seat(seat, geography):
    # Existing extractor's exactSource field is a lookup interface here only.
    # Exposed certification is never changed: transport metadata stays separate.
    return dict(seat, exactSourceElectorateId=geography['dominantPredecessorId'])


def transported_s(candidate, seat, geography, threshold, parties, occurrences, splits):
    if not admitted(geography,threshold):
        return neutral('outside_guaranteed_two_sided_transport_tier')
    value=s_feature(candidate,source_seat(seat,geography),parties,occurrences,splits)
    return dict(value, transportStatus=classification(geography),
        assumption='exact_reuse' if geography['certifiedTwoSidedExact'] else 'predecessor_flat_party_row_split; not reconstructed candidate ballots',
        predecessorElectorateId=geography['dominantPredecessorId'])


def transported_r(link, seat, geography, threshold, residuals, strict=False):
    if not admitted(geography,threshold):
        return neutral('outside_guaranteed_two_sided_transport_tier')
    record=residuals.get(link['sourceOccurrenceId'])
    if record is None or record['electorateId']!=geography['dominantPredecessorId']:
        return neutral('no_linked_source_person_in_dominant_predecessor')
    lookup=dict(link,geographyCompatible=True)
    value=r_feature(lookup,source_seat(seat,geography),residuals,strict)
    return dict(value, transportStatus=classification(geography),
        assumption='exact_reuse' if geography['certifiedTwoSidedExact'] else 'source residual predictor under high_overlap; not target-boundary residual reconstruction',
        predecessorElectorateId=geography['dominantPredecessorId'])


def build(*, frame=None, snapshot=None, links=None, parties=None, occurrences=None, residuals=None, splits=None, party_scenario=None):
    frame=read(SNAPSHOT+'target-frame.json')['records'] if frame is None else frame
    snapshot=read(SNAPSHOT+'snapshot.json') if snapshot is None else snapshot
    links=read(SNAPSHOT+'identity-links.json')['records'] if links is None else links
    parties=read(SNAPSHOT+'party-relationships.json')['records'] if parties is None else parties
    occurrences=read(LINKS+'occurrences.json')['records'] if occurrences is None else occurrences
    residuals=read('data/processed/models/candidate-overperformance/occurrences.json')['records'] if residuals is None else residuals
    splits=read('data/processed/split-votes/2023.json')['matrices'] if splits is None else splits
    party_scenario=read(PREFIX+'/party-construction.json')['transitions']['2023-2026'] if party_scenario is None else party_scenario
    geography={g['targetElectorateId']:g for g in canonical_2026(frame)}
    frames={s['targetElectorateId']:s for s in frame};relations={p['targetGroupKey']:p for p in parties}
    res={r['candidateOccurrenceId']:r for r in residuals if r['year']==2023}
    edge={e['targetOccurrenceId']:e for e in links};candidates=[];source_features=[];seats=[]
    for seat in frame:
        g=geography[seat['targetElectorateId']]
        for p in parties:
            source_features.append({'targetElectorateId':seat['targetElectorateId'],'targetPartyGroup':p['targetGroupKey'],
                'sourceBallotGroup':p['sourceBallotGroupKey'],'personIdentityRequired':False,
                'scenarios':{str(t):transported_s({'originalAffiliation':p['targetGroupKey']},seat,g,t,relations,occurrences,splits) for t in (90,95)}})
        source=[o for o in occurrences if o['electorateId']==g['dominantPredecessorId']]
        local=next(t for t in party_scenario['scopes'][seat['scope']]['targetPartyVectors'] if t['targetCode']==seat['boundaryCode'])
        seats.append({'targetElectorateId':seat['targetElectorateId'],'officialName':seat['officialName'],'scope':seat['scope'],
            'geography':g,'transportTier':classification(g),
            'dominantSourceContestStatuses':sorted({o['candidateContestStatus'] for o in source}),
            'partyInputStatus':'coherent_source_party_scenario; complete source categories; future target roster/scenario still required',
            'partyScenarioRef':{'path':PREFIX+'/party-construction.json','transition':'2023-2026','scope':seat['scope'],'targetCode':seat['boundaryCode']},
            'completeSourcePartyCategoryCount':len(local['parties']),
            'candidateSlateStatus':'official_complete' if seat['targetElectorateId'] in snapshot['completeSlateDeclarations'] else
                'incomplete_known_announcements' if any(c['active'] and c['targetElectorateId']==seat['targetElectorateId'] for c in snapshot['occurrences']) else 'unknown',
            'candidatePredictionsPermitted':False,'maoriGeneralCoefficientsPermitted':False if seat['scope']=='maori' else None,
            'additionalUncertainty':['local_party_error','candidate_error','population_to_vote_assumption','parameter_uncertainty','incomplete_slate','fine_party_allocation']+
                ([] if g['certifiedTwoSidedExact'] else ['source_S_R_transport_error_not_bounded_by_population_overlap'])+
                (['separate_maori_baseline_poll_layer'] if seat['scope']=='maori' else []),
            'nextAction':'official nomination refresh; joint local/candidate uncertainty; Maori poll layer separately bounded'})
    for c in snapshot['occurrences']:
        seat=frames[c['targetElectorateId']];g=geography[c['targetElectorateId']]
        link=edge[c['targetOccurrenceId']]
        by_tier={}
        for threshold in (90,95):
            s=transported_s(c,seat,g,threshold,relations,occurrences,splits) if c['originalAffiliation'] in relations else neutral('ambiguous_party_group','requires_explicit_abstention')
            by_tier[str(threshold)]={'S':s,'R':transported_r(link,seat,g,threshold,res),
                'RStrict':transported_r(link,seat,g,threshold,res,True)}
        candidates.append({'targetOccurrenceId':c['targetOccurrenceId'],'targetElectorateId':c['targetElectorateId'],
            'name':c['displayedName'],'affiliation':c['originalAffiliation'],'ballotGroupKey':c['ballotGroupKey'],
            'candidateStatus':c['status'],'active':c['active'],'conflict':c['conflict'],
            'tier':classification(g),'geography':g,'sourceIdentityEvidence':link,'scenarios':by_tier,
            'candidateSharesCalculated':False})
    coverage={'seatTiersByScope':{scope:dict(Counter(s['transportTier'] for s in seats if s['scope']==scope)) for scope in ('general','maori')},
        'heldGeneralTierCounts':dict(Counter(s['transportTier'] for s in seats if s['scope']=='general' and s['dominantSourceContestStatuses']==['held'])),
        'knownCandidates':len(candidates),'completeCandidateSlates':0,'candidateFeatures':{},'sourcePartySeatS':{}}
    for t in ('90','95'):
        coverage['candidateFeatures'][t]={name:dict(Counter(c['scenarios'][t][name]['status'] for c in candidates)) for name in ('S','R','RStrict')}
        coverage['sourcePartySeatS'][t]=dict(Counter(p['scenarios'][t]['status'] for p in source_features))
    return {'stage':41,'sourceSnapshot':SNAPSHOT,'sourceCutoff':snapshot['acquisitionCutoffUTC'],
            'candidateRecords':candidates,'sourcePartySeatRecords':source_features,'seatRecords':seats,
            'coverage':coverage,'liveForecastProduced':False,'operationalSelection':None,
            'historicalStage40SnapshotChanged':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    verify_inputs();value=build();save('readiness-2026.json',value,a.check)
    save('relationship-inventory.json',{'records':relationship_records(all_rows(),read(LINKS+'occurrences.json')['records']),
        'role':'canonical predecessor geography linked to separate outcome-independent candidature status'},a.check)
    print(value['coverage']);print('Prior preserved',preserve())


if __name__=='__main__':main()
