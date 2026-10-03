"""Earlier-only construction, separate from held-out outcomes and scoring."""
import argparse
from collections import Counter
from .common import local,read,unique,RES,SCALES,verify_inputs,verify_prefit,save,manifest
from .inventory import value
from .numerics import fit,mean_fit

CODE=['scripts/models/expanded_candidate_persistence/'+n+'.py' for n in ('numerics','construction')]


def counts(rows,view):
    refs=Counter(r['sourceReferenceId'] for r in rows)
    return {'pairs':len(rows),'people':len({r[view+'PersonGroupId'] for r in rows}),
            'seatMembershipChains':len({r['seatMembershipChainId'] for r in rows}),
            'targetSeats':len({r['targetElectorateId'] for r in rows}),
            'transitionEnvironments':len({(r['sourceYear'],r['targetYear']) for r in rows}),
            'elections':sorted({r[k] for r in rows for k in ('sourceYear','targetYear')}),
            'sourcePartyElectionReferences':len(refs),'maximumPairsSharingSourceReference':max(refs.values(),default=0),
            'repeatedPersonExtraRows':len(rows)-len({r[view+'PersonGroupId'] for r in rows}),
            'repeatedSeatChainExtraRows':len(rows)-len({r['seatMembershipChainId'] for r in rows})}


def target_values(ids,index,actuals,scale,fold=None):
    if fold:
        for i in ids:
            r=index[i]
            allowed=r['targetYear']<fold['targetYear'] and (r['targetYear']<=fold['sourceYear'] if fold['protocol']=='expanding_window' else r['targetYear']<fold['sourceYear'])
            if not allowed:raise ValueError('Forbidden target/later training response')
    return [value(actuals[index[i]['targetOccurrenceId']],scale) for i in ids]


def trained(rows,y,scale):
    return {'regression':fit([r['sourceResiduals'][scale] for r in rows],y),'historical_mean':mean_fit(y)}


def predictions(rows,fits,scale):
    result={}
    for method in ('regression','zero','carry_forward','historical_mean'):
        status='available' if method in ('zero','carry_forward') else fits[method]['status']
        if status!='available':
            result[method]={'status':'abstain','reason':fits[method]['reason'],'values':[]};continue
        values=[]
        for r in rows:
            x=r['sourceResiduals'][scale]
            p=(0.0 if method=='zero' else x if method=='carry_forward' else fits[method]['mean'] if method=='historical_mean' else fits[method]['alpha']+fits[method]['beta']*x)
            values.append({'id':r['id'],'prediction':p})
        result[method]={'status':'available','values':values}
    return result


def build(inventory=None,plan=None,actuals=None):
    inventory=local('inventory.json') if inventory is None else inventory
    plan=local('fold-plan.json') if plan is None else plan
    actuals=unique(read(RES+'occurrences.json')['records'],'candidateOccurrenceId') if actuals is None else actuals
    index=unique(inventory['pairs'],'id');folds=[]
    for f in plan['folds']:
        training=[index[i] for i in f['trainingIds']];evaluation=[index[i] for i in f['evaluationIds']]
        for r in training+evaluation:
            if r['scope']!=f['scope'] or not r['scaleEligibility'][f['scale']][f['view']]:raise ValueError('Invalid fold membership')
        if any(r['targetYear']!=f['targetYear'] for r in evaluation):raise ValueError('Wrong evaluation election')
        y=target_values(f['trainingIds'],index,actuals,f['scale'],f)
        fits=trained(training,y,f['scale'])
        folds.append({**f,'trainingCoverage':counts(training,f['view']),'evaluationCoverage':counts(evaluation,f['view']),
                      'fits':fits,'predictions':predictions(evaluation,fits,f['scale']),
                      'warning':'few_elections_repeated_people_seats_shared_references; retrospective_algorithmic_linkage'})
    descriptive=[]
    for view in ('broad','strict'):
        for scope in ('general','maori'):
            for scale in SCALES:
                rows=[r for r in inventory['pairs'] if r['scope']==scope and r['scaleEligibility'][scale][view]]
                transitions=sorted({(r['sourceYear'],r['targetYear']) for r in rows})
                for omitted in [None]+transitions:
                    retained=[r for r in rows if (r['sourceYear'],r['targetYear'])!=omitted]
                    ids=[r['id'] for r in retained];y=target_values(ids,index,actuals,scale)
                    fits=trained(retained,y,scale)
                    descriptive.append({'view':view,'scope':scope,'scale':scale,'omittedTransition':list(omitted) if omitted else None,
                        'retainedIds':ids,'coverage':counts(retained,view),'fits':fits,
                        'predictions':predictions(retained,fits,scale),
                        'interpretation':'full_panel_or_retained_sample_description; no_deleted_transition_forecast'})
    return {'stage':30,'folds':folds,'information':'conditional_on_candidacy_and_retrospective_linkage; holdout_actuals_not_read',
            'descriptive':descriptive,'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    verify_inputs();verify_prefit();data=build();save('construction.json',data,args.check)
    manifest('construction',['construction.json'],CODE,args.check)
    print('Constructed',len(data['folds']),'chronological cases;',sum(f['fits']['regression']['status']=='available' for f in data['folds']),'identified regressions;',len(data['descriptive']),'descriptive cases')


if __name__=='__main__':main()
