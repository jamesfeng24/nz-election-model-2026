"""Complete outcome-independent target slates, all source predecessor components."""
from scripts.checkpoints.stage25_availability import target_candidates
from scripts.transport.geography import classification
from scripts.checkpoints.joint_candidate_share.kernel import centered
from .features import context, links_for_geography, flow_index, candidate_features
from .common import read


def inventory(geography, ctx=None, flows=None, edges=None):
    ctx=context() if ctx is None else ctx
    flows=flow_index(geography,ctx['occurrences']) if flows is None else flows
    if edges is None:edges,_=links_for_geography(geography,ctx['occurrences'])
    original={r['targetElectorateId']:r for r in read('data/processed/forecast-transport/historical-inventory.json')['records']}
    folds=read('data/processed/forecast-transport/sample-manifest.json')['folds']
    means={f['targetYear']:f['trainingOnlyMeans'] for f in folds}
    statuses={}
    for o in ctx['occurrences']:statuses.setdefault(o['electorateId'],set()).add(o['candidateContestStatus'])
    records=[];coverage=[]
    for g in geography:
        sy,ty=g['sourceYear'],g['targetYear']
        if ty not in (2014,2020):continue
        tid=g['targetElectorateId'];cover={'targetElectorateId':tid,'targetYear':ty,'scope':g['scope'],
            'tier':classification(g),'status':'abstained','reason':None}
        if g['scope']!='general':cover['reason']='separate_maori_candidate_contract_required'
        elif statuses.get(tid)!={'held'}:cover['reason']='cancelled_or_missing_target_candidature_status'
        else:
            target=ctx['seats'][ty].get(tid)
            roster={p['partyKey'] for s in ctx['elections'][ty]['electorates'] for p in s['parties']}
            classified,problem=target_candidates(ctx['mapping'].get((ty,tid)),target,roster)
            if classified is None:cover['reason']=problem
            elif tid not in flows:cover['reason']='missing_coherent_party_flow'
            else:
                candidates=[];old={c['targetOccurrenceId']:c for c in original.get(tid,{}).get('candidates',[])}
                for c in classified:
                    party=c['partyKey']
                    actual_party={p['partyKey']:p['votes'] for p in target['parties']}
                    if c['noRegisteredPartyGroup']:support=0.0
                    elif party not in actual_party or target['validPartyVotes']<=0:raise ValueError('Incomplete observed party input')
                    else:support=actual_party[party]/target['validPartyVotes']
                    continuous=candidate_features(ctx,g,c,target,flows[tid],edges,means[ty])
                    inherited={}
                    for view in ('broad','strict'):
                        f=old.get(c['candidateOccurrenceId'])
                        inherited[view]={n:centered(f,n,means[ty],view,'printed') if f else 0.0 for n in ('S','R')}
                    candidates.append({'targetOccurrenceId':c['candidateOccurrenceId'],'partyBallotGroupKey':party,
                        'originalAffiliation':c.get('candidatePartyLabel',c.get('originalCandidatePartyKey')),
                        'observedPartySupport':support,'continuous':continuous,'inheritedStage41Centered':inherited})
                records.append({'sourceYear':sy,'targetYear':ty,'targetElectorateId':tid,'scope':g['scope'],
                    'transportTier':classification(g),'geographyId':g['geographyId'],'candidates':candidates})
                cover.update(status='available',reason=None)
        coverage.append(cover)
    return {'stage':42,'records':records,'fullFrame':coverage,
        'targetCandidateOutcomesConsumed':False,'heldoutResidualRequired':False}
