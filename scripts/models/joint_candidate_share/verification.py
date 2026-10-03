"""Independent direct intensity, optimum and metric arithmetic for Stage33."""
import argparse
from math import exp,log,fsum,sqrt
from statistics import mean
import numpy as np
from scipy.optimize import minimize
from .common import *
from .adapters import folds_inventory,fold_rows,prepare
from scripts.checkpoints.joint_candidate_share.kernel import feature

CODE=['scripts/models/joint_candidate_share/verification.py']


def direct_objective(vector,payload):
    k=vector[0];theta=vector[1:];base=np.asarray(payload['base']);x=np.asarray(payload['features']).reshape(len(base),len(theta));y=np.asarray(payload['actual'])
    loss=0.;gradient=np.zeros(len(vector));starts=payload['starts']
    for lo,hi in zip(starts,starts[1:]+[len(base)]):
        z=np.log(base[lo:hi]+k)+x[lo:hi]@theta;shift=z-max(z);w=np.exp(shift);q=w/sum(w)
        loss+=-float(np.dot(y[lo:hi],shift-log(sum(w))))
        diff=q-y[lo:hi];gradient[0]+=np.sum(diff/(base[lo:hi]+k))
        if len(theta):gradient[1:]+=x[lo:hi].T@diff
    return loss/len(starts),gradient/len(starts)


def optimum_checks(folds,inventory,elections,construction):
    cases=keyed(construction['folds'],'id');checks=[]
    for fold in folds:
        if fold['branch']!='primary' or fold['targetYear'] not in (2014,2023):continue
        for method in METHODS:
            fitted=cases[fold['id']]['fits'][method]['parameters']
            if fitted['status']!='fitted':continue
            payload=prepare(fold,inventory,elections,method)['payload'];runs=[]
            for k in (.001,.01,.05,.1):
                initial=np.array([k]+[0.]*len(METHODS[method]))
                r=minimize(lambda v:direct_objective(v,payload),initial,jac=True,method='SLSQP',
                    bounds=[(.0001,.1)]+[(-4,4)]*len(METHODS[method]),options={'ftol':1e-12,'maxiter':2000})
                runs.append({'success':bool(r.success),'objective':float(r.fun),'parameters':r.x.tolist()})
            successful=[r for r in runs if r['success']]
            if not successful:raise ValueError('Independent joint optimizer has no successful solution')
            best=min(r['objective'] for r in successful)
            if abs(best-fitted['objective'])>1e-8:raise ValueError('Independent representative fit disagreement')
            checks.append({'foldId':fold['id'],'method':method,'maximumAllowedDifference':1e-8,
                           'savedObjective':fitted['objective'],'independentObjective':best,'runs':runs})
    return checks


def build():
    folds,inventory=folds_inventory();construction=local('construction.json');evaluation=local('evaluation.json')
    rows=keyed(inventory['contestRecords'],'targetElectorateId');actuals=evaluation['evaluationOnlyActuals'];counts={'shares':0,'metrics':0,'pairedGains':0}
    by_case=keyed(evaluation['folds'],'id');maximum=0.
    for case in construction['folds']:
        scored=by_case[case['id']];own_errors={}
        for method in METHODS:
            fitted=case['fits'][method]['parameters']
            if fitted['status']!='fitted':continue
            errors=[];contest_mae=[];contest_mse=[]
            for predicted in case['predictions'][method]:
                row=rows[predicted['targetElectorateId']];weights=[]
                for c in row['candidates']:
                    p=c['constructedPartySupport' if case['partyInput']=='constructed' else 'observedPartySupport'];power=0.
                    for name,theta in zip(METHODS[method],fitted['theta']):
                        v=feature(c,name,case['view'],case['roundingScenario'])
                        if v is not None:power+=theta*(v-case['trainingOnlyMeans'][name])
                    weights.append((p+fitted['kappa'])*exp(power))
                total=fsum(weights);block=[]
                for c,w in zip(row['candidates'],weights):
                    cid=c['targetOccurrenceId'];q=w/total;delta=abs(q-predicted['candidateShares'][cid]);maximum=max(maximum,delta)
                    if delta>1e-12:raise ValueError('Independent prediction disagreement')
                    block.append(100*(q-actuals[row['targetElectorateId']]['candidateShares'][cid]));counts['shares']+=1
                errors.extend(block);contest_mae.append(mean(abs(v) for v in block));contest_mse.append(mean(v*v for v in block))
            direct=[mean(contest_mae),sqrt(mean(contest_mse)),mean(abs(v) for v in errors),sqrt(mean(v*v for v in errors))]
            saved=scored['availableMethodMetrics'][method]
            for name,value in zip(('contestEqualMaePP','contestEqualRmsePP','candidateEqualMaePP','candidateEqualRmsePP'),direct):
                if abs(value-saved[name])>1e-8:raise ValueError('Independent metric disagreement')
                counts['metrics']+=1
            own_errors[method]=contest_mae
        if scored['records']:
            for model,control in PAIRS:
                value=mean(b-a for a,b in zip(own_errors[model],own_errors[control]))
                if abs(value-scored['pairs'][model+'__versus__'+control]['maeImprovementPP'])>1e-8:raise ValueError('Independent paired gain disagreement')
                counts['pairedGains']+=1
    elections={y:read(p) for y,p in ELECTIONS.items()}
    return {'stage':33,'counts':counts,'maximumShareDiscrepancy':maximum,
        'representativeIndependentFits':optimum_checks(folds,inventory,elections,construction),
        'priorFilesPreserved':preserve(),'tolerances':{'share':1e-12,'metricsPP':1e-8,'fitObjective':1e-8}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify_inputs();verify_phase('construction');verify_phase('evaluation')
    result=build()
    # Independent optimized parameters are diagnostics, not alternative predictions. Platform solver
    # iterates can differ; compare objective gates and direct arithmetic, preserve the saved witness.
    if a.check:
        saved=local('independent-verification.json')
        if result['counts']!=saved['counts'] or len(result['representativeIndependentFits'])!=len(saved['representativeIndependentFits']):raise ValueError('Independent verification coverage changed')
        verify_phase('verification')
    else:
        save('independent-verification.json',result);phase('verification',['independent-verification.json'],CODE)
    print(result['counts'],'independent fits',len(result['representativeIndependentFits']),'prior',preserve())


if __name__=='__main__':main()
