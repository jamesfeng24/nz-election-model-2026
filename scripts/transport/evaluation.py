"""Paired conditional scores only, after the construction checkpoint."""
import argparse
from math import fsum, sqrt
from statistics import mean
from .common import read, save, verify_inputs, preserve, PREFIX


def errors(prediction, target):
    actual={c['id']:c['votes']/target['validCandidateVotes'] for c in target['candidates']}
    if set(actual)!=set(prediction) or abs(fsum(actual.values())-1)>1e-12 or abs(fsum(prediction.values())-1)>1e-12:
        raise ValueError('Complete slate or valid-candidate denominator mismatch')
    values={cid:100*(prediction[cid]-p) for cid,p in actual.items()}
    return {'candidateErrorsPP':values,'contestMaePP':mean(abs(v) for v in values.values()),
            'contestMsePP2':mean(v*v for v in values.values()),'fullSlateBiasPPAccounting':mean(values.values())}


def aggregate(rows):
    if not rows:return None
    vals=[v for r in rows for v in r['candidateErrorsPP'].values()]
    return {'contests':len(rows),'candidates':len(vals),
            'maePP':mean(r['contestMaePP'] for r in rows),'rmsePP':sqrt(mean(r['contestMsePP2'] for r in rows)),
            'candidateEqualMaePP':mean(abs(v) for v in vals),'candidateEqualRmsePP':sqrt(mean(v*v for v in vals)),
            'fullSlateSignedBiasPPAccounting':mean(vals)}


def summary(rows, branches):
    models={b:aggregate([r['errors'][b] for r in rows]) for b in branches}
    pairs={}
    for b in branches:
        if b.startswith('fallback'):continue
        control='fallback_strict' if b.endswith('_strict') else 'fallback'
        effects=[{'targetElectorateId':r['targetElectorateId'],'targetName':r['targetName'],
                  'gainPP':r['errors'][control]['contestMaePP']-r['errors'][b]['contestMaePP']} for r in rows]
        pairs[b]={'fallbackControl':control,'maeGainPP':mean(v['gainPP'] for v in effects) if effects else None,
                  'rmseGainPP':models[control]['rmsePP']-models[b]['rmsePP'] if rows else None,
                  'improved':sum(v['gainPP']>0 for v in effects),'worsened':sum(v['gainPP']<0 for v in effects),
                  'largestFiveAbsoluteEffects':sorted(effects,key=lambda r:(-abs(r['gainPP']),r['targetElectorateId']))[:5],
                  'pairedContests':effects}
    groups={}
    for name in ('national','labour','other_mapped','no_party_group'):
        ids=[c['targetOccurrenceId'] for r in rows for c in r['candidates'] if
             ('national' if c['partyBallotGroupKey']=='nationalparty' else 'labour' if c['partyBallotGroupKey']=='labourparty'
              else 'no_party_group' if c['partyBallotGroupKey'] is None else 'other_mapped')==name]
        methods={}
        for b in branches:
            values=[v for r in rows for cid,v in r['errors'][b]['candidateErrorsPP'].items() if cid in ids]
            methods[b]=None if not values else {'candidateEqualMaePP':mean(abs(v) for v in values),
                'candidateEqualRmsePP':sqrt(mean(v*v for v in values)),'candidateEqualBiasPP':mean(values)}
        groups[name]={'candidates':len(ids),'weighting':'one per member candidate; not additive whole-slate metrics','methods':methods}
    return {'metrics':models,'pairs':pairs,'categoryMetrics':groups}


def build(construction=None, inventory=None, elections=None):
    construction=read(PREFIX+'/construction.json') if construction is None else construction
    inventory=read(PREFIX+'/historical-inventory.json') if inventory is None else inventory
    elections={y:read(f'data/processed/elections/{y}.json') for y in (2014,2020)} if elections is None else elections
    indexed={r['targetElectorateId']:r for r in inventory['records']};folds=[]
    for fold in construction['folds']:
        targets={r['id']:r for r in elections[fold['targetYear']]['electorates']}
        pred={b:{p['targetElectorateId']:p['candidateShares'] for p in ps} for b,ps in fold['predictions'].items()}
        ids=list(next(iter(pred.values())))
        if any(set(v)!=set(ids) for v in pred.values()):raise ValueError('Paired samples differ')
        rows=[]
        for cid in ids:
            original=indexed[cid]
            rows.append({'targetElectorateId':cid,'targetName':targets[cid]['name'],
                'tier':original['transportTier'],'candidates':[{'targetOccurrenceId':c['targetOccurrenceId'],
                    'partyBallotGroupKey':c['partyBallotGroupKey']} for c in original['candidates']],
                'errors':{b:errors(p[cid],targets[cid]) for b,p in pred.items()}})
        samples={'common90':rows,'exact':[r for r in rows if r['tier']=='exact'],
            'approximate95_only':[r for r in rows if r['tier']=='approximate_95'],
            'approximate90_only':[r for r in rows if r['tier']=='approximate_90'],
            'cumulative95':[r for r in rows if r['tier']!='approximate_90']}
        folds.append({'targetYear':fold['targetYear'],'records':rows,'samples':{name:summary(rs,pred.keys()) for name,rs in samples.items()},
            'constructionCoverage':fold['coverage'],'abstentions':[r for r in inventory['fullFrame'] if r['targetYear']==fold['targetYear'] and r['status']!='available']})
    return {'stage':41,'folds':folds,'primaryWeighting':'equal contest within election; folds reported separately',
        'gainSign':'fallback MAE minus transported MAE; positive improvement','operationalSelection':None,
        'information':'conditional observed target local party support; fixed earlier fit; reused development elections'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    verify_inputs();value=build();save('evaluation.json',value,a.check)
    for f in value['folds']:
        s=f['samples']['common90'];print(f['targetYear'],{b:round(x['maePP'],5) for b,x in s['metrics'].items()},
            {b:round(x['maeGainPP'],5) for b,x in s['pairs'].items()})
    print('Prior files unchanged:',preserve())


if __name__=='__main__':main()
