"""One party-seat fit and prediction pipeline, parameterized by party baseline."""
import math
from scripts.models.party_vote_transform.scoring import quantile


def fit(rows):
    if not rows or len({r['party'] for r in rows})!=1 or any(r['scope']!='general' for r in rows):raise ValueError('Separate general party fit required')
    x=[r['deltaParty'] for r in rows];y=[r['deltaCandidate'] for r in rows]
    if not all(math.isfinite(v) for v in x+y):raise ValueError('Invalid delta')
    denominator=math.fsum(v*v for v in x)
    if denominator<=0:raise ValueError('Unidentified zero-intercept slope')
    return {'beta':math.fsum(a*b for a,b in zip(x,y))/denominator,'n':len(rows),'trainingSourceYears':sorted({r['sourceYear'] for r in rows}),'intercept':0}


def predict(row,beta,baseline='actual_observed_local_party'):
    target=row['targetPartyShare'] if baseline=='actual_observed_local_party' else row['stage5PredictedTargetParty'][baseline]
    return row['sourceCandidateShare']+beta*(target-row['sourcePartyShare'])


def evaluate(rows,beta,baseline):
    predictions=[{'recordId':r['id'],'prediction':predict(r,beta,baseline),'actual':r['targetCandidateShare']} for r in rows]
    errors=[r['prediction']-r['actual'] for r in predictions];absolute=[abs(e) for e in errors];n=len(rows)
    if not n:return {'n':0,'metrics':None,'predictions':[]}
    return {'n':n,'metrics':{'maePP':100*sum(absolute)/n,'rmsePP':100*math.sqrt(sum(e*e for e in errors)/n),'biasPP':100*sum(errors)/n,'medianAbsoluteErrorPP':100*quantile(absolute,.5),'p90AbsoluteErrorPP':100*quantile(absolute,.9),'outOfRangePredictions':sum(not 0<=r['prediction']<=1 for r in predictions)},'predictions':predictions}


def chronological_fit(train,test):
    if not train or not test or max(r['targetYear'] for r in train)>min(r['sourceYear'] for r in test):raise ValueError('Future target leakage into chronological training')
    return fit(train)


def analyse(records):
    fits={};backtests=[];maori={}
    baselines=['actual_observed_local_party','additive','proportional','log_odds']
    for party in ['nationalparty','labourparty']:
        rows=[r for r in records if r['party']==party and r['scope']=='general'];years=sorted({r['sourceYear'] for r in rows});full=fit(rows)
        fits[party]={'full':full,'transitionSpecific':{str(y):fit([r for r in rows if r['sourceYear']==y]) for y in years},'leaveOneOut':{},'chronological':{}}
        for year in years:
            test=[r for r in rows if r['sourceYear']==year]
            modes=[('full_fit_descriptive',full),('leave_one_transition_out_stability',fit([r for r in rows if r['sourceYear']!=year]))]
            fits[party]['leaveOneOut'][str(year)]=modes[-1][1]
            earlier=[r for r in rows if r['sourceYear']<year]
            if earlier:
                chrono=chronological_fit(earlier,test);fits[party]['chronological'][str(year)]=chrono;modes.append(('chronological',chrono))
            for mode,fitted in modes:
                for baseline in baselines:
                    for label,beta in [('no_response',0.),('one_for_one',1.),('fitted',fitted['beta'])]:
                        backtests.append({'party':party,'holdoutSourceYear':year,'mode':mode,'baseline':baseline,'model':label,'beta':beta,'trainingSourceYears':fitted['trainingSourceYears'] if label=='fitted' else [],**evaluate(test,beta,baseline)})
        paired=[r for r in records if r['party']==party and r['scope']=='maori']
        maori[party]={'pairedObservations':len(paired),'operationalMaoriCoefficient':None,'status':'descriptive_only_small_cluster_count' if paired else 'no_paired_candidacies','generalCoefficientReferenceDiagnostics':{str(y):{label:evaluate([r for r in paired if r['sourceYear']==y],beta,'actual_observed_local_party') for label,beta in [('no_response',0.),('one_for_one',1.),('general_beta_reference',full['beta'])]} for y in years}}
    return fits,backtests,maori
