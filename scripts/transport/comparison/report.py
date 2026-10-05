"""Reproducible bounded findings from sealed predictions and scores."""
import argparse
from .common import ROOT, PREFIX, BRANCHES, read, verify


def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] + ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows]


def build():
    value = read(PREFIX + '/evaluation.json')
    samples = read(PREFIX + '/sample-manifest.json')['folds']
    lines = ['# Stage43 continuous S versus S+R comparison', '',
        'Contract e9e93f6 was committed before calculation; predictions c7748a1 were committed before scoring. PR49 merge613ec78 and reviewedc75a4c4 ancestry verified from a clean checkout. No uncertainty work existed locally. No fitting, acquisition, new flow, MCMC or live predictions.', '',
        '## Inputs and independent saved fits', '',
        'Fixed primary expanding-window Stage33 constructed-input-trained fits, applied to observed target local party support. Every predecessor uses the frozen Stage42 party mass; supported source features are centered before weighting. Unsupported mass stays in the denominator, contributing neutral exponent. No outgoing residual transfer. All complete slates and ID orders reproduce Stage42; broad and strict joint predictions agree within1e-12.', '']
    rows = []
    for f in samples:
        for model in ('S', 'joint'):
            p = f['fits'][model]['parameters']
            rows.append([f['targetYear'], model, len(f['trainingIds']), f'{p["kappa"]:.10f}', ', '.join(f'{t:.8f}' for t in p['theta']), f'{f["trainingOnlyMeans"]["S"]:.10f}', f'{f["trainingOnlyMeans"]["R"]:.10f}'])
    lines += table(['Election', 'Model', 'Training contests', 'Own kappa', 'Own theta S[,R]', 'Mean S', 'Mean R'], rows)
    lines += ['', 'Means are shared within each saved fold, verified explicitly. The models have independently fitted floors and S coefficients. S is never formed by setting joint R to zero. Strict changes R evidence only in the broad-trained joint fit; the S prediction remains identical. All selected fits are interior, numerically agreed Stage33 fits; no new optimum is estimated.', '',
        '## Full-slate paired results', '',
        'Errors in percentage points. **Joint-minus-S is negative when joint is better.** RMSE is the square root of mean contest MSE, not mean contest RMSE.', '']
    rows = []
    for f in value['folds']:
        s = f['samples']['full']
        for b in BRANCHES:
            m = s['metrics'][b]
            rows.append([f['targetYear'], b, f'{s["contests"]}/{s["candidates"]}', f'{m["contestEqualMaePP"]:.5f}', f'{m["contestEqualRmsePP"]:.5f}', f'{m["candidateEqualMaePP"]:.5f}', '—' if b == 'S' else f'{s["pairs"][b]["jointMinusSMaePP"]:+.5f}', f'{m["uniqueCorrect"]}/{s["contests"]}', f'{m["actualTopTwoMarginMaePP"]:.5f}'])
    lines += table(['Election', 'Model', 'Contests/candidates', 'MAE', 'RMSE', 'Candidate-equal MAE', 'Joint−S MAE', 'Unique correct', 'Actual-top-two margin MAE'], rows)
    lines += ['', 'All129 held general contests/1012 candidates constructed; zero general abstentions. The seven Māori seats per election remain coverage-only, preserving separate candidate-model requirements. No predicted ties in these samples; tie tolerance1e-12 and tied-set inclusion remain explicit in the machine output. Full-slate signed bias is essentially zero by conservation, an accounting check. Margins use predicted shares of the actual winner and runner(s), averaging tied runners without ID tie-breaking. Predicted-top-two gap errors are separately saved.', '']
    rows = []
    for b in BRANCHES:
        p = value['pooled']['metrics'][b]
        e = value['equalElection']['metrics'][b]
        rows.append([b, f'{p["contestEqualMaePP"]:.5f}', f'{p["contestEqualRmsePP"]:.5f}', f'{e["maePP"]:.5f}', f'{e["rmsePP"]:.5f}'])
    lines += table(['Model', 'Contest-pooled MAE', 'Contest-pooled RMSE', 'Equal-election MAE', 'Equal-election RMSE'], rows)
    lines += ['', 'Contest pooling weights elections64/129 and65/129; equal-election view weights each1/2 and takes root mean election MSE for RMSE. Joint pooled MAE gain over S is0.10977pp; strict0.07283pp. Equal-election gains0.11178/0.07488pp. These two MAEs and their dispersion cannot estimate future robustness.', '',
        '## Frozen geographic strata', '']
    rows = []
    for f in value['folds']:
        for band in ('exact', 'approximate_95', 'approximate_90', 'fallback', 'cumulative95'):
            s = f['samples'][band]
            rows.append([f['targetYear'], band, s['contests'], *[f'{s["metrics"][b]["contestEqualMaePP"]:.5f}' for b in BRANCHES], f'{s["pairs"]["joint"]["jointMinusSMaePP"]:+.5f}'])
    lines += table(['Election', 'Band', 'Contests', 'S MAE', 'Joint MAE', 'Strict joint MAE', 'Joint−S'], rows)
    lines += ['', 'approximate95 and90 are exclusive added bands (95–100 and90–95 under guaranteed two-sided bounds); fallback denotes below90 or unresolved dominance, not a continuous-rule rejection. Cumulative95 includes exact. Comparisons are paired within each band, not transport-effect contrasts between different samples.', '',
        '## Category diagnostics', '',
        'One weight per member candidate; original valid-candidate denominator. Groups are not additive to whole-slate contest metrics. Bias is prediction minus actual. All models use the same category IDs.', '']
    rows = []
    for f in value['folds']:
        for group in ('national', 'labour', 'other_mapped', 'affirmative_no_party_group'):
            g = f['samples']['full']['groups'][group]
            rows.append([f['targetYear'], group, g['counts']['S']['candidates'], *[f'{g["metrics"][b]["maePP"]:.4f}/{g["metrics"][b]["rmsePP"]:.4f}/{g["metrics"][b]["biasPP"]:+.4f}' for b in BRANCHES]])
    lines += table(['Election', 'Category', 'Candidates', 'S MAE/RMSE/bias', 'Joint MAE/RMSE/bias', 'Strict joint MAE/RMSE/bias'], rows)
    lines += ['', 'Joint improves National and Labour in2014, while both worsen in2020; other mapped/no-group errors improve in both primary folds. Winner counts improve49→56 and52→55, but actual-top-two margin MAE improves15.27→12.73 in2014 and worsens9.04→9.91 in2020. Share accuracy remains primary; winners do not override the2020 share loss.', '',
        '## Supported mass and no-history effects', '']
    rows = []
    for f in value['folds']:
        s = f['samples']['full']
        for key in ('S', 'R', 'RStrict'):
            x = s['support'][key]
            rows.append([f['targetYear'], key, x['candidatesWithSupportedMass'], x['contestsWithAnySupportedMass'], f'{x["candidateEqualMeanSupportedMass"]:.5f}', f'{x["contestEqualMeanSupportedMass"]:.5f}'])
    lines += table(['Election', 'Feature', 'Candidates', 'Contests', 'Candidate mean supported mass', 'Contest mean supported mass'], rows)
    rows = []
    for f in value['folds']:
        for group in ('R_any', 'R_none', 'RStrict_any', 'RStrict_none'):
            s = f['samples'][group]
            rows.append([f['targetYear'], group, s['contests'], f'{s["pairs"]["joint"]["jointMinusSMaePP"]:+.5f}', f'{s["pairs"]["joint_strict"]["jointMinusSMaePP"]:+.5f}'])
    lines += ['', *table(['Election', 'Contest R group', 'Contests', 'Broad joint−S', 'Strict joint−S'], rows)]
    rows = []
    for f in value['folds']:
        for name in ('R_supported', 'R_unsupported'):
            g = f['samples']['full']['groups'][name]
            rows.append([f['targetYear'], name, g['counts']['S']['candidates'], *[f'{g["metrics"][b]["maePP"]:.5f}/{g["metrics"][b]["rmsePP"]:.5f}/{g["metrics"][b]["biasPP"]:+.5f}' for b in BRANCHES]])
    lines += ['', *table(['Election', 'Fixed broad candidate group', 'Candidates', 'S MAE/RMSE/bias', 'Joint MAE/RMSE/bias', 'Strict joint MAE/RMSE/bias'], rows), '',
        'R candidate groups remain fixed to broad support for all branches; strict coverage is separately reported. Unsupported candidates can gain or lose through complete-slate normalization. Even a contest with no usable R can differ between S and joint because their own fitted floors and S coefficients differ. This comparison tests independent saved models, not an isolated R coefficient intervention.', '',
        '## Individual gains, losses and influence', '']
    rows = []
    for f in value['folds']:
        pair = f['samples']['full']['pairs']['joint']
        for name in ('largestFiveGains', 'largestFiveLosses'):
            for r in pair[name]:
                rows.append([f['targetYear'], name, r['targetName'], f'{r["jointMinusSMaePP"]:+.5f}'])
    lines += table(['Election', 'Direction', 'Contest', 'Joint−S MAE'], rows)
    for f in value['folds']:
        pair = f['samples']['full']['pairs']['joint']
        lines += ['', f'{f["targetYear"]}: joint improves{pair["improvedContests"]}, worsens{pair["worsenedContests"]} contests; fixed-fit leave-one-contest-out mean-difference range {pair["leaveOneContestOutDifferenceRangePP"]}. All observations remain in primary scores.']
    lines += ['', '## Recommendation and limits', '',
        '**Retain S+R preferred and S active.** Continuous transport does not establish consistent superiority: joint gains0.37071pp in2014 but loses0.14715pp in2020, and strict preserves this direction. The modest pooled gain and RMSE improvement support keeping the existing preference without discarding the simpler S alternative.2020 major-party/margin losses remain substantive. No new threshold or tuning follows.', '',
        'Stage33–34 and Stage39 remain separate evidence with overlapping elections and different samples/information sets; their forecasts are not naively pooled here. Fixed earlier fits, conditional observed local party inputs, selected historical geography, algorithmic identity, uniform within-source party transport and only two reused environments limit interpretation. Population overlap does not reconstruct candidate votes or bound candidate error. θR is a log-intensity coefficient, not personal-vote retention. No causal or operational claim, electorate probabilities or uncertainty calibration.', '',
        'Next separately authorized task: one coherent local-party/candidate uncertainty implementation around continuous transport and the retained mean-model preference, sharing national error once and making local/transport/feature/parameter uncertainty explicit. Official nominations and Māori electorate polling remain separately bounded. Stop further candidate mean-model experiments here.']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    verify()
    path = ROOT / 'docs/stage43-comparison-findings.md'
    text = build()
    if args.check:
        if path.read_text() != text:
            raise ValueError('Stale Stage43 findings')
    else:
        path.write_text(text)
    print('Stage43 findings reproduced')


if __name__ == '__main__':
    main()
