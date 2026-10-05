"""Independent scalar arithmetic over cached features/predictions; no fitting."""
import argparse
from fractions import Fraction
from math import exp,fsum,sqrt
from statistics import mean
from .common import read,save,verify,PREFIX


def check():
    inv=read(PREFIX+'/inventory.json');construction=read(PREFIX+'/construction.json');evaluation=read(PREFIX+'/evaluation.json')
    features=0;vectors=0;identities=0
    for row in inv['records']:
        fold=next(f for f in construction['folds'] if f['targetYear']==row['targetYear'])
        means=fold['trainingOnlyMeans'];fit=fold['savedFit']['parameters']
        for c in row['candidates']:
            for name,f in c['continuous'].items():
                mass=sum((Fraction(p['partyMassExact']) for p in f['components']),Fraction(0))
                value=fsum(float(Fraction(p['partyMassExact'])/mass)*(p['valueFraction']-means['S' if name=='S' else 'R'])
                    for p in f['components'] if mass>0 and p['valueFraction'] is not None)
                if abs(value-f['contribution'])>1e-12:raise ValueError('Independent centered feature mismatch')
                support=sum((Fraction(p['partyMassExact'])/mass for p in f['components'] if mass>0 and p['valueFraction'] is not None),Fraction(0))
                if abs(float(support)-f['supportedWeight'])>1e-12:raise ValueError('Independent support weight mismatch')
                features+=1
        for branch,predictions in fold['predictions'].items():
            p=next(p for p in predictions if p['targetElectorateId']==row['targetElectorateId'])
            values=[]
            for c in row['candidates']:
                z=p['centeredContributions'][c['targetOccurrenceId']]
                values.append((c['observedPartySupport']+fit['kappa'])*exp(fsum(t*x for t,x in zip(fit['theta'],z))))
            expected=[v/fsum(values) for v in values]
            if max(abs(q-p['candidateShares'][c['targetOccurrenceId']]) for c,q in zip(row['candidates'],expected))>1e-12:
                raise ValueError('Independent prediction mismatch')
            vectors+=1
    for fold in evaluation['folds']:
        targets={s['id']:s for s in read(f"data/processed/elections/{fold['targetYear']}.json")['electorates']}
        raw=next(f for f in construction['folds'] if f['targetYear']==fold['targetYear'])
        maes={};mses={}
        for branch,ps in raw['predictions'].items():
            vals=[];squares=[]
            for p in ps:
                t=targets[p['targetElectorateId']]
                errors=[100*(p['candidateShares'][c['id']]-c['votes']/t['validCandidateVotes']) for c in t['candidates']]
                vals.append(sum(abs(v) for v in errors)/len(errors));squares.append(sum(v*v for v in errors)/len(errors))
            maes[branch]=sum(vals)/len(vals);mses[branch]=sqrt(sum(squares)/len(squares))
            metric=fold['samples']['full']['metrics'][branch]
            if abs(maes[branch]-metric['maePP'])>1e-12 or abs(mses[branch]-metric['rmsePP'])>1e-12:
                raise ValueError('Independent fold score mismatch')
            identities+=2
        for pair in fold['samples']['full']['pairs'].values():
            if abs(maes[pair['comparator']]-maes[pair['model']]-pair['maeGainPP'])>1e-12:
                raise ValueError('Independent paired gain mismatch')
            identities+=1
    return {'stage':42,'independentlyCheckedFeatureValues':features,'independentlyCheckedCandidateVectors':vectors,
        'foldAndPairIdentities':identities,'agreementWithin1eMinus12':True,
        'method':'Fraction mass weights; ordinary scalar exp normalization; direct votes/valid denominator errors; no principal predictor/report functions imported'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();count=verify()
    result=check();save('independent-verification.json',result,a.check);print(result,'prior preserved',count)


if __name__=='__main__':main()
