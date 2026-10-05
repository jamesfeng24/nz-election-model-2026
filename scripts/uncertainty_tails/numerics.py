"""Pre-scoring synthetic centre/tail and conditional location verification."""
import numpy as np
from scipy.stats import norm,t
from .common import PREFIX,read,save,verify,arguments
from .integration import conditional_check


def build():
    synthetic=[{'name':'competitive','mean':[.48,.48,.04],'groups':['national','labour','other']},
               {'name':'multi','mean':[.37,.32,.15,.08,.04,.04],'groups':['national','labour','other','other','other','no_group']},
               {'name':'tiny','mean':[.499,.499,.001,.001],'groups':['national','labour','other','other']},
               {'name':'missing_major','mean':[.55,.35,.1],'groups':['national','other','no_group']}]
    scales=read(PREFIX+'/scales.json');reports=[]
    for fold in scales['centralFits']:
        old=next(f for f in scales['methods']['stage45']['folds']['candidate'] if f['targetYear']==fold['targetYear'])['scales']
        total={'balanceShared':old['balance']['shared'],'balanceSeat':fold['studentScale'],
               'balance':float(np.hypot(old['balance']['shared'],fold['studentSD'])),
               'mass':float(np.hypot(old['mass']['shared'],old['mass']['seat'])),
               'within':float(np.hypot(old['within']['shared'],old['within']['seat']))}
        reports.append({'year':fold['targetYear'],'pooledMAD':fold['pooledMAD'],'gaussianSD':fold['gaussianSD'],
                        'studentScale':fold['studentScale'],'studentSD':fold['studentSD'],'nu':4,
                        'seatCentralIntervalsLogBalance':{str(level):{'gaussianWidth':float(2*fold['gaussianSD']*norm.ppf((1+level)/2)),
                           'studentWidth':float(2*fold['studentScale']*t.ppf((1+level)/2,4))} for level in (.5,.8,.9)},
                        'syntheticChecks':[{**r,'checks':conditional_check(r['mean'],r['groups'],total,True)} for r in synthetic]})
    maximum=max(v for f in reports for r in f['syntheticChecks'] for v in r['checks'].values())
    return {'stage':46,'syntheticOnly':True,'scaleAndSDDistinguished':True,'reports':reports,
            'maximumConditionalExpectationGapPP':maximum,'gatePP':.05,'passed':maximum<=.05,
            'failureAction':'report integration limitation; no tolerance, family or mean change'}


def main():
    args=arguments();verify();save('numerics.json',build(),args.check)


if __name__=='__main__':main()
