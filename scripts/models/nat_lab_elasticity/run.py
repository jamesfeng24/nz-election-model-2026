"""Deterministic Stage6 structural and temporal diagnostics, no forecasts."""
import argparse
import hashlib
import json
from scripts.models.nat_lab_elasticity.records import ROOT,DEST,build as records
from scripts.models.nat_lab_elasticity.model import analyse


def encode(d):return (json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()


def aggregate(rows):
    n=sum(r['n'] for r in rows)
    return sum(r['n']*r['metrics']['maePP'] for r in rows)/n


def sensitivity(backtests):
    result={}
    for party in ['nationalparty','labourparty']:
        result[party]={}
        for baseline in ['actual_observed_local_party','additive','proportional','log_odds']:
            rs=[r for r in backtests if r['party']==party and r['mode']=='chronological' and r['baseline']==baseline]
            scores={m:aggregate([r for r in rs if r['model']==m]) for m in ['no_response','one_for_one','fitted']}
            gains={str(y):next(r['metrics']['maePP'] for r in rs if r['holdoutSourceYear']==y and r['model']=='one_for_one')-next(r['metrics']['maePP'] for r in rs if r['holdoutSourceYear']==y and r['model']=='fitted') for y in [2014,2020]}
            result[party][baseline]={'chronologicalMAEpp':scores,'fittedGainOverOneForOnePP':scores['one_for_one']-scores['fitted'],'gainByHoldoutPP':gains}
    return result


def select(fits,sens):
    result={}
    for party,f in fits.items():
        observed=sens[party]['actual_observed_local_party'];gains=[x['fittedGainOverOneForOnePP'] for x in sens[party].values()]
        stable_gain=all(g>0 for x in sens[party].values() for g in x['gainByHoldoutPP'].values())
        retained=min(gains)>=.25 and stable_gain
        result[party]={'historicalOLS':f['full']['beta'],'status':'retained_historical_elasticity' if retained else 'unresolved_no_stable_material_gain',
            'selectedBeta':f['full']['beta'] if retained else None,'benchmarkBeta':1,
            'transitionBetaRange':[min(x['beta'] for x in f['transitionSpecific'].values()),max(x['beta'] for x in f['transitionSpecific'].values())],
            'minimumAggregateGainAcrossBaselinesPP':min(gains),'allChronologicalHoldoutsImproveAcrossBaselines':stable_gain,
            'reason':'Frozen0.25pp material-gain screen plus consistent holdout/transform improvement; empirical OLS remains descriptive when the screen fails.'}
    return {'schemaVersion':1,'parties':result,'stage5SelectionUnchanged':True,'limitations':['Three transition clusters only; no formal asymptotic standard errors.', 'Candidate changes remain residual noise; coefficient is not an incumbent or person effect.', 'Māori evidence descriptive only; no operational Māori coefficient.', 'No changed-boundary candidate pairs or2026 predictions.'],'nextStage':'Normalized candidate overperformance only'}


def build():
    contract=json.loads((DEST/'input-contract.json').read_bytes())
    for path,h in contract.items():
        if '/2026' in path or any(w in path for w in ['polls/','forecast','opportunity']):raise ValueError('Forbidden input')
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('Changed prior input: '+path)
    d=records()
    if d['inputHashes']!=contract:raise ValueError('Unpinned Stage6 evidence')
    spec=json.loads((DEST/'specification.json').read_bytes())
    if [(t['sourceYear'],t['targetYear']) for t in spec['transitions']]!=[(2008,2011),(2014,2017),(2020,2023)]:raise ValueError('Invalid fitting transition')
    fits,backtests,maori=analyse(d['records']);sens=sensitivity(backtests)
    outputs={'records.json':d,'fits.json':{'schemaVersion':1,'general':fits,'maoriDiagnostics':maori},'backtests.json':{'schemaVersion':1,'records':backtests,'predictionPolicy':'raw linear, no clipping; out-of-range counts reported'},'sensitivity.json':{'schemaVersion':1,'chronological':sens},'selection.json':select(fits,sens)}
    code=sorted([*(ROOT/'scripts/models/nat_lab_elasticity').glob('*.py'),ROOT/'scripts/models/source_provenance.py'])
    outputs['manifest.json']={'schemaVersion':1,'inputHashes':contract,'specificationSha256':hashlib.sha256((DEST/'specification.json').read_bytes()).hexdigest(),'codeHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code},'outputHashes':{p:hashlib.sha256(encode(d)).hexdigest() for p,d in outputs.items()}}
    return outputs


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args();out=build()
    for name,d in out.items():
        raw=encode(d);path=DEST/name
        if args.check:
            if not path.exists() or path.read_bytes()!=raw:raise ValueError('Stale '+name)
        else:path.write_bytes(raw)
    print(json.dumps(out['selection.json']['parties']))

if __name__=='__main__':main()
