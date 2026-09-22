"""Point scores or marginal conservative score enclosures; units percentage points."""
import math
from scripts.models.party_vote_transform.formulas import METHODS


def mean(xs):return sum(xs)/len(xs)


def quantile(xs,p):
    values=sorted(xs);i=(len(xs)-1)*p;lo=int(i);hi=math.ceil(i)
    return values[lo]+(values[hi]-values[lo])*(i-lo)


def metrics(rows,method):
    result={'records':len(rows),'parties':len({r['canonicalPartyId'] for r in rows}),
            'interpretation':'point scores' if all(r['primary'] for r in rows) else 'conservative marginal enclosures; not jointly attainable loss extrema'}
    if not rows:return result
    parties=sorted({r['canonicalPartyId'] for r in rows});total=sum(r['actualTargetPartyVotes'] for r in rows)
    for metric in ['mae','rmse','bias','medianAbsoluteError','p90AbsoluteError','macroPartyMAE','voteWeightedMAE','clippingFrequency']:
        pair=[]
        for suffix in ['Lower','Upper']:
            absolute=[r['predictions'][method]['absoluteError'+suffix] for r in rows]
            if metric=='mae':value=mean(absolute)*100
            elif metric=='rmse':value=math.sqrt(mean([r['predictions'][method]['squaredError'+suffix] for r in rows]))*100
            elif metric=='bias':value=mean([r['predictions'][method]['signedError'+suffix] for r in rows])*100
            elif metric=='medianAbsoluteError':value=quantile(absolute,.5)*100
            elif metric=='p90AbsoluteError':value=quantile(absolute,.9)*100
            elif metric=='macroPartyMAE':value=mean([mean([r['predictions'][method]['absoluteError'+suffix] for r in rows if r['canonicalPartyId']==p]) for p in parties])*100
            elif metric=='voteWeightedMAE':value=sum(v*r['actualTargetPartyVotes'] for v,r in zip(absolute,rows))/total*100 if total else None
            else:value=mean([int(r['predictions'][method]['clippingCertain' if suffix=='Lower' else 'clippingPossible']) for r in rows])
            pair.append(value)
        result[metric]=pair
    return result


def score(rows):return {m:metrics(rows,m) for m in METHODS}


def build_scores(records):
    reports=[]
    transitions=sorted({r['sourceYear'] for r in records})
    for scope in ['general','maori']:
        scoped=[r for r in records if r['electorateType']==scope]
        for evidence in ['primary_observed','all_five']:
            selected=[r for r in scoped if evidence=='all_five' or r['primary']]
            groups={'all_persistent':selected,'national_labour':[r for r in selected if r['canonicalPartyId'] in ['nationalparty','labourparty']],
                    'other_persistent':[r for r in selected if r['canonicalPartyId'] not in ['nationalparty','labourparty']]}
            for threshold in [.005,.01]:groups[f'both_national_at_least_{threshold}']=[r for r in selected if min(r['sourceNationalShare'],r['targetNationalShare'])>=threshold]
            for label,rows in groups.items():reports.append({'scope':scope,'evidence':evidence,'group':label,'scores':score(rows)})
            for year in sorted({r['sourceYear'] for r in selected}):reports.append({'scope':scope,'evidence':evidence,'group':f'leave_out_{year}','scores':score([r for r in selected if r['sourceYear']!=year])})
        for year in transitions:reports.append({'scope':scope,'evidence':'transition','group':str(year),'scores':score([r for r in scoped if r['sourceYear']==year])})
        for party in sorted({r['canonicalPartyId'] for r in scoped}):
            for evidence in ['primary_observed','all_five']:
                reports.append({'scope':scope,'evidence':evidence,'group':'party:'+party,'scores':score([r for r in scoped if r['canonicalPartyId']==party and (evidence=='all_five' or r['primary'])])})
    return reports
