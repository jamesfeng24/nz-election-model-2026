"""Proper scores on original share units; no fitting or calibration choices."""
import numpy as np
from .transforms import validate


def crps(draws, actual):
    """Empirical V-statistic CRPS, including finite-ensemble self pairs."""
    x=np.asarray(draws,dtype=float);y=np.asarray(actual,dtype=float)
    if x.ndim==1:x=x[:,None]
    y=np.atleast_1d(y)
    if x.shape[1]!=len(y) or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):raise ValueError('Invalid score arrays')
    ordered=np.sort(x,axis=0);n=len(x)
    if not n:raise ValueError('Empty score draws')
    pair=np.sum((2*np.arange(1,n+1)-n-1)[:,None]*ordered,axis=0)/(n*n)
    return np.mean(np.abs(x-y),axis=0)-pair


def interval(draws, actual, level):
    if level not in (.5,.9):raise ValueError('Unregistered interval')
    x=np.asarray(draws);y=np.asarray(actual);alpha=1-level
    lower,upper=np.quantile(x,[alpha/2,1-alpha/2],axis=0)
    score=upper-lower+2/alpha*(np.maximum(lower-y,0)+np.maximum(y-upper,0))
    return {'level':level,'lower':np.atleast_1d(lower).tolist(),'upper':np.atleast_1d(upper).tolist(),
        'covered':np.atleast_1d((y>=lower)&(y<=upper)).tolist(),'widths':np.atleast_1d(upper-lower).tolist(),
        'scores':np.atleast_1d(score).tolist()}


def energy(draws, actual, limit=128):
    x=np.asarray(draws,dtype=float)[:limit];y=np.asarray(actual,dtype=float)
    if not len(x) or x.ndim!=2 or x.shape[1]!=len(y):raise ValueError('Invalid energy arrays')
    distance=sum(float(np.linalg.norm(x[i:i+32,None,:]-x[None,:,:],axis=2).sum()) for i in range(0,len(x),32))
    return float(np.mean(np.linalg.norm(x-y,axis=1))-distance/(2*len(x)**2))


def ranking(draws, actual, ids, pair_mean=None):
    q=np.asarray(draws);y=np.asarray(actual);mean=q.mean(axis=0)
    tied=np.abs(q-q.max(axis=1,keepdims=True))<=1e-12
    probabilities=(tied/tied.sum(axis=1,keepdims=True)).mean(axis=0)
    observed=np.flatnonzero(np.abs(y-y.max())<=1e-12)
    if len(observed)==1:
        winner=int(observed[0]);truth=np.zeros(len(y));truth[winner]=1
        p=float(probabilities[winner]);brier=float(np.sum((probabilities-truth)**2));logloss=None if p==0 else float(-np.log(p))
    else:winner=None;p=None;brier=None;logloss=None
    predicted=np.flatnonzero(np.abs(mean-mean.max())<=1e-12)
    selection=mean if pair_mean is None else validate(pair_mean)
    order=sorted(range(len(ids)),key=lambda i:(-selection[i],ids[i]));a,b=order[:2]
    margin_draws=100*(q[:,a]-q[:,b]);margin_actual=100*(y[a]-y[b])
    # A tie has half credit in the prediction-time pair's binary forecast.
    win=float(np.mean((margin_draws>1e-10)+.5*(np.abs(margin_draws)<=1e-10)))
    pair_brier=None if abs(margin_actual)<=1e-10 else (win-float(margin_actual>0))**2
    observed_pairs=[]
    if winner is not None:
        second=max(v for i,v in enumerate(y) if i!=winner)
        runners=[i for i,v in enumerate(y) if i!=winner and abs(v-second)<=1e-12]
        for runner in runners:
            d=100*(q[:,winner]-q[:,runner]);truth_gap=100*(y[winner]-y[runner])
            observed_pairs.append({'ids':[ids[winner],ids[runner]],'absoluteMeanMarginErrorPP':abs(float(d.mean())-truth_gap),
                'crpsPP':float(crps(d,[truth_gap])[0])})
    return {'winnerProbabilities':probabilities.tolist(),'drawTieCount':int(np.sum(tied.sum(axis=1)>1)),
        'uniqueObservedWinner':winner is not None,'observedWinnerProbability':p,'winnerBrier':brier,
        'winnerLogLoss':logloss,'zeroObservedWinnerProbability':p==0 if p is not None else False,
        'uniquePredictedMeanWinner':len(predicted)==1,'meanWinnerCorrect':bool(len(predicted)==1 and winner is not None and predicted[0]==winner),
        'tiedSetIncludesObservedWinner':bool(winner in predicted) if winner is not None else None,
        'predictionTimePair':{'ids':[ids[a],ids[b]],'actualSignedMarginPP':margin_actual,
            'meanSignedMarginPP':float(margin_draws.mean()),'absoluteMarginErrorPP':abs(float(margin_draws.mean())-margin_actual),
            'crpsPP':float(crps(margin_draws,[margin_actual])[0]),'interval50':interval(margin_draws,margin_actual,.5),
            'interval90':interval(margin_draws,margin_actual,.9),'firstBeatsSecondProbability':win,'brier':pair_brier},
        'observedTopTwoEvaluationOnly':observed_pairs}


