"""In-sample scores and independent calculations for the post-result supplement."""
import argparse
import json
import numpy as np

from .common import ROOT, DEST, read, verify_inputs, phase_write, phase_manifest
from .evaluation import actuals, score_case
from .numerics import RESTRICTIONS


def display_metric(value):
    """Canonicalize signed zero only in rounded independent-check displays."""
    rounded=round(value,6)
    return 0.0 if rounded==0 else rounded


def independently_verify(case, actual):
    rows={r['id']:r for r in read('data/processed/models/exact-geography-retests/inventory.json')['responseRecords']}
    predictions=case['predictions']
    # Regimes are fixed by the saved central full-panel anchor, not inferred from errors.
    t={p['id']:None for p in predictions['asymmetric']}
    parent=json.loads((DEST/'supplemental-construction.json').read_bytes())
    party=rows[next(iter(t))]['party']
    full=next(c for c in parent['cases'] if c['party']==party)
    regimes={(r['sourceYear'],r['targetYear']):r['labels'][0]['T'] for r in full['anchorDiagnostic']['transitionLabels']}
    ids=case['trainingIds'];x=np.array([rows[i]['x'] for i in ids]);c0=np.array([rows[i]['c0'] for i in ids])
    y=np.array([actual[i] for i in ids]);T=np.array([regimes[(rows[i]['sourceYear'],rows[i]['targetYear'])] for i in ids])
    checks=[]
    for name in RESTRICTIONS:
        if name=='beta_one':
            coefficients=np.array([np.mean(y-c0-x)]);expected=c0+coefficients[0]+x
            saved=[case['fits'][name]['alpha']]
        elif name=='constant':
            matrix=np.column_stack((np.ones(len(ids)),x));coefficients=np.linalg.lstsq(matrix,y-c0,rcond=None)[0]
            expected=c0+matrix@coefficients;saved=[case['fits'][name]['alpha'],case['fits'][name]['betaAway']]
        else:
            matrix=np.column_stack((np.ones(len(ids)),x,x*T));coefficients=np.linalg.lstsq(matrix,y-c0,rcond=None)[0]
            expected=c0+matrix@coefficients;saved=[case['fits'][name][k] for k in ('alpha','betaAway','delta')]
        observed=np.array([p['candidateShare'] for p in predictions[name]])
        errors=expected-y
        metrics={'maePP':float(np.mean(np.abs(errors))*100),
                 'rmsePP':float(np.sqrt(np.mean(errors*errors))*100),'biasPP':float(np.mean(errors)*100)}
        score=score_case(case,actual)['metrics'][name]
        passed=(np.max(np.abs(coefficients-saved))<=1e-8 and np.max(np.abs(expected-observed))<=1e-8
                and all(abs(metrics[k]-score[k])<=1e-8 for k in metrics))
        if not passed:raise ValueError('Independent response fit/prediction/error disagreement')
        checks.append({'restriction':name,'independentCoefficientsPredictionsAndMetricsWithin1eMinus8':True,
                       'independentMetricDisplay':{k:display_metric(v) for k,v in metrics.items()}})
    return checks


def evaluate():
    construction=json.loads((DEST/'supplemental-construction.json').read_bytes())
    result=[]
    for case in construction['cases']:
        actual=actuals(case['trainingIds']) if case['status']=='available' else {}
        score=score_case(case,actual);checks=independently_verify(case,actual) if case['status']=='available' else []
        deletions=[]
        for child in case['transitionDeletions']:
            actual=actuals(child['trainingIds']) if child['status']=='available' else {}
            deletions.append({'deletedEnvironment':child['deletedEnvironment'],
                'centralAnchorFixed':child['centralAnchorFixed'],'retainedCount':len(child['trainingIds']),
                'regimes':child['regimes'],'formalResponseGate':child['formalResponseGate'],
                'numericalDesign':child['numericalDesign'],'fits':child.get('fits'),
                **score_case(child,actual), 'deletedTransitionScored':False,
                'independentChecks':independently_verify(child,actual) if child['status']=='available' else []})
        result.append({'party':case['party'],'centralAnchor':case['centralAnchor'],'regimes':case.get('regimes'),
            'formalResponseGate':case.get('formalResponseGate'),'numericalDesign':case.get('numericalDesign'),
            'fits':case.get('fits'),**score,'independentChecks':checks,'transitionDeletions':deletions})
    return {'stage':29,'scope':'post_result_central_anchor_descriptive_amendment',
            'interpretation':'in_sample_fit_improvement_and_structural_influence; not_temporal_validation_or_forecasting_improvement',
            'cases':result,'operationalSelection':None,
            'independentResponseChecks':sum(len(c['independentChecks'])+sum(len(d['independentChecks']) for d in c['transitionDeletions']) for c in result)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    verify_inputs();result=evaluate()
    phase_write('supplemental-evaluation.json',result,args.check)
    phase_manifest('supplemental-evaluation',['supplemental-evaluation.json'],[
        'scripts/models/asymmetric_response_test/supplement_evaluation.py','scripts/models/asymmetric_response_test/evaluation.py'],args.check)
    print({'independentResponseChecks':result['independentResponseChecks']})


if __name__=='__main__':main()
