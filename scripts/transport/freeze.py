"""Freeze geography, complete samples and one population scenario before predictions/scores."""
import argparse
from collections import Counter
from .common import ROOT, PREFIX, SNAPSHOT, LINKS, METHOD, read, digest, save
from .geography import all_rows, admitted
from .history import inventory
from scripts.checkpoints.stage25_availability import ELECTIONS, SPLITS, MAPPING, CONTINUITY

INPUTS = [MAPPING,CONTINUITY,*ELECTIONS.values(),*SPLITS.values(),
    'data/processed/checkpoints/stage25-historical-geography/geography.json',
    'data/processed/checkpoints/joint-candidate-share-design/inventory.json',
    'data/processed/models/joint-candidate-share/construction.json',
    'data/processed/models/candidate-overperformance/occurrences.json',
    *[LINKS+n+'.json' for n in ('occurrences','aliases','proposed-links','accepted-relationships')],
    *[SNAPSHOT+n+'.json' for n in ('snapshot','target-frame','party-relationships','identity-links','candidate-feature-readiness','party-seat-feature-readiness')],
    *[f'data/processed/boundaries/{t}/{n}.json' for t in ('2011-2014','2017-2020','2023-2026') for n in ('crosswalk','manifest','party-votes','party-votes-manifest')]]


def specification():
    return {'stage':41,'role':'preserved-source pre-scoring transport contract',
        'geography':'Stage25 historical canonical; Stage40 2026 frame mapped into same rational fields; original files unchanged',
        'candidatePolicy':{'exact':'unchanged source S/R reuse',
            'approximate_95':'guaranteed lower bounds >=95/100 in BOTH directions, unique dominant predecessor',
            'approximate_90':'guaranteed lower bounds >=90/100 in BOTH directions, unique dominant predecessor; broader development scenario',
            'S':'predecessor-flat source group-row to supported destination; no person identity requirement; printed working approximation',
            'R':'accepted same person in the dominant predecessor; frozen source normalized residual; broad primary/strict sensitivity',
            'linkageAmendment':'only geographically refused Stage26 direct edges in admitted 2014/2020 predecessor pairs are reassessed using unchanged name/context/election-wide competitor/component guards; no prior adjudication overwritten, no new person grouping',
            'outsideTier':'neutral exponent fallback, not zero observed strength; existing missing-table/mapping abstentions retained',
            'cancelled':'no source behavioural S/R; valid party votes remain usable',
            'maori':'population/party inputs and evidence inventoried; no general candidate coefficient extension'},
        'partyScenario':{'choice':'lexicographically minimum integral feasible population network vertex',
            'ordering':'(groupId, sourceCode, targetCode) ascending; sequentially minimize each flow with earlier flows fixed',
            'constraints':'all preserved group intervals, suppression bounds and exact destination controls; no marginal midpoints',
            'solver':'HiGHS dual simplex; primal/dual tolerance1e-9; certify integral witness exactly, else abstain',
            'weights':'w[source,target]=flow[source,target]/sum_destination flow[source,destination]',
            'partyVotes':'sum_source observedSourcePartyVotes * w; valid-party denominator transported with same weights',
            'meaning':'chosen feasible mean-input scenario under uniform within-source population-to-party-vote allocation; not an observed reconstruction or identified expectation',
            'nationalReconciliation':'not imposed; source party mass conserved over complete target population'},
        'historicalDiagnostic':{'targetYears':[2014,2020],'method':METHOD,
            'fits':'saved Stage33 primary constructed-input expanding-window S+R parameters/means, applied to observed local party inputs',
            'training':'no refitting, no recentering, no later parameters',
            'comparisons':['fallback','transport_90','transport_95','fallback_strict','transport_90_strict','transport_95_strict'],
            'commonPopulation':'available complete general slates in cumulative two-sided90; all six branches use these identical IDs',
            'exactFeatures':'retain in every corresponding broad/strict branch; no changed-boundary feature transfer in fallback',
            'strict':'same PRIMARY fit/means; only R linkage view changes, including exact records; compare with corresponding strict fallback',
            'reportingSamples':['whole common90','exact','approximate95-only','approximate90-only','cumulative95','cumulative90'],
            'metrics':'contest-equal MAE, sqrt(mean contest MSE), candidate-equal sensitivity; candidate-equal group bias; full-slate bias accounting',
            'gainSign':'fallback_error minus transport_error, positive is improvement',
            'influence':'five largest absolute paired contest effects, retain all primary observations',
            'noThresholdSelection':True,'eligibility':'outcome-independent source evidence/candidature/geography; target votes and winner score only'},
        '2026':'71-seat source party scenario, source party-seat S inventory and206-known-candidate readiness companion only; no candidate shares or national scenario',
        'uncertainty':'overlap does not bound candidate error; no transport variance/calibrated win probabilities; assumptions carried to next joint uncertainty layer',
        'stop':'no extra thresholds, fits, new sources, national comparisons or live forecast; S+Rpreferred/Sactive/baselinecontrol; operational records unchanged'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if not args.check:
        prior={str(p.relative_to(ROOT)):digest(str(p.relative_to(ROOT))) for p in sorted((ROOT/'data').rglob('*'))
               if p.is_file() and not str(p.relative_to(ROOT)).startswith(PREFIX+'/')}
        save('preservation.json',{'priorDataHashes':prior})
    save('input-contract.json',{'inputHashes':{p:digest(p) for p in INPUTS},'requiredSources':'transitive pinned boundary/split/linkage contracts; no acquisition or registry additions'},args.check)
    save('specification.json',specification(),args.check)
    geo=all_rows();inv=inventory(geo)
    save('geography.json',{'records':geo},args.check)
    save('historical-inventory.json',inv,args.check)
    folds=read('data/processed/models/joint-candidate-share/construction.json')['folds'];samples=[]
    for y in (2014,2020):
        fold=next(f for f in folds if f['branch']=='primary' and f['targetYear']==y)
        records=[r for r in inv['records'] if r['targetYear']==y]
        ids=[r['targetElectorateId'] for r in records]
        candidate_ids=[c['targetOccurrenceId'] for r in records for c in r['candidates']]
        if set(ids)&set(fold['trainingIds']):raise ValueError('Training/evaluation overlap')
        samples.append({'targetYear':y,'comparisonIds':ids,'candidateIds':candidate_ids,
            'ids95':[r['targetElectorateId'] for r in records if admitted(r['geography'],95)],
            'exclusiveTierCounts':dict(Counter(r['transportTier'] for r in records)),
            'savedFoldId':fold['id'],'trainingIds':fold['trainingIds'],
            'savedFit':fold['fits'][METHOD],'trainingOnlyMeans':fold['trainingOnlyMeans'],
            'sourceFeatureCoverage':{v:{'S':sum(c['s0Reported'] is not None for r in records for c in r['candidates']),
                'R':sum(c['R'][v]['valueFraction'] is not None for r in records for c in r['candidates'])} for v in ('broad','strict')}})
    save('sample-manifest.json',{'folds':samples,'scoresCalculated':False},args.check)
    print([{'year':s['targetYear'],'contests':len(s['comparisonIds']),'candidates':len(s['candidateIds']),
            'tierCounts':s['exclusiveTierCounts'],'features':s['sourceFeatureCoverage']} for s in samples])


if __name__=='__main__':main()
