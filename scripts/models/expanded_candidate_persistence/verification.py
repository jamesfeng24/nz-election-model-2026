"""Independent covariance estimates and direct per-record arithmetic."""
import argparse
from math import fsum,sqrt
from .common import local,read,unique,RES,save,manifest,verify_inputs,verify_prefit,preservation
from .inventory import value


def assert_close(a,b,label):
    if abs(a-b)>1e-8:raise ValueError('Independent discrepancy: '+label)


def independent_fit(ids,index,actuals,scale,stored):
    if stored['status']!='available':return 0
    x=[index[i]['sourceResiduals'][scale] for i in ids]
    y=[value(actuals[index[i]['targetOccurrenceId']],scale) for i in ids]
    mx,my=fsum(x)/len(x),fsum(y)/len(y)
    beta=fsum((a-mx)*(b-my) for a,b in zip(x,y))/fsum((a-mx)*(a-mx) for a in x)
    alpha=my-beta*mx
    assert_close(alpha,stored['alpha'],'alpha');assert_close(beta,stored['beta'],'beta')
    return 1


def build():
    verify_inputs();verify_prefit();index=unique(local('inventory.json')['pairs'],'id')
    actuals=unique(read(RES+'occurrences.json')['records'],'candidateOccurrenceId')
    construction=local('construction.json');evaluation=local('evaluation.json');scores={r['id']:r for r in evaluation['folds']}
    fits=preds=metric_count=paired=0
    for f in construction['folds']:
        fits+=independent_fit(f['trainingIds'],index,actuals,f['scale'],f['fits']['regression'])
        if f['fits']['historical_mean']['status']=='available':
            ys=[value(actuals[index[i]['targetOccurrenceId']],f['scale']) for i in f['trainingIds']]
            assert_close(fsum(ys)/len(ys),f['fits']['historical_mean']['mean'],'independent mean')
        target=[value(actuals[index[i]['targetOccurrenceId']],f['scale']) for i in f['evaluationIds']]
        for method,record in f['predictions'].items():
            if record['status']!='available':continue
            errors=[]
            for r,y in zip(record['values'],target):
                x=index[r['id']]['sourceResiduals'][f['scale']]
                expected=0 if method=='zero' else x if method=='carry_forward' else f['fits']['historical_mean']['mean'] if method=='historical_mean' else f['fits']['regression']['alpha']+f['fits']['regression']['beta']*x
                assert_close(expected,r['prediction'],'prediction');errors.append(expected-y);preds+=1
            s=scores[f['id']]['scores'][method]
            if errors:
                for key,v in [('MAEpp',100*fsum(map(abs,errors))/len(errors)),('RMSEpp',100*sqrt(fsum(e*e for e in errors)/len(errors))),('biasPp',100*fsum(errors)/len(errors))]:
                    assert_close(v,s[key],key);metric_count+=1
        for control,record in scores[f['id']]['pairedGains'].items():
            if not record['n']:continue
            rows=scores[f['id']]['records']
            gain=100*fsum(abs(r['errors'][control])-abs(r['errors']['regression']) for r in rows)/len(rows)
            assert_close(gain,record['MAEgainPp'],'paired gain');paired+=1
    for f in construction['descriptive']:
        fits+=independent_fit(f['retainedIds'],index,actuals,f['scale'],f['fits']['regression'])
    return {'independentlyVerifiedOLS':fits,'predictions':preds,'foldMetricValues':metric_count,
            'pairedFoldGains':paired,'absoluteTolerance':1e-8,'priorFilesPreserved':preservation(),
            'checks':'covariance_not_normal_equations; direct_prediction_and_fsum_error_arithmetic; no_serialized_solver_epsilon',
            'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    result=build();save('independent-verification.json',result,a.check)
    manifest('verification',['independent-verification.json'],['scripts/models/expanded_candidate_persistence/verification.py'],a.check)
    print(result)


if __name__=='__main__':main()
