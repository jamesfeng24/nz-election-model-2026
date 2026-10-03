"""Readable frozen-score handoff, generated without fitting or constructing inputs."""
import argparse
from .common import ROOT, local, read, GEO, verify_inputs, preserve
from .integrity import verify_phase

PATH = ROOT / 'docs/stage31-expanded-party-input-substitution-results.md'
CELLS = ('A', 'B', 'C', 'D')
GROUPS = ('national', 'labour', 'national_labour', 'other_mapped', 'affirmative_no_party_group')


def number(x):
    return '—' if x is None else f'{x:.4f}'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows])


def cell_table(rows, metric='contestEqualMaePP'):
    return table(['Year/sample', 'Contests/candidates', 'A', 'B', 'C', 'D'],
                 [[r.get('targetYear', r.get('label')), f"{r['contests']}/{r['candidates']}"] +
                  [number(r['cells'][c][metric]) for c in CELLS] for r in rows])


def pairs_table(rows):
    fields = ('baselineSubstitutionDamagePP', 'sSubstitutionDamagePP',
              'observedSAdvantagePp', 'constructedSAdvantagePp', 'interactionPP')
    return table(['Year/sample', 'C−A', 'D−B', 'A−B', 'C−D', 'I'],
                 [[r.get('targetYear', r.get('label'))] +
                  [number(r['paired'][k]) for k in fields] for r in rows])


def group_tables(rows):
    result = []
    for r in rows:
        result.append(f"### {r['targetYear']} candidate groups\n")
        for metric, label in [('candidateEqualMaePP', 'MAE'), ('candidateEqualRmsePP', 'RMSE'),
                              ('candidateEqualSignedBiasPP', 'Signed bias')]:
            result.append(label + ' (candidate-equal, pp):\n')
            result.append(table(['Group', 'Candidates/present contests', 'A', 'B', 'C', 'D'],
                [[g, f"{r['groups'][g]['candidates']}/{r['groups'][g]['contestsContainingGroup']}"] +
                 [number(r['groups'][g]['cells'][c][metric]) for c in CELLS] for g in GROUPS]))
        result.append('Paired group MAE differences (candidate-equal, pp; negative improves):\n')
        result.append(table(['Group', 'B−A', 'D−C', 'C−A', 'D−B', 'I'],
            [[g] + [number(r['groups'][g]['pairedCandidateEqualMaePP'][k]) for k in
                    ('S_observed_B_minus_A', 'S_predicted_D_minus_C', 'baseline_substitution_C_minus_A',
                     'S_substitution_D_minus_B', 'interaction')] for g in GROUPS]))
    return '\n\n'.join(result)


def party_section(d):
    folds = d['folds']
    rows = []
    for f in folds:
        r = f['heldGeneral']; groups = r['byGroup']
        rows.append([f['targetYear'], r['n'], r['model']['partyCells'], number(r['model']['maePP']),
                     number(r['model']['rmsePP']), number(r['flatNational']['maePP']),
                     number(r['flatNational']['rmsePP']), number(groups['national']['model']['MAEpp']),
                     number(groups['labour']['model']['MAEpp'])])
    sections = ['## Complete local party vectors',
        'All target categories appear once. Continuing-group affinity is source local valid-party share divided by source national valid-party share; entrants receive affinity one; exits are omitted. Multiply by supplied target national support and close the **whole party vector** jointly. Observed source zeros remain zero; missing continuing-group evidence abstains. No party support is re-normalized over standing candidates. The full source national denominator uses all electorates, including Māori, rather than the selected exact-seat subset.',
        table(['Year', 'Held seats', 'Party cells', 'Model MAE', 'Model RMSE', 'Flat MAE', 'Flat RMSE', 'NAT MAE', 'LAB MAE'], rows),
        'Primary party metrics average category errors within each electorate, then give each electorate equal weight; RMSE takes the root after averaging squared errors. The saved evaluation also reports observed valid-party-total-weighted sensitivity, all-category pooled results and each category separately. National/Labour errors materially exceed the all-category average in several folds; that average does not imply nearly perfect candidate inputs. Source geography improves over flat national support in both added elections and all original folds.',
        table(['Year', 'Group', 'Model MAE/RMSE/bias', 'Flat MAE/RMSE/bias'],
            [[f['targetYear'], g, '/'.join(number(f['heldGeneral']['byGroup'][g]['model'][k]) for k in ('MAEpp', 'RMSEpp', 'biasPp')),
              '/'.join(number(f['heldGeneral']['byGroup'][g]['flat'][k]) for k in ('MAEpp', 'RMSEpp', 'biasPp'))]
             for f in folds for g in ('national', 'labour', 'other_categories')]),
        '### National reconciliation limitation',
        'No national reconciliation is imposed. The following gaps use observed target valid-party totals as **evaluation-only oracle weights over selected exact general seats**. They omit Māori and nonexact seats; comparison with national support is not a claim that this subset should reproduce national totals. The evaluation separately retains model-minus-actual-subset and actual-subset-minus-national gaps, plus Stage23’s unchanged complete-population gap context. Port Waikato contributes its valid party ballot only to the all-exact-party diagnostic, not candidate evaluation.',
        table(['Year', 'Exact party seats', 'Max |model subset − national scenario| pp'],
              [[g['targetYear'], g['electorates'], number(g['maxAbsoluteSubsetModelScenarioGapPp'])] for g in d['subsetGaps']])]
    return '\n\n'.join(sections)


