"""Independent saved-artifact audit; no fitted machinery or prediction calculation."""
import argparse
from collections import Counter
from fractions import Fraction
from math import isfinite
from .common import load, save, verify_preservation, verify_sources

BASE='data/processed/forecast-readiness/snapshots/2026-10-05/'


def verify():
    manifest=load('data/processed/forecast-readiness/acquisition-manifest.json');verify_sources(manifest)
    frame=load(BASE+'target-frame.json')['records'];snap=load(BASE+'snapshot.json')
    links=load(BASE+'identity-links.json')['records'];features=load(BASE+'candidate-feature-readiness.json')['records']
    source_features=load(BASE+'party-seat-feature-readiness.json')['records']
    cross=load('data/processed/boundaries/2023-2026/crosswalk.json')['scopes']
    residuals={r['candidateOccurrenceId']:r for r in load('data/processed/models/candidate-overperformance/occurrences.json')['records'] if r['year']==2023}
    splits={m['id']:m for m in load('data/processed/split-votes/2023.json')['matrices']}
    exact=[]
    for scope,part in cross.items():
        for target in part['targets']:
            incoming=[e for e in part['edges'] if e['target']==target['code'] and e['upper']>0]
            if len(incoming)!=1 or target['unchangedMembershipStatus']!='identity':continue
            e=incoming[0];outgoing=[e2 for e2 in part['edges'] if e2['source']==e['source'] and e2['upper']>0]
            if len(outgoing)!=1:continue
            membership=target['composition'][0]
            checks=[e['weightLower'],e['weightUpper'],membership['shareLower'],membership['shareUpper']]
            if all(v['numerator']==v['denominator'] for v in checks):exact.append((scope,target['code']))
    saved={(s['scope'],s['boundaryCode']) for s in frame if s['exactSourceElectorateId']}
    if saved!=set(exact):raise ValueError('Independent two-sided geography mismatch')
    ids={r['targetOccurrenceId'] for r in snap['occurrences']}
    if len(ids)!=len(snap['occurrences']) or {e['targetOccurrenceId'] for e in links}!=ids or {f['targetOccurrenceId'] for f in features}!=ids:
        raise ValueError('Candidate join membership mismatch')
    support=0;witnesses=0
    for row in source_features:
        s=row['S']
        if s['status']!='supported':continue
        support+=1;matrix=splits[s['sourceMatrixId']]
        original=next(r for r in matrix['rows'] if r['totalPartyVotes']==s['sourcePartyRowMass'] and any(c['candidateId']==s['sourceOccurrenceId'] and c['reportedPercent']==s['printedPercentWorkingApproximation'] for c in r['cells']))
        for values in s['completeRowWitnesses'].values():
            values=[Fraction(v) for v in values]
            if sum(values)!=100 or len(values)!=len(original['cells']):raise ValueError('Coupled row conservation mismatch')
            for value,cell in zip(values,original['cells']):
                printed=Fraction(str(cell['reportedPercent']))
                if not max(0,printed-Fraction(1,200))<=value<=min(100,printed+Fraction(1,200)):raise ValueError('Witness outside rounding constraint')
            witnesses+=1
    rchecks=0
    for f in features:
        if f['R']['status']!='supported':continue
        r=f['R'];original=residuals[r['sourceOccurrenceId']]
        if r['valueFraction']!=original['normalizedPremium'] or not isfinite(r['valueFraction']) or r['sourceReferenceId']!=original['referenceId']:
            raise ValueError('Source residual identity mismatch')
        rchecks+=1
    return {'stage':40,'method':'independent saved-source rational geography, full rounding witness and source residual checks; no model outputs',
        'targetSeats':len(frame),'exactByScope':dict(Counter(scope for scope,_ in exact)),
        'candidateRecords':len(ids),'supportedPartySeatS':support,'completeCoupledRowWitnessesChecked':witnesses,
        'supportedSourceResidualsChecked':rchecks,'preservation':verify_preservation(),
        'candidatePredictionsCalculated':False,'historicalFitsRun':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=verify();save(BASE+'independent-verification.json',result,args.check);print(result)


if __name__=='__main__':main()
