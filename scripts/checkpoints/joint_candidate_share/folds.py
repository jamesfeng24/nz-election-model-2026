"""Canonical common samples and strictly earlier feature preprocessing/rank audits."""
from .common import read, GEO, local
from .inventory import counts
from .kernel import means, centered, rank_audit
from scripts.models.exact_geography_retests.adapters import permitted_fold


def variation(rows, center, view, scenario):
    if center is None:
        return {'S':None,'R':None}
    result = {}
    for name in ('S','R'):
        if center[name] is None:
            result[name]=None
            continue
        n=0
        for row in rows:
            vs=[centered(c,name,center,view,scenario) for c in row['candidates']]
            n+=max(vs)-min(vs)>1e-9
        result[name]=n
    return result


def build(inventory, canonical=None, specification=None):
    canonical = read(GEO+'fold-plan.json')['folds'] if canonical is None else canonical
    spec = local('specification.json') if specification is None else specification
    result=[]
    for branch in spec['comparisonMatrix']:
        for f in canonical:
            if f['family']!='complete_share_baseline_s' or f['chronologyProtocol']!=branch['chronology']:
                continue
            # The canonical permitted_fold enforces source/target chronology before any preprocessing.
            train,test=permitted_fold(f,inventory['contestRecords'])
            missing=[r['targetElectorateId'] for r in train+test if r['status']!='available']
            train=[r for r in train if r['status']=='available'];test=[r for r in test if r['status']=='available']
            center=means(train,branch['linkage'],branch['Sscenario']) if train else None
            audit=rank_audit(train,center,branch['linkage'],branch['Sscenario'],'constructed' if branch['id']=='primary_fixed_to_observed' else branch['partyInput'])
            gates=all(m['estimable'] for m in audit['methods'].values())
            refs=[r['R'][branch['linkage']]['sourceOccurrenceId'] for row in train for r in row['candidates'] if r['R'][branch['linkage']]['valueFraction'] is not None]
            result.append({'id':branch['id']+':'+f['foldId'],'branch':branch['id'],'targetYear':f['targetYear'],
                'sourceYear':f['sourceYear'],'protocol':branch['chronology'],'view':branch['linkage'],
                'partyInput':branch['partyInput'],'roundingScenario':branch['Sscenario'],'fitMode':branch['fit'],
                'canonicalFoldId':f['foldId'],'trainingIds':[r['targetElectorateId'] for r in train],
                'evaluationIds':[r['targetElectorateId'] for r in test],
                'trainingCandidateIds':[c['targetOccurrenceId'] for r in train for c in r['candidates']],
                'evaluationCandidateIds':[c['targetOccurrenceId'] for r in test for c in r['candidates']],
                'commonIdsForAllRestrictions':True,'excludedWholeContestIds':missing,
                'trainingOnlyMeans':center,'trainingFeatureCoverage':counts(train,branch['linkage']),
                'evaluationFeatureCoverage':counts(test,branch['linkage']),
                'trainingWithinSlateVariationContests':variation(train,center,branch['linkage'],branch['Sscenario']),
                'evaluationWithinSlateVariationContests':variation(test,center,branch['linkage'],branch['Sscenario']),
                'trainingSourceResidualOccurrenceIds':refs,'numericalAudit':audit,
                'fourModelFitReady':gates,'historicalFitPerformed':False,
                'trainingTransitionEnvironments':sorted({str(r['sourceYear'])+'-'+str(r['targetYear']) for r in train}),
                'reusePrimaryFitId':('primary:'+f['foldId']) if branch['id']=='primary_fixed_to_observed' else None})
    # All branches share whole slates, never linked-returnee subsets.
    for f in result:
        if set(f['trainingCandidateIds']) & set(f['evaluationCandidateIds']):
            raise ValueError('Training/holdout occurrence overlap')
    return {'stage':32,'folds':result,'operationalSelection':None}
