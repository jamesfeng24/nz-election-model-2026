"""Independent exact-count party ratios, direct intensity arithmetic and paired errors."""
import argparse
from fractions import Fraction
from .integrity import verify_phase
from math import exp,fsum,sqrt
from .common import local,save,phase,verify_inputs,preserve,keyed


def close(a,b,label):
    if abs(a-b)>1e-8:raise ValueError('Independent verification failed: '+label)


def verify_parties(inv,party):
    national={r['year']:r['validPartyVotes'] for r in inv['nationalPopulation']}
    cats={(r['sourceYear'],r['targetYear']):r['categories'] for r in inv['categoryRelationships']}
    sources=keyed(inv['partyFrame'],'targetElectorateId');n=0
    for p in party['records']:
        row=sources[p['targetElectorateId']];source=keyed(row['sourceCategories'],'categoryId');u={}
        for c in cats[(row['sourceYear'],row['targetYear'])]:
            if c['relationship']=='exit':continue
            q=Fraction(c['targetNationalVotesScenario'],national[row['targetYear']])
            ratio=Fraction(1) if c['relationship']=='entrant' else Fraction(source[c['categoryId']]['sourceLocalVotes']*national[row['sourceYear']],row['sourceValidPartyVotes']*c['sourceNationalVotes'])
            u[c['categoryId']]=q*ratio
        total=sum(u.values())
        for c,v in p['localPartyShares'].items():close(float(u[c]/total),v,'party share');n+=1
    return n


def independent_prediction(contest,block,scenario,cell):
    method='baseline' if cell in ('A','C') else 'baseline_plus_S';f=block['fits'][method];center=block['trainingOnlyMeans']['S'];weights={}
    for c in contest['candidates']:
        b=c['observedTargetPartySupport'] if cell in ('A','B') else c['predictedTargetPartySupport']
        s=c['s0Reported']
        if s is not None and scenario!='printed':s=float(Fraction(c['coupledSamePartyPercent'][0 if scenario=='selected_lower' else 1])/100)
        weight=b+f['kappa']
        if method=='baseline_plus_S' and s is not None:weight*=exp(f['theta'][0]*(s-center))
        weights[c['candidateOccurrenceId']]=weight
    total=fsum(weights.values());return {c:w/total for c,w in weights.items()}


def build():
    verify_inputs();verify_phase('construction');verify_phase('evaluation');inv=local('input-inventory.json');party=local('party-vectors.json');candidate=local('candidate-predictions.json');evaluation=local('evaluation.json')
    count=verify_parties(inv,party);folds=keyed(inv['folds'],'foldId');results={(f['foldId'],f['scenario']):f for f in evaluation['folds']}
    shares=metric_count=interactions=0
    for f in candidate['folds']:
        contests=keyed(f['contests'],'targetElectorateId')
        for scenario,block in f['scenarios'].items():
            if block['status']!='constructed':continue
            for cell,rows in block['cells'].items():
                for r in rows:
                    independent=independent_prediction(contests[r['targetElectorateId']],folds[f['foldId']]['scenarios'][scenario],scenario,cell)
                    for cid,v in r['candidateShares'].items():close(independent[cid],v,'candidate share');shares+=1
            result=results[(f['foldId'],scenario)];records=result['records'];maes={}
            for cell in ('A','B','C','D'):
                errors=[[c['errorPP'] for c in row['cells'][cell]['candidateErrors']] for row in records]
                mae=fsum(fsum(map(abs,es))/len(es) for es in errors)/len(errors)
                rmse=sqrt(fsum(fsum(e*e for e in es)/len(es) for es in errors)/len(errors))
                close(mae,result['cells'][cell]['contestEqualMaePP'],'fold MAE');close(rmse,result['cells'][cell]['contestEqualRmsePP'],'fold RMSE');metric_count+=2;maes[cell]=mae
            interaction=(maes['D']-maes['C'])-(maes['B']-maes['A']);close(interaction,result['paired']['interactionPP'],'four mean I')
            pairs=[]
            for row in records:
                m={c:fsum(abs(x['errorPP']) for x in row['cells'][c]['candidateErrors'])/len(row['cells'][c]['candidateErrors']) for c in ('A','B','C','D')}
                pairs.append((m['D']-m['C'])-(m['B']-m['A']))
            close(fsum(pairs)/len(pairs),interaction,'paired contest I');interactions+=1
    for f in evaluation['partyDiagnostics']['folds']:
        rows=[r for r in evaluation['partyDiagnostics']['records'] if r['targetYear']==f['targetYear'] and r['targetElectorateId'] in {c['targetElectorateId'] for c in inv['candidateRecords']}]
        for method,field in [('model','errors'),('flatNational','flatErrors')]:
            es=[list(r[field].values()) for r in rows]
            close(fsum(fsum(map(abs,x))/len(x) for x in es)/len(es),f['heldGeneral'][method]['maePP'],'party MAE');metric_count+=1
    return {'stage':31,'partyCellsExactCountRatioVerified':count,'candidateSharesDirectExpVerified':shares,
            'foldMetricsIndependentlyVerified':metric_count,'fourMeanAndPairedInteractionsVerified':interactions,
            'absoluteTolerance':1e-8,'priorFilesPreserved':preserve(),'solverOrFitCalls':0,'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();v=build();save('independent-verification.json',v,a.check)
    phase('verification',['independent-verification.json'],['scripts/models/expanded_party_substitution/verification.py'],a.check);print(v)


if __name__=='__main__':main()
