"""Resumable complete forecasts sealed before evaluation; fixed numerical cap."""
import json
import numpy as np
from scripts.uncertainty_revision.construction import cases
from scripts.uncertainty.construction import national_case,scale_for
from scripts.uncertainty.metrics import crps
from .common import ROOT,PREFIX,INVENTORY,read,save,verify,arguments,signature,digest,encode,equivalent
from .simulation import component,compose,compose_pair
from .streams import permutation
from .metrics import energy
METHODS=('stage45','robust_gaussian','student')


def paths(case_id,count,kind):
    p=ROOT/'.cache/stage46'/signature()/f'{kind}-{case_id.replace(":","-")}-{count}'
    return p.with_suffix('.npz'),p.with_suffix('.json')


def restore(case_id,count,kind):
    archive,manifest=paths(case_id,count,kind)
    if not manifest.exists():return None
    value=json.loads(manifest.read_text())
    if value['signature']!=signature() or value['draws']!=count or value['id']!=case_id:raise ValueError('Incompatible exact cache')
    if digest(str(archive.relative_to(ROOT)))!=value['drawCache']['sha256']:raise ValueError('Corrupt Stage46 draw cache')
    return value


def arrays(case):
    value=restore(case['id'],case['draws'],case['kind'])
    if value is None or not equivalent(value,case):raise ValueError('Construct matching forecasts first')
    return np.load(ROOT/value['drawCache']['path'],allow_pickle=False)


def seal(case_id,count,kind,vectors,metadata):
    archive,manifest=paths(case_id,count,kind);archive.parent.mkdir(parents=True,exist_ok=True)
    if archive.exists():
        with np.load(archive,allow_pickle=False) as old:
            if set(old.files)!=set(vectors) or any(not np.allclose(old[k],vectors[k],rtol=0,atol=1e-10) for k in vectors):raise ValueError('Changed deterministic draws')
    else:
        temporary=archive.with_suffix('.temporary.npz');np.savez_compressed(temporary,**vectors);temporary.replace(archive)
    value={'id':case_id,'draws':count,'kind':kind,'signature':signature(),**metadata,
           'drawCache':{'path':str(archive.relative_to(ROOT)),'sha256':digest(str(archive.relative_to(ROOT)))}}
    manifest.write_bytes(encode(value));return value


def case_build(layer,year,rows,count,kind,scales,parties,regenerate=False):
    cid=f'{layer}:{year}';restored=None if regenerate else restore(cid,count,kind)
    if restored is not None:return restored
    national=None;identifiers=None;provenance=None
    if layer=='composed':
        base,ids,provenance=national_case(year,parties[rows[0]['targetElectorateId']]['ids'],4096)
        order=permutation(4096,f'national:{year}');national=np.tile(base[order],(count//4096,1))
        identifiers={'baseIds':[ids[int(i)] for i in order],'replicas':count//4096,
                     'rule':'draw index i -> national baseIds[i % 4096], local replicate i // 4096',
                     'weight':1/count,'independentNationalScenarios':4096}
    vectors={};records=[]
    for row in rows:
        metadata={}
        paired=None
        if layer=='composed':
            party=parties[row['targetElectorateId']]
            fits={m:scale_for(scales['methods'][m],row['layer'],year)['scales'] for m in METHODS}
            pfits={m:scale_for(scales['methods'][m],'local_party',year)['scales'] for m in METHODS}
            paired=compose_pair(party,row,national,pfits['robust_gaussian'],fits['robust_gaussian'],pfits['student'],fits['student'])
        for method in METHODS:
            fit=scale_for(scales['methods'][method],row['layer'],year)['scales']
            if layer!='composed':q,meta=component(row,fit,count,method)
            elif method=='stage45':q,meta=compose(party,row,national,pfits[method],fits[method],method)
            else:q,meta=paired[method]
            vectors[method+':'+row['targetElectorateId']]=q;metadata[method]=meta
        records.append({'id':row['targetElectorateId'],'metadata':metadata})
    value=seal(cid,count,kind,vectors,{'layer':layer,'year':year,'records':records,'nationalDrawIds':identifiers,
                                     'nationalProvenance':provenance,'outcomesConsumed':False,'meanRefitting':False})
    print('Sealed',kind,cid,count,len(rows),flush=True);return value


def monitored(case,rows):
    result={}
    with arrays(case) as bank:
        for method in METHODS:
            values=[]
            for row in rows:
                q=bank[method+':'+row['targetElectorateId']];y=100*np.array(row['actual'])
                value={'id':row['targetElectorateId'],'meanPP':(100*q.mean(axis=0)).tolist(),
                       'crpsPP':crps(100*q,y).tolist(),'energyPP':[energy(100*q,y,row['targetElectorateId'])['score']]}
                for level in (.5,.8,.9):
                    alpha=1-level;value[f'width{int(level*100)}PP']=(100*(np.quantile(q,1-alpha/2,axis=0)-np.quantile(q,alpha/2,axis=0))).tolist()
                values.append(value)
            result[method]=values
    return result


def convergence(inventory,scales,parties,regenerate=False):
    spec=read(PREFIX+'/specification.json');previous=None;rounds=[];passed=False
    for count in spec['drawCounts']:
        current={}
        for layer,year,rows in cases(inventory):
            chosen=[rows[i] for i in sorted({0,len(rows)//2,len(rows)-1})]
            case=case_build(layer,year,chosen,count,'precision',scales,parties,regenerate)
            current[case['id']]=monitored(case,chosen)
        changes={}
        if previous is not None:
            for field in spec['convergence']:
                changes[field]=max(abs(a-b) for cid in current for method in METHODS
                     for now,old in zip(current[cid][method],previous[cid][method]) for a,b in zip(now[field],old[field]))
            passed=all(changes[k]<=t for k,t in spec['convergence'].items())
        rounds.append({'draws':count,'changes':changes,'passed':passed,'monitored':current})
        if passed:break
        previous=current
    return {'stage':46,'selectedDraws':count,'converged':passed,'capReached':count==spec['capDraws'],'rounds':rounds,
            'status':'precision_gates_passed' if passed else 'cap_used_precision_gates_unmet','noToleranceRelaxation':True}


def build(regenerate=False):
    inventory=read(INVENTORY);scales=read(PREFIX+'/scales.json');parties={r['targetElectorateId']:r for r in inventory['partyRecords']}
    precision=convergence(inventory,scales,parties,regenerate);save('convergence.json',precision,regenerate)
    count=precision['selectedDraws']
    completed=[case_build(layer,year,rows,count,'full',scales,parties,regenerate) for layer,year,rows in cases(inventory)]
    return {'stage':46,'signature':signature(),'draws':count,'precisionStatus':precision['status'],'cases':completed,
            'predictionsSealedBeforeEvaluation':True,'operationalSelection':None}


def main():
    args=arguments();verify();save('construction.json',build(args.check),args.check)
    print('Stage46 complete distributions sealed; no mean or national fitting')


if __name__=='__main__':main()
