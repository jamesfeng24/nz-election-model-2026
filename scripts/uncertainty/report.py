"""Reproducible findings; all comparisons preserve frozen uncertainty choices."""
from .common import PREFIX,ROOT,read,arguments


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])


def build():
    evaluation=read(PREFIX+'/evaluation.json');inventory=read(PREFIX+'/inventory.json');scales=read(PREFIX+'/scales.json');precision=read(PREFIX+'/precision.json')
    text=['# Stage44 local-party and candidate uncertainty findings','',
        '2026-10-05. One frozen pooled log-ratio family, no mean refitting, source acquisition or MCMC. External gauss provisional; continuous S+R mean preferred, S active and baseline mandatory. No operational selection.',
        '', '## Evidence and chronology','',
        '321 general local-party vectors (2011/14/17/20/23:63/64/64/65/65);257 candidate residual vectors (2014/17/20/23:64/64/65/64),1902 candidates. Wider356 records retain35 Māori coverage-only cases and cancellation. Valid2023 Port Waikato party votes remain; its cancelled candidate ballot is absent.2011 has no fitted candidate residual.',
        '', 'Party residuals condition on observed national support; candidate residuals condition on observed local party support. Thus polling misses do not estimate local scales and ordinary party-input errors do not estimate candidate scales.2014/2020 candidate means consistently use continuous transport,2017/2023 exact means reproduce Stage33 fixed-to-observed predictions. Original vote denominators, slate/category IDs, source features, supported mass, broad evidence tiers, training IDs and means are pinned in the inventory.',
        '', '2011 party and2014 candidate use fixed assumption-based priors; later folds use only completed earlier target years. One to four election environments and three prior pseudo-environments imply strong pooling, not calibrated variance. Full-panel moments are separately descriptive and never enter earlier forecasts. No current2026 partial slate is normalized. Geography band `fallback` means below90/uncertain dominance in the old classification; the candidate mean still uses continuous weighting.',
        '', '## Representation and dependence','',
        'CLR residuals use fixed1e-6 share resolution replacement for observations/predictions only. Noise is projected shared coarse-class plus isotropic seat noise, followed by softmax. Zero frozen means stay on the zero face. Shared Gaussian effects are common across seats within an election; national cached draw IDs remain shared once. No unrestricted covariance, coefficient jitter, scale-parameter draws or probability over flow vertices/Other scenarios.',
        '', 'Class scales are pooled equally by earlier election; seat replication is not election replication. Cross-layer independence is an explicit approximation, not established by conditional residual definitions. National/Labour within-election-centered CLR correlations are '+ '/'.join(f"{r['withinElectionCenteredPearson']:.4f}" for r in scales['crossLayerAssociation'])+' on257 matching seats/four environments. Fine minor parties share the other class. Parameter/scale-estimation uncertainty is omitted; past predictive residuals contain some earlier fixed-fit estimation error.',
        '', '### Earlier-only fitted/assumed log-unit scales','']
    coverage=[]
    for year in (2014,2017,2020,2023):
        rows=[r for r in inventory['candidateRecords'] if r['targetYear']==year]
        features=[f for r in rows for f in r['features']]
        tiers={e['evidenceTier'] for f in features for e in f['residualEvidence'] if e.get('evidenceTier') is not None}
        coverage.append([year,len(rows),sum(r['geography']=='exact' for r in rows),len(features),
            sum(f['supportedMass']['S']>0 for f in features),sum(f['supportedMass']['R']>0 for f in features),
            f"{sum(f['supportedMass']['R'] for f in features)/len(features):.4f}",','.join(sorted(tiers))])
    text += [table(['Year','Seats','Exact seats','Candidates','S supported','R supported','Mean R mass','R evidence tiers'],coverage),'',
        'Supported mass is source coverage, not identity confidence or known strength. Missing contributions stay neutral; every standing candidate remains. Candidate historical means/identity tiers are not re-estimated by this uncertainty layer. All general simulation cases construct successfully; Māori and2011 no-candidate-fit remain explicit scope exclusions.','']
    scale_rows=[]
    for layer,folds in scales['folds'].items():
        for f in folds:scale_rows.append([layer,f['targetYear'],','.join(map(str,f['trainingYears'])) or 'none',f['environments'],f"{f['scales']['shared']:.5f}",f"{f['scales']['seat']:.5f}",f['status']])
    text += [table(['Layer','Target','Earlier targets','Environments','Shared SD','Seat SD','Status'],scale_rows),'','## Component and bounded composed scores','',
        'Units pp. MAE and RMSE give each complete contest equal total weight; CRPS, widths and interval scores average categories/candidates within contest then contests. Energy uses complete-vector Euclidean pp norm/first128 joint draws. Coverage below reports raw covered/coordinate counts; categories within seats and seats within elections are correlated. The mean point vector itself is a degenerate CRPS reference, not another fitted model.', '']
    score_rows=[]
    for c in evaluation['cases']:
        s=c['summary'];score_rows.append([c['id'],s['contests'],s['coordinates'],f"{s['contestEqualMAEPP']:.4f}",f"{s['contestEqualRMSEPP']:.4f}",f"{s['contestEqualCRPSPP']:.4f}",f"{s['energyPP']:.4f}",f"{s['interval50']['covered']}/{s['interval50']['total']}",f"{s['interval90']['covered']}/{s['interval90']['total']}",f"{s['interval90']['contestEqualWidthPP']:.3f}",f"{s['interval90']['contestEqualScorePP']:.3f}"])
    text += [table(['Case','Seats','Coordinates','MAE','RMSE','CRPS','Energy','50% covered','90% covered','90% width','90% score'],score_rows),'',
        'Local all-category point MAE0.43–0.62pp conceals National/Labour point errors about1.4–2.8pp and unusually wide90% intervals27–44pp. Both majors are covered in every party case. All local CRPS values exceed their degenerate-mean MAE reference: the proper score penalizes dispersion despite superficially near90% pooled coverage. The isotropic log-ratio residual family, heavily influenced by sparse minor-category errors, is too diffuse for these major-party shares. This is substantive evidence against claiming calibrated sharpness, not a numerical failure. Do not automatically search a new covariance family.',
        '', 'Candidate intervals are also broad: major-party90% widths38–56pp. Candidate CRPS improves on the degenerate mean in2014/2017/2020 but not2023. Minor-party misses remain, including unusually strong candidate overperformance. Pooled coverage alone does not establish calibrated winner probabilities.',
        '', 'Composition uses three preserved external56-day national forecasts and recent_report_prior fine allocation, with64/65/64 complete slates.2020 includes continuous changed-boundary seats beyond Stage39 exact34; these results are not a matching Stage39 replay. Its90% major-party intervals cover all193 National and193 Labour observations, with widths51–64pp. This suggests poor sharpness even when marginal coverage looks acceptable.2020 CRPS is worse than its mean point reference. No national uncertainty was inflated or recalibrated.',
        '', '### Major-party diagnostics (candidate/category equal)','']
    major=[]
    for c in evaluation['cases']:
        for name in ('national','labour'):
            g=c['summary']['groups'][name];major.append([c['id'],name,g['coordinates'],f"{g['maePP']:.3f}",f"{g['biasPP']:+.3f}",f"{g['crpsPP']:.3f}",f"{g['interval90']['covered']}/{g['interval90']['total']}",f"{g['interval90']['widthPP']:.2f}"])
    text += [table(['Case','Group','Count','MAE','Bias pred−actual','CRPS','90% covered','90% width'],major),'',
        'Other mapped/no-party-group counts, biases and scores, coordinate-equal sensitivities, exact/transport provenance, full-slate accounting bias and the five largest interval misses in every case are preserved in evaluation.json. Group averages do not sum to complete-slate contest metrics.',
        '', '### Pooled summaries','']
    pooled=[]
    for layer,v in evaluation['pooled'].items():
        s=v['contestWeighted'];pooled.append([layer,s['contests'],f"{s['contestEqualMAEPP']:.4f}",f"{s['contestEqualCRPSPP']:.4f}",f"{v['equalElectionMAEPP']:.4f}",f"{v['equalElectionCRPSPP']:.4f}"])
    text += [table(['Layer','Seats','Contest MAE','Contest CRPS','Equal-election MAE','Equal-election CRPS'],pooled),'', '## Expected shares, stress and precision','',
        'Conditional component mean preservation agrees within1e-10 shares (1e-8pp); the offset is outcome-independent finite-bank marginal adjustment. For varying national draws it does not guarantee per-national-draw conditional means. After local uncertainty the candidate map is nonlinear; preserving candidate mean around that new conditional ensemble cannot erase its Jensen shift relative to national-only propagation.', '']
    shifts=[]
    for s in evaluation['meanShifts']['composed']:shifts.append([s['year'],f"{s['meanAbsoluteNonlinearShiftPP']:.4f}",f"{s['maximumAbsoluteNonlinearShiftPP']:.4f}",f"{s['maximumCandidateMeanAdjustmentErrorPP']:.2e}"])
    text += [table(['Election','Mean absolute nonlinear shift pp','Maximum shift pp','Candidate adjustment gap pp'],shifts),'',
        'There is one zero-mean/positive-outcome lock:2014 electorate23 Democrats for Social Credit,7/27338 valid party votes. Its interval cannot cover that observation while preserving frozen mean0. Nine2023 zero-vote standing candidates use the frozen finite-resolution residual policy. Neither changes mean coefficients.',
        '', 'The sole transport stress adds50% candidate seat variance on nonexact seats, on identical random banks; exact predictions stay unchanged. It is assumed excess variance, possibly duplicating transport variation already in ordinary pooled residuals, not an overlap-calibrated distribution.', '']
    stress=[]
    for c in evaluation['cases']:
        if 'transportStress' in c:stress.append([c['id'],f"{c['transportStress']['pairedContestCRPSChangePP']:+.4f}",f"{c['transportStress']['summary']['interval90']['coverage']:.3f}",f"{c['transportStress']['summary']['interval90']['contestEqualWidthPP']:.3f}"])
    text += [table(['Case','Stress−primary CRPS pp','Stress90% coverage','Stress90% width'],stress),'',
        'Stress worsens proper CRPS in the affected2014/2020 cases; wider intervals are not a success criterion. No scale was selected from this comparison.',
        '', 'Frozen1024draw first/last-seat precision audit:24 records; maximum mean CRPS change '+f"{max(abs(r['meanCRPSDifferencePP']) for r in precision['records']):.4f}"+'pp, maximum90% width change '+f"{max(r['maximum90WidthDifferencePP'] for r in precision['records']):.3f}"+'pp; '+str(sum(r['changed90CoverageCoordinates'] for r in precision['records']))+' coverage classifications change. Composed expected-share differences reach '+f"{max(r['maximumExpectedShareDifferencePP'] for r in precision['records'] if r['case'].startswith('composed')):.4f}"+'pp from finite national/noise integration; component means remain locked. These are numerical-resolution warnings, not calibrated error bounds; do not publish high-precision probability claims from512 draws.',
        '', '## Margins and diagnostic probabilities','']
    rank=[]
    for c in evaluation['cases']:
        if 'ranking' not in c['summary']:continue
        r=c['summary']['ranking'];rank.append([c['id'],f"{r['uniqueMeanWinnerCorrect']}/{r['contests']}",f"{r['winnerBrier']:.4f}",f"{r['finiteWinnerLogLossMean']:.4f}",r['infiniteLogLossCount'],f"{r['forecastPairMarginCRPSPP']:.3f}",f"{r['forecastPairMarginCoverage90']:.3f}",f"{r['observedTopTwoMarginMAEPP']:.3f}"])
    text += [table(['Case','Mean winners','Winner Brier','Finite log loss','Infinite count','Forecast pair CRPS','Pair90% coverage','Observed-top-two MAE'],rank),'',
        'Competitive pairs are chosen from deterministic prediction-time means (national-only mean in composition); actual-top-two reporting is separately retrospective. Draw ties share probability equally, with frozen1e-12 tolerance. Probabilities, Brier and log loss are diagnostics, not calibrated electorate win odds. No general coefficients or uncertainty are applied to Māori seats.',
        '', '## Readiness, limits and next decision','',
        '**Retain the coherent simulation interface for development; do not claim production-calibrated local probabilities.** The single family is numerically sound but major-party intervals are excessively broad, point means can move through nonlinear composition, and sparse minor-category residuals affect scale pooling. No new uncertainty tournament or mean search follows automatically. A separately scoped residual-scale adequacy decision is needed before presenting probabilities; this stage records the defect rather than concealing it with national variance.',
        '', 'Remaining deployment blockers: complete dated official nominations; separate Māori-seat baseline and candidate/local-party electorate polls with question/denominator/dates/sample/dependence and unpolled/stale fallback; justified all-population turnout/valid-party reconciliation; fine-party allocation remains scenarios; unidentified fragment political composition; omitted explicit parameter/scale uncertainty and independent-layer approximation; finite simulation precision. National reconciliation is not imposed by this layer. A later weighted all-seat reconciliation operator must preserve shared dependence before candidate mapping and requires its own contract.',
        '', 'Concrete next bounded forecast-building task: official nomination refresh after bulk publication plus the separately authorized Māori baseline/poll interface. This uncertainty implementation remains a versioned development scenario pending an explicit calibration/sharpness decision; do not fit alternatives now. External gauss/S+R mean preferences, S alternative/baseline control and all historical operational nulls remain unchanged.',
        '', '## Reproduction and validation','',
        'Run `.venv/bin/python -m scripts.uncertainty.NAME --check` for inventory, estimation, construction, evaluation, precision, verification, report and manifest, in that order. Case caches under `.cache/stage44/<exact-signature>/` resume construction; check mode reconstructs and verifies. No MCMC. Score generation consumes sealed draws only. Dependencies reuse pinned numpy2.2.6/scipy1.16.0; no new environment/backend.',
        '', 'Independent scalar CLR/QR moment calculations, manual draw expectations and all-pair proper-score arithmetic are recorded in independent-verification.json. Focused tests exercise actual adapter counterfactuals, chronology, source-only R, no outgoing transfer, streams/conservation/mean treatment, cache signatures/checksums and scores. Full configured/local and final-head CI results are recorded in PROJECT_STATE and the PR handoff. Consumed-source hashes are separate from all-prior preservation checks; unrelated registry additions do not change model signatures. No political acquisition, old-artifact changes or operational selections.']
    return '\n'.join(text)+'\n'


def main():
    args=arguments();value=build();path=ROOT/'docs/stage44-uncertainty-findings.md'
    if args.check:
        if path.read_text()!=value:raise ValueError('Stale Stage44 findings')
    else:path.write_text(value)
    print('Stage44 findings reproduced')


if __name__=='__main__':main()
