"""Secondary evidence availability only: no reconstructed candidate or split votes."""
import argparse
import json
from scripts.boundaries.readiness import read, names
from scripts.boundaries.census_2013 import ROOT
from scripts.boundaries.contract import TRANSITIONS, system
from scripts.transform.historical import key


def build():
    hashes={};transitions={}
    for transition in TRANSITIONS:
        year=int(transition[:4])
        election=read(f'data/processed/elections/{year}.json',hashes)
        split=read(f'data/processed/split-votes/{year}.json',hashes)
        cross=read(f'data/processed/boundaries/{transition}/crosswalk.json',hashes)
        records={key(r['name']):r for r in election['electorates']}
        scope=cross['scopes']['general'];population=system(scope)
        held={s['code']:records[key(s['name'])].get('candidateContestStatus','held')=='held' for s in scope['sources']}
        coverage=[]
        for target in scope['targets']:
            vector=sum((population.vector(s,target['code']) for s in held if held[s]), population.vector()*0)
            lo,hi=population.bounds(vector);total=target['populationControl']
            coverage.append({'targetCode':target['code'],'targetName':target['name'],
                             'heldContestPredecessorPopulationFractionLower':lo/total,
                             'heldContestPredecessorPopulationFractionUpper':hi/total,
                             'meaning':'Population-origin coverage only, not a candidate-ballot observation rate.'})
        transitions[transition]={'heldGeneralSourceContests':sum(held.values()),'cancelledGeneralSourceContests':sum(not v for v in held.values()),
            'localSplitPublications':len(split['matrices']),'candidateAffiliationBaseline':None,'splitJointBaseline':None,
            'status':'evidence_coverage_only_reconstruction_not_identified','targetCoverage':coverage,
            'sourceDiscrepancies':split.get('sourceDiscrepancies',[]),
            'reason':'Source-electorate totals do not identify candidate-affiliation or candidate-destination distributions within transferred populations. Candidate choices are contest-local; population weighting would add an unvalidated local-homogeneity assumption. Rounded split percentages additionally do not identify joint counts. No forced secondary vote output.'}
    if len(transitions['2023-2026']['sourceDiscrepancies'])!=21:raise ValueError('Unexpected known discrepancy inventory')
    return {'schemaVersion':1,'dataClass':'secondary_evidence_availability_not_reconstructed_votes','inputHashes':hashes,'transitions':transitions,
            'limitations':['No person linking or candidate continuity assertion. No exact local split counts inferred.',
                          'Port Waikato cancelled candidate and split evidence is unavailable, never a zero-performance observation. Its ordinary party vote remains in the primary baseline.',
                          'The 21 preserved 2023 discrepancies are propagated unchanged; aggregate denominator gaps are not imputed or normalized.',
                          'No voting-place residence inference. Māori secondary evidence is not reconstructed; general-primary coverage only.']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
    raw=(json.dumps(build(),ensure_ascii=False,indent=2)+'\n').encode();path=ROOT/'data/processed/boundaries/secondary-availability.json'
    if args.check:
        if path.read_bytes()!=raw:raise ValueError('Stale secondary assessment')
    else:path.write_bytes(raw)
    print('Secondary coverage preserved; no unidentified candidate/split baselines manufactured')

if __name__=='__main__':main()
