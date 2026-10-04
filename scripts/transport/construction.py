"""Fixed earlier fits, identical complete slates, source-only features; no evaluation."""
import argparse
from copy import deepcopy
from scripts.models.joint_candidate_share.numerics import predict
from .common import read, save, verify_inputs, preserve, PREFIX, METHOD
from .geography import admitted

BRANCHES = {'fallback':(None,'broad'),'transport_90':(90,'broad'),'transport_95':(95,'broad'),
            'fallback_strict':(None,'strict'),'transport_90_strict':(90,'strict'),'transport_95_strict':(95,'strict')}


def feature_rows(records, threshold, view):
    rows=deepcopy(records)
    for row in rows:
        use=row['transportTier']=='exact' or threshold is not None and admitted(row['geography'],threshold)
        for c in row['candidates']:
            if not use:
                c['s0Reported']=None
                c['R'][view]=dict(c['R'][view],valueFraction=None,sourceOccurrenceId=None,
                    status='neutral_fallback',reason='approximate_transport_not_enabled_for_branch')
            available=c['R'][view]['valueFraction'] is not None
            c['R'][view]['availabilityPattern']='both_features' if available and c['s0Reported'] is not None else 'R_only' if available else 'S_only' if c['s0Reported'] is not None else 'neither_feature'
    return rows


def build(inventory=None, samples=None, saved=None):
    inventory=read(PREFIX+'/historical-inventory.json') if inventory is None else inventory
    samples=read(PREFIX+'/sample-manifest.json')['folds'] if samples is None else samples
    saved=read('data/processed/models/joint-candidate-share/construction.json') if saved is None else saved
    output=[]
    for sample in samples:
        fold=next(f for f in saved['folds'] if f['id']==sample['savedFoldId'])
        if (fold['trainingOnlyMeans']!=sample['trainingOnlyMeans'] or fold['fits'][METHOD]!=sample['savedFit']
                or fold['trainingIds']!=sample['trainingIds']):
            raise ValueError('Frozen fit, training IDs or preprocessing changed')
        records=[r for r in inventory['records'] if r['targetYear']==sample['targetYear']]
        if [r['targetElectorateId'] for r in records]!=sample['comparisonIds'] or [c['targetOccurrenceId'] for r in records for c in r['candidates']]!=sample['candidateIds']:
            raise ValueError('Frozen complete common slate changed')
        if any(int(i.split('-')[2])>=sample['targetYear'] for i in fold['trainingIds']):
            raise ValueError('Target/later fitted training IDs')
        predictions={};coverage={}
        for branch,(threshold,view) in BRANCHES.items():
            rows=feature_rows(records,threshold,view)
            predictions[branch]=predict(rows,dict(fold,partyInput='observed',view=view),METHOD,sample['savedFit']['parameters'])
            if [p['targetElectorateId'] for p in predictions[branch]]!=sample['comparisonIds']:
                raise ValueError('Numerical abstention; no partial paired score permitted')
            coverage[branch]={'contests':len(rows),'candidates':sum(len(r['candidates']) for r in rows),
                'withS':sum(c['s0Reported'] is not None for r in rows for c in r['candidates']),
                'withR':sum(c['R'][view]['valueFraction'] is not None for r in rows for c in r['candidates']),
                'transportedS':sum(c['s0Reported'] is not None for r in rows if r['transportTier']!='exact' for c in r['candidates']),
                'transportedR':sum(c['R'][view]['valueFraction'] is not None for r in rows if r['transportTier']!='exact' for c in r['candidates'])}
        reference=next(f for f in saved['folds'] if f['branch']=='primary_fixed_to_observed' and f['targetYear']==sample['targetYear'])
        reference_q={p['targetElectorateId']:p['candidateShares'] for p in reference['predictions'][METHOD]}
        deviations=[]
        for p in predictions['fallback']:
            if p['targetElectorateId'] in reference_q:
                ref=reference_q[p['targetElectorateId']]
                if ref.keys()!=p['candidateShares'].keys():raise ValueError('Exact reference slate differs')
                deviations.extend(abs(v-ref[c]) for c,v in p['candidateShares'].items())
        if len(reference_q)!=sum(r['transportTier']=='exact' for r in records) or max(deviations,default=0)>1e-12:
            raise ValueError('Exact observed-input Stage33 reproduction failed')
        output.append({'targetYear':sample['targetYear'],'savedFit':sample['savedFit'],
            'trainingOnlyMeans':sample['trainingOnlyMeans'],'predictions':predictions,'coverage':coverage,
            'exactStage33MaximumShareDeviation':max(deviations,default=0),
            'targetCandidateOutcomesConsumed':False,'fittingPerformed':False})
    return {'stage':41,'folds':output,'operationalSelection':None,
        'informationSet':'observed local party inputs, retrospective complete slates, earlier fixed fits; no live forecast'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    verify_inputs();save('construction.json',build(),a.check);print('Saved fixed-fit predictions; prior data unchanged:',preserve())


if __name__=='__main__':main()
