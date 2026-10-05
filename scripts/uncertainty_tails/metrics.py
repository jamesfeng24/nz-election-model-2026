"""Three registered interval levels and bounded reproducible complete-vector scores."""
import numpy as np
from scripts.uncertainty.metrics import crps,record as original_record,distribution_summary
from .streams import permutation


def interval(draws,actual,level):
    if level not in (.5,.8,.9):raise ValueError('Unregistered interval')
    x=np.asarray(draws);y=np.asarray(actual);alpha=1-level
    lower,upper=np.quantile(x,[alpha/2,1-alpha/2],axis=0)
    score=upper-lower+2/alpha*(np.maximum(lower-y,0)+np.maximum(y-upper,0))
    return {'level':level,'lower':np.atleast_1d(lower).tolist(),'upper':np.atleast_1d(upper).tolist(),
        'covered':np.atleast_1d((y>=lower)&(y<=upper)).tolist(),'widths':np.atleast_1d(upper-lower).tolist(),'scores':np.atleast_1d(score).tolist()}


def energy(draws,actual,key):
    x=np.asarray(draws,float);y=np.asarray(actual,float);first=np.linalg.norm(x-y,axis=1).mean()
    scores=[]
    for repeat in (0,1):
        order=permutation(len(x),f'{key}:energy:{repeat}');pair=np.roll(order,1)
        scores.append(float(first-.5*np.linalg.norm(x[order]-x[pair],axis=1).mean()))
    return {'score':float(np.mean(scores)),'pairEstimates':scores,'pairDifference':abs(scores[0]-scores[1]),
            'pairsPerEstimate':len(x),'selfPairs':False,'approximation':'two outcome-independent permutation-cycle U-statistic pair estimates'}


def record(row,q,point):
    result=original_record(row,q,point)
    result['interval80']=interval(100*q,100*np.array(row['actual']),.8)
    e=energy(100*q,100*np.array(row['actual']),row['targetElectorateId'])
    result['energyPP']=e['score'];result['energyPrecision']=e
    if 'ranking' in result:
        pair=result['ranking']['predictionTimePair']['ids'];a,b=[row['ids'].index(i) for i in pair]
        result['ranking']['predictionTimePair']['interval80']=interval(100*(q[:,a]-q[:,b]),100*(row['actual'][a]-row['actual'][b]),.8)
    return result


def summarize(rows):
    result=distribution_summary(rows)
    covers=[v for r in rows for v in r['interval80']['covered']]
    result['interval80']={'covered':sum(covers),'total':len(covers),'coverage':sum(covers)/len(covers),
                         'contestEqualWidthPP':float(np.mean([np.mean(r['interval80']['widths']) for r in rows])),
                         'contestEqualScorePP':float(np.mean([np.mean(r['interval80']['scores']) for r in rows]))}
    for group,value in result['groups'].items():
        selected=[(r,i) for r in rows for i,g in enumerate(r['groups']) if g==group]
        covers=[r['interval80']['covered'][i] for r,i in selected]
        value['interval80']={'covered':sum(covers),'total':len(covers),'coverage':sum(covers)/len(covers),
                            'widthPP':float(np.mean([r['interval80']['widths'][i] for r,i in selected])),
                            'scorePP':float(np.mean([r['interval80']['scores'][i] for r,i in selected]))}
    result['maximumEnergyPairDifferencePP']=max(r['energyPrecision']['pairDifference'] for r in rows)
    return result