def record(row,draws,pair_mean=None):
    q=validate(draws);y=validate(row['actual']);mean=q.mean(axis=0);error=100*(mean-y)
    result={'id':row['targetElectorateId'],'name':row['name'],'year':row['targetYear'],'geography':row['geography'],
        'ids':row['ids'],'groups':row['groups'],'denominator':row['denominator'],'actual':y.tolist(),
        'simulatedMean':mean.tolist(),'errorPP':error.tolist(),'maePP':float(np.mean(np.abs(error))),
        'msePP2':float(np.mean(error**2)),'biasPP':float(np.mean(error)),
        'crpsPP':crps(100*q,100*y).tolist(),'interval50':interval(100*q,100*y,.5),
        'interval90':interval(100*q,100*y,.9),'energyPP':energy(100*q,100*y),
        'positiveOutcomeOnMeanZero':int(np.sum((np.array(row['mean'])==0)&(y>0)))}
    if row['layer']=='candidate':result['ranking']=ranking(q,y,row['ids'],pair_mean)
    return result


def distribution_summary(rows):
    result={'coordinates':sum(len(r['ids']) for r in rows),'contests':len(rows),
        'contestEqualMAEPP':float(np.mean([r['maePP'] for r in rows])),
        'contestEqualRMSEPP':float(np.sqrt(np.mean([r['msePP2'] for r in rows]))),
        'candidateCategoryEqualMAEPP':float(np.mean(np.abs([v for r in rows for v in r['errorPP']]))),
        'candidateCategoryEqualRMSEPP':float(np.sqrt(np.mean([v*v for r in rows for v in r['errorPP']]))),
        'fullSlateBiasAccountingPP':float(np.mean([r['biasPP'] for r in rows])),
        'degenerateMeanCRPSReferencePP':float(np.mean([r['maePP'] for r in rows])),
        'contestEqualCRPSPP':float(np.mean([np.mean(r['crpsPP']) for r in rows])),
        'energyPP':float(np.mean([r['energyPP'] for r in rows])),
        'positiveOutcomeOnMeanZero':sum(r['positiveOutcomeOnMeanZero'] for r in rows)}
    for key in ('interval50','interval90'):
        covers=[v for r in rows for v in r[key]['covered']]
        result[key]={'covered':sum(covers),'total':len(covers),'coverage':sum(covers)/len(covers),
            'contestEqualWidthPP':float(np.mean([np.mean(r[key]['widths']) for r in rows])),
            'contestEqualScorePP':float(np.mean([np.mean(r[key]['scores']) for r in rows]))}
    groups={}
    for group in ('national','labour','other','no_group'):
        selected=[(r,i) for r in rows for i,g in enumerate(r['groups']) if g==group]
        if not selected:continue
        errors=np.array([r['errorPP'][i] for r,i in selected])
        groups[group]={'coordinates':len(selected),'containingContests':len({r['id'] for r,i in selected}),
            'weighting':'equal selected category/candidate; not an additive whole-slate decomposition',
            'maePP':float(np.mean(np.abs(errors))),'rmsePP':float(np.sqrt(np.mean(errors**2))),'biasPP':float(np.mean(errors)),
            'crpsPP':float(np.mean([r['crpsPP'][i] for r,i in selected]))}
        for key in ('interval50','interval90'):
            covers=[r[key]['covered'][i] for r,i in selected]
            groups[group][key]={'covered':sum(covers),'total':len(covers),'coverage':sum(covers)/len(covers),
                'widthPP':float(np.mean([r[key]['widths'][i] for r,i in selected])),
                'scorePP':float(np.mean([r[key]['scores'][i] for r,i in selected]))}
    result['groups']=groups
    if 'ranking' in rows[0]:
        eligible=[r['ranking'] for r in rows if r['ranking']['uniqueObservedWinner']]
        logs=[r['winnerLogLoss'] for r in eligible if r['winnerLogLoss'] is not None]
        result['ranking']={'contests':len(eligible),'uniqueMeanWinnerCorrect':sum(r['meanWinnerCorrect'] for r in eligible),
            'predictedMeanTies':sum(not r['uniquePredictedMeanWinner'] for r in eligible),
            'winnerBrier':float(np.mean([r['winnerBrier'] for r in eligible])),
            'zeroWinnerProbabilityCount':sum(r['zeroObservedWinnerProbability'] for r in eligible),
            'finiteWinnerLogLossMean':float(np.mean(logs)) if logs else None,
            'infiniteLogLossCount':sum(r['zeroObservedWinnerProbability'] for r in eligible),
            'forecastPairMarginMAEPP':float(np.mean([r['predictionTimePair']['absoluteMarginErrorPP'] for r in eligible])),
            'forecastPairMarginCRPSPP':float(np.mean([r['predictionTimePair']['crpsPP'] for r in eligible])),
            'forecastPairMarginCoverage90':float(np.mean([r['predictionTimePair']['interval90']['covered'][0] for r in eligible])),
            'observedTopTwoMarginMAEPP':float(np.mean([np.mean([p['absoluteMeanMarginErrorPP'] for p in r['observedTopTwoEvaluationOnly']]) for r in eligible]))}
    return result
