"""Deterministic Stage37 findings; no fitting or additional score definitions."""
import argparse
from .common import OUT, ROOT, read


def build():
    manifest=read(OUT/'allocation-manifest.json');inventory=read(OUT/'inventory.json')
    evaluation=read(OUT/'external-evaluation.json');verification=read(OUT/'independent-verification.json')
    lines=['# Stage37 — category interface and bounded external benchmark', '',
           'Frozen protocols e65a5d5; acquisition/schema clarification82d412e; complete allocation/point checkpoint aa74719 precedes external scores. No inference, candidate predictions/scores, interval recalibration or operational selection.', '',
           '## Interface readiness and allocation sensitivity', '',
           'Eight primary cases, two fixed conditional policies,15/16/17/17 fine ballot groups. Current/election-day paired draw IDs and explicit support are unchanged. Whole Other is allocated once; no remainder is dropped. Benchmark independently allocates TOP within its coarse Other; it never borrows the national model TOP posterior. All groups remain even without electorate candidates.', '',
           'Recent rounded minor reports supply relative working weights where available, then supported prior shares; unsupported entrants have0.001 neutral weights. Sensitivity uses prior shares/seeds only. Shared alliances stay whole and no constituent continuity is invented. Retrospective rosters, inferred availability and unknown decided-denominator assumptions remain flagged. Reused polls are not independent evidence; these fixed conditional allocations are not a fine-party posterior or calibrated interval.', '',
           '| Case | Fine groups | Model Other pp | Average Other pp | Model policy TV pp | Average policy TV pp |',
           '|---|---:|---:|---:|---:|---:|']
    for c in manifest['cases']:
        p=c['policies']['recent_report_prior']
        lines.append(f"| {c['id']} | {len(c['fineCategories'])} | {100*p['model']['summaries']['electionDay']['allocatedOtherMean']:.4f} | {100*p['average']['summaries']['point']['allocatedOtherMean']:.4f} | {c['policyDifference']['model']['totalVariationPP']:.4f} | {c['policyDifference']['average']['totalVariationPP']:.4f} |")
    lines += ['', '### Evidence-informed versus assumption-driven mass', '',
              'Prior support informs relative weights but its temporal transport is an assumption. The table separates reported weights, prior weights and neutral seeds; it does not imply any allocation is known without error. Zero reported support is not structural impossibility.', '',
              '| Case | Recent eligible reports | Model recent-report mass pp | Model prior mass pp | Model seed mass pp |',
              '|---|---:|---:|---:|---:|']
    inv={c['id']:c for c in inventory['cases']}
    for c in manifest['cases']:
        masses=c['policies']['recent_report_prior']['model']['summaries']['electionDay']['allocatedMassByBasis']
        lines.append(f"| {c['id']} | {len(inv[c['id']]['reports'])} | {100*masses.get('recent_published_working_approximation',0):.4f} | {100*masses.get('supported_prior',0):.4f} | {100*masses.get('neutral_seed_assumption',0):.4f} |")
    lines += ['', '## External artifact availability', '',
              'Exactly20 distinct official resources preserved/checksummed; current main matches pinned ef76cf6562e1d028b4fff46d063f4b93945299de. Retrospective gauss case means exist for all three56-day cases. Ensemble CSV provides case-level signed mean errors: named means recover by adding the exact archived base scoring outcome. Base/gauss schemas and outcomes agree. This does not invert aggregate scores or reconstruct Other distributions. No saved joint NPZ archives or release assets were exposed by the official manifests; published downloads are current outputs, not these historical draw cases.', '',
              '**2020 unavailable for the requested six/seven-category comparison:** Te Pāti Māori is folded into external Other. No missing share, five-party substitution or pseudo-draw is invented. Every attempted case remains visible.2017/2023 form only a two-case supported subset, not the requested complete three-election test.', '',
              'The cutoff calendar days match exactly, but external hour/timezone is unarchived. Both timing rules use inferred publication; external uses pollster-specific lag and different poll sources, rounding/count assumptions and coarsening. Source snapshots are retrospective. Ensemble weights use other elections, including later elections in earlier cases. Published configuration comments say minor-party error scaling was informed by2011–2023 errors; chronology of that choice is not independently proven. Current fixed gauss does exclude held-out result anchors in the inspected marshal, but this does not establish fully earlier-only hyperparameter development.', '',
              '### Six named parties, original national-share denominator', '',
              'NAT/LAB/GRN/ACT/NZF/MRI, no subset normalization. Other and TOP are excluded. Equal election weighting within the explicitly incomplete two-case subset.', '',
              '| Election | Our model MAE / RMSE pp | Average MAE / RMSE pp | Gauss MAE / RMSE pp | Ensemble MAE / RMSE pp |',
              '|---|---:|---:|---:|---:|']
    systems=['own_model','own_average','external_gauss','external_ensemble']
    for c in evaluation['cases']:
        if 'namedSix' not in c:
            lines.append(f"| {c['year']} | unavailable | unavailable | MRI inside Other | MRI inside Other |")
        else:
            lines.append('| '+str(c['year'])+' | '+' | '.join(f"{c['namedSix'][s]['maePP']:.4f} / {c['namedSix'][s]['rmsePP']:.4f}" for s in systems)+' |')
    p=evaluation['supportedSubsetPooled']['namedSix']
    lines.append('| Supported two-case mean | '+' | '.join(f"{p[s]['maePP']:.4f} / {p[s]['rmsePP']:.4f}" for s in systems)+' |')
    lines += ['', '### Major-party signed errors (prediction minus result, pp)', '',
              '| Election / party | Our model | Average | Gauss | Ensemble |', '|---|---:|---:|---:|---:|']
    for c in evaluation['cases']:
        if 'namedSix' in c:
            for party in ('NAT','LAB'):
                lines.append(f"| {c['year']} / {party} | "+' | '.join(f"{c['namedSix'][s]['partyErrorPP'][party]:.4f}" for s in systems)+' |')
    lines += ['', '### Complete coarse seven-category points (gauss only)', '',
              'All external categories outside the six named parties are aggregated once into Other including TOP. This uses actual complete means, not an inferred missing Other distribution. Ensemble lacks complete means/draws and is absent from this table.', '',
              '| Election | Our model MAE / RMSE pp | Average MAE / RMSE pp | Gauss MAE / RMSE pp |', '|---|---:|---:|---:|']
    for c in evaluation['cases']:
        if 'completeCoarseSeven' in c:
            lines.append('| '+str(c['year'])+' | '+' | '.join(f"{c['completeCoarseSeven'][s]['maePP']:.4f} / {c['completeCoarseSeven'][s]['rmsePP']:.4f}" for s in systems[:-1])+' |')
    p=evaluation['supportedSubsetPooled']['completeCoarseSeven']
    lines.append('| Supported two-case mean | '+' | '.join(f"{p[s]['maePP']:.4f} / {p[s]['rmsePP']:.4f}" for s in systems[:-1])+' |')
    lines += ['', '## Numerical/calibration and decision limits', '',
              'Artifact commits pin the published records and inspected code, but cached case run fingerprints, exact prepared polling snapshots, dependency/seed/settings manifests are not archived. Configuration comments do not prove every cached case was generated under the current settings; exact reproduction and chronology of development choices remain unverified.', '',
              'External gauss R-hat/ESS:2017 1.02656/94.66;2020 1.01536/218.08;2023 1.01561/179.92, zero reported divergences. Only107/93/164 parameters were summarized; full latent mixing and tail ESS are unavailable. Record these limitations rather than pretending archived estimates pass our inference checks. No external joint samples or matching interval endpoints support harmonized CRPS/coverage/width/energy. Standard deviations/PIT/aggregate scores are not pseudo-distributions. Our Stage36 undercoverage (90%44/56;50%20/56) remains unchanged and unresolved.', '',
              'The supported point subset modestly favours our model, but two elections, missing2020, different data/calibration and numerical limitations do not establish superiority or calibration. D070 gives ownership no preference. A sufficiently fair future comparison may justify adopting external code with licensing/attribution, preserving ours as a benchmark. No replacement or automatic protective hurdle is imposed here.', '',
              'A small separately authorized three-case gauss archive run is worth considering for joint-distribution/calibration evidence, not an entire ensemble tournament. See [executable proposal](stage37-external-run-proposal.md);2020 category representation and prepared data/expanded numerical diagnostics must be frozen before it can resolve the full comparison. No external inference ran.', '',
              '## Candidate replay handoff — not executed', '',
              'The [precise replay contract](stage37-candidate-replay-contract.md) and pinned candidate-replay-plan reference four saved primary fits,182 complete contests and14/56-day horizons; no candidate calculation occurs here. The allocation interface is ready for **conditional scenario replay** of the saved baseline/S/R/S+R fits, preserving their specifications. Every national draw ID must be shared across electorates; apply Stage31 complete local affinity, then candidate mapping/intensity closure per draw. Average transformed candidate shares to obtain expected shares, rather than transforming only mean support. Do not add a second common national error draw. Run primary and the single allocation sensitivity, retaining all candidates and explicit missing-feature fallbacks. Category scenario uncertainty, Stage36 undercoverage, retrospective slates/rosters and publication assumptions limit a fully as-of claim. External availability is independent and cannot block this interface.', '',
              '## Validation and reproduction', '',
              f"Independent arithmetic verifies{verification['checks']['policyWeights']} policy weights,{verification['checks']['convertedReports']} report conversions,{verification['checks']['completeVectors']:,} full vectors,{verification['checks']['expectedShareVectors']} expected vectors,{verification['externalPointAndPoolingChecks']} point/pooling checks; all{verification['priorDataFilesByteIdentical']:,} prior data files byte-identical and20 resources checksummed.", '',
              'The portable gzip companion changes only header byte9 to255: all32 decompressed allocation payloads and numerical values remain unchanged. Original headers/SHA and construction contract preserve exact reversibility; no tolerance or byte-check relaxation. The historical statistical-document appendix was moved into a companion to preserve Stage28 input bytes. See [preservation details](stage37-research-handoff.md).', '',
              'Focused synthetic/actual-adapter tests cover conservation, zeros/missingness, TOP, whole alliances/renames, cutoff/outcome independence, exact dates and subset-score arithmetic. Deterministic `python -m scripts.polling.category_interface.run --check`, `verification --check` and `report --check` use saved archives only; no MCMC or candidate runner. Final-head GitHub CI is reported separately in the handoff and runs the configured full tests/source checks/earlier deterministic checks/frontend. No configured Python formatter/linter; compilation and whitespace checks apply.', '',
              '**Next decision:** separately authorize cached-draw fixed-candidate conditional replay through this two-policy interface; independently decide whether the small external distribution run warrants authorization before deployment. Preserve national model plus average and S/S+R active/R challenger/baseline control. No new model, allocation tuning, inference, live forecast or MMP begins automatically.', '']
    return '\n'.join(lines)


def run(check=False):
    path=ROOT/'docs/stage37-national-interface-results.md';content=build()
    if check:
        if path.read_text()!=content:raise ValueError('Stale Stage37 report')
    else:path.write_text(content)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
