"""Chronological and retrospective descriptive construction, without holdout scoring."""
import argparse
from collections import Counter
from fractions import Fraction

from scripts.models.asymmetric_response.design import national_regime
from scripts.models.asymmetric_response.inputs import election_inputs, fold_inventory, unique
from scripts.models.exact_geography_retests.adapters import response_training, permitted_fold
from .common import DEST, DESIGN, read, verify_inputs, phase_write, phase_manifest
from .numerics import estimate_anchor, fit_restrictions, prediction


CODE = ['scripts/models/asymmetric_response_test/'+p+'.py' for p in ('construction','numerics','common')]


def classification(rows, aggregates, anchor):
    if anchor['status']!='available':
        return {'status':'abstain','reason':'anchor_unavailable','rows':[]}
    snapshots = unique(aggregates, 'id')
    result, failures = [], []
    for r in rows:
        n0 = snapshots[f'{r["sourceYear"]}:{r["party"]}']['nationalSupport']
        n1 = snapshots[f'{r["targetYear"]}:{r["party"]}']['nationalSupport']
        p1 = r['partyInputs']['actual_observed_local_party'][0]
        regime = national_regime({'nationalSource':n0,'nationalTarget':n1,
                                  'partySource':str(r['p0']),'partyTarget':str(p1)},
                                 anchor['stabilityAnchors'])
        if regime['status']!='available':
            failures.append({'id':r['id'],'reason':regime['reason']})
        else:
            result.append({**r,'T':regime['T'],'classification':regime,
                           'environmentId':f'{r["sourceYear"]}-{r["targetYear"]}:{r["party"]}'})
    if failures:
        return {'status':'abstain','reason':'classification_not_stable_for_entire_case',
                'failedRecords':failures,'rows':result}
    return {'status':'available','rows':result}


def regime_counts(rows):
    environments = {r['environmentId']:r['T'] for r in rows}
    return {'recordCounts':dict(Counter(str(r['T']) for r in rows)),
            'environmentCounts':dict(Counter(str(t) for t in environments.values())),
            'nationalLocalDisagreements':sum(r['classification']['nationalLocalOppose'] for r in rows)}


def response_case(train, test, elections):
    training = response_training(train, elections)
    fit = fit_restrictions(training)
    result = {**fit,'trainingIds':[r['id'] for r in train], 'evaluationIds':[r['id'] for r in test],
              'trainingRegimes':regime_counts(train),'evaluationRegimes':regime_counts(test),
              'classifiedTraining':train,'classifiedEvaluation':test}
    if fit['status']=='available':
        result['predictions'] = {name:[{'id':r['id'],'candidateShare':prediction(r,f),
                                       'outOfRange':not 0<=prediction(r,f)<=1} for r in test]
                                 for name,f in fit['fits'].items()}
    return result


def chronological_case(fold, records, aggregates, elections, canonical_folds):
    original = next(f for f in canonical_folds if f['foldId']==fold['stage25FoldId'])
    all_train, all_test = permitted_fold(original, records)
    train = [r for r in all_train if r['party']==fold['party']]
    test = [r for r in all_test if r['party']==fold['party']]
    if [r['id'] for r in train]!=fold['trainingIds'] or [r['id'] for r in test]!=fold['evaluationIds']:
        raise ValueError('Canonical party sample disagreement')
    snapshots = unique(aggregates,'id')
    anchor = estimate_anchor([snapshots[i] for i in fold['permittedAnchorSnapshotIds']])
    result = {'id':fold['id'],'party':fold['party'],'targetYear':fold['targetYear'],
              'protocol':fold['protocol'],'anchor':anchor,'trainingIds':fold['trainingIds'],
              'evaluationIds':fold['evaluationIds'],'countGatesPotentiallyFeasible':fold['countGatesPotentiallyFeasible']}
    if anchor['status']!='available':
        return {**result,'status':'abstain','reason':'anchor:'+anchor['reason']}
    if not fold['countGatesPotentiallyFeasible']:
        return {**result,'status':'abstain','reason':'insufficient_transition_environment_count'}
    classified = classification(train+test, aggregates, anchor)
    if classified['status']!='available':
        return {**result,**classified}
    by_id = unique(classified['rows'],'id')
    return {**result,**response_case([by_id[i] for i in fold['trainingIds']],
                                     [by_id[i] for i in fold['evaluationIds']],elections)}


def descriptive_case(spec, records, aggregates, elections):
    snap = unique(aggregates,'id')
    anchor = estimate_anchor([snap[i] for i in spec['snapshotIds']])
    rows = unique(records,'id')
    selected = [rows[i] for i in spec['responseIds']]
    result = {'party':spec['party'],'anchor':anchor,'responseIds':spec['responseIds'],
              'scope':'full_panel_retrospective_descriptive_not_validation', 'deletions':[]}
    if anchor['status']!='available':
        result.update(status='abstain',reason='anchor:'+anchor['reason'])
    else:
        classified = classification(selected,aggregates,anchor)
        if classified['status']!='available':
            result.update(classified)
        else:
            result.update(response_case(classified['rows'],classified['rows'],elections))
    for deletion in spec['transitionDeletions']:
        child = {**deletion,'anchorPolicy':'fixed_parent_full_and_snapshot_deletion_stability_set',
                 'deletedTransitionScored':False}
        if result['status']!='available':
            child.update(status='not_attempted',reason='parent_descriptive_setup_unavailable')
        else:
            kept = unique(result['classifiedTraining'],'id')
            retained = [kept[i] for i in deletion['retainedIds']]
            child.update(response_case(retained,retained,elections))
        result['deletions'].append(child)
    return result


def build(elections=None, records=None):
    inventory = read('data/processed/models/exact-geography-retests/inventory.json')
    records = records if records is not None else inventory['responseRecords']
    elections = elections if elections is not None else {
        y:read(f'data/processed/elections/{y}.json') for y in (2008,2011,2014,2017,2020,2023)}
    aggregates = [r for election in elections.values() for r in election_inputs(election)]
    canonical = read('data/processed/checkpoints/stage25-historical-geography/fold-plan.json')['folds']
    folds = fold_inventory(canonical,records,aggregates)
    pinned = read(str((DEST/'sample-inventory.json').relative_to(DEST.parents[3])))
    if folds!=pinned['chronologicalFolds']:
        raise ValueError('Frozen chronological sample changed')
    return ({'stage':29,'informationSet':'earlier_only_anchors_and_response; target_party_results_supplied; no_as_of_forecast',
              'cases':[chronological_case(f,records,aggregates,elections,canonical) for f in folds]},
            {'stage':29,'informationSet':'all_six_snapshot_anchor_and_five_transition_responses; retrospective_descriptive',
             'cases':[descriptive_case(s,records,aggregates,elections) for s in pinned['fullPanelDescriptive']]})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    verify_inputs()
    chronological, descriptive=build()
    phase_write('chronological-construction.json',chronological,args.check)
    phase_write('descriptive-construction.json',descriptive,args.check)
    phase_manifest('construction',['chronological-construction.json','descriptive-construction.json'],CODE,args.check)
    print({'chronological':Counter(r['reason'] if r['status']!='available' else 'fitted' for r in chronological['cases']),
           'descriptive':[(r['party'],r['status'],r.get('reason')) for r in descriptive['cases']]})


if __name__=='__main__':
    main()
