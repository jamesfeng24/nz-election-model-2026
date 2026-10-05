"""2026 all-predecessor feature companion; no shares from incomplete slates."""
import argparse
from collections import Counter
from scripts.readiness.features import s_feature,r_feature
from scripts.transport.geography import canonical_2026
from .features import context,flow_index,weighted
from .common import read,save,verify,PREFIX,SNAPSHOT,METHOD


def unavailable(reason):
    return {'contribution':0.0,'supportedWeight':0.0,'unsupportedWeight':1.0,
        'totalMassExact':None,'reason':reason,'components':[]}


def features(candidate,seat,flows,relations,occurrences,splits,link,residuals,means):
    if len({f['sourceElectorateId'] for f in flows})!=len(flows):raise ValueError('Duplicate predecessor party mass')
    group=candidate.get('ballotGroupKey',candidate.get('originalAffiliation'))
    relation=relations.get(group)
    source=relation['sourceBallotGroupKey'] if relation else None
    if source is None:return {n:unavailable('no_group_or_supported_source_ballot_continuity') for n in ('S','R','RStrict')}
    if any(source not in f['partyMassExact'] for f in flows):raise ValueError('Missing continuing group mass')
    predecessors={f['sourceElectorateId'] for f in flows};components={n:[] for n in ('S','R','RStrict')}
    for f in flows:
        sid=f['sourceElectorateId'];source_seat=dict(seat,exactSourceElectorateId=sid)
        s=s_feature({'originalAffiliation':group},source_seat,relations,occurrences,splits)
        components['S'].append({'sourceElectorateId':sid,'partyMassExact':f['partyMassExact'][source],
            'sourcePartyKey':source,'valueFraction':s['valueFraction'],'reason':s['reason'],'evidence':s})
        for name,strict in (('R',False),('RStrict',True)):
            record=residuals.get(link.get('sourceOccurrenceId')) if link else None
            if record and record['electorateId']==sid and sid in predecessors:
                r=r_feature(dict(link,geographyCompatible=True),source_seat,residuals,strict)
            else:r={'valueFraction':None,'reason':'no_unique_accepted_source_person_in_this_predecessor'}
            components[name].append({'sourceElectorateId':sid,'partyMassExact':f['partyMassExact'][source],
                'sourcePartyKey':source,'valueFraction':r['valueFraction'],'reason':r['reason'],'evidence':r})
    return {n:weighted(cs,means['S' if n=='S' else 'R']) for n,cs in components.items()}


def build(frame=None,snapshot=None,links=None,relations=None,ctx=None,flows=None):
    frame=read(SNAPSHOT+'target-frame.json')['records'] if frame is None else frame
    snapshot=read(SNAPSHOT+'snapshot.json') if snapshot is None else snapshot
    links=read(SNAPSHOT+'identity-links.json')['records'] if links is None else links
    relations=read(SNAPSHOT+'party-relationships.json')['records'] if relations is None else relations
    ctx=context() if ctx is None else ctx
    geo=canonical_2026(frame);flows=flow_index(geo,ctx['occurrences']) if flows is None else flows
    edge={e['targetOccurrenceId']:e for e in links}
    if len(edge)!=len(links):raise ValueError('Duplicate2026 target identity assessment')
    parties={p['targetGroupKey']:p for p in relations}
    fold=next(f for f in read('data/processed/models/joint-candidate-share/construction.json')['folds'] if f['branch']=='primary' and f['targetYear']==2023)
    means=fold['trainingOnlyMeans'];seats={s['targetElectorateId']:s for s in frame};gs={g['targetElectorateId']:g for g in geo}
    residuals={i:r for i,r in ctx['residuals'].items() if r['year']==2023}
    splits=list(ctx['splits'][2023].values());source_features=[];candidates=[]
    for seat in frame:
        for relation in relations:
            candidate={'originalAffiliation':relation['targetGroupKey'],'ballotGroupKey':relation['targetGroupKey']}
            value=features(candidate,seat,flows[seat['targetElectorateId']],parties,ctx['occurrences'],splits,None,residuals,means)
            source_features.append({'targetElectorateId':seat['targetElectorateId'],'scope':seat['scope'],
                'targetGroupKey':relation['targetGroupKey'],'sourceGroupKey':relation['sourceBallotGroupKey'],
                'S':value['S'],'personIdentityRequired':False})
    for c in snapshot['occurrences']:
        seat=seats[c['targetElectorateId']]
        value=features(c,seat,flows[c['targetElectorateId']],parties,ctx['occurrences'],splits,edge.get(c['targetOccurrenceId']),residuals,means)
        candidates.append({'targetOccurrenceId':c['targetOccurrenceId'],'targetElectorateId':c['targetElectorateId'],
            'displayedName':c['displayedName'],'originalAffiliation':c['originalAffiliation'],'ballotGroupKey':c['ballotGroupKey'],
            'active':c['active'],'status':c['status'],'conflict':c['conflict'],'scope':seat['scope'],
            'identityEvidence':edge.get(c['targetOccurrenceId']),'continuous':value,
            'candidateSharesCalculated':False,'maoriRequiresSeparateBaseline':seat['scope']=='maori'})
    seat_records=[{'targetElectorateId':s['targetElectorateId'],'officialName':s['officialName'],'scope':s['scope'],
        'geography':gs[s['targetElectorateId']],'allPredecessorFlows':flows[s['targetElectorateId']],
        'partyInputStatus':'frozen coherent source-party scenario; future national scenario and confirmed target roster still required',
        'slateComplete':s['targetElectorateId'] in snapshot['completeSlateDeclarations'],
        'candidateForecastPermitted':False,'additionalUncertainty':['within_source_party_composition','local_party_error',
            'candidate_feature_transport_error','candidate_residual_error','parameter_and_linkage_uncertainty','incomplete_slate']+
            (['separate_maori_baseline_and_electorate_polling'] if s['scope']=='maori' else [])} for s in frame]
    coverage={'seats':len(frame),'knownCandidates':len(candidates),'completeSlates':sum(s['slateComplete'] for s in seat_records),
        'candidateFeatureSupport':{scope:{n:sum(c['continuous'][n]['supportedWeight']>0 for c in candidates if c['scope']==scope)
            for n in ('S','R','RStrict')} for scope in ('general','maori')},
        'sourcePartySeatSSupport':{scope:sum(r['S']['supportedWeight']>0 for r in source_features if r['scope']==scope) for scope in ('general','maori')},
        'candidatePartialSupport':{n:sum(0<c['continuous'][n]['supportedWeight']<1 for c in candidates if c['scope']=='general') for n in ('S','R','RStrict')}}
    return {'stage':42,'sourceSnapshot':SNAPSHOT,'sourceCutoffUTC':snapshot['acquisitionCutoffUTC'],
        'developmentCenterReference':{'savedFoldId':fold['id'],'trainingOnlyMeans':means,'meaning':'latest saved general training transform reference only, no2026candidate predictions'},
        'candidateRecords':candidates,'sourcePartySeatRecords':source_features,'seatRecords':seat_records,'coverage':coverage,
        'liveForecastProduced':False,'operationalSelection':None,'priorSnapshotsChanged':False,
        'maoriInterface':'national TPM party votes != Maori candidate votes; separate dated question/denominator/polling dependence and unpolled baseline required'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify()
    value=build();save('readiness-2026.json',value,a.check);print(value['coverage'])


if __name__=='__main__':main()
