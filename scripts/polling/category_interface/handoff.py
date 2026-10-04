"""Pin a future candidate replay contract; never call a candidate model."""
import argparse
from .common import ROOT, OUT, read, sha, save


def build():
    base='data/processed/models/joint-candidate-share/construction.json'
    folds=[]
    for f in read(ROOT/base)['folds']:
        if f['branch']!='primary' or f['targetYear'] not in (2014,2017,2020,2023):
            continue
        if any(r['parameters']['status']!='fitted' for r in f['fits'].values()):
            raise ValueError('Saved primary fit unavailable')
        folds.append({k:f[k] for k in ('id','targetYear','trainingIds','evaluationIds','evaluationCandidateIds','trainingOnlyMeans')} |
                     {'savedFitIds':{m:r['fitId'] for m,r in f['fits'].items()},
                      'savedFitStatus':{m:r['parameters']['status'] for m,r in f['fits'].items()}})
    if [len(f['evaluationIds']) for f in folds]!=[20,64,34,64]:
        raise ValueError('Future replay sample differs from saved primary')
    paths=[base,'data/processed/models/joint-candidate-share/fit-cache.json',
           'data/processed/checkpoints/joint-candidate-share-design/inventory.json',
           'data/processed/models/expanded-party-substitution/input-inventory.json',
           'data/processed/polling/category-interface/allocation-manifest.json']
    manifest=read(OUT/'allocation-manifest.json')
    paths += ['data/processed/polling/category-interface/'+x['path'] for c in manifest['cases'] for policy in c['policies'].values() for x in policy.values()]
    return {'stage':37,'implementationAuthorizedNow':False,
            'restrictions':['baseline','baseline_plus_S','baseline_plus_R','baseline_plus_S_plus_R'],
            'folds':folds,'horizonsDays':[14,56],'primaryHorizonDays':14,
            'allocationPolicies':['recent_report_prior','prior_only'],'nationalDrawField':'arrays.electionDay',
            'sharedNationalDrawIds':True,'candidateExpectedShareRule':'mean of fully transformed national draws',
            'candidateUncertaintyModelled':False,'parameterRefitting':False,
            'consumedSha256':{p:sha(ROOT/p) for p in paths},'operationalSelection':None}


def run(check=False):
    save('candidate-replay-plan.json',build(),check)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
