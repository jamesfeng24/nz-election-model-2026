"""Post-result user-authorized central-anchor diagnostic, never formal validation."""
import argparse
from fractions import Fraction
import json
from math import isfinite

import numpy as np
from scripts.checkpoints.complete_share_feature_rank import rank_details
from scripts.models.asymmetric_response.design import initial_direction, regime_rank_guard
from scripts.models.exact_geography_retests.adapters import response_training
from .common import ROOT, DEST, DESIGN, read, verify_inputs, phase_write, phase_manifest, digest
from .construction import classification, regime_counts
from .numerics import solve_restrictions, prediction
from .verification import verify_prefit

CONTRACT='descriptive-diagnostic-contract.json'
CODE=['scripts/models/asymmetric_response_test/'+name+'.py' for name in
      ('descriptive_diagnostic','numerics','construction','common')]


def detailed_anchor_diagnostics(case, snapshots, selected):
    anchor=case['anchor'];estimates=anchor['estimates']
    full_premiums=[Fraction(r['generalPremium']) for r in snapshots]
    formal_bracket=min(full_premiums)<0<max(full_premiums)
    signs={e['slope']>0 for e in estimates if e['slope'] is not None and abs(e['slope'])>1e-12}
    sign_unstable=len(signs)!=1
    by_year={r['year']:r for r in snapshots}
    environments=sorted({(r['sourceYear'],r['targetYear']) for r in selected})
    transitions=[]
    for sy,ty in environments:
        labels=[]
        for e in estimates:
            root=e['anchor'];valid=root is not None and isfinite(root) and 0<=root<=1
            label=initial_direction(by_year[sy]['nationalSupport'],by_year[ty]['nationalSupport'],str(root)) if valid else {'regime':'ambiguous','T':None}
            labels.append({'omittedSnapshotYear':e['omittedYear'],'label':label['regime'],'T':label['T'],
                           'crossesAnchor':label.get('crossesAnchor'), 'startsAtAnchor':label.get('startsAtAnchor'),
                           'crossingWithinOwnObservedSupport':not e['extrapolated'],
                           'numericallyDefined':valid})
        transitions.append({'sourceYear':sy,'targetYear':ty,'records':sum(r['sourceYear']==sy and r['targetYear']==ty for r in selected),
                            'labels':labels,'classificationChanges':len({r['label'] for r in labels})>1})
    conflict_count=sum(t['classificationChanges'] for t in transitions)
    fits=[]
    for e in estimates:
        retained=[r for r in snapshots if r['year']!=e['omittedYear']]
        premiums=[Fraction(r['generalPremium']) for r in retained]
        failures=[]
        if not formal_bracket:failures.append('full_observed_premium_sign_bracket_absent')
        if e['anchor'] is None or not isfinite(e['anchor']) or abs(e['slope'])<=1e-12:failures.append('nonfinite_or_zero_slope')
        elif not 0<=e['anchor']<=1:failures.append('crossing_outside_[0,1]')
        elif e['extrapolated']:failures.append('crossing_outside_own_observed_support_range')
        if e['rank']!=2 or e['scaledCondition'] is None or e['scaledCondition']>1e6:failures.append('numerical_rank_or_condition')
        if sign_unstable:failures.append('snapshot_slope_sign_instability')
        distance=None if e['anchor'] is None else max(e['nationalRange'][0]-e['anchor'],e['anchor']-e['nationalRange'][1],0)*100
        fits.append({**e,'ownEstimateFormalFailures':failures,'outsideSupportDistancePP':distance,
                     'retainedRawPremiumSignBracket':min(premiums)<0<max(premiums),
                     'retainedBracketRole':'diagnostic; original_gate_requires_full_snapshot_set_sign_bracket'})
    return {'party':case['party'],'formalAnchorStatus':anchor['status'],'formalAnchorFirstFailure':anchor.get('reason'),
            'anchorEstimates':fits,'transitionLabels':transitions,'changedTransitionClassifications':conflict_count,
            'transitionCount':len(transitions),'slopeSignUnstable':sign_unstable,
            'conflictingTowardAwayLabels':conflict_count>0,
            'independentlyAssessableSetGates':{
                'insufficientSnapshots':len(snapshots)<4,
                'fullRawPremiumSignBracketAbsent':not formal_bracket,
                'anyCrossingOutsideObservedSupport':any(e['extrapolated'] for e in estimates),
                'slopeSignInstability':sign_unstable,
                'numericalRankOrConditionFailure':any(e['rank']!=2 or e['scaledCondition'] is None or e['scaledCondition']>1e6 for e in estimates),
                'conflictingTransitionClassifications':conflict_count>0,
                'separateExcessiveWidthGate':'unavailable_not_defined_in_frozen_contract'},
            'excessiveInstabilityGate':'no_separate_width_threshold_was_preregistered; every_snapshot_deletion_range_sign_rank_and_classification_checks_are_the_stability_rules',
            'finiteSetNotConfidenceInterval':True}


