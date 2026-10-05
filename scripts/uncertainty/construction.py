"""Save uncertainty draws/metadata before any held-out evaluation."""
import hashlib
import numpy as np
from .common import *
from .simulation import component,compose
from .streams import national_indices


def scale_for(scales,layer,year):
    return next(f for f in scales['folds'][layer] if f['targetYear']==year)


def national_case(year, party_ids, draws):
    national=read(f'data/processed/polling/candidate-integration/national/{year}-recent_report_prior.json.gz')
    if set(national['categories'])!=set(party_ids):raise ValueError('National fine-group schema differs')
    indices=national_indices(national['fineChainShape'],draws)
    columns=[national['categories'].index(i) for i in party_ids]
    return np.array(national['arrays'])[indices][:,columns],[national['drawIds'][i] for i in indices],{
        'cutoff':national['cutoff'],'horizonDays':national['horizonDays'],'system':national['system'],
        'availability':national['availability'],'sourceAttribution':national['sourceAttribution'],
        'forecastTarget':national['forecastTarget'],'sourceVersion':national['version']}


def signature():
    paths=[str(p.relative_to(ROOT)) for p in sorted((ROOT/'scripts/uncertainty').glob('*.py')) if p.stem in ('common','inventory','transforms','estimation','streams','simulation','construction')]
    return hashlib.sha256(encode({'inputs':read(PREFIX+'/input-contract.json'),'specification':digest(PREFIX+'/specification.json'),
        'inventory':digest(PREFIX+'/inventory.json'),'scales':digest(PREFIX+'/scales.json'),
        'code':{p:digest(p) for p in paths},'numpy':np.__version__,'draws':DRAWS,'seed':SEED})).hexdigest()


def restore_case(case_id, run_signature):
    path=f'.cache/stage44/{run_signature}/{case_id.replace(":","-")}-manifest.json'
    if not (ROOT/path).exists():return None
    value=read(path)
    if digest(value['drawCache']['path'])!=value['drawCache']['sha256']:
        raise ValueError('Corrupt exact-signature draw cache')
    return value


def checkpoint(value,run_signature):
    path=ROOT/f'.cache/stage44/{run_signature}/{value["id"].replace(":","-")}-manifest.json'
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encode(value))
    return value


def build(regenerate=False):
    inv=read(PREFIX+'/inventory.json');scales=read(PREFIX+'/scales.json');cases=[];run_signature=signature()
    for layer,key in (('local_party','partyRecords'),('candidate','candidateRecords')):
        for year in YEARS:
            rows=[r for r in inv[key] if r['targetYear']==year]
            if not rows:continue
            existing=None if regenerate else restore_case(f'{layer}:{year}',run_signature)
            if existing is not None:cases.append(existing);continue
            fitted=scale_for(scales,layer,year);records=[];archive={}
            for row in rows:
                q,metadata=component(row,fitted['scales'],DRAWS)
                cid=row['targetElectorateId'];archive[cid]=q.tolist()
                record={'id':cid,'metadata':metadata}
                if layer=='candidate':
                    if row['geography']=='exact':qs,ms=q,metadata
                    else:qs,ms=component(row,fitted['scales'],DRAWS,True)
                    archive[cid+':transport_stress']=qs.tolist();record['transportStressMetadata']=ms
                records.append(record)
            info=cache(f'{run_signature}/{layer}-{year}.json.gz',{'drawIds':[f'stage44:{layer}:{year}:{i}' for i in range(DRAWS)],'vectors':archive})
            cases.append(checkpoint({'id':f'{layer}:{year}','layer':layer,'year':year,'records':records,
                'scaleFit':fitted,'drawCache':info,'outcomesConsumed':False},run_signature))
    parties={r['targetElectorateId']:r for r in inv['partyRecords']}
    for year in (2017,2020,2023):
        existing=None if regenerate else restore_case(f'composed:{year}',run_signature)
        if existing is not None:cases.append(existing);continue
        rows=[r for r in inv['candidateRecords'] if r['targetYear']==year]
        archive={};records=[]
        pscale=scale_for(scales,'local_party',year);cscale=scale_for(scales,'candidate',year)
        national,ids,provenance=national_case(year,parties[rows[0]['targetElectorateId']]['ids'],DRAWS)
        for row in rows:
            cid=row['targetElectorateId'];party=parties[cid]
            q,m=compose(party,row,national,pscale['scales'],cscale['scales']);archive[cid]=q.tolist()
            record={'id':cid,'metadata':m}
            if row['geography']=='exact':qs,ms=q,m
            else:qs,ms=compose(party,row,national,pscale['scales'],cscale['scales'],True)
            archive[cid+':transport_stress']=qs.tolist();record['transportStressMetadata']=ms;records.append(record)
        info=cache(f'{run_signature}/composed-{year}.json.gz',{'drawIds':ids,'vectors':archive})
        cases.append(checkpoint({'id':f'composed:{year}','layer':'composed','year':year,'records':records,'drawCache':info,
            'partyScaleFit':pscale,'candidateScaleFit':cscale,'nationalProvenance':provenance,
            'drawsSharedAcrossEverySeat':True,'outcomesConsumed':False},run_signature))
    return {'stage':44,'signature':signature(),'cases':cases,'cacheReconstruction':'deterministic; no MCMC',
        'meanFittingPerformed':False,'operationalSelection':None}


def main():
    args=arguments();verify();result=build(regenerate=args.check);save('construction.json',result,args.check)
    print('Stage44 draws sealed',[(c['id'],len(c['records'])) for c in result['cases']])


if __name__=='__main__':main()
