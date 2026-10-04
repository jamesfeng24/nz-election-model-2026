"""Cutoff-first poll/anchor adapters, independent of held-out outcomes."""
from datetime import date,timedelta
import numpy as np
from scripts.polling.national_foundation.timing import select,day_end,timestamp
from .common import FOUNDATION,ORDER,read,schema,digest
from .transforms import helmert,bridge_factor

DATES={2011:'2011-11-26',2014:'2014-09-20',2017:'2017-09-23',2020:'2020-10-17',2023:'2023-10-14'}
MINORS={'UNF','NCP','MNA','INT','INM'}


def interval_rows(r,categories):
    """One operator per named party; one supported lower-censored Other row."""
    rows=[];factor=1.;reason=None
    if r['denominator']=='all_respondents':
        nonresponse=r.get('nonresponseCombined')
        if nonresponse is None:return [],'all_respondent_denominator_unresolved'
        factor=1-nonresponse
        if not 0<factor<=1:return [],'invalid_decided_fraction'
    for p in categories:
        obs=r['estimates'].get(p)
        if obs and obs['bounds'] is not None:
            rows.append({'category':p,'lower':obs['bounds'][0]/factor,'upper':min(1,obs['bounds'][1]/factor),'kind':obs['status']})
    # No preserved historically verified exclusive-Other definition exists.
    minor=r['additionalPublishedCategories'];positive={p for p,o in minor.items() if p in MINORS and o['bounds'] and o['bounds'][0]>0}
    if 'INM' in positive and positive&{'MNA','INT'}:reason='overlapping_alliance_minor_aggregate_unavailable'
    else:
        lower=sum(minor[p]['bounds'][0] for p in positive)/factor
        if lower>0:rows.append({'category':'OTH','lower':lower,'upper':None,'kind':'supported_minor_lower_censor'})
    if sum(x['lower'] for x in rows)>1+1e-12:return [],'incompatible_row_lower_sum'
    return rows,reason


def initial_shares(previous,categories):
    s=np.array([previous['shares'][p] for p in categories],float)
    if 'TOP' not in categories:s[-1]+=previous['shares'].get('TOP',0)
    entrants=[]
    if 'TOP' in categories and previous['year']<2017:
        i=categories.index('TOP');s[i]=.002;s[-1]-=.002;entrants.append(i)
    if np.any(s<=0) or abs(sum(s)-1)>1e-10:raise ValueError('Unsupported starting simplex')
    h=helmert(len(s));v=np.full(len(s),.01**2);v[entrants]=1.
    return {'shares':s.tolist(),'mean':(h.T@np.log(s)).tolist(),
            'factor':np.linalg.cholesky(h.T@np.diag(v)@h).tolist(),'entrants':[categories[i] for i in entrants]}


def cycle_data(year,end,polls,previous,endpoint,missing_n):
    categories=schema(year);start=date.fromisoformat(DATES[previous['year']]);endday=date.fromisoformat(end[:10]);last=(endday-start).days
    if last<=0:raise ValueError('Cycle ordering')
    nodes=list(range(0,last,7))+[last];nodes=np.array(nodes,float)
    rows=[];wave=[];days=[];exclusions=[]
    for r in sorted(polls,key=lambda r:r['id']):
        operators,reason=interval_rows(r,categories)
        if not operators:exclusions.append({'id':r['id'],'reason':reason or 'no_modelled_observations'});continue
        first=date.fromisoformat(r['fieldworkStartBounds'][0]);finish=date.fromisoformat(r['fieldworkEndBounds'][1])
        offsets=[(first+timedelta(days=i)-start).days-.5 for i in range((finish-first).days+1)]
        if min(offsets)<0 or max(offsets)>last:exclusions.append({'id':r['id'],'reason':'fieldwork_outside_cycle'});continue
        idx=len(wave);fraction=1-r['nonresponseCombined'] if r.get('nonresponseCombined') is not None else .85
        if not 0<fraction<=1:raise ValueError('Decided fraction')
        wave.append({'id':r['id'],'pollster':r['pollsterCode'],'segment':r['methodSegment'],'nDecided':(r['sampleSize'] or missing_n)*fraction,'source':r['provenance'],'publicationQuality':r['publicationConfidence'],'fieldEnd':r['fieldworkEndBounds'][1]})
        for x in offsets:
            hi=min(np.searchsorted(nodes,x,side='right'),len(nodes)-1);lo=hi-1
            days.append({'poll':idx,'lo':int(lo),'hi':int(hi),'fraction':float((x-nodes[lo])/(nodes[hi]-nodes[lo])),'weight':1/len(offsets)})
        for op in operators:rows.append({'poll':idx,'index':categories.index(op['category']),**op})
        if reason:exclusions.append({'id':r['id'],'reason':reason,'onlyMinorAggregateExcluded':True})
    ep=None
    if endpoint is not None:
        ep=[endpoint['shares'][p] for p in categories]
        if 'TOP' not in categories:ep[-1]+=endpoint['shares'].get('TOP',0)
    return {'year':year,'categories':categories,'start':start.isoformat(),'end':end,'nodes':nodes.tolist(),
            'bridgeFactor':bridge_factor(nodes[1:]).tolist(),'initial':initial_shares(previous,categories),
            'polls':wave,'days':days,'rows':rows,'endpointShares':ep,'excluded':exclusions}


def prepare(year,horizon,branch='primary',polls=None,results=None):
    polls=read(FOUNDATION/'polls.json')['records'] if polls is None else polls
    results=read(FOUNDATION/'official-results-isolated.json')['records'] if results is None else results
    cutoff=day_end((date.fromisoformat(DATES[year])-timedelta(days=horizon)).isoformat()).isoformat()
    lag=10 if branch=='publication_lag10' else 5
    selected,excluded=select(polls,cutoff,lag,branch=='verified_only')
    # Filter before any access to result shares; even corrupt future results are invisible.
    anchors={r['year']:r for r in results if r['year']<year and timestamp(r['availableAt'])<=timestamp(cutoff) and timestamp(r['electionAt'])<timestamp(cutoff)}
    cycles=[]
    for cy in (2014,2017,2020,2023):
        if cy>year:continue
        previous_year={2014:2011,2017:2014,2020:2017,2023:2020}[cy]
        if previous_year not in anchors:raise ValueError('Missing earlier initial anchor')
        endpoint=anchors.get(cy) if cy<year else None
        if cy<year and endpoint is None:raise ValueError('Missing earlier endpoint anchor')
        end=day_end(DATES[cy]).isoformat() if cy<year else cutoff
        cycles.append(cycle_data(cy,end,[r for r in selected if r['cycle']==cy],anchors[previous_year],endpoint,1000 if branch=='missing_n1000' else 750))
    current_count=len(cycles[-1]['polls'])
    roster=sorted({r['pollster'] for c in cycles for r in c['polls']})
    return {'id':f'{branch}-{year}-{horizon}','branch':branch,'year':year,'horizonDays':horizon,'cutoff':cutoff,
            'electionDate':DATES[year],'schema':schema(year),'cycles':cycles,'pollsterRoster':roster,
            'permittedAnchorYears':sorted(anchors),'excluded':excluded,
            'status':'ready' if current_count else 'data_abstention','reason':None if current_count else 'no_usable_current_cycle_poll',
            'informationSet':'retrospective source snapshot; verified dates plus inferred publication assumptions; oracle earlier results only'}