def diagnostic_response(rows, elections):
    """Numerical admission only; report rather than relax the formal political gates."""
    if not rows:
        return {'status':'abstain','reason':'empty_sample'}
    training=response_training(rows,elections)
    design=np.array([[1,r['x'],r['x']*r['T']] for r in training],dtype=float)
    rank=rank_details(design,[0,1,2]);formal=regime_rank_guard(training)
    result={'trainingIds':[r['id'] for r in training],'regimes':regime_counts(rows),
            'formalResponseGate':formal,'numericalDesign':rank,
            'interpretation':'non_operational_in_sample_descriptive_only'}
    if len({r['T'] for r in training})<2:
        return {**result,'status':'abstain','reason':'regime_disappeared'}
    if rank['rank']!=3 or rank['weakCondition']:
        return {**result,'status':'abstain','reason':'numerical_rank_or_condition'}
    fitted=solve_restrictions(training)
    result.update(fitted)
    if fitted['status']=='available':
        result['predictions']={name:[{'id':r['id'],'candidateShare':prediction(r,f),
                                      'outOfRange':not 0<=prediction(r,f)<=1} for r in rows]
                               for name,f in fitted['fits'].items()}
    return result


def build():
    cases=json.loads((DEST/'descriptive-construction.json').read_bytes())['cases']
    sample=json.loads((DEST/'sample-inventory.json').read_bytes())['fullPanelDescriptive']
    aggregates=read(DESIGN+'input-inventory.json')['electionAggregateInputs']
    rows={r['id']:r for r in read('data/processed/models/exact-geography-retests/inventory.json')['responseRecords']}
    elections={y:read(f'data/processed/elections/{y}.json') for y in (2008,2011,2014,2017,2020,2023)}
    result=[]
    for case,ids in zip(cases,sample):
        selected=[rows[i] for i in ids['responseIds']]
        snaps=[r for r in aggregates if r['party']==case['party']]
        diagnostic=detailed_anchor_diagnostics(case,snaps,selected)
        central=next(e for e in case['anchor']['estimates'] if e['omittedYear'] is None)
        output={'party':case['party'],'anchorDiagnostic':diagnostic,'centralAnchor':central['anchor'],
                'formalGateFirstResultUnchanged':True,'transitionDeletions':[]}
        valid=(central['anchor'] is not None and isfinite(central['anchor']) and 0<=central['anchor']<=1
               and abs(central['slope'])>1e-12 and central['rank']==2
               and central['scaledCondition'] is not None and central['scaledCondition']<=1e6)
        if not valid:
            output.update(status='abstain',reason='central_anchor_numerically_unavailable')
        else:
            classified=classification(selected,aggregates,{'status':'available','stabilityAnchors':[central['anchor']]})
            if classified['status']!='available':output.update(status='abstain',reason=classified['reason'])
            else:
                output.update(diagnostic_response(classified['rows'],elections))
                classified_rows={r['id']:r for r in classified['rows']}
                for deletion in ids['transitionDeletions']:
                    kept=[classified_rows[i] for i in deletion['retainedIds']]
                    output['transitionDeletions'].append({'deletedEnvironment':deletion['deletedEnvironment'],
                        'centralAnchorFixed':central['anchor'],'deletedTransitionScored':False,
                        **diagnostic_response(kept,elections)})
        result.append(output)
    return {'stage':29,'scope':'post_result_separately_authorized_central_anchor_descriptive_extension',
            'operationalSelection':None,'cases':result}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    verify_inputs();verify_prefit()
    expected=json.loads((DEST/'supplement-prefit-manifest.json').read_bytes())
    if digest(str((DEST/CONTRACT).relative_to(ROOT)))!=expected['contractSha256']:
        raise ValueError('Changed supplemental pre-fit contract')
    for name, original in expected['formalConstructionSha256'].items():
        if digest(str((DEST/name).relative_to(ROOT)))!=original:
            raise ValueError('Formal gate-first construction changed: '+name)
    phase_write('supplemental-construction.json',build(),args.check)
    phase_manifest('supplemental-construction',['supplemental-construction.json'],CODE,args.check)


if __name__=='__main__':main()
