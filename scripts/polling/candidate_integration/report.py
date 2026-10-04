"""Small deterministic report from sealed Stage39 integration and evaluations."""
import argparse
from math import fsum
from .common import *

LABELS = dict(zip(METHODS, ('Baseline', 'S', 'S+R')))


def accuracy(evaluation):
    lines = ['## Expected-share accuracy', '',
             'MAE is contest-equal valid-candidate-share absolute error in pp. RMSE is the square root after pooling within-contest candidate squared errors. All 162 contests receive equal pooled weight (64/34/64 by election); this does not give a 20- or 34-seat sample the weight of a 64-seat election. Candidate-equal sensitivities and every paired contest error are saved in evaluation.json. Full-slate signed bias cancels as an accounting check.', '',
             '| Policy / election | Contests | Baseline MAE / RMSE | S MAE / RMSE | S+R MAE / RMSE | Joint improvement over S |',
             '|---|---:|---:|---:|---:|---:|']
    for case in evaluation['cases'] + evaluation['pooled']:
        year = case.get('year', 'pooled')
        cells = ['{:.4f} / {:.4f}'.format(case['methods'][m]['contestEqualMaePP'], case['methods'][m]['contestEqualRmsePP']) for m in METHODS]
        gain = case['pairs']['baseline_plus_S_plus_R__versus__baseline_plus_S']['maeImprovementPP']
        lines.append(f"| {case['policy']} / {year} | {case['contests']} | {' | '.join(cells)} | {gain:.4f} |")
    lines += ['', 'Positive improvement means comparator error minus model error. Under recent-report allocation, S and joint improve pooled MAE by 0.8895/0.8902pp over baseline; joint versus S is only 0.0006pp. Prior-only reverses this tiny ordering (joint 0.0043pp worse). Joint shareMAE wins 2017, S wins 2020/2023; joint RMSE improves 2017/pooled, worsens 2020 and is nearly tied 2023. Preserve the user’s provisional S+R development preference, S active alternative and baseline control; small scores do not trigger another tuning/model-selection cycle.', '']
    return lines


def context(evaluation):
    lines = ['## Matching conditional context — combined input and averaging change', '',
             'Saved Stage33 primary predictions used complete local affinity vectors conditional on observed national support. The same coefficients, source features, slates and exact IDs are used here. This context does not substitute observed-local retrained predictions, create a four-cell experiment or causally separate national/geographic/candidate error. Negative change means replay error is lower; a lower error can include cancellation and is not isolated evidence for the candidate feature.', '',
             '| Election (recent policy) | Baseline conditional→replay MAE | S conditional→replay MAE | Joint conditional→replay MAE |', '|---|---:|---:|---:|']
    for c in evaluation['cases']:
        if c['policy'] != POLICIES[0]: continue
        cells = [f"{c['conditionalContext']['methods'][m]['contestEqualMaePP']:.4f}→{c['methods'][m]['contestEqualMaePP']:.4f}" for m in METHODS]
        lines.append(f"| {c['year']} | {' | '.join(cells)} |")
    return lines + ['', '2017/2023 replay MAE deteriorates versus conditional context; 2020 can improve. These are three reused development environments and selected unchanged general seats, with overlapping training transitions and retrospective slates. No as-of or representative-national-candidate validation claim.', '']


def group_table(evaluation):
    lines = ['## Category diagnostics', '', 'Recent-report policy, pooled. Each error/bias averages candidates in that group on the original valid-candidate denominator. Groups do not sum to the contest-equal primary score. National/Labour combined is an overlapping diagnostic, not extra observations. No-party-group candidates remain distinct from smaller mapped parties.', '',
             '| Group | Candidates / present contests | Baseline MAE / bias | S MAE / bias | Joint MAE / bias |', '|---|---:|---:|---:|---:|']
    primary = next(p for p in evaluation['pooled'] if p['policy'] == POLICIES[0])
    for group, data in primary['groups'].items():
        cells = [f"{data['methods'][m]['candidateEqualMaePP']:.4f} / {data['methods'][m]['candidateEqualSignedBiasPP']:.4f}" for m in METHODS]
        lines.append(f"| {group} | {data['candidates']} / {data['presentContests']} | {' | '.join(cells)} |")
    return lines + ['', 'Joint improves Labour/other mapped shareMAE slightly versus S but National is nearly tied/slightly worse. Neither feature model beats baseline on no-group MAE; joint improves no-group MAE/bias versus S. Their support still changes through complete-slate normalization. This bounded diagnostic does not authorize a new fallback fit.', '']


