"""Descriptive shape audit: saved shared effects, no new predictive fitting."""
import numpy as np
from scipy.stats import norm
from scripts.uncertainty_revision.coordinates import coordinates, partition
from scripts.uncertainty_revision.estimation import labels
from .common import PREFIX, CONTROL, INVENTORY, read, verify, save, arguments

QUANTILES = [.01, .025, .05, .1, .25, .5, .75, .9, .95, .975, .99]


def weighted_quantile(values, weights, probabilities):
    x, w = np.asarray(values, float), np.asarray(weights, float)
    if len(x) == 0 or x.shape != w.shape or not np.isfinite(x).all() or not np.isfinite(w).all() or np.any(w <= 0):
        raise ValueError('Invalid descriptive weighted records')
    order = np.argsort(x, kind='stable'); x, w = x[order], w[order]
    cdf = np.cumsum(w)/w.sum()
    return x[np.minimum(np.searchsorted(cdf, probabilities), len(x)-1)]


def top_squared_fraction(x, w, fraction):
    order = np.argsort(-np.abs(x), kind='stable'); x, w = x[order], w[order]/w.sum()
    before = np.cumsum(w)-w
    take = np.minimum(w, np.maximum(0., fraction-before))
    total = np.sum(w*x*x)
    return float(np.sum(take*x*x)/total) if total else None


def summary(records, pooled=False):
    if not records: return {'status':'unavailable'}
    years = sorted({r['year'] for r in records})
    weights = np.array([r['weight'] for r in records], float)
    for year in years:
        ix = np.array([r['year']==year for r in records])
        weights[ix] /= weights[ix].sum()
    weights /= weights.sum()
    x = np.array([r['seatResidual'] for r in records]); median = float(weighted_quantile(x, weights, [.5])[0])
    absolute = np.abs(x-median); mad = float(weighted_quantile(absolute, weights, [.5])[0])
    rms = float(np.sqrt(np.sum(weights*x*x)))
    result = {'records':len(records),'contests':len({r['id'] for r in records}), 'environments':len(years),
              'weighting':'equal elections, seats within elections, normalized coordinates within seat',
              'median':median, 'mean':float(np.sum(weights*x)), 'rms':rms, 'mad':mad,
              'gaussianEquivalentMAD':mad/float(norm.ppf(.75)),
              'centralScaleToRMS':mad/float(norm.ppf(.75))/rms if rms else None,
              'quantiles':dict(zip(map(str, QUANTILES), weighted_quantile(x,weights,QUANTILES).tolist())),
              'absoluteQuantiles':dict(zip(map(str,[.5,.8,.9,.95,.99]),weighted_quantile(absolute,weights,[.5,.8,.9,.95,.99]).tolist())),
              'largestSquaredFractions':{str(f):top_squared_fraction(x,weights,f) for f in (.01,.05,.1)},
              'noObservationsRemoved':True}
    z = np.array([r['seatResidual']/r['electionRMS'] if r['electionRMS'] else 0 for r in records])
    prior_z = np.array([r['seatResidual']/r['earlierSeatSD'] for r in records])
    result['gaussianChecks'] = {'referenceCentreHalfSD':float(norm.cdf(.5)-norm.cdf(-.5)),
        'empiricalCentreHalfElectionRMS':float(np.sum(weights*(np.abs(z)<.5))),
        'referenceBeyondThreeSD':float(2*norm.sf(3)),
        'empiricalBeyondThreeElectionRMS':float(np.sum(weights*(np.abs(z)>3))),
        'conditionalSharedEffectWasRemovedDescriptively':True,
        'earlierGaussianSeatCoverage':{str(level):float(np.sum(weights*(np.abs(prior_z)<=norm.ppf((1+level)/2)))) for level in (.5,.8,.9)}}
    result['influential'] = sorted(records,key=lambda r:(-abs(r['seatResidual']),r['id'],r['option']))[:8]
    return result