def ranking_section(rows):
    sections = ['## Rankings and margins',
        'Tie tolerance remains 1e−12 in share units. No ties occur in any evaluated cell/scenario. Unique-winner counts use all evaluated contests as denominator; tied-set inclusion is zero. Margin error is the absolute difference between predicted and observed **actual winner share minus the largest other-candidate share**, using the complete slate. It is an evaluation-only diagnostic, not a prediction-time choice of winner. No calibrated winner probabilities exist.',
        table(['Year', 'n', 'A wins/margin MAE', 'B wins/margin MAE', 'C wins/margin MAE', 'D wins/margin MAE'],
              [[r['targetYear'], r['contests']] + [f"{r['cells'][c]['uniqueCorrectCount']}/{number(r['cells'][c]['meanAbsoluteActualWinnerMarginErrorPP'])}" for c in CELLS] for r in rows]),
        table(['Year', 'Substitution', 'Changed winner sets', 'Correct→incorrect', 'Incorrect→correct'],
              [[r['targetYear'], t['comparison'], t['changedPredictedWinnerSets'], t['uniqueCorrectToNotUniqueCorrect'], t['notUniqueCorrectToUniqueCorrect']]
               for r in rows for t in r['rankingTransitions']]),
        'Share and ranking performance differ: constructed-input S has lower MAE than baseline in 2023 but 53/64 correct winners versus 54/64. In 2017 it has slightly worse share MAE but 59/64 versus 56/64 correct winners. The shared floor and no-group fallback do not model independent candidate strength.']
    return '\n\n'.join(sections)


def influence_section(rows):
    sections = ['## Fixed-fit influence and rounding sensitivity',
        'Every observation stays in primary scores. Leave-one-contest-out score ranges reuse the fixed predictions without fitting; they are not leave-one-election-out validation. I’s sign survives deletion of any single contest within each primary printed fold. The small 2014 S advantage itself can reverse under single-contest score deletion. Complete paired records and the five largest absolute baseline/S damage and I cases are retained in evaluation.json.',
        table(['Year', 'I min/median/max', 'I leave-one-contest range', 'D−C leave-one-contest range'],
              [[r['targetYear'], '/'.join(number(r['paired']['interactionContestDistributionPP'][k]) for k in ('min', 'median', 'max')),
                '/'.join(number(v) for v in r['paired']['interactionContestDistributionPP']['leaveOneContestOutMeanRange']),
                '/'.join(number(v) for v in r['paired']['leaveOneContestOutPairedMaeDifferenceRangePP']['sPredictedMaeDifferencePP'])] for r in rows])]
    names = {r['targetElectorateId']: r['targetElectorateName'] for r in read(GEO + 'geography.json')['records']}
    sections.append(table(['Year', 'Largest absolute I contest', 'I pp'],
        [[r['targetYear'], names[p['targetElectorateId']] + ' (' + p['targetElectorateId'] + ')', number(p['interactionPP'])]
         for r in rows for p in r['paired']['fiveLargestAbsoluteInteractionContests']]))
    return '\n\n'.join(sections)


