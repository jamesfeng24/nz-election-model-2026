"""Outcome-independent complete historical slates and source-only transport features."""
from copy import deepcopy
from math import isfinite
from scripts.checkpoints.stage25_availability import ELECTIONS, SPLITS, MAPPING, CONTINUITY, mapped_contests, target_candidates
from scripts.checkpoints.complete_share_features import continuity_index, source_rows, _feature
from scripts.evidence.practical_candidate_linkage.components import validate_components
from scripts.evidence.practical_candidate_linkage.names import alias_pairs, strict_member
from .common import read, LINKS
from .geography import admitted, classification, all_rows


def supplemental_links(edges, occurrences, aliases, permitted_pairs):
    """Reassess only the old geographic refusal; never override another identity conflict."""
    assessed = deepcopy(edges)
    amended = set()
    for edge in assessed:
        if ((edge['sourceElectorateId'],edge['targetElectorateId']) in permitted_pairs
                and edge['label']=='unresolved_ambiguous' and edge['ambiguityType']=='seat_change_or_nonexact_geography'
                and edge['nameAssessment']['compatible'] and not edge['competingOccurrenceIds']
                and edge['contextAssessment'] in ('documented_party_continuity_same_original_affiliation',
                    'documented_single_party_label_continuity','independent_no_party_context')):
            edge['label'] = 'accepted_algorithmic_same_person'
            amended.add(edge['edgeId'])
    audits = validate_components(assessed, occurrences, aliases)
    output = []
    for original, edge in zip(edges, assessed):
        if edge['edgeId'] in amended:
            output.append({**edge, 'originalLabel':original['label'], 'originalReason':original['ambiguityType'],
                           'assessmentLayer':'Stage41 supplemental direct transport relationship; no prior adjudication rewrite',
                           'historicalAdjudicationsOverwritten':False})
    return assessed, output, audits


def r_source(target_id, geography, view, edges, residuals):
    selected = [e for e in edges if e['targetOccurrenceId']==target_id
                and (e['sourceYear'],e['targetYear'])==(geography['sourceYear'],geography['targetYear'])
                and e['label'] in ('documentary_same_person','accepted_algorithmic_same_person')
                and (view=='broad' or strict_member(e))]
    missing = {'valueFraction':None,'sourceOccurrenceId':None,'status':'neutral_fallback',
               'reason':'no_unique_accepted_same_person_source; not_proof_of_replacement'}
    if len(selected)!=1:
        return missing
    edge=selected[0]
    if edge['sourceElectorateId']!=geography['dominantPredecessorId']:
        return dict(missing, reason='linked_person_outside_dominant_predecessor')
    record=residuals.get(edge['sourceOccurrenceId'])
    if record is None or (record['year'],record['electorateId'])!=(geography['sourceYear'],geography['dominantPredecessorId']):
        return dict(missing, reason='missing_or_inconsistent_source_residual')
    value=record.get('normalizedPremium')
    if record['candidateContestStatus']!='held' or value is None or not isfinite(value):
        return dict(missing, reason='source_residual_unavailable_or_cancelled')
    return {'valueFraction':value,'sourceOccurrenceId':record['candidateOccurrenceId'],
            'sourceReferenceId':record['referenceId'],'status':'supported','reason':None,
            'edgeId':edge['edgeId'],'evidenceTier':edge['label'],'ruleFlags':edge['ruleFlags'],
            'sourceNormalization':'frozen_whole_source_contest; no target residual required',
            'transportMeaning':'source residual predictor, not reconstructed candidate votes'}


def defaults():
    elections={y:read(p) for y,p in ELECTIONS.items()}
    splits={y:read(p) for y,p in SPLITS.items()}
    occurrences=read(LINKS+'occurrences.json')['records']
    permitted={(r['dominantPredecessorId'],r['targetElectorateId']) for r in all_rows()
               if r['targetYear'] in (2014,2020) and not r['certifiedTwoSidedExact'] and admitted(r,90)}
    assessed,supplemental,audits=supplemental_links(read(LINKS+'proposed-links.json')['records'],occurrences,
        alias_pairs(read(LINKS+'aliases.json')),permitted)
    return elections,splits,read(MAPPING),read(CONTINUITY)['records'],assessed,supplemental,audits


