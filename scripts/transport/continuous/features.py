"""Center source features before weighting by conserved predecessor party mass."""
from copy import deepcopy
from fractions import Fraction
from math import fsum, isfinite
from scripts.checkpoints.stage25_geography import local_ids, seat_id
from scripts.evidence.practical_candidate_linkage.names import strict_member
from scripts.evidence.practical_candidate_linkage.components import validate_components
from scripts.checkpoints.complete_share_features import source_rows, _feature, continuity_index
from scripts.checkpoints.stage25_availability import ELECTIONS, SPLITS, MAPPING, CONTINUITY, mapped_contests, target_candidates
from scripts.evidence.practical_candidate_linkage.names import alias_pairs
from .common import read, LINKS


def context():
    occurrences=read(LINKS+'occurrences.json')['records']
    elections={y:read(p) for y,p in ELECTIONS.items()}
    return {'occurrences':occurrences,'elections':elections,
        'seats':{y:{s['id']:s for s in e['electorates']} for y,e in elections.items()},
        'splits':{y:{m['electorateId']:m for m in read(p)['matrices']} for y,p in SPLITS.items()},
        'mapping':mapped_contests(read(MAPPING)), 'continuity':continuity_index(read(CONTINUITY)['records']),
        'residuals':{r['candidateOccurrenceId']:r for r in read('data/processed/models/candidate-overperformance/occurrences.json')['records']}}


def links_for_geography(geography, occurrences):
    held={o['candidateOccurrenceId'] for o in occurrences if o['candidateContestStatus']=='held'}
    original=read(LINKS+'proposed-links.json')['records']
    pairs={(p['sourceElectorateId'],g['targetElectorateId']) for g in geography for p in g['predecessors']}
    # Retain the complete graph: removing rejected/cancelled edges could conceal a conflict.
    assessed=deepcopy(original);amended=set()
    for edge in assessed:
        if ((edge['sourceElectorateId'],edge['targetElectorateId']) in pairs
            and edge['sourceOccurrenceId'] in held and edge['targetOccurrenceId'] in held
            and edge['label']=='unresolved_ambiguous' and edge['ambiguityType']=='seat_change_or_nonexact_geography'
            and edge['nameAssessment']['compatible'] and not edge['competingOccurrenceIds']
            and edge['contextAssessment'] in ('documented_party_continuity_same_original_affiliation',
                'documented_single_party_label_continuity','independent_no_party_context')):
            edge['label']='accepted_algorithmic_same_person';amended.add(edge['edgeId'])
    audits=validate_components(assessed,occurrences,alias_pairs(read(LINKS+'aliases.json')))
    supplemental=[dict(edge,originalLabel=old['label'],originalReason=old['ambiguityType'],
        assessmentLayer='Stage42 genuine predecessor geographic-only supplement')
        for old,edge in zip(original,assessed) if edge['edgeId'] in amended]
    return assessed,{'records':supplemental,'componentAudits':audits,
        'priorAdjudicationsChanged':False,'newPersonGroupsAssigned':False}



def flow_index(geography, occurrences, scenario=None):
    scenario=read('data/processed/forecast-transport/party-construction.json') if scenario is None else scenario
    local=local_ids(read('data/processed/models/candidate-overperformance/occurrences.json')['records']); result={}
    for transition,t in scenario['transitions'].items():
        sy,ty=map(int,transition.split('-'))
        cross=read(f'data/processed/boundaries/{transition}/crosswalk.json')
        party=read(f'data/processed/boundaries/{transition}/party-votes.json')
        for scope,s in t['scopes'].items():
            if s['status']!='constructed':raise ValueError('Frozen party-flow scope unavailable')
            names={v['code']:v['name'] for v in cross['scopes'][scope]['sources']}
            ids={code:seat_id(sy,scope,code,name,local) for code,name in names.items()}
            targets={g['targetElectorateId']:g for g in geography if (g['sourceYear'],g['targetYear'],g['scope'])==(sy,ty,scope)}
            target_codes={g.get('boundaryCode',str(int(g['targetElectorateId'].split('-')[-1])).zfill(3)):g for g in targets.values()}
            # Māori canonical historical IDs use official names, not general-seat numbers.
            if ty!=2026 and scope=='maori':
                target_codes={v['code']:targets[seat_id(ty,scope,v['code'],v['name'],local)] for v in cross['scopes'][scope]['targets']}
            for edge in s['aggregatedEdges']:
                g=target_codes[edge['targetCode']];sid=ids[edge['sourceCode']]
                if sid not in {p['sourceElectorateId'] for p in g['predecessors']}:
                    raise ValueError('Party flow outside canonical predecessor relation')
                weight=Fraction(edge['weight']['numerator'],edge['weight']['denominator'])
                source=party['scopes'][scope]['sources'][edge['sourceCode']]
                votes={p['partyKey']:p['votes'] for p in source['parties']}
                result.setdefault(g['targetElectorateId'],[]).append({'sourceElectorateId':sid,
                    'sourceCode':edge['sourceCode'],'populationWeightExact':str(weight),
                    'partyMassExact':{p:str(v*weight) for p,v in votes.items()},
                    'sourceVotes':votes,'flowSource':'frozen Stage41 feasible population witness',
                    'assumption':'uniform within source electorate party voting; not observed fragment votes'})
    for g in geography:
        if g['targetElectorateId'] in result and {x['sourceElectorateId'] for x in result[g['targetElectorateId']]}!={p['sourceElectorateId'] for p in g['predecessors']}:
            raise ValueError('Missing canonical predecessor party flow')
    return result