def residual_records(rows, moments, fold):
    out = {name:[] for name in ('balance','mass','within')}
    for row in rows:
        actual, mean = coordinates(row['actual'],row['groups']), coordinates(row['mean'],row['groups'])
        for name in ('balance','mass'):
            if actual[name] is None or mean[name] is None: continue
            raw = float(actual[name]-mean[name]); shared = moments[name]['descriptiveElectionEffect']
            out[name].append({'id':row['targetElectorateId'],'name':row['name'],'year':row['targetYear'],
                'option':name,'rawResidual':raw,'sharedResidual':shared,'seatResidual':raw-shared,'weight':1.,
                'electionRMS':float(np.sqrt(moments[name]['seat'])), 'earlierSeatSD':fold['scales'][name]['seat'],
                'geography':row['geography'],'stratum':'all scalar seats'})
        if actual['within'] is None or mean['within'] is None: continue
        indices = partition(row['groups'])[2]; tags=labels(row); count=len(indices)
        effects = moments['within'].get('classEffects',{})
        shared = np.array([effects.get(tags[i],0.) for i in indices]); shared -= shared.mean()
        raw=actual['within']-mean['within']; left=raw-shared; correction=np.sqrt(count/(count-1))
        for j,i in enumerate(indices):
            out['within'].append({'id':row['targetElectorateId'],'name':row['name'],'year':row['targetYear'],
                'option':row['ids'][i], 'ballotGroup':tags[i], 'stratum':tags[i], 'group':row['groups'][i],
                'rawResidual':float(correction*raw[j]),'sharedResidual':float(correction*shared[j]),
                'seatResidual':float(correction*left[j]),'weight':1/count,
                'electionRMS':float(np.sqrt(moments['within']['seat'])),
                'earlierSeatSD':fold['scales']['within']['seat'],'geography':row['geography']})
    return out


def heterogeneity(records):
    # Descriptive only. Every row remains, including small strata with pooled fallback.
    strata = {(r['year'],r['stratum']) for r in records}; scaled=[]
    for key in sorted(strata):
        rows=[r for r in records if (r['year'],r['stratum'])==key]
        sigma=float(np.sqrt(np.mean([r['seatResidual']**2 for r in rows]))) if len(rows)>=8 else None
        for row in rows:
            sd=sigma or row['electionRMS']
            scaled.append({**row,'seatResidual':row['seatResidual']/sd if sd else 0.,
                           'electionRMS':1.,'earlierSeatSD':1.})
    return {'rule':'within election and preserved group, n>=8 descriptive RMS; otherwise election RMS; not a variance model',
            'standardized':summary(scaled),
            'strata':{str(key):summary([r for r in records if (r['year'],r['stratum'])==key]) for key in sorted(strata)}}


def build():
    inventory,scales=read(INVENTORY),read(CONTROL+'/scales.json'); result={}
    for layer,key in (('local_party','partyRecords'),('candidate','candidateRecords')):
        all_records={name:[] for name in ('balance','mass','within')}; by_year={}
        for env in scales['descriptive'][layer]['moments']:
            year=env['year'];rows=[r for r in inventory[key] if r['targetYear']==year]
            fold=next(f for f in scales['folds'][layer] if f['targetYear']==year)
            records=residual_records(rows,env['moments'],fold)
            by_year[str(year)]={}
            for name,values in records.items():
                all_records[name]+=values
                s=summary(values)
                if values:
                    denominator=sum(r['weight']*r['rawResidual']**2 for r in values)
                    s['sharedFractionOfRawSquaredMagnitude']=sum(r['weight']*r['sharedResidual']**2 for r in values)/denominator if denominator else None
                by_year[str(year)][name]=s
        result[layer]={'byElection':by_year,'pooled':{name:summary(rows,True) for name,rows in all_records.items()},
            'geography':{name:{g:summary([r for r in rows if r['geography']==g]) for g in sorted({r['geography'] for r in rows})} for name,rows in all_records.items()},
            'withinHeterogeneity':heterogeneity(all_records['within']), 'records':all_records}
    return {'stage':46,'purpose':'descriptive residual-shape diagnosis, no new uncertainty fits or forecast scores',
            'savedSharedEffects':'Stage45 full-panel per-election decomposition; descriptive, not available at held-out prediction time',
            'layers':result,'retainedAllObservations':True,'operationalSelection':None}


def main():
    args=arguments();verify();save('diagnosis.json',build(),args.check)
    print('Stage46 residual centre/tails audited; no new predictive fit or score')


if __name__=='__main__':main()