def build():
    x = local('evaluation.json'); inv = local('input-inventory.json')
    primary = [f for f in x['folds'] if f['protocol'] == 'expanding_window' and f['scenario'] == 'printed' and f['status'] == 'evaluated']
    separated = [f for f in x['folds'] if f['protocol'] == 'more_separated' and f['scenario'] == 'printed' and f['status'] == 'evaluated']
    pools = [{**r, 'label': r['protocol']} for r in x['pooled'] if r['scenario'] == 'printed']
    chunks = ['# Stage31 — expanded party vectors and fixed-parameter candidate input substitution',
        '**Conditional reused development evidence; no fitting, operational selection, acquisition or forecast.** Preconstruction a91cc7d pins the samples/equations/input hashes; construction 6e7a4dd commits vectors and four-cell predictions before scoring. Earlier specifications and numerical outputs remain historical checkpoints.',
        '## Coverage and construction',
        table(['Target', 'Held candidate contests', 'Candidate occurrences', 'Exact general party vectors', 'Primary fit', 'Separated fit'],
              [[r['targetYear'], r['heldGeneralContests'], r['candidateOccurrences'], r['partyVectorsAvailable'],
                'no' if r['targetYear'] == 2011 else 'yes', 'no' if r['targetYear'] in (2011, 2014) else 'yes'] for r in inv['coverage']]),
        'The canonical 356-target frame retains 35 Māori coverage-only and 75 nonexact general seats. There are 246 exact general party vectors (including cancelled Port Waikato), 245 held complete candidate slates and 1,742 candidate occurrences. Party data availability does not create a fitted candidate model. Primary fitted comparison: 182 contests/1,319 candidates (2014/2017/2020/2023); more-separated: 162/1,176 (2017/2020/2023). All 21 fitted fold/scenario cases have identical four-cell IDs and no mapping abstentions; nine no-fit cases explicitly cover 2011 under both protocols and separated 2014 across three scenarios. No Māori candidate prediction or approximate-boundary transport is added.',
        party_section(x['partyDiagnostics']),
        '## Four-cell comparison',
        'A = baseline/observed local party input; B = S/observed; C = baseline/constructed; D = S/constructed. Every fitted parameter, training-only mean, S feature, source-rounding scenario, candidate slate and ballot-group mapping stays fixed within each substitution. Intensities and candidate normalization reuse the frozen Stage24 numerical evaluator. No Stage30 residual, response, incumbency or replacement coefficient is added.',
        'Primary **contest-equal MAE (pp)**:\n\n' + cell_table(primary),
        'Primary **contest-equal RMSE (pp)**:\n\n' + cell_table(primary, 'contestEqualRmsePP'),
        'Primary **candidate-equal MAE/RMSE sensitivity (pp)**:\n\n' +
        table(['Year', 'A', 'B', 'C', 'D'], [[r['targetYear']] +
              [number(r['cells'][c]['candidateEqualMaePP']) + '/' + number(r['cells'][c]['candidateEqualRmsePP']) for c in CELLS] for r in primary]),
        'Paired MAE changes (pp). Positive C−A or D−B is substitution damage; positive A−B/C−D is S advantage. I = (D−C)−(B−A), independently checked from paired contest errors; positive weakens S’s relative advantage. This is a descriptive interaction, not a causal/error decomposition or fitted coefficient.\n\n' + pairs_table(primary),
        '### Pooled weighting and chronology',
        'Pooling gives every evaluated contest one vote, so primary election weights are 20/182, 64/182, 34/182 and 64/182; separated weights are 64/162, 34/162 and 64/162. No absent fitted fold enters the denominator. RMSE is sqrt(mean contest mean squared error), not mean contest RMSE. Candidate-equal sensitivity gives each candidate one vote.\n\n' + cell_table(pools),
        cell_table(pools, 'contestEqualRmsePP'), pairs_table(pools),
        'More-separated printed folds (same saved fits, no refit):\n\n' + cell_table(separated), pairs_table(separated),
        '### Original versus added evaluation populations',
        'Original-common and added subsets reuse these same amended/expanded-trained predictions. They are not separate fits or outcome-selected subsets. The 2017/2023 original-common sample contains 128 contests/890 candidates; the added 2014/2020 primary contains 54/429. The 2011 original frame has no candidate fit.',
        cell_table([{**r[k], 'label': f"{r['targetYear']} {k}"} for r in primary for k in ('originalCommon', 'new2014_2020') if r[k]['contests']]),
        ranking_section(primary),
        '## Candidate groups and input error',
        'Group tables use candidate-equal weights. National/Labour combined overlaps the two individual groups and is a separate diagnostic, not an additive decomposition. Other mapped groups and affirmative no-party-group candidates remain distinct. Saved present-contest-equal group metrics average only over contests containing that group and report their denominators; they do not automatically sum to whole-slate metrics. Full-slate signed bias is approximately zero by conservation, not calibration. No-group shares can change through the shared candidate normalization denominator even though their party input remains zero.',
        group_tables(primary),
        'Major-party party-input errors use valid-party shares, while candidate errors use valid-candidate shares. In 2017 National/Labour input MAE is 2.819/2.816pp; candidate-equal S substitution damage is +1.616/+0.810pp versus baseline +0.814/−0.235pp. In 2020 imperfect inputs reduce candidate errors in both models; error compensation is possible and does not imply a causal decomposition. The saved major-party candidate/error pairs and unchanged Stage24 bins (≤−5, (−5,−2], (−2,0], (0,2], (2,5], >5 pp) expose direction without new thresholds, smoothing or subgroup search.',
        influence_section(primary),
        'All saved coupled selected-lower/selected-upper scenarios use their corresponding immutable Stage27 fits, means and feasible source-row features. These are finite rounding measurement sensitivities, not exhaustive extrema or calibrated intervals. None is chosen by performance.\n\n' +
        table(['Protocol', 'Year', 'Scenario', 'A−B', 'C−D', 'I'], [[f['protocol'], f['targetYear'], f['scenario']] +
              [number(f['paired'][k]) for k in ('observedSAdvantagePp', 'constructedSAdvantagePp', 'interactionPP')]
               for f in x['folds'] if f['status'] == 'evaluated']),
        '## Interpretation and exact next decision',
        'Source local party geography remains useful against flat national support in the added elections. S retains a complete-share advantage under constructed inputs in 2014/2020/2023, with a 2017 reversal. Primary pooled advantage declines from 0.5675 to 0.5191pp (I +0.0485pp), masking that fold-specific damage. The 2017 I remains positive under chronology, rounding and single-contest influence checks. The sign of I remains negative in the other primary folds. No new success threshold is introduced; earlier frozen Stage27 screens stay unchanged.',
        'Retain S as the preferred complete-share **development** candidate with mandatory baseline. This mixed substitution result does not justify discarding prior residual information or declaring their combination successful. Stage30 supports useful carry-forward information without consistently better fitted retention. Sub-one response remains a possible later joint contribution; asymmetric parity is documented and paused. Every operational selection remains null/unresolved.',
        'These calculations supply actual target national support and retrospective complete slates. They neither verify dated input availability nor establish an as-of/live forecast. Entrants’ flat local affinity is an explicit assumption; no nationally reconciled allocation is claimed. Exact unchanged seats are selected, Māori candidate coverage and changed-boundary transfer remain unresolved, and repeated seats/overlapping transitions share only a few reused election environments. No calibrated uncertainty or winner probabilities follow.',
        '**Recommended next separately authorized scope:** freeze one small coherent joint/regularized complete-share comparison: baseline; S; supported prior normalized residual; S plus prior residual. Define a slate-wide embedding and explicit entrant/unknown-history fallbacks, jointly estimated coefficients and refitted ablations, broad/strict linkage and observed/constructed-input interfaces before fitting. A response contribution enters the shortlist only if a specific coherent representation is justified in that contract. Do not add separately fitted bonuses, search subsets, reopen identities, introduce another party transform or begin integration. This stage implements none of that next task.',
        '## Reproduction, independent checks and preservation',
        'Construction reproduces all 192 matching Stage23 general vectors and all saved Stage27 A/B predictions to 1e−12. The 54 new vectors follow the same rule. Bounded Stage24 checks reproduce all four cells using matching original saved parameters/scenarios to 1e−12; the separate Stage27 original-training comparison uses its already documented 1e−7 numerical agreement, without requiring expanded fits to equal Stage24. All 36 compatibility checks pass.',
        'Independent Fraction count ratios verify 3,826 party cells, direct exponential intensity arithmetic verifies 29,940 candidate shares, and independent sums verify 178 fold metrics and all 21 paired I values at the frozen 1e−8 check tolerance. No fit/solver call occurs. Held-out candidate/winner/identity mutations affect scoring only; held-out local-party mutations change A/B and evaluation but cannot change vectors/C/D; supplied national support can legitimately change vectors. Saved parameters/means are immutable. Required record/raw contracts and all 1,414 prior tracked data artifacts are verified.',
        'Candidate evaluation uses explicit error multiplication e×e for the same registered MSE; this is a numerical serialization choice, not a different equation, tolerance or statistical rule. No earlier output is regenerated. New JSON is compact with sorted keys. The report rounds displayed values to four decimals; machine artifacts preserve precision.',
        'Run each command with `--check` for byte-identical regeneration; omit it only to regenerate this new companion:\n\n```sh\n' +
        '\n'.join('python3 -m scripts.models.expanded_party_substitution.' + p + ' --check' for p in ('inventory', 'construction', 'evaluation', 'verification', 'report')) +
        '\npython3 -m unittest scripts.tests.test_stage31_construction scripts.tests.test_stage31_evaluation\npython3 scripts/validate/source_files.py\n```',
        'Final full-suite/CI status and the PR link are recorded in PROJECT_STATE.md. No formatter/linter is configured for Python; compilation and whitespace checks apply. This Python-only checkpoint does not repeat unrelated frontend checks locally; final-head CI runs them. Stop after review handoff.']
    return '\n\n'.join(chunks) + '\n'


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    verify_inputs(); verify_phase('construction'); verify_phase('evaluation'); verify_phase('verification')
    text = build()
    if args.check:
        if PATH.read_text() != text:
            raise ValueError('Changed Stage31 report')
    else:
        PATH.write_text(text)
    print('Stage31 report reproduced; prior artifacts:', preserve())


if __name__ == '__main__':
    main()