def rankings(evaluation):
    lines = ['## Rankings and margins — descriptive, not calibrated probabilities', '',
             '| Election (recent policy) | Baseline correct / margin MAE | S correct / margin MAE | Joint correct / margin MAE |', '|---|---:|---:|---:|']
    for case in evaluation['cases'] + evaluation['pooled']:
        if case['policy'] != POLICIES[0]: continue
        cells = [f"{case['methods'][m]['uniqueCorrect']}/{case['contests']} / {case['methods'][m]['actualTopTwoMarginMaePP']:.4f}" for m in METHODS]
        lines.append(f"| {case.get('year', 'pooled')} | {' | '.join(cells)} |")
    lines += ['', 'All predictions have unique winners (existing 1e−12 tie tolerance; no outcome-based tie breaking). Joint correct counts 61/29/56 versus S54/28/55; pooled 146 versus 137, baseline 127. These rank counts are not a veto on better shares and not draw winner probabilities. Margin MAE uses predicted share difference between observed winner/runner-up minus their observed difference; actual ties retain every runner as in Stage33. Predicted top-two-gap error is separately saved.', '', '### Fixed-fit contest influence', '', '| Election (recent policy) | Joint−S gain | Leave-one-contest-out gain range | Most influential retained contests |', '|---|---:|---:|---|']
    for case in evaluation['cases']:
        if case['policy'] != POLICIES[0]: continue
        pair = case['pairs']['baseline_plus_S_plus_R__versus__baseline_plus_S']
        influence = ' to '.join(f'{v:.4f}' for v in pair['fixedFitLeaveOneContestOutMaeGainRangePP'])
        lines.append(f"| {case['year']} | {pair['maeImprovementPP']:.4f} | {influence} | " + '; '.join(f"{r['targetElectorateId']}:{r['maeImprovementPP']:.4f}" for r in pair['fiveLargestAbsoluteEffects']) + ' |')
    return lines + ['', 'All contests remain in primary scores. These are fixed-prediction score influences, not leave-one-election-out forecasts or refitted ablations.', '']


def allocation(inventory, construction):
    lines = ['## Allocation sensitivity and nonlinear expectations', '',
             'Raw gauss schemas are preserved: 2017 explicit Conservative/United Future, 2020 MRI/TOP inside Other, 2023 explicit MRI/TOP. Existing category continuity maps 2017“New Conservative” to conservative; 2023 MRI to ballot key tepatimaori. Explicit shares are unchanged; only Other is allocated. Whole alliances and parties without candidates remain represented. For 2020 MRI, recent reports use the same Stage37 cutoff/weight arithmetic on already-preserved MRI observations; prior-only retains earlier support. Unknown support is not zero and target final shares do not select weights.', '',
             '| Election / policy | Other allocated pp | Recent-report mass pp | Prior mass pp | Neutral-seed mass pp |', '|---|---:|---:|---:|---:|']
    for c in construction['cases']:
        basis = c['allocatedMassByBasis']
        lines.append(f"| {c['year']} / {c['policy']} | {100*c['allocatedOtherMean']:.4f} | {100*basis.get('recent_published_working_approximation', 0):.4f} | {100*basis.get('supported_prior', 0):.4f} | {100*basis.get('neutral_seed_assumption', 0):.4f} |")
    lines += ['', 'Prior/reported weights inform a conditional scenario, not observed true support or a fine-party posterior. Both scenarios conserve all Other; no unresolved mass is dropped. Some minor polling evidence also informed national inference and is not independent corroboration.', '', '| Election | Primary→prior national fine-vector TV pp | Māori-party national share, primary / prior pp | Maximum expected-candidate allocation difference pp |', '|---|---:|---:|---:|']
    for case in inventory['cases']:
        year = case['year']
        a, b = [read(OUT / f'national/{year}-{p}.json.gz')['arrays'] for p in POLICIES]
        means = [[fsum(v[j] for v in x)/len(x) for j in range(len(case['roster']))] for x in (a,b)]
        tv = 50*fsum(abs(x-y) for x,y in zip(*means))
        idx = next(i for i,c in enumerate(case['roster']) if c['categoryId']=='maoriparty')
        cases = [next(c for c in construction['cases'] if c['year']==year and c['policy']==p) for p in POLICIES]
        maximum = max(100*abs(r['methods'][m]['candidateShares'][cid]-s['methods'][m]['candidateShares'][cid]) for r,s in zip(cases[0]['records'],cases[1]['records']) for m in METHODS for cid in r['methods'][m]['candidateShares'])
        lines.append(f"| {year} | {tv:.4f} | {100*means[0][idx]:.4f} / {100*means[1][idx]:.4f} | {maximum:.4f} |")
    lines += ['', 'MRI column is a scenario allocation, including 2020 conditional Other support, not an observed Māori electorate quantity. No national reconciliation is imposed over selected exact seats.', '', 'Expected shares average all 8,000 transformed candidate vectors. The shortcut using only mean national inputs differs by up to4.3906pp for a candidate in 2020 joint (1.5385pp in 2023 joint,0.2718pp in 2017 joint). This is why the nonlinear draw propagation is required; it does not identify an additional causal effect.', '']
    return lines


