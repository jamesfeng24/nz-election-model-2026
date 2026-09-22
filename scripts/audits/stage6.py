"""Bounded exploratory architecture audit; never replaces frozen Stage6 outputs."""
import hashlib
import json
import numpy as np
from scripts.boundaries.census_2013 import ROOT
from scripts.transform.historical import key


def run():
    path=ROOT/'data/processed/models/nat-lab-elasticity/records.json';raw=path.read_bytes()
    records=json.loads(raw)['records'];result={}
    elections={y:json.loads((ROOT/f'data/processed/elections/{y}.json').read_bytes()) for y in [2008,2011,2014,2017,2020,2023]}
    def fit(rows,intercept=False,weights=None):
        x=np.array([r['deltaParty'] for r in rows]);y=np.array([r['deltaCandidate'] for r in rows]);w=np.ones(len(x)) if weights is None else np.array(weights)
        X=np.column_stack([np.ones(len(x)),x]) if intercept else x[:,None]
        b=np.linalg.lstsq(X*np.sqrt(w[:,None]),y*np.sqrt(w),rcond=None)[0]
        return (float(b[0]),float(b[1])) if intercept else (0.,float(b[0]))
    for party in ['nationalparty','labourparty']:
        rs=[r for r in records if r['scope']=='general' and r['party']==party];x=np.array([r['deltaParty'] for r in rs]);y=np.array([r['deltaCandidate'] for r in rs]);a,b=fit(rs);af,bf=fit(rs,True)
        centered=[];alphas={}
        for yr in [2008,2014,2020]:
            sub=[r for r in rs if r['sourceYear']==yr];mx=np.mean([r['deltaParty'] for r in sub]);my=np.mean([r['deltaCandidate'] for r in sub]);centered.extend([(r['deltaParty']-mx,r['deltaCandidate']-my) for r in sub]);alphas[yr]=(mx,my)
        fe=sum(x*y for x,y in centered)/sum(x*x for x,y in centered)
        weights=[];denominator_effect=[]
        for r in rs:
            pair=[]
            for year in [r['sourceYear'],r['targetYear']]:
                e=next(e for e in elections[year]['electorates'] if key(e['name'])==key(r['electorateName']))
                c=next(c for c in e['candidates'] if c['partyKey']==party)
                pair.append(c['votes']/e['validPartyVotes']-c['share'])
            weights.append(e['validCandidateVotes']);denominator_effect.append(abs(pair[1]-pair[0])*100)
        chrono={}
        for yr in [2014,2020]:
            train=[r for r in rs if r['sourceYear']<yr];test=[r for r in rs if r['sourceYear']==yr]
            chrono[yr]={}
            for label,params in [('zero',fit(train)),('common_intercept',fit(train,True)),('beta1',(0.,1.))]:
                aa,bb=params;err=np.array([aa+bb*r['deltaParty']-r['deltaCandidate'] for r in test])
                chrono[yr][label]={'alpha':aa,'beta':bb,'maePP':float(np.mean(abs(err))*100),'rmsePP':float(np.sqrt(np.mean(err**2))*100)}
        residual=y-b*x
        result[party]={'zeroBeta':b,'commonIntercept':{'alphaPP':af*100,'beta':bf},'transitionInterceptDiagnostic':{'beta':fe,'alphaPP':{str(yr):float((my-fe*mx)*100) for yr,(mx,my) in alphas.items()},'unseenInterceptPolicy':'Not forecastable without a separately validated prior; no holdout outcome used to set alpha.'},
            'targetCandidateVoteWeightedBeta':fit(rs,weights=weights)[1], 'transitionBalancedBeta':fit(rs,weights=[1/sum(q['sourceYear']==r['sourceYear'] for q in rs) for r in rs])[1],
            'residualCorrelations':{k:float(np.corrcoef(residual,[r[k] for r in rs])[0,1]) for k in ['sourceCandidateShare','sourcePartyShare']},
            'denominatorConventionDeltaDifferencePP':{'median':float(np.median(denominator_effect)),'p90':float(np.quantile(denominator_effect,.9)),'max':max(denominator_effect)},'chronological':chrono}
    return {'status':'exploratory_not_model_selection','inputRecordsSha256':hashlib.sha256(raw).hexdigest(), 'inputElectionHashes':{str(y):hashlib.sha256((ROOT/f'data/processed/elections/{y}.json').read_bytes()).hexdigest() for y in elections},'results':result,'limitations':['Only three transitions; intercept diagnostics are not causal identification.','Residual/source-level correlation in change models may contain mechanical regression-to-mean and omitted candidate effects.','No person linkage or candidate effect estimated.']}

if __name__=='__main__':
    result=run();(ROOT/'docs/audits/stage6-exploratory.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['results'],indent=2))
