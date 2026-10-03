"""Evaluate only gate-passing construction; anchor failures remain explicit."""
import argparse
from math import sqrt

from .common import DEST, ROOT, read, verify_inputs, phase_write, phase_manifest
from .numerics import RESTRICTIONS


def metrics(predictions, actual):
    ids=[p['id'] for p in predictions]
    if len(ids)!=len(set(ids)) or set(ids)!=set(actual):
        raise ValueError('Scoring sample mismatch')
    errors=[p['candidateShare']-actual[p['id']] for p in predictions]
    n=len(errors)
    if not n:
        raise ValueError('Empty evaluated sample')
    return {'n':n,'maePP':100*sum(abs(e) for e in errors)/n,
            'rmsePP':100*sqrt(sum(e*e for e in errors)/n),
            'biasPP':100*sum(errors)/n,'outOfRange':sum(p['outOfRange'] for p in predictions)}


def score_case(case, actual):
    if case['status']!='available':
        return {'status':case['status'],'reason':case['reason'],'metrics':None}
    scores={name:metrics(case['predictions'][name],actual) for name in RESTRICTIONS}
    absolute={name:[abs(p['candidateShare']-actual[p['id']])*100 for p in case['predictions'][name]]
              for name in RESTRICTIONS}
    gains=[c-a for c,a in zip(absolute['constant'],absolute['asymmetric'])]
    pooled=sum(gains)/len(gains)
    influence=[{'id':r['id'],'maeGainPP':g,
                'gainWithoutRecordPP':(sum(gains)-g)/(len(gains)-1)}
               for r,g in zip(case['predictions']['asymmetric'],gains)] if len(gains)>1 else []
    return {'status':'available','metrics':scores,
            'asymmetricVersusConstantMAEGainPP':pooled,
            'influenceScoreOnlyFitsFixed':sorted(influence,key=lambda r:(-abs(r['gainWithoutRecordPP']-pooled),r['id']))}


def actuals(ids):
    inventory=read('data/processed/models/exact-geography-retests/inventory.json')
    rows={r['id']:r for r in inventory['responseRecords']}
    years={rows[i]['targetYear'] for i in ids}
    seats={s['id']:s for y in years for s in read(f'data/processed/elections/{y}.json')['electorates']}
    return {i:next(c['votes'] for c in seats[rows[i]['electorateId']]['candidates']
                   if c['id']==rows[i]['targetOccurrenceId'])/seats[rows[i]['electorateId']]['validCandidateVotes']
            for i in ids}


def evaluate(chronological, descriptive):
    chronology=[]
    for case in chronological['cases']:
        ids=case['evaluationIds']
        score=score_case(case, actuals(ids) if case['status']=='available' else {})
        chronology.append({'id':case['id'],'party':case['party'],'protocol':case['protocol'],
                           'targetYear':case['targetYear'],'frameCount':len(ids),**score})
    full=[]
    for case in descriptive['cases']:
        score=score_case(case,actuals(case['responseIds']) if case['status']=='available' else {})
        children=[]
        for child in case['deletions']:
            children.append({'deletedEnvironment':child['deletedEnvironment'],'retainedCount':len(child['retainedIds']),
                             'deletedTransitionScored':False,
                             **score_case(child,actuals(child['retainedIds']) if child['status']=='available' else {})})
        full.append({'party':case['party'],'frameCount':len(case['responseIds']),**score,'transitionDeletions':children})
    screen={}
    for party in sorted({c['party'] for c in chronology}):
        for protocol in sorted({c['protocol'] for c in chronology}):
            cases=[c for c in chronology if c['party']==party and c['protocol']==protocol and c['status']=='available']
            n=sum(c['metrics']['constant']['n'] for c in cases)
            gain=(sum(c['asymmetricVersusConstantMAEGainPP']*c['metrics']['constant']['n'] for c in cases)/n if n else None)
            screen[party+':'+protocol]={'fittedHoldouts':len(cases),'pooledMAEGainPP':gain,
                'passes':len(cases)>=2 and gain>=.25 and all(c['asymmetricVersusConstantMAEGainPP']>0 and
                    c['metrics']['asymmetric']['rmsePP']-c['metrics']['constant']['rmsePP']<.25 for c in cases),
                'interpretation':'development_screen_only; no_operational_permission'}
    return {'chronological':chronology,'fullPanelDescriptive':full,'developmentScreen':screen,
            'selectedOperationalEffect':None,'noDescriptiveSubstitutionForChronologicalEvidence':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    verify_inputs()
    chronological=read(str((DEST/'chronological-construction.json').relative_to(ROOT)))
    descriptive=read(str((DEST/'descriptive-construction.json').relative_to(ROOT)))
    result=evaluate(chronological,descriptive)
    phase_write('evaluation.json',result,args.check)
    phase_manifest('evaluation',['evaluation.json'],['scripts/models/asymmetric_response_test/evaluation.py'],args.check)
    print({'chronologicalFits':sum(c['status']=='available' for c in result['chronological']),
           'descriptiveFits':sum(c['status']=='available' for c in result['fullPanelDescriptive'])})


if __name__=='__main__':
    main()