def source_group(ctx, sy, ty, party):
    if party is None:return None,'affirmative_no_party_group_weight_undefined'
    relation=ctx['continuity'].get((sy,ty,party))
    if relation is None:return None,'missing_supported_group_continuity'
    if relation['status']=='entrant':return None,'documented_entry_no_historical_party_mass'
    if relation['status']!='eligible' or not relation['source']:return None,'ambiguous_group_continuity'
    return relation['source']['sourceKey'],None


def selected_link(target, sy, ty, edges, predecessors, view):
    accepted=[e for e in edges if e['targetOccurrenceId']==target and (e['sourceYear'],e['targetYear'])==(sy,ty)
        and e['label'] in ('documentary_same_person','accepted_algorithmic_same_person')]
    if len(accepted)!=1:return None,'no_unique_accepted_relationship; nonmatch_is_not_replacement'
    edge=accepted[0]
    if view=='strict' and not strict_member(edge):return None,'outside_strict_linkage'
    if edge['sourceElectorateId'] not in predecessors:return None,'accepted_source_outside_genuine_predecessors'
    return edge,None


def source_s(ctx, source_id, candidate, target, sy, ty):
    source=ctx['seats'][sy].get(source_id);matrix=ctx['splits'][sy].get(source_id)
    if source is None:return None,'missing_source_contest',None
    if source['validCandidateVotes']<=0:return None,'cancelled_source_candidate_contest',None
    if matrix is None or matrix.get('behaviouralEvidence') is False:return None,'missing_source_split_table',None
    try:
        f=_feature(candidate,source,target,source_rows(matrix,source),matrix,ctx['continuity'],sy,ty)
        return f['s0Reported'],('; '.join(f['fallbackReasons']) or None),{
            'sourceMatrixId':f['sourceMatrixId'],'sourceCandidateId':f['sourceCandidateId'],
            'splitSourceIds':f['splitSourceIds'],'coupledPercentBounds':f['coupledSamePartyPercent']}
    except ValueError as error:
        return None,'unsupported_source_feature: '+str(error),None


def source_r(ctx, source_id, edge):
    if edge is None or edge['sourceElectorateId']!=source_id:return None,'no_same_person_in_this_predecessor',None
    r=ctx['residuals'].get(edge['sourceOccurrenceId'])
    if r is None or r['electorateId']!=source_id or r['year']!=edge['sourceYear']:
        return None,'missing_or_inconsistent_source_residual',None
    value=r.get('normalizedPremium')
    if r['candidateContestStatus']!='held' or value is None or not isfinite(value):return None,'source_residual_unavailable_or_cancelled',None
    return value,None,{'sourceOccurrenceId':r['candidateOccurrenceId'],'sourceReferenceId':r['referenceId'],
        'edgeId':edge['edgeId'],'evidenceTier':edge['label'],'ruleFlags':edge['ruleFlags']}


def weighted(components, center):
    """Missing evidence shrinks to neutral; never renormalize supported mass."""
    total=sum((Fraction(c['partyMassExact']) for c in components),Fraction(0))
    if total<=0:
        return {'contribution':0.0,'supportedWeight':0.0,'unsupportedWeight':1.0,
            'totalMassExact':str(total),'reason':'zero_or_undefined_transported_party_mass','components':components}
    supported=Fraction(0);terms=[];rows=[]
    for c in components:
        mass=Fraction(c['partyMassExact'])
        if mass<0:raise ValueError('Negative party mass')
        weight=mass/total;value=c['valueFraction']
        if value is not None:
            if not isfinite(value) or center is None:raise ValueError('Nonfinite source feature or missing frozen mean')
            supported+=weight;z=value-center
        else:z=0.0
        terms.append(float(weight)*z)
        rows.append(dict(c,weightExact=str(weight),weight=float(weight),centeredSource=z))
    return {'contribution':fsum(terms),'supportedWeight':float(supported),'unsupportedWeight':float(1-supported),
        'totalMassExact':str(total),'reason':None if supported else 'all_predecessor_features_unsupported',
        'components':rows}


def candidate_features(ctx, g, candidate, target, flows, edges, means):
    sy,ty=g['sourceYear'],g['targetYear'];group,reason=source_group(ctx,sy,ty,candidate['partyKey'])
    if group is None:
        return {n:{'contribution':0.0,'supportedWeight':0.0,'unsupportedWeight':1.0,
            'totalMassExact':None,'reason':reason,'components':[]} for n in ('S','R','RStrict')}
    if any(group not in f['partyMassExact'] for f in flows):raise ValueError('Continuing party mass missing; not structural zero')
    predecessors={f['sourceElectorateId'] for f in flows}
    components={n:[] for n in ('S','R','RStrict')}
    links={v:selected_link(candidate['candidateOccurrenceId'],sy,ty,edges,predecessors,v) for v in ('broad','strict')}
    for f in flows:
        sid=f['sourceElectorateId'];mass=f['partyMassExact'][group]
        value,why,evidence=source_s(ctx,sid,candidate,target,sy,ty)
        components['S'].append({'sourceElectorateId':sid,'partyMassExact':mass,'sourcePartyKey':group,
            'valueFraction':value,'reason':why,'evidence':evidence})
        for name,view in (('R','broad'),('RStrict','strict')):
            edge,link_reason=links[view];value,why,evidence=source_r(ctx,sid,edge)
            components[name].append({'sourceElectorateId':sid,'partyMassExact':mass,'sourcePartyKey':group,
                'valueFraction':value,'reason':link_reason or why,'evidence':evidence})
    return {n:weighted(cs,means['S' if n=='S' else 'R']) for n,cs in components.items()}
