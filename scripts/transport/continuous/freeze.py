"""Pin audited evidence, all slates and unchanged fits before predictions."""
import argparse
from collections import Counter
from scripts.transport.freeze import INPUTS as INHERITED_INPUTS
from scripts.transport.geography import all_rows
from .common import ROOT, PREFIX, read, digest, save
from .features import context,links_for_geography,flow_index
from .inventory import inventory

INPUTS=list(INHERITED_INPUTS)+[
    'data/processed/forecast-transport/party-construction.json',
    'data/processed/forecast-transport/historical-inventory.json',
    'data/processed/forecast-transport/sample-manifest.json',
    'data/processed/forecast-transport/construction.json',
    'data/processed/forecast-transport/readiness-2026.json',
    'docs/stage42-within-seat-evidence-audit.md']


def specification():
    return {'stage':42,'role':'frozen continuous predecessor feature diagnostic',
        'audit':'preserved sources do not identify residential fragment political composition; no finer flow; zero acquisition',
        'flow':'F_spt=V_sp*w_st; exact cached Stage41 feasible witness; uniform within-source party voting',
        'weights':'lambda_spt=F_spt/sum_j F_jpt, ALL genuine predecessors including unsupported features',
        'S':'sum lambda*(printed source split fraction - saved S mean) over supported source group destinations',
        'R':'sum lambda*(source normalized residual - saved R mean) over uniquely accepted same-person source in any genuine predecessor',
        'missing':'unsupported exponent contribution zero; do not renormalize supported mass or infer zero strength',
        'exceptions':'no group, entrant/unsupported continuity or zero party mass => neutral continuous contribution; no invented weights; cancelled/missing source table => unsupported component; target mapping incoherence => slate abstention',
        'sharedGroups':'preserved whole-group continuity only; never distribute alliance mass to constituents or duplicate local group support',
        'linkage':'reversible geographic-only reassessment on all genuine historical predecessors; unchanged names/context/election-wide competitors/components; held sources/targets; broad primary and strict sensitivity',
        'fits':'fixed Stage33 primary expanding-window S+R for2014/2020, with exact saved means/training IDs; no refit/recentering',
        'sample':'all constructible held general2014/2020 complete slates; Maori retained coverage-only',
        'policies':['exact_fallback','stage41_90','continuous'],
        'sensitivity':'same three policies under strict R availability; same primary fit and means, no Cartesian branches',
        'inputs':'observed target local party support identical across policies, complete retrospective slates',
        'metrics':'contest-equal MAE/RMSE, candidate-equal sensitivity/category bias; full sample and exclusive exact/95/90/below90 bands; positive gain=comparator MAE-policy MAE',
        'reporting':'all records retained, largest five losses/gains; fold-specific and contest-weighted pooled; two reused environments not independent seat replications',
        '2026':'source party-seat and known candidate component readiness; center using latest saved2023primary training means as named reference only; no candidate predictions; separate Maori baseline/polls',
        'uncertainty':'party/candidate feature transport are modelling assumptions, population overlap does not bound candidate error; no calibrated probabilities',
        'stop':'no other flow/feature searches; next separately authorized coherent local/candidate uncertainty'}


def build(check=False):
    if not check:
        prior={str(p.relative_to(ROOT)):digest(str(p.relative_to(ROOT))) for p in sorted((ROOT/'data').rglob('*'))
            if p.is_file() and not str(p.relative_to(ROOT)).startswith(PREFIX+'/')}
        save('preservation.json',{'priorDataHashes':prior})
    save('input-contract.json',{'inputHashes':{p:digest(p) for p in sorted(set(INPUTS))},
        'acquisition':{'queries':0,'resources':0,'finerFlowImplemented':False},
        'requiredSources':'transitive preserved boundary/election/split/linkage contracts; unrelated registry additions permitted'},check)
    save('specification.json',specification(),check)
    geo=all_rows();ctx=context();edges,companion=links_for_geography(geo,ctx['occurrences']);flows=flow_index(geo,ctx['occurrences'])
    inv=inventory(geo,ctx,flows,edges);save('inventory.json',inv,check);save('supplemental-links.json',companion,check)
    samples=[]
    for f in read('data/processed/forecast-transport/sample-manifest.json')['folds']:
        rows=[r for r in inv['records'] if r['targetYear']==f['targetYear']]
        samples.append({k:f[k] for k in ('targetYear','savedFoldId','trainingIds','savedFit','trainingOnlyMeans')}|
            {'comparisonIds':[r['targetElectorateId'] for r in rows],
             'candidateIds':[c['targetOccurrenceId'] for r in rows for c in r['candidates']],
             'exclusiveTierCounts':dict(Counter(r['transportTier'] for r in rows)),
             'originalStage41ComparisonIds':f['comparisonIds']})
    save('sample-manifest.json',{'folds':samples,'scoresCalculated':False},check)
    print([(s['targetYear'],len(s['comparisonIds']),len(s['candidateIds']),s['exclusiveTierCounts']) for s in samples])


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();build(a.check)


if __name__=='__main__':main()
