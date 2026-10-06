"""Reproducible Stage47 numerical, width and structural findings."""
from pathlib import Path
import numpy as np
from .common import ROOT, PREFIX, arguments, read, verify


def table(header, rows):
    return ['| '+' | '.join(header)+' |', '| '+' | '.join('---' for _ in header)+' |',
            *['| '+' | '.join(str(v) for v in r)+' |' for r in rows], '']


def build():
    evaluated = read(PREFIX+'/evaluation.json')
    construction = read(PREFIX+'/construction.json')
    attribution = read(PREFIX+'/attribution.json')
    prior = read(PREFIX+'/prior-audit.json')
    independent = read(PREFIX+'/verification.json')
    structure = read(PREFIX+'/structure.json')
    structural = read(PREFIX+'/structural-diagnostics.json')
    candidates = [c for c in construction['cases'] if c['layer'] == 'candidate']
    composed = [c for c in construction['cases'] if c['layer'] == 'composed']
    component_diagnostics = [r['metadata']['conditionalIntegration'] for c in construction['cases'] if c['layer'] != 'composed' for r in c['records']]
    composed_diagnostics = [r['metadata'][k]['conditionalIntegration'] for c in composed for r in c['records'] for k in ('local','candidate')]
    out = ['# Stage47: numerical expectation repair and width attribution', '',
        '## Decision and scope', '',
        '**Recommendation B: one separately authorized Gaussian dispersion comparison.** Carry the numerical-only corrected Stage45 Gaussian law forward; preserve original Stage44–46 decisions and controls. S+R remains preferred, S active, baseline mandatory; no mean, scale or national model was fitted here.', '',
        'The future frozen contract compares the corrected control, one earlier-trained constant candidate-seat balance adjustment, and one strongly pooled conditional adjustment. The two future characteristics are R-support deficit and continuous historical nonmajor support. Historical support replaces geography rather than adding a third predictor; it does not encode a target-result exception or an undated challenger-strength claim. No challengers are fitted in Stage47. See [future contract](../data/processed/uncertainty-expectation/next-test-contract.json).', '',
        '## Numerical repair', '',
        'Stage46’s worst reported conditional gap was **0.738928pp**. Larger independent references reduce the old-location discrepancy to **0.589445pp**, with **0.000157pp** reference spread. The reference error was material to the reported number, but the underlying location error remains real. This is a numerical expectation correction, not a new statistical distribution or bias fit.', '',
        f'All **{sum(v["checkedInputs"] for v in component_diagnostics)} component conditional inputs** and **{sum(v["checkedInputs"] for v in composed_diagnostics)} composed local/candidate conditional inputs** passed the retained **0.05pp** criterion using a stricter 0.02pp construction/reference target. Maximum accepted composed reference gap **{max(v["maximumConditionalGapPP"] for v in composed_diagnostics):.8f}pp**. Finite independent-reference convergence is not a rigorous absolute error bound.', '',
        f'Independent raw-option covariance references on 12 first/middle/last candidate seats have maximum conditional gap **{max(r["conditionalGapPP"] for r in independent["independentRawCovarianceReferences"]):.6f}pp**, reference disagreement **{max(r["referenceDisagreementPP"] for r in independent["independentRawCovarianceReferences"]):.6f}pp**. Repeated labels, unique labels, zero faces and near-boundary fixtures are separately tested. Every constructed input is checked by two independent scrambled Gaussian integrations or escalating GH rules; a separate 262,144-node reference was not calculated for every composed input.', '',
        'Shared ballot-label effects and individual effects use their actual contrast covariance. Supported active faces alone enter the softmax solve; predicted zeros remain locked. One-dimensional Gaussian reductions and damped analytic Newton solving are reusable, with independent convergence checks and fixed caps. No scale, mean coefficient, source, national inference or observation was changed.', '',
        '### Separate numerical limitations', '',
        'Components use 32,768 draws; composed cases use the prespecified 512 common stream indices across all 193 seats, selected from the preserved national permutation. Representative composed checks use 256/512/1,024 draws. **Both control and corrected banks fail the simulation precision gates at the cap.** This does not invalidate conditional-location checks, but prevents fine score/probability claims. No draw count or tolerance was selected after scores.', '']
    changes = evaluated['precision']['rounds'][-1]['changesPP']['corrected']
    out += table(['512→1,024 representative change', 'maximum pp'], [[k, f'{v:.6f}'] for k,v in changes.items()])
    pair_gap = max(c['methods']['corrected']['summary']['maximumEnergyPairDifferencePP'] for c in evaluated['cases'] if c['layer']=='composed')
    out += [f'Full-frame composed energy-score permutation-pair disagreement reaches **{pair_gap:.6f}pp**; this separately limits joint-score precision. The small repaired-versus-control energy differences must not be interpreted as resolved improvements.', '']
    finite = max(abs(x) for c in composed for r in c['records'] for x in r['metadata']['candidateFiniteBankShiftPP'])
    nonlinear = max(abs(x) for c in composed for r in c['records'] for x in r['metadata']['genuineNonlinearShiftPP'])
    component_shift = max(abs(x) for c in candidates for r in c['records'] for x in r['metadata']['meanShiftPP'])
    out += [f'Maximum component simulated mean shift **{component_shift:.6f}pp**. Composed candidate finite-bank shift **{finite:.6f}pp**, while genuine local-to-candidate nonlinear expectation shift reaches **{nonlinear:.6f}pp**. The latter is retained: no final mean is forced back to the national-input-only deterministic prediction. Component expected shares remain frozen arithmetic means; composed expected shares use averaged conditional candidate means (Rao–Blackwell), with finite upstream precision explicit. Ordinary paired MAE compares both finite-bank means; separate expected-share summaries are not falsely presented as a pure numerical-effect comparison against an exact control expectation.', '',
        '## Major-candidate full interval widths', '',
        'All widths are full percentage-point spans, **not ± margins**. Conditional candidate distributions use observed local-party inputs. Composed distributions use cached external gauss 56-day draws plus local/candidate shocks. All 257 candidate seats and 193 composed seats remain. The forecast-leading pair is chosen from the fixed deterministic prediction, never the observed winner.', '']
    width_cases = evaluated['widthInventory']['corrected']['cases']
    for group in ('national', 'labour', 'forecast_pair'):
        out += ['### '+group.replace('_',' '), '']
        rows = []
        for c in width_cases:
            s = c['summaries'][group]
            rows.append([c['id'], s['contests'], *[f'{s["intervals"][str(l)]["widthPP"]:.2f}' for l in (50,80,90)],
                         *[f'{s["intervals"][str(l)]["covered"]}/{s["intervals"][str(l)]["total"]}' for l in (50,80,90)],
                         f'{s["crpsPP"]:.3f}', *[f'{s["intervals"][str(l)]["intervalScorePP"]:.3f}' for l in (50,80,90)]])
        out += table(['case','seats','50 width','80 width','90 width','50 covered','80 covered','90 covered','CRPS','IS50','IS80','IS90'],rows)
    pairs = read(PREFIX+'/leading-pair-options.json')
    out += ['### Individual shares of the forecast-leading two candidates', '',
            'These spans concern each selected candidate, averaged within its contest; they are not the difference/margin interval above. Two correlated candidates are not two independent temporal replications. No selected-party renormalization is used.', '']
    out += table(['case','candidates','50 width','80 width','90 width','CRPS','90 covered','IS90'],
        [[c['id'],c['summary']['coordinates'],*[f'{c["summary"]["intervals"][str(l)]["widthPP"]:.2f}' for l in (50,80,90)],
          f'{c["summary"]["crpsPP"]:.3f}',f'{c["summary"]["intervals"]["90"]["covered"]}/{c["summary"]["intervals"]["90"]["total"]}',
          f'{c["summary"]["intervals"]["90"]["intervalScorePP"]:.3f}'] for c in pairs['sources']['corrected']['cases']])
    out += ['### Width distributions and weighting', '']
    original = read(PREFIX+'/original-audit.json')['sources']['originalStage45_8000']['cases']
    common = evaluated['widthInventory']['common_control']['cases']
    rows = []
    for c in width_cases:
        a = next(r for r in original if r['id']==c['id'])['summaries']
        b = next(r for r in common if r['id']==c['id'])['summaries']
        for g in ('national','labour','forecast_pair'):
            rows.append([c['id'],g,f'{a[g]["intervals"]["90"]["widthPP"]:.2f}',
                         f'{b[g]["intervals"]["90"]["widthPP"]:.2f}',f'{c["summaries"][g]["intervals"]["90"]["widthPP"]:.2f}'])
    out += table(['case','group','original8000 full90','common control full90','corrected full90'],rows)
    rows=[]
    for layer,pools in evaluated['widthInventory']['corrected']['pooled'].items():
        for weighting,groups in pools.items():
            for g,s in groups.items():
                v=s['intervals']['90']; q=v['seatMeanWidthDistribution']['quantilesPP']
                rows.append([layer,weighting,g,f'{v["widthPP"]:.2f}',f'{q["10"]:.2f}',f'{q["50"]:.2f}',f'{q["90"]:.2f}'])
    out += table(['layer','weights','group','90 mean width','seat p10','seat median','seat p90'],rows)
    out += ['Whole-slate averages do not describe competitive-seat intervals. Other candidates are reported separately in the inventory with their actual errors and denominators. Candidate-equal and contest/equal-election weighting are distinct; seat distributions describe the selected exact/continuous-transport sample, not the whole country.', '',
        '## Numerical-only comparison to original Gaussian controls', '',
        'Original Stage45 8,000-draw artifacts are untouched; missing 80% summaries were calculated from their cached banks. The unchanged-law Stage46 32,768 control is a separate numerical companion, not a rewritten original result. Composed repaired/control comparisons below use identical 512 indices; the original 8,000-bank summaries do not have identical sampling precision.', '']
    rows=[]
    for c in evaluated['cases']:
        if c['layer']=='local_party':continue
        a,b=c['methods']['common_control']['summary'],c['methods']['corrected']['summary']
        rows.append([c['id'],f'{a["contestEqualCRPSPP"]:.6f}',f'{b["contestEqualCRPSPP"]:.6f}',
                     f'{c["correctedMinusControl"]["crpsPP"]:+.6f}',f'{c["correctedMinusControl"]["maePP"]:+.6f}'])
    out += table(['case','common control CRPS','corrected CRPS','corrected−control CRPS','corrected−control finite-mean MAE'],rows)
    out += ['Conditional N/L draws are **exactly unchanged in all 578 component seats**, verified from cached arrays: within-remainder repair cannot change aggregate major balance/mass under this tree. Tiny conditional whole-slate changes are in other options. Composed differences also reflect repaired local remainder allocation passing through candidate normalization. Their small score changes are not a new statistical improvement or calibration claim; finite-bank uncertainty is larger.', '',
        '## Width drivers', '',
        'The bounded ablation covers exactly nine prespecified first/middle/last composed seats. Each row removes one block, keeps common random streams and recomputes outcome-free locations for that changed covariance. Width differences are **not additive variance shares** and the sample is not a national average. National-at-mean uses the full 4,096 cached-national mean; its comparison to 512 selected scenarios includes finite sampling differences.', '']
    rows=[]
    for policy in read(PREFIX+'/companion-contract.json')['attribution']['policies']:
        rows.append([policy,*[f'{np.mean([r["policies"][policy]["widths"][g]["intervals"]["90"]["widthPP"] for r in attribution["records"]]):.2f}' for g in ('national','labour','forecast_pair')]])
    out += table(['policy','NAT full90 width','LAB full90 width','pair margin full90 width'],rows)
    out += ['Candidate seat/balance variation is the largest removable block in this diagnostic; national and local uncertainty remain consequential. Shared shocks still matter to cross-seat dependence; moving a shock from shared to seat-specific would not itself reduce its marginal variance. Within-remainder shocks cannot directly widen conditional N/L intervals, though they can affect a nonmajor leading pair and upstream candidate composition.', '',
        'For each representative seat, analytic law of total variance partitions candidate variance into E[Var(candidate | national, local)] plus Var(E[candidate | national, local]). It retains the finite upstream sample and the mass×balance interaction. In 2020 several upstream contributions are as large as or larger than the candidate contribution. We do not assign independent national/local percentages without nested local replication. Full-frame 578-vector analytic mass/balance variance and covariance identities are in prior-audit.json.', '',
        '## Prior versus data', '',
        'Three prior election-equivalents remain unchanged. Prior **weight** is 3/(E+3); actual variance contribution depends on prior scale and observed second moments. Candidate2014 is fully prior-driven. At2023 the candidate balance shared/seat prior weight is 50%, but its actual combined variance fraction is **55.1714%**. Local balance’s combined fraction is47.2336%; local major mass71.8946%. Broad widths therefore reflect both data and substantial prior assumptions, not merely numerical integration.', '',
        'Every layer/coordinate/fold/kind follows below. Variance is dimensionless log-unit squared; within scales are raw exchangeable log-intensities with projection/label covariance, not each CLR coordinate SD. Empirical-only estimates are descriptive and never substituted as forecasts.', '']
    out += table(['layer','target','coordinate','kind','earlier E','prior weight','history variance','prior variance','result SD'],
        [[r['layer'],r['targetYear'],r['coordinate'],r['kind'],r['earlierEnvironments'],f'{r["priorWeight"]:.3f}',
          f'{r["historicalVarianceContribution"]:.6f}',f'{r["priorVarianceContribution"]:.6f}',f'{r["resultingSD"]:.6f}'] for r in prior['scaleAttribution']])
    out += ['## Heterogeneity, dependence and remaining persistence', '',
        'Frozen R-support and target-incoming population fragmentation diagnostics retain unknowns, full/partial/no support and all seats. Within-election balance-error dispersion versus R support is inconsistent (Pearson2014/17/20/23: +0.038,+0.053,+0.307,−0.096). Fragmentation versus squared balance error is −0.190/−0.064 in2014/20; exact-only folds have no fragmentation variation. This does not support a blanket claim that more history or stronger continuity makes seats less uncertain.', '',
        'Matched local/candidate raw-log balance and mass residual associations, centered within election with equal total election weight, are −0.011 and −0.091. Across just four election means the balance association is −0.764; this is sparse shared-environment evidence, not many independent seat replications. Conditional definitions can induce relationships; they do not establish independence or automatic double-counting of national error. A new covariance fit is not the next priority.', '',
        'Remaining complete-S+R balance-error correlations on certified exact seat pairs2014→17/2017→20/2020→23 are −0.111,+0.274,−0.048. Mass correlations are +0.114,+0.227,+0.307. These are descriptive persistence checks after the full mean, not Stage30 personal strength evidence or authorization for a latent seat effect.', '',
        '## Structural-continuity amendment', '',
        'The amendment was recorded after Stage47 began and before its new structural tables. All257 seats, including successful forecasts, use identical evidence rules; no viability threshold or exceptional-seat list is chosen from errors. Every nonmajor source occurrence contributes a continuous source-support proxy; this population-weighted candidate-share proxy is not a reconstructed target candidate vote.', '',
        f'Coverage: {structure["summary"]["sourceOccurrenceRepresentations"]} source occurrence representations, {structure["summary"]["sourceStatusCounts"]}. Target states: {structure["summary"]["targetStatusCounts"]}. There are **no preserved dated new-strength facts** and **no verified complete56-day rosters**. Nonmatch remains unresolved, not departure. Documentary distinctness alone is not evidence of retirement or contender viability. {structure["summary"]["SDespiteNoAcceptedPersonLinkCandidates"]} target candidates retain source S without an accepted person link; this is permitted party/geography behavior, not proof that their S is obsolete.', '']
    out += table(['year','seats','source support vs centered squared balance','source support vs centered squared mass','unknown target states'],
        [[r['year'],r['seats'],f'{r["associations"]["balance"]["sourceSupportVsSquaredWithinElectionError"]["pearson"]:.3f}',
          f'{r["associations"]["mass"]["sourceSupportVsSquaredWithinElectionError"]["pearson"]:.3f}',r['targetStates'].get('unresolved',0)] for r in structural['byElection']])
    out += ['Historical nonmajor support is associated with balance dispersion in2014/17, weakly in2023 and not2020. The pooled impression is not a universal tactical regime; election composition and small-share log denominators matter. Descriptive centering/standardization subtracts election errors for diagnosis only and is not actual forecast-standardized uncertainty.', '',
        '### Highlighted hypotheses verified against actual features', '',
        '- **Ōhāriu2017:** United Future’s replacement retains Dunne-derived centered S(+0.294), but receives no outgoing R. National retains its own suppressed S(−0.275) and same-person R(−0.347). Saved baseline/S/R/joint balance errors are−0.306/+0.433/+1.082/+1.427; joint mass error+0.471. The preserved secondary chronology dates Dunne’s retirement21August, **after** the actual29July56-day cutoff; publication is unverified. This supports a retrospective obsolete-participant hypothesis, not a known forecast-time reset rule.',
        '- **Auckland Central2020:** Swarbrick receives Roche-derived negative S(−0.328), R0; the major replacement also receives predecessor party S without outgoing R. Baseline versus joint mass errors−0.247/−0.546 show allocation error alongside balance error(+0.440). No preserved dated pre-cutoff challenger-strength fact establishes an eligible reset. In2023 Swarbrick is linked, with positive S/R, while balance error remains sizeable: continuity is not sufficient to ensure accuracy.',
        '- **Tāmaki2023:** van Velden receives Claridge-derived negative ACT S(−0.375) and no outgoing R; O’Connor retains his own positive S/R. Joint balance error−1.026 and major-mass error−2.046 are both large. ACT’s actual-minus-joint share error is a major pp miss, not only a small-denominator log artefact. Stage46’s balance-only t test did not test third-party allocation. This identifies a separately scoped mean-continuity hypothesis; it does not authorize a reset or historical override.',
        '- **Epsom:** accepted Seymour/Goldsmith continuation coexists with large2017/20 balance errors(+0.897/+0.604) but near-zero2023 balance error(+0.018), while2023 mass error is+0.400. Stable tactical participants are not interchangeable with tactical transitions and do not automatically require wider intervals.', '',
        'All saved four-model comparisons are loaded only on matching complete exact IDs; changed-seat baseline/R predictions are not manufactured. Source S names, centered contributions, supported masses, accepted links, strict flags, fallback reasons and balance/mass/pp errors are separately preserved. The actual source-only R constructor and outcome-counterfactual tests verify the existing no-outgoing-transfer guard. Structural evidence is insufficient for a universal forecast-time departure/strength classifier; a future S-continuity mean test needs its own authorization, coherent complete-slate formulation and dated information.', '',
        '## Practical next action and deployment blockers', '',
        'Implement the frozen three-restriction Gaussian candidate-seat balance scale comparison only if separately authorized. Constant recalibration distinguishes scale-level adequacy from conditional heterogeneity. The conditional model is strongly pooled, can increase or decrease scales, and must earn complexity on proper scores and fold-specific coverage/sharpness. There is no every-fold materiality veto or promise to halve widths. No additional coordinates, tail families, covariance, mean reset or new acquisition are bundled into it.', '',
        'Current blockers remain finite composed simulation precision, scarce repeatedly reused election environments, prior/parameter uncertainty, fragment composition and fine-party allocation assumptions, historical cutoff/roster availability, complete live nominations, separate Māori baseline and electorate-poll measurement, turnout/reconciliation and MMP assembly. Winner frequencies are development diagnostics; finite-bank zero is not mathematical impossibility.', '',
        'Manual adjustments must keep dated reasons, unadjusted outputs, author/review/expiry and coherent slate changes; a mean change does not justify lower variance. They cannot be assumed to identify every future surprise and do not justify narrowing all remaining seats. Electorate polls are uncertain measurements (question, denominator, dates, sample and dependence), with Māori polls separately scoped. National Te Pāti Māori party support differs from Māori candidate support. Party-vote reconciliation must not constrain candidate-vote totals.', '',
        '## Validation and reproduction', '',
        f'Independent checks cover **{independent["simplexVectorsChecked"]:,} corrected simplex vectors**, all578 component major-vector equivalences, scalar CRPS/proper intervals on first/middle/last each case, independent raw-covariance references, prior contributions/product covariance, leakage/chronology, zero faces, repeated labels and random-stream separation. Local/Ubuntu check status is recorded in PROJECT_STATE and the final PR handoff; hashes alone do not prove Linux reconstruction.', '',
        'Use the pinned `.venv/bin/python`. `construction --check` explicitly reconstructs the new bounded companions; normal construction resumes exact signatures. `evaluation/attribution/verification --check` reuse sealed banks. `pilot/prior/audits/structure/structural_diagnostics/report/manifest --check` reproduce derived findings. Original banks are never regenerated merely for local repetition; final existing archival Ubuntu commands remain intact. No MCMC or acquisition occurs.', '',
        'New artifacts are under `data/processed/uncertainty-expectation/`; producer signature, consumed helper/source closure, separate structural evidence hashes and prior-file preservation are sealed. Cache files under `.cache/stage47/` are local reproducible conveniences, not off-device backups. Routine checkpoints stay local; only the consolidated unskipped review head is pushed. Leave the PR unmerged.', '']
    return '\n'.join(out)


def main():
    args = arguments()
    verify()
    p = ROOT/'docs/stage47-expectation-width-findings.md'
    value = build()
    if args.check:
        if p.read_text() != value:
            raise ValueError('Stale Stage47 findings')
    else:
        p.write_text(value)


if __name__ == '__main__':
    main()