def render():
    verify_inputs(); verify_phase('construction'); verify_phase('evaluation')
    inventory = read(OUT / 'inventory.json'); construction = read(OUT / 'construction.json'); evaluation = read(OUT / 'evaluation.json')
    verification = read(OUT / 'independent-verification.json')
    lines = ['# Stage39 — bounded national-to-candidate integration', '',
             '2026-10-05. Frozen contract a8cf66a and prediction seal5b864f2 precede scoring. No new national/candidate fits, owned replay, R-only replay, acquisition, calibrated electorate probabilities or live forecast. External gauss is provisional national engine; S+R preferred development candidate, S active alternative/baseline control. Historical numerical findings/screens/operational nulls remain unchanged (D073).', '',
             '## Coverage and construction', '',
             'Three cached 56-day cases: 2017/2020/2023; 64/34/64 held exact-general contests, 431/286/459 candidates (162/1176). All six election/policy cases construct on identical complete slates with zero abstentions. Māori coverage-only, nonexact, cancelled and outside-scope cases remain in the linked wider 356-record ledger; no 2014/14-day forecast is manufactured. Source S coverage 285/159/271 and source R 116/61/108; unsupported candidates remain with neutral missing-feature exponents. All R-supported candidates also have S, without implying interchangeable information. The wider ledger retains35 Māori coverage-only and75 nonexact records plus84 outside-case exclusions (including cancelled Port Waikato); its original contestStatus remains explicit.', '',
             'Raw joint election-target draws and chain IDs are shared across every seat/model/policy. The Sunday-start election-week approximation is preserved; last-data support is distinct and never scored as election-day forecast. No per-seat redraw, second national error, outgoing residual transfer or candidate-only party renormalization. Complete local vectors use original affinity/entrant rules. Every matching Stage33 conditional vector reproduces, maximum gap 2.22e−16 (gate 1e−12). Decimal 50 fixed exponent factors implement the same intensity equation efficiently and portably; no tolerance/statistical change. Joint log-intensity coefficients are not personal-vote retention percentages or causal decompositions.', '']
    lines += accuracy(evaluation) + context(evaluation) + group_table(evaluation) + rankings(evaluation) + allocation(inventory, construction)
    lines += ['## What uncertainty is represented', '',
              'Saved per-candidate 50%/90% quantiles are **national-input-only conditional intervals**. They propagate national common polling error/future movement through deterministic local affinity, conditionalOther policy and fixed candidate fits. They omit local-party forecast error, candidate residual error, fitted parameter uncertainty, changed-boundary transport and stochastic fine-category allocation. The two policies are not a probability distribution. No calibrated electorate win probability or interval-calibration claim follows, and misses do not authorize inflating national uncertainty.', '',
              'Inferred publication dates, retrospective rosters/source-feature availability, retrospective gauss error-scale development and only three dependent election environments remain. Full share conservation establishes correctness, not completeness of uncertainty. Fixed-fit replay does not select political mechanisms or erase component evidence.', '',
              '## Validation and practical next step', '',
              'Independent checks are recorded in independent-verification.json: ' + str(verification.get('checks', verification.get('counts', verification))) + '. Actual-path outcome/cutoff mutations, synthetic entrant/zeroOther/sharedgroup/no-group/extreme-vector stress, fixed fits/means, batching and cache/provenance checks pass. All 1,671 prior datafiles are byte-identical; no earlier identity/geography/model/operational output is rewritten. Deterministic regeneration uses cached external forecasts and never MCMC. Candidate draw transforms are saved in a local 458 MiB runtime cache with committed checksums; CI recreates them from committed fine national archives, fixed fits and features. Source checks/configured tests/finalCI are reported separately at handoff; no Python formatter/linter is configured.', '',
              '**Next separately authorized bounded implementation:** build 2026 target-boundary/candidate-slate readiness records, using the preserved 2023→2026 geography contracts and a finite dated nomination/source plan. Deliver every target seat with explicit known/unknown slate status, original affiliation/ballot-group mapping, source-feature eligibility and neutral-history fallbacks. Population/party reconstruction does not reconstruct candidate votes, so unsupported residual transport must remain unavailable. Do not produce a live forecast in that readiness task. Then implement the coherent joint local/candidate uncertainty design and separately planned Māori polls/unpolled baseline, before reconciliation/denominators and MMP/publication. See stage39-forecast-roadmap.md.', '',
              'National TPM party support is not Māori electorate candidate support. Future candidate/localparty/both poll routes must preserve question, denominator, fieldwork/publication,n, poll age/noise and dependence. Use an explicit Māori-seat baseline and wider documented unpolled fallback without double-counting national/local information. No such acquisition or implementation occurred here.', '',
              'Stop after the bounded replay/review. Small score differences are not authorization for new national comparison, candidate tuning, learned blend, fallback estimation, live output or operational adoption.']
    return '\n'.join(lines) + '\n'


def run(check=False):
    text = render(); path = ROOT / 'docs/stage39-national-candidate-integration-results.md'
    if check:
        if path.read_text() != text: raise ValueError('Changed deterministic Stage39 report')
    else: path.write_text(text)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); run(p.parse_args().check)
