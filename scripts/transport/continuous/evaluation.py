"""Three paired fixed-prediction policies on identical full historical slates."""
import argparse
from statistics import mean
from math import sqrt
from scripts.transport.evaluation import errors,aggregate
from .common import read,save,verify,PREFIX


def summarize(rows,branches):
    metrics={b:aggregate([r['errors'][b] for r in rows]) for b in branches};pairs={}
    for suffix in ('','_strict'):
        for model,control in (('stage41_90','exact_fallback'),('continuous','exact_fallback'),('continuous','stage41_90')):
            m,c=model+suffix,control+suffix
            effects=[{'targetElectorateId':r['targetElectorateId'],'targetName':r['targetName'],
                'gainPP':r['errors'][c]['contestMaePP']-r['errors'][m]['contestMaePP']} for r in rows]
            pairs[m+'_versus_'+c]={'model':m,'comparator':c,
                'maeGainPP':mean(e['gainPP'] for e in effects) if rows else None,
                'rmseGainPP':metrics[c]['rmsePP']-metrics[m]['rmsePP'] if rows else None,
                'improved':sum(e['gainPP']>0 for e in effects),'worsened':sum(e['gainPP']<0 for e in effects),
                'pairedContests':effects,
                'largestFiveLosses':sorted([e for e in effects if e['gainPP']<0],key=lambda e:(e['gainPP'],e['targetElectorateId']))[:5],
                'largestFiveGains':sorted([e for e in effects if e['gainPP']>0],key=lambda e:(-e['gainPP'],e['targetElectorateId']))[:5]}
    groups={}
    for name in ('national','labour','other_mapped','no_party_group'):
        ids={c['targetOccurrenceId'] for r in rows for c in r['candidates'] if
            ('national' if c['partyBallotGroupKey']=='nationalparty' else 'labour' if c['partyBallotGroupKey']=='labourparty'
             else 'no_party_group' if c['partyBallotGroupKey'] is None else 'other_mapped')==name}
        values={b:[v for r in rows for cid,v in r['errors'][b]['candidateErrorsPP'].items() if cid in ids] for b in branches}
        groups[name]={'candidates':len(ids),'denominator':'equal member candidate, original valid-candidate votes; not additive whole-slate metric',
            'metrics':{b:None if not vs else {'maePP':mean(abs(v) for v in vs),'rmsePP':sqrt(mean(v*v for v in vs)),
                'biasPP':mean(vs)} for b,vs in values.items()}}
    support={}
    for name in ('S','R','RStrict'):
        fs=[c['continuous'][name] for r in rows for c in r['candidates']]
        support[name]={'candidates':len(fs),'positiveSupportedMass':sum(f['supportedWeight']>0 for f in fs),
            'fractionalSupport':sum(0<f['supportedWeight']<1 for f in fs),
            'meanSupportedWeightCandidateEqual':mean(f['supportedWeight'] for f in fs) if fs else None,
            'meanUnsupportedWeightCandidateEqual':mean(f['unsupportedWeight'] for f in fs) if fs else None,
            'meanUnsupportedWeightContestEqual':mean(mean(c['continuous'][name]['unsupportedWeight'] for c in r['candidates']) for r in rows) if rows else None}
    return {'metrics':metrics,'pairs':pairs,'categoryMetrics':groups,'continuousFeatureSupport':support}


def build(construction=None,inv=None,elections=None):
    construction=read(PREFIX+'/construction.json') if construction is None else construction
    inv=read(PREFIX+'/inventory.json') if inv is None else inv
    elections={y:read(f'data/processed/elections/{y}.json') for y in (2014,2020)} if elections is None else elections
    original={r['targetElectorateId']:r for r in inv['records']};folds=[];all_rows=[]
    for fold in construction['folds']:
        targets={s['id']:s for s in elections[fold['targetYear']]['electorates']}
        ps={b:{p['targetElectorateId']:p['candidateShares'] for p in preds} for b,preds in fold['predictions'].items()}
        ids=list(next(iter(ps.values())))
        if any(list(v)!=ids for v in ps.values()):raise ValueError('Paired policy IDs differ')
        rows=[dict(original[cid],targetName=targets[cid]['name'],
            errors={b:errors(p[cid],targets[cid]) for b,p in ps.items()}) for cid in ids]
        samples={'full':rows,**{tier:[r for r in rows if r['transportTier']==tier] for tier in ('exact','approximate_95','approximate_90','fallback')}}
        samples['stage41_common90']=[r for r in rows if r['transportTier']!='fallback']
        folds.append({'targetYear':fold['targetYear'],'records':rows,'samples':{name:summarize(rs,ps) for name,rs in samples.items()},
            'exclusions':[r for r in inv['fullFrame'] if r['targetYear']==fold['targetYear'] and r['status']!='available']})
        all_rows.extend(rows)
    return {'stage':42,'folds':folds,'pooled':summarize(all_rows,next(iter(construction['folds']))['predictions']),
        'pooledWeighting':'one weight per complete contest; election weights64/129 and65/129, not two independent seat replications',
        'gainSign':'comparator MAE minus policy MAE; positive lower error','operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify()
    value=build();save('evaluation.json',value,a.check)
    for f in value['folds']:print(f['targetYear'],{b:round(m['maePP'],5) for b,m in f['samples']['full']['metrics'].items()})


if __name__=='__main__':main()