def inventory(geography, *, inputs=None, residuals=None, exact=None):
    elections,splits,mapping,continuity_rows,edges,supplemental,audits=defaults() if inputs is None else inputs
    residuals={r['candidateOccurrenceId']:r for r in read('data/processed/models/candidate-overperformance/occurrences.json')['records']} if residuals is None else residuals
    exact={r['targetElectorateId']:r for r in read('data/processed/checkpoints/joint-candidate-share-design/inventory.json')['contestRecords']} if exact is None else exact
    seats={y:{r['id']:r for r in e['electorates']} for y,e in elections.items()}
    matrices={y:{r['electorateId']:r for r in s['matrices']} for y,s in splits.items()}
    mapped=mapped_contests(mapping);continuity=continuity_index(continuity_rows)
    rows=[];coverage=[]
    for g in geography:
        if g['targetYear'] not in (2014,2020):
            continue
        cid=g['targetElectorateId'];sy,ty=g['sourceYear'],g['targetYear']
        cover={'geographyId':g['geographyId'],'targetElectorateId':cid,'targetYear':ty,
               'scope':g['scope'],'tier':classification(g),'status':'abstain','reason':None}
        if g['scope']!='general':
            cover['reason']='separate_maori_baseline_required'
        elif not admitted(g,90):
            cover['reason']='not_guaranteed_two_sided_90'
        else:
            source=seats[sy].get(g['dominantPredecessorId']);target=seats[ty].get(cid)
            classified,problem=target_candidates(mapped.get((ty,cid)),target,
                {p['partyKey'] for seat in elections[ty]['electorates'] for p in seat['parties']})
            if source is None or classified is None:
                cover['reason']=problem or 'missing_source_seat'
            elif source['validCandidateVotes']<=0 or target['validCandidateVotes']<=0:
                cover['reason']='cancelled_or_missing_valid_candidate_denominator'
            elif g['certifiedTwoSidedExact']:
                if cid not in exact or exact[cid]['status']!='available':
                    cover['reason']='original_exact_sample_abstention'
                else:
                    row=deepcopy(exact[cid]);row['transportTier']='exact';row['geography']=g
                    rows.append(row);cover.update(status='available',reason=None)
            else:
                matrix=matrices[sy].get(source['id'])
                if matrix is None or matrix.get('behaviouralEvidence') is False:
                    cover['reason']='missing_or_nonbehavioural_source_split_table'
                else:
                    try:
                        parties=source_rows(matrix,source);candidates=[]
                        for candidate in classified:
                            f=_feature(candidate,source,target,parties,matrix,continuity,sy,ty)
                            f['observedPartySupport']=f['targetPartySupport']
                            f['partyBallotGroupKey']=f['targetPartyKey']
                            f['R']={v:r_source(f['targetOccurrenceId'],g,v,edges,residuals) for v in ('broad','strict')}
                            for value in f['R'].values():
                                value['availabilityPattern']='both_features' if value['valueFraction'] is not None and f['s0Reported'] is not None else 'R_only' if value['valueFraction'] is not None else 'S_only' if f['s0Reported'] is not None else 'neither_feature'
                            candidates.append(f)
                        row={'sourceYear':sy,'targetYear':ty,'scope':g['scope'],
                             'sourceElectorateId':source['id'],'targetElectorateId':cid,'geographyId':g['geographyId'],
                             'transportTier':classification(g),'geography':g,'status':'available','candidates':candidates}
                        rows.append(row);cover.update(status='available',reason=None)
                    except ValueError as error:
                        cover['reason']='source_feature_contract: '+str(error)
        coverage.append(cover)
    return {'records':rows,'fullFrame':coverage,'supplementalRelationships':supplemental,
            'supplementalComponentAudits':audits,'heldoutCandidateOutcomesConsumed':False}
