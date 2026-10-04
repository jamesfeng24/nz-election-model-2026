"""Finite reporting for the frozen transport scenario and same-sample diagnostic."""
import argparse
from .common import ROOT, PREFIX, read


def render():
    evaluation=read(PREFIX+'/evaluation.json');ready=read(PREFIX+'/readiness-2026.json')
    samples=read(PREFIX+'/sample-manifest.json')['folds']
    party=read(PREFIX+'/party-construction.json')
    text=['# Stage41: practical boundary transport','',
        'Post-Stage40 implementation under the frozen Stage41 contract. No refitting, source acquisition, MCMC or live 2026 forecast. External gauss provisional; S+R preferred, S active and baseline mandatory. Original decisions and operational records remain unchanged.','',
        '## Coherent party-input scenario','',
        'All six general/Māori scopes across 2011→2014,2017→2020 and2023→2026 construct. A lexicographically minimum integral feasible population network satisfies the full parent-group/suppression bounds and destination controls. It is a chosen scenario, not a midpoint, observed reconstruction or expected population allocation. Source party votes and their valid denominator use the same source-outgoing population weights; exact rational mass is conserved across every target. Complete categories include parties without electorate candidates.','',
        'The within-source uniform population-to-party-vote distribution is assumed. Target valid-party totals are not observed turnout forecasts. Future national support is not supplied here, and no national reconciliation to a future scenario is imposed. The complete source national denominator includes every general and Māori electorate, never the selected overlap sample.','',
        '| Transition | General / Māori target vectors | Full source valid-party denominator |',
        '| --- | ---: | ---: |']
    for transition,data in party['transitions'].items():
        text.append(f"| {transition} | {len(data['scopes']['general']['targetPartyVectors'])} / {len(data['scopes']['maori']['targetPartyVectors'])} | {data['nationalSourceShares']['sourceValidPartyVotes']:,} |")
    text+=['','## Historical fixed-fit diagnostic','',
        'S+R uses the saved Stage33 primary expanding-window parameters and training means, applied to observed target local party support. All six branches share 37/47 complete slates; strict sensitivity changes only R linkage availability, with the same primary fit. Exact features remain in both branches. Positive paired gain means fallback error minus transported error. Errors are percentage points; MAE/RMSE are contest-equal. Full-slate bias cancels by construction and is an accounting check.','',
        '| Election | View / tier on common90 sample | Contests / candidates | MAE | RMSE | MAE gain over matching fallback | Transported S / R |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for fold in evaluation['folds']:
        data=fold['samples']['common90']
        for branch,metrics in data['metrics'].items():
            counts=fold['constructionCoverage'][branch];gain=data['pairs'].get(branch,{}).get('maeGainPP',0)
            text.append(f"| {fold['targetYear']} | {branch} | {metrics['contests']} / {metrics['candidates']} | {metrics['maePP']:.4f} | {metrics['rmsePP']:.4f} | {gain:+.4f} | {counts['transportedS']} / {counts['transportedR']} |")
    text+=['','### Exclusive additions and cumulative coverage','',
        'Tier-wide errors are not compared as if their populations were identical. The paired effects below compare each transport branch with its corresponding fallback on identical records.','',
        '| Election | Sample | Contests / candidates | Broad90 gain | Broad95 gain |',
        '| --- | --- | ---: | ---: | ---: |']
    for fold in evaluation['folds']:
        for name in ('exact','approximate95_only','approximate90_only','cumulative95','common90'):
            sample=fold['samples'][name];metrics=sample['metrics']['fallback']
            text.append(f"| {fold['targetYear']} | {name} | {metrics['contests']} / {metrics['candidates']} | {sample['pairs']['transport_90']['maeGainPP']:+.4f} | {sample['pairs']['transport_95']['maeGainPP']:+.4f} |")
    text+=['','### Category errors and bias','',
        'Category metrics weight each member candidate equally, with its original valid-candidate denominator. They do not sum to the contest-equal whole-slate metric.','',
        '| Election | Category / candidates | Fallback MAE / bias | Broad90 MAE / bias |',
        '| --- | --- | ---: | ---: |']
    for fold in evaluation['folds']:
        for group,data in fold['samples']['common90']['categoryMetrics'].items():
            a=data['methods']['fallback'];b=data['methods']['transport_90']
            if a:
                text.append(f"| {fold['targetYear']} | {group} / {data['candidates']} | {a['candidateEqualMaePP']:.4f} / {a['candidateEqualBiasPP']:+.4f} | {b['candidateEqualMaePP']:.4f} / {b['candidateEqualBiasPP']:+.4f} |")
    text+=['','### Material individual failures','',
        'Up to five largest losses under the broad 90% scenario, retained in every primary score:','',
        '| Election | Seat | Paired MAE gain |', '| --- | --- | ---: |']
    for fold in evaluation['folds']:
        effects=fold['samples']['common90']['pairs']['transport_90']['pairedContests']
        for effect in sorted((r for r in effects if r['gainPP']<0),key=lambda r:(r['gainPP'],r['targetElectorateId']))[:5]:
            text.append(f"| {fold['targetYear']} | {effect['targetName']} | {effect['gainPP']:+.4f} |")
    text+=['','### Interpretation','',
        'The broader 90% scenario lowers mean share error in both retained election environments; strict R gives similar gains. The tight 95% scenario slightly worsens 2014 and improves 2020. This is mixed evidence for a practical transport assumption, not permission to optimize a threshold or claim geographical reconstruction. There are substantial individual losses and only two reused election environments. Keep the frozen broader 90% development scenario and tight 95% sensitivity; carry transport error to the next uncertainty layer.','',
        "Stage26's original nonexact refusals remain intact. The supplementary direct link layer removes only that geographic refusal on admitted predecessor pairs and reapplies unchanged names, context, competitors and component checks. It does not reopen exceptions, assign persons or claim documentary identity. Source R is not target-boundary residual strength; S is not a same-person effect. No outgoing residual goes to a replacement.",'',
        '## 2026 readiness companion','',
        '| Scope | Exact | Approximate95 additions | Approximate90-only additions | Fallback |',
        '| --- | ---: | ---: | ---: | ---: |']
    for scope,counts in ready['coverage']['seatTiersByScope'].items():
        text.append('| '+scope+' | '+' | '.join(str(counts.get(k,0)) for k in ('exact','approximate_95','approximate_90','fallback'))+' |')
    text+=['','General exact 14 includes cancelled-source PortWaikato, leaving 13 held exact plus 15 approximate95 and 8 approximate90-only (36 held general sources in cumulative90). Cancelled source candidate features remain unavailable even though valid party votes can be transported. All Māori party inputs are constructed; the general fitted candidate coefficients are not extended to Māori.','',
        '| Scenario | Known candidate S / general R / strict R | Source party-seat S rows |',
        '| --- | ---: | ---: |']
    for tier in ('90','95'):
        counts=ready['coverage']['candidateFeatures'][tier]
        text.append(f"| {tier} | {counts['S'].get('supported',0)} / {counts['R'].get('supported',0)} / {counts['RStrict'].get('supported',0)} | {ready['coverage']['sourcePartySeatS'][tier].get('supported',0)} |")
    text+=['','One accepted Māori source residual is evidence only, requiring its separate baseline contract. Source party-seat S availability is inventoried independently of candidate announcements. All 206 known candidates and all 71 target seats are retained; zero slates are complete. No partial slate is normalized and no 2026 candidate share is produced. Missing features remain neutral assumptions, not known zero strength. Registered-group participation/continuity and complete nominations remain conditional.','',
        '## Validation and next action','',
        'Focused synthetic and actual-adapter tests cover rational thresholds, missing directions, suppressed/ambiguous membership, names/identity/replacements, coupled feasibility/conservation, no target-outcome admission, and fixed-fit/mean reuse. Independent arithmetic checks recompute vectors, paired errors and source transport; deterministic CLI checks preserve prior artifacts. Final check counts and CI are recorded in PROJECT_STATE and the PR.','',
        'Next separately authorized implementation: coherent joint local-party/candidate uncertainty, explicitly covering population-to-vote transport, predecessor-flat S/R error, unknown histories, local/candidate residual dependence and parameter uncertainty. Shared national error must enter once; overlap is not a calibrated variance. Official nomination refresh and Māori electorate-poll/unpolled-seat baseline remain separately bounded. No new threshold, model fit, acquisition, national comparison or live forecast begins automatically.','']
    return '\n'.join(text)


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    path=ROOT/'docs/stage41-transport-findings.md';raw=render().encode()
    if a.check:
        if path.read_bytes()!=raw:raise ValueError('Stale Stage41 findings')
    else:path.write_bytes(raw)


if __name__=='__main__':main()
