"""Readable findings from frozen post-construction comparisons."""
import argparse
from .common import *

PATH=ROOT/'docs/stage33-joint-candidate-share-results.md'
NAMES={'baseline':'Baseline','baseline_plus_S':'S','baseline_plus_R':'R','baseline_plus_S_plus_R':'S+R'}
ORDER=('baseline','baseline_plus_S','baseline_plus_R','baseline_plus_S_plus_R')


def num(v):return '—' if v is None else f'{v:.4f}'

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def build():
    c=local('construction.json');e=local('evaluation.json');v=local('independent-verification.json');p=next(r for r in e['pooled'] if r['branch']=='primary')
    primary=[r for r in e['folds'] if r['branch']=='primary'];params=[]
    for case in c['folds']:
        if case['branch']!='primary' or case['targetYear']==2011:continue
        for m in ORDER:
            f=case['fits'][m]['parameters'];params.append([case['targetYear'],NAMES[m],num(f['kappa']),num(f['coefficients'].get('S')),num(f['coefficients'].get('R')),f['boundary'],','.join(n for n,t in zip(METHODS[m],f['thetaAtBoundary']) if t) or 'none'])
    sensitivities=[];fold_gains=[]
    for r in e['pooled']:
        sensitivities.append([r['branch'],r['contests'],*[num(r['methods'][m]['contestEqualMaePP']) for m in ORDER],num(r['pairs']['baseline_plus_S_plus_R__versus__baseline_plus_S']['maeImprovementPP'])])
    for r in e['folds']:
        if r['records']:
            fold_gains.append([r['branch'],r['targetYear'],*[num(r['pairs'][a+'__versus__'+b]['maeImprovementPP']) for a,b in PAIRS]])
    group_rows=[]
    for g,r in p['groups'].items():
        group_rows.append([g,r['candidates'],r['presentContests'],*[num(r['methods'][m]['candidateEqualMaePP']) if r['methods'][m] else '—' for m in ORDER]])
    group_bias=[[g,*[num(r['methods'][m]['candidateEqualSignedBiasPP']) if r['methods'][m] else '—' for m in ORDER]] for g,r in p['groups'].items()]
    influence=[]
    for a,b in PAIRS:
        q=p['pairs'][a+'__versus__'+b];influence.append([NAMES[a]+' vs '+NAMES[b],num(q['maeImprovementPP']),*[num(x) for x in q['fixedFitLeaveOneContestOutMaeGainRangePP']],q['improvedContests'],q['worsenedContests']])
    descriptions=['# Stage33 — complete-share baseline/S/R/S+R findings',
      '**Conditional development comparison, not an as-of forecast or operational adoption.** Pre-fit input/plan0142d2f preceded numerical work; verified constructionab3cf82 was committed/pushed before any evaluation. Stage32 equations, exact IDs, centering, bounds, objectives, branches and gates remain unchanged. Every restriction is fitted independently; no Stage30 coefficient or independent bonus is imported.',
      '## Decision and direct answers',
      'Prior normalized R contains useful information against the baseline: MAE gains0.4179/0.3266/0.2562/0.3803 pp in2014/2017/2020/2023, pooled0.3424 pp. R-only is better than S in2014/2017 and worse in2020/2023. The independently refitted joint model gains over S0.3972/−0.0263/−0.2476/+0.0701 pp; pooled improvement is only0.0128 pp. The strict view gives0.0156 pp, while separated chronology reverses it to−0.0881 pp. This does not justify replacing S with the extra joint coefficient as the default development model.',
      '**Provisional development recommendation:** retain S as the preferred complete-share candidate, baseline mandatory; retain R-only as a useful research challenger with stronger early-fold share performance. Archive S+R as mixed incremental evidence, not a failed real-world personal effect or a proven improvement. Joint estimates should not be imported into S independently. Winner counts favor joint in some folds, but share MAE is primary and its pooled advantage is small/influence-sensitive. All operational selections and historical failed screens remain unchanged.',
      'These are graded development conclusions, not a new binary screen. R coefficients reach the frozen+4 boundary in three primary folds; they are constrained estimates, **not** evidence of weak signal. No bound is widened. θR adjusts log intensity per unit fractional normalized residual, not a personal-vote retention percentage. S/R cannot causally separate tactical voting, stable seat conditions and personal strength.',
      '## Coverage, common samples and information',
      'The preserved Stage32 frame retains356 target seats/2,485 occurrences,245 complete held exact-general slates/1,742 candidates and all excluded/cancelled/Māori records. Primary four-model scoring covers182 contests/1,319 candidates in2014/2017/2020/2023; no fitted2011 is manufactured. Separated chronology covers162/1,176 and retains no-fit2014. All fitted methods share exact whole-contest/candidate IDs; there are no final numerical/mapping abstentions in trained folds. Uniform is available on every full slate; restricted zero-floor uses only its documented positive-support/no-no-group subset, with contextual same-sample metrics saved separately.',
      'Source S coverage across the full eligible panel is1,094; R452 broad/386 strict. In primary fitted evaluations:332 both-feature,482 S-only,0 R-only and505 neither-feature candidates. All current R support also has S, but R never requires S by rule or target residual availability. Māori source-R evidence30/27 remains audit-only. No source residual transfers to replacements; unlinked/missing histories contribute a neutral exponent **after** earlier-only centering, not claimed zero actual strength. Complete closure lets their shares change when others change.',
      'Primary trains and evaluates with saved Stage31 complete party vectors conditional on observed target national support and retrospective target slates. Shared group support is mapped once; no candidate-roster party-input renormalization, source continuity invention or national calibration. The separate observed retraining and fixed-parameter substitution branches retain their different estimands. Exact geography is selected, not representative; boundaries/identity/normalization/source timing remain frozen.',
      '## Primary errors by election (pp)',
      table(['Target','Contests/candidates',*[NAMES[m]+' MAE / RMSE' for m in ORDER]],[
        [r['targetYear'],str(r['contests'])+'/'+str(r['candidates']),*[num(r['methods'][m]['contestEqualMaePP'])+' / '+num(r['methods'][m]['contestEqualRmsePP']) for m in ORDER]] for r in primary if r['records']]+[['Pooled',str(p['contests'])+'/'+str(p['candidates']),*[num(p['methods'][m]['contestEqualMaePP'])+' / '+num(p['methods'][m]['contestEqualRmsePP']) for m in ORDER]]]),
      'MAE averages candidate absolute pp error within a contest, then contests equally. RMSE is sqrt(mean_contests(mean_candidates(error²))), not the mean of contest RMSEs. Pooled rows weight each contest, not each election equally;20-seat2014 does not weigh as much as64-seat2017. Complete candidate/party vote denominators remain distinct. Full-slate bias cancels only as an accounting identity.',
      '## Independently refitted paired improvements',
      'Positive numbers mean named comparator error minus model error. All five pairs use identical records. Reduced restrictions have their own κ/coefficient estimates, not zeroed combined coefficients.',
      table(['Branch','Target','S vs baseline','R vs baseline','S+R vs baseline','S+R vs S','S+R vs R'],fold_gains),
      '## Finite sensitivities (pooled contest-equal MAE, pp)',
      table(['Branch','Contests',*[NAMES[m] for m in ORDER],'S+R gain vs S'],sensitivities),
      'Lower/upper rows are the two frozen coherent all-row measurement scenarios and saved witnesses, refitting the same restrictions and training means. Their effects are tiny at four-decimal display; unrounded artifacts retain differences. They are not exhaustive extrema or calibrated uncertainty. Strict linkage changes available R/centering, never the complete evaluation slates. Separated chronology changes both allowed training and no-fit coverage, so its pooled scores have a different denominator; fold-specific comparisons above preserve that distinction.',
      'Observed-retrained uses independently estimated earlier observed-input parameters. Primary-fixed-to-observed uses primary constructed-fit parameters/means/source features unchanged and changes only evaluation party inputs. Neither branch is an as-of forecast. All branches retain the complete finite matrix rather than its Cartesian product.',
      '## Coefficients and numerical status',
      table(['Target','Restriction','κ','θS','θR','Floor location','Coefficient bound contact'],params),
      'All56 distinct training-array signatures pass optimizer success, projected-gradient/all-start objective gates, independent4097-grid floor-profile agreement and fitted-point rank. Relevant identical problems are reused; the fixed-to-observed branch does not fit. Eight unique jobs have a coefficient boundary contact; primary R-only2014/2017/2020 is+4. Every primary joint coefficient is interior. Full unrounded parameters, independent optima, objectives, gradients, conditioning and branch references live in construction/fit-cache artifacts.',
      'The [numerical audit](stage33-numerical-implementation.md) preserves22 initial and32 intermediate line-search abstentions before scoring. The final same-equation implementation uses constant-shift/direct reduction and184 precision retries from the exact same starts/options; all final checks pass. No status failure was accepted solely because its gradient was small, no pseudoinverse, tolerance weakening or parameter-bound expansion. Original Stage22 semantics/code/data remain unchanged.',
      '## Group errors and bias',
      'Primary group metrics are candidate-equal, over the shown candidate count. Present-contest-equal group sensitivities average only contests containing that group and name their denominator in the machine output. National/Labour combined overlaps its constituents; category and feature-support tables do not add up automatically to the whole-slate metric. No subgroup coefficients or post-result admission.',
      table(['Group','Candidates','Present contests',*[NAMES[m]+' MAE' for m in ORDER]],group_rows),
      table(['Group',*[NAMES[m]+' signed bias' for m in ORDER]],group_bias),
      'Compared with S, joint lowers smaller mapped-party, no-group and unsupported-feature average errors, but worsens pooled National/Labour candidate-equal MAE. Both-feature average incremental gain is also small; source-only R usefulness alone does not guarantee complementary gains once S is jointly refitted. No-group candidates cannot gain a uniquely personal feature here, but their predictions legitimately respond through the shared denominator and κ. Unsupported candidates remain fully evaluated.',
      'Unsupported-feature errors do not establish a single generic split fallback would repair them: the pooled neither-feature share MAE is modest, and no-group/entrant heterogeneity remains. **Do not launch a fallback estimate by default.** At most one later test needs a concrete source route and consequential expected benefit. No biography/tenure/linkage expansion is needed for this frozen comparison.',
      '## Rankings, margins and composition',
      table(['Target',*[NAMES[m]+' unique correct / contests; ties' for m in ORDER]],[
        [r['targetYear'],*[str(r['methods'][m]['uniqueCorrect'])+'/'+str(r['contests'])+'; '+str(r['methods'][m]['tieCount']) for m in ORDER]] for r in primary if r['records']]),
      table(['Target',*[NAMES[m]+' observed-top-two margin MAE' for m in ORDER]],[
        [r['targetYear'],*[num(r['methods'][m]['actualTopTwoMarginMaePP']) for m in ORDER]] for r in primary if r['records']]),
      'Observed ordered top-two margin compares q(actual winner)−q(actual runner-up) with their actual share gap; tied observed runners are averaged, no ID tie-break. Predicted top-two gap error is separately recorded. Unique accuracy, explicit predicted ties/tied-set inclusion and all margin outputs are diagnostic, not calibrated winner probabilities or an automatic share-model veto.',
      table(['Composition','Contests/candidates',*[NAMES[m]+' MAE' for m in ORDER]],[
        [label,str(p[name]['contests'])+'/'+str(p[name]['candidates']),*[num(p[name]['methods'][m]['contestEqualMaePP']) for m in ORDER]] for name,label in [('originalTransitions','Original2017/2023 fitted'),('added2014_2020','Added2014/2020')]]),
      'Original2011 has benchmarks only; it is not silently included in fitted pooled accuracy. Added2014/2020 evidence represents individually exact seats, not entire redistributed elections. Adjacent transitions/repeated people/seats/shared party-election residual references/national inputs create dependence. Seat counts do not create independent temporal replications; every election has already informed development.',
      '## Fixed-fit influence',
      table(['Pair','Pooled MAE improvement','Delete-one minimum','Delete-one maximum','Improved contests','Worsened contests'],influence),
      table(['Joint vs S largest absolute effect contest','MAE improvement pp'],[[r['targetElectorateId'],num(r['maeImprovementPP'])] for r in p['pairs']['baseline_plus_S_plus_R__versus__baseline_plus_S']['fiveLargestAbsoluteEffects']]),
      'Joint vs S pooled gain ranges−0.0153 to+0.0385 pp after deleting one score only. This is influence on a fixed fit, not refitting, deleted-election forecasting or a reason to omit any primary record. Keep the historical0.25pp convention contextual; no new every-fold threshold or significance requirement is imposed. Forecast usefulness, strength of evidence and operational selection remain distinct.',
      '## Independent validation and reproduction',
      f"Independent direct arithmetic verified{v['counts']['shares']:,} predicted shares,{v['counts']['metrics']} metrics and{v['counts']['pairedGains']} paired gains; eight representative primary2014/2023 optima agree with independent direct joint-SLSQP checks at1e−8 objective tolerance. Direct share tolerance1e−12 and metric tolerance1e−8 remain fixed. Source checksum/preservation and actual-adapter counterfactual tests are distinct from these arithmetic checks. Final local-suite and final-head CI results appear in PROJECT_STATE.md/PR.",
      '```sh\npython -m scripts.models.joint_candidate_share.construction --check\npython -m scripts.models.joint_candidate_share.evaluation --check\npython -m scripts.models.joint_candidate_share.verification --check\npython -m scripts.models.joint_candidate_share.report --check\npython -m unittest scripts.tests.test_stage33_numerics scripts.tests.test_stage33_pipeline -v\n```',
      'Construction --check verifies exact-array cache signatures, objective/gradient/rank and phase hashes, then reproduces predictions. It does not repeat all expensive historical optimizers; explicit --refit recomputes only this stage. The independent verifier reruns representative numerical checks without choosing alternative parameters. All1,434 earlier tracked data artifacts/raw sources/identity/geography/fits/operational selections remain byte-identical. Held-out candidate results affect scoring only; earlier candidate outcomes legitimately fit later-fold parameters.',
      '## Exact next decision and stop',
      'Review these findings and adopt S provisionally for share development, retaining baseline/R-only research references and the mixed joint result. The next separately authorized implementation should be a bounded dated national-support/direct electorate-poll, live-slate and target-boundary input-readiness layer with explicit forecast cutoffs. National reconciliation, shared uncertainty (national error propagated once), coherent simulations/MMP and archived raw/adjusted forecasts follow separately. No automatic generic fallback, R-bound expansion, response integration, penalty search, new mean family, acquisition or operational deployment follows from these results.']
    return '\n\n'.join(descriptions)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify_inputs();verify_phase('construction');verify_phase('evaluation');verify_phase('verification');verify_phase('numerical-audit');text=build()
    if a.check:
        if PATH.read_text()!=text:raise ValueError('Changed Stage33 report')
    else:PATH.write_text(text)
    print('Stage33 report reproduced; prior preserved',preserve())


if __name__=='__main__':main()
