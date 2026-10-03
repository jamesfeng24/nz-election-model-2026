"""Reproduce Stage32 design and applicability only; no historical fit or score."""
import argparse
from collections import Counter, defaultdict
from .common import ROOT, DEST, PREFIX, INPUTS, read, local, digest, save, snapshot, verify_inputs, preserve
from .inventory import build, counts
from .folds import build as build_folds

FILES=('specification.json','inventory.json','fold-plan.json','coverage.json','input-contract.json','prior-data-contract.json')
CODE=['scripts/checkpoints/joint_candidate_share/'+n+'.py' for n in ('common','residuals','kernel','inventory','folds','run')]


def coverage(inv, folds):
    records=[]
    for year in sorted({r['targetYear'] for r in inv['fullFrame']}):
        rows=[r for r in inv['contestRecords'] if r['targetYear']==year and r['status']=='available']
        frame=[r for r in inv['fullFrame'] if r['targetYear']==year]
        groups=defaultdict(list)
        for row in rows:
            for c in row['candidates']:
                groups[c['partyBallotGroupKey'] or 'affirmative_no_party_group'].append(c)
        records.append({'targetYear':year,'fullFrameReasons':dict(sorted(Counter(r['reason'] or r['status'] for r in frame).items())),
            'views':{v:counts(rows,v) for v in ('broad','strict')},
            'ballotGroupCoverage':{g:{'candidates':len(cs),'S':sum(c['s0Reported'] is not None for c in cs),
                                    'R':{v:sum(c['R'][v]['valueFraction'] is not None for c in cs) for v in ('broad','strict')}} for g,cs in sorted(groups.items())},
            'residualEvidenceTiers':dict(sorted(Counter(c['R']['broad'].get('evidenceTier','none') for cs in groups.values() for c in cs).items()))})
    return {'stage':32,'records':records,'completeSlateCandidateCount':sum(r['views']['broad']['candidates'] for r in records),
            'fullFrameCandidateOccurrences':len(inv['candidateCoverageFrame']),
            'maoriSourceResidualEvidenceAuditOnly':{v:sum(c.get('residualEvidenceAuditOnly',{}).get(v,{}).get('valueFraction') is not None for c in inv['candidateCoverageFrame'] if c['scope']=='maori') for v in ('broad','strict')},
            'sourceOnlyR':{v:sum(r['views'][v]['R'] for r in records) for v in ('broad','strict')},
            'foldReadiness':[{'id':f['id'],'ready':f['fourModelFitReady'],'training':len(f['trainingIds']),
                             'evaluation':len(f['evaluationIds'])} for f in folds['folds']],
            'allTemporalPublicationClaims':'retrospective; unknown as_of availability stays unknown',
            'fitOrPredictionOrScoringPerformed':False,'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    if args.check:
        verify_inputs()
    inv=build();folds=build_folds(inv);cov=coverage(inv,folds)
    for name,value in [('inventory.json',inv),('fold-plan.json',folds),('coverage.json',cov)]:
        save(name,value,args.check)
    if not args.check:
        save('input-contract.json',{'inputSha256':{p:digest(p) for p in INPUTS+[PREFIX+'specification.json']},
             'requiredSourceContracts':['data/processed/models/expanded-party-substitution/input-contract.json',
                                       'data/processed/evidence/practical-candidate-linkage/input-contract.json',
                                       'data/processed/models/candidate-overperformance/input-contract.json'],
             'wholeRegistryPinned':False},False)
        old=local('prior-data-contract.json') if (DEST/'prior-data-contract.json').exists() else snapshot()
        save('prior-data-contract.json',old,False)
    verify_inputs()
    save('manifest.json',{'outputSha256':{n:digest(PREFIX+n) for n in FILES},'generatorSha256':{c:digest(c) for c in CODE}},args.check)
    print({'candidates':cov['completeSlateCandidateCount'],'R':cov['sourceOnlyR'],'priorFiles':preserve()})


if __name__=='__main__':main()
