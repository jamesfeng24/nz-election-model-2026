"""Readable finite findings from saved experts; no fitting or adaptive weights."""
import argparse
from .common import *
from .presentation import csv_table, scatter

PATH = ROOT/'docs/stage34-s-r-error-pattern-results.md'
ORDER = ('baseline', S, R, JOINT)
NAMES = {'baseline': 'Baseline', S: 'S', R: 'R', JOINT: 'S+R'}


def num(v):
    return 'unavailable' if v is None else f'{v:.4f}'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(str, row))+' |' for row in rows])


def build(data, movement, audit):
    primary = next(b for b in data['branches'] if b['branch']=='primary'); cases = [f for f in data['folds'] if f['branch']=='primary' and f['records']]
    within = primary['withinElectionCentered']; robust = primary['robustness']['methods']
    lines = ['# Stage34 — bounded post-result S/R error patterns and robustness',
        '**Descriptive investigation of frozen Stage33 experts, not new predictive fitting or independent validation.** Contract/inventory208ea60 was committed/pushed before diagnostics. [Frozen contract](stage34-analysis-contract.md) fixes one movement measure, samples, weights and finite sensitivities. Stage33 results/recommendation, coefficients/bounds/predictions and all operational nulls remain unchanged.',
        '## Decision and interpretation',
        'Retain **S and S+R as active complete-share development alternatives**, R-only as a meaningful challenger and baseline as mandatory control. This subsequent decision does not rewrite Stage33\'s provisional S-default recommendation or discard the joint model. Joint lower environment dispersion deserves continued comparison, while its tiny contest-weighted incremental gain and separated-chronology loss remain visible.',
        '**Recommend A: move to bounded dated-input readiness/replay while retaining these alternatives.** Movement is associated with S/R differences in this finite panel, but upstream input error, feature coverage, constrained fits, partial-election selection and only four environments prevent identifying an adaptive rule. A blend experiment is conceivable later, not the next automatic stage. The likely immediate decision value of realistic dated national/poll/slate/boundary inputs exceeds learning weights from scarce chronological meta-training data.',
        '## Whole-party movement and denominators',
        'TV D=0.5Σ|Ptarget−Psource| uses the entire valid-party simplex, including categories without local candidates. Display100D is displaced-share pp, not individual voter switching. Official nationwide support includes the complete electorate population; no national denominator is rebuilt from selected seats. Source/target local valid-party denominators differ from valid-candidate denominators in the share errors. Stage31 affinity vectors remain conditional on actual target national results, locally coherent and not exactly nationally reconciled.',
        f"All five roster audits have complete canonical whole-group alignment; {sum(r['status']=='available' for r in movement['records'])} exact-general party-ballot records are available in the full356-seat ledger (including2011 no-fit and cancelled Port Waikato party ballot). All182 primary evaluated contests have distances; there are no movement-only exclusions. Māori/cancelled/nonexact/no-fit cases are retained outside fitted candidate scoring. Diagnostic exclusion machinery never trims original performance rows.",
        'Preserved D017/D022 aliases prevent renamed Conservative/Social Credit/Te Pāti Māori/NewZeal groups generating artificial turnover. Internet-MANA and Freedoms NZ are indivisible ballot groups; constituent affiliation does not identify whole-group continuity. Their documented roster entry/exit is counted as structural displacement, including alliance reorganization, without assigning constituent votes. Missing evidence is never zero-filled. Full mapping/structural/denominator records are in inventory.json and movement.json.',
        '## Four national environments',
        table(['Target','Contests','National100D','G: R−S MAE pp','J: S−joint MAE pp'], [[r['targetYear'], r['contests'], num(100*r['nationalDistance']), num(r['meanGpp']), num(r['meanJpp'])] for r in primary['environmentRows']]),
        'The two smaller-national-movement environments favor R;2020/2023 favor S. It is not a strictly increasing four-point relationship:2023 has slightly larger D but smaller G than2020. These are four election environments, not182 independent national observations. No national regression or adaptive weighting rule is fitted.',
        '## Within-election associations',
        table(['Target','n','Constructed D slope per10pp','Constructed Spearman','Observed D slope per10pp','Observed Spearman'], [[f['targetYear'], f['contests'], num(f['associations']['constructedLocalDistance']['slopeGainPPPer10ppMovement']), num(f['associations']['constructedLocalDistance']['spearman']), num(f['associations']['observedLocalDistance']['slopeGainPPPer10ppMovement']), num(f['associations']['observedLocalDistance']['spearman'])] for f in cases]),
        f"Constructed-distance slopes are positive in each primary fold, so the story is not merely between elections. Strength varies:2023 rank association is weak. Pooled within-election-centered/equal-total-election slope is {num(within['constructedLocalDistance']['slopeGainPPPer10ppMovement'])} pp G per10pp D; correlation {num(within['constructedLocalDistance']['pearson'])}. Observed-local-distance sensitivity is weaker: slope {num(within['observedLocalDistance']['slopeGainPPPer10ppMovement'])}, correlation {num(within['observedLocalDistance']['pearson'])}. No significance tests, optimized bins, smoothers or multivariable attribution.",
        '![Constructed local movement scatter](../data/processed/diagnostics/s-r-robustness/constructed-movement.svg)',
        '![Observed local movement scatter](../data/processed/diagnostics/s-r-robustness/observed-movement.svg)',
        'Plots show every available primary point, four fixed panels, TV0–100pp horizontal scale and one shared symmetric vertical scale covering all gains/losses. Axis extent is a layout rule, not a selected effect threshold. Hover labels identify contests. [Complete per-contest data table](../data/processed/diagnostics/s-r-robustness/contest-diagnostics.csv) includes all five branches, candidate counts, support fractions/counts, upstream errors and four model MAEs; analysis.json retains all candidate errors.',
        '## Input/linkage/chronology sensitivities and election influence',
        table(['Saved branch','D definition','Centered slope per10pp','Centered correlation','Elections/contests'], [[b['branch'], k, num(v['slopeGainPPPer10ppMovement']), num(v['pearson']), str(v['elections'])+'/'+str(v['contests'])] for b in data['branches'] for k, v in b['withinElectionCentered'].items()]),
        'Strict-linkage positive constructed association persists. The observed-input branches attenuate it, so constructed party-input errors are a plausible contributor rather than an explanation ruled out. `observed_retrained` uses separately trained saved fits; `primary_fixed_to_observed` changes only held-out party inputs using primary fits. Neither operation is a new Stage34 fit. When observed local movement and observed inputs are used together,2017 slope is slightly negative and its rank association essentially zero; the pattern is not uniform across all evidence views.',
        table(['Branch','Target','Observed-input/observed-D slope','Spearman'], [[f['branch'], f['targetYear'], num(f['associations']['observedLocalDistance']['slopeGainPPPer10ppMovement']), num(f['associations']['observedLocalDistance']['spearman'])] for f in data['folds'] if f['records'] and f['branch'] in ('observed_retrained','primary_fixed_to_observed')]),
        table(['Branch','Deleted election','Constructed-D slope','Correlation','Observed-D slope','Correlation'], [[b['branch'], r['deletedTargetYear'], num(r['associations']['constructedLocalDistance']['slopeGainPPPer10ppMovement']), num(r['associations']['constructedLocalDistance']['pearson']), num(r['associations']['observedLocalDistance']['slopeGainPPPer10ppMovement']), num(r['associations']['observedLocalDistance']['pearson'])] for b in data['branches'] for r in b['fixedPredictionDeleteOneElection']]),
        'All primary delete-one-election centered associations stay positive. This is score/association influence with saved predictions, not deleting an election from expert training or an out-of-time forecast. Adjacent training transitions, repeated seats and national environments remain dependent.',
        '## Competing explanations kept visible',
        table(['Target','Slate candidates','Broad R / strict R','Training contests/environments','R θ; bound','Full-vector input MAE','NAT input MAE','LAB input MAE'], [[r['targetYear'], r['candidates'], str(r['RSupported']['broad'])+'/'+str(r['RSupported']['strict']), str(r['trainingContests'])+'/'+str(len(r['trainingEnvironments'])), num(r['savedRFit']['coefficient'])+'; '+str(r['savedRFit']['thetaAtBoundary']), num(r['meanPartyInputMAEpp']), num(r['majorPartyInputMAEpp']['nationalparty']), num(r['majorPartyInputMAEpp']['labourparty'])] for r in primary['environmentRows']]),
        'Broad R coverage falls from47/143 candidates in2014 to108/459 in2023; strict coverage falls to78/459. Training grows from one to four transition environments. R is constrained at+4 in2014/2017/2020, interior in2023. These co-vary with election conditions; no multivariable fit separates them. Major-party input errors are much larger than the all-category average; small-category averaging must not imply perfect candidate inputs. Contest records show slate size, both coverage fractions, training/fit references and upstream signed errors. Coefficient-bound contacts describe constrained expert predictions; unconstrained R behavior is unknown.',
        table(['Branch','R group','Candidates / present contests','Baseline MAE','S MAE','R MAE','Joint MAE','G','J'], [[b['branch'], name, str(g['candidates'])+'/'+str(g['presentContests']), *[num(g['methods'][m]['candidateEqualMaePP']) if g['methods'][m] else 'unavailable' for m in ORDER], num(g['Gpp']), num(g['Jpp'])] for b in data['branches'] for name, g in b['Rgroups'].items()]),
        'Group errors above are candidate-equal; present-contest-equal sensitivities and signed bias are saved with explicit denominators. Unsupported rows remain in complete-slate scores. R acts exponentially on current party intensity and changes other candidates through normalization; it is not a fixed carry-forward bonus. S is historical and can also become stale. S+R is jointly fitted, not a convex average of standalone forecasts. General results are not explained using Māori examples outside the sample.',
        '## Across-election robustness, with baseline-relative control',
        table(['Branch','Model','Pooled contest MAE / RMSE','Equal-election mean','Population SD','Range','Worst MAE / election','Gain mean / SD','Worst gain / election'], [[b['branch'], NAMES[m], num(r['originalContestEqualPooledMaePP'])+' / '+num(r['originalContestEqualPooledRmsePP']), num(r['electionMaeDispersion']['equalElectionMeanPP']), num(r['electionMaeDispersion']['populationSDPP']), num(r['electionMaeDispersion']['rangePP']), num(r['electionMaeDispersion']['maximumPP'])+' / '+str(r['electionMaeDispersion']['worstTargetYears']), num(r['baselineRelativeImprovementDispersion']['equalElectionMeanPP'])+' / '+num(r['baselineRelativeImprovementDispersion']['populationSDPP']), num(r['baselineRelativeImprovementDispersion']['minimumPP'])+' / '+str(r['baselineRelativeImprovementDispersion']['worstImprovementTargetYears'])] for b in data['branches'] if 'robustness' in b for m in ORDER for r in [b['robustness']['methods'][m]]]),
        table(['Branch','Target',*[NAMES[m]+' gain vs baseline' for m in ORDER]], [[b['branch'], y, *[num(next(r for r in b['robustness']['methods'][m]['byElection'] if r['targetYear']==y)['improvementOverBaselinePP']) for m in ORDER]] for b in data['branches'] if 'robustness' in b for y in b['robustness']['availableTargetYears']]),
        f"Primary joint environment SD {num(robust[JOINT]['electionMaeDispersion']['populationSDPP'])} pp is below baseline {num(robust['baseline']['electionMaeDispersion']['populationSDPP'])}, S {num(robust[S]['electionMaeDispersion']['populationSDPP'])} and R {num(robust[R]['electionMaeDispersion']['populationSDPP'])}; its worst average error is also lower. This is useful descriptive robustness supporting continued retention. Equal-election mean favors joint more than original contest weighting because20-seat2014 gains receive a full election weight. It does not replace Stage33's weighting or make2014 representative.",
        'Baseline-relative gains supply a different check: joint still deteriorates in2017, slightly more than S; R-only has the smallest gain dispersion and improves baseline in every primary fold. Joint lower absolute dispersion therefore does not mean uniformly better baseline-relative robustness. Separated chronology has three available folds (no fitted2014); compare all four models on those same folds, not primary four-fold dispersion as if populations matched. Baseline gain dispersion is identically zero by definition, not evidence of perfect robustness. No composite accuracy/variance score or calibrated forecast uncertainty is constructed.',
        '## Largest joint-versus-S contest effects',
        table(['Type','Contest','J pp'], [[kind, str(r['targetSeatName'])+' ('+r['targetElectorateId']+')', num(r['Jpp'])] for name, kind in [('fiveLargestGains','gain'), ('fiveLargestLosses','loss')] for r in primary['jointVsS'][name]]),
        f"Joint improves {primary['jointVsS']['improvedContests']} primary contests, worsens {primary['jointVsS']['worsenedContests']}, ties {primary['jointVsS']['ties']}; all remain in primary summaries. No influential seat removal, expert refit or blend fitting.",
        '## Preservation, verification and finite next decision',
        f"Independent arithmetic checks {audit['counts']['distances']} distances, {audit['counts']['contestModelErrors']} contest/model errors, {audit['counts']['robustnessIdentities']} robustness identities and {audit['counts']['centeredAssociationIdentities']} centered/influence identities, {audit['counts']['spearmanChecks']} independent rank associations and {audit['counts']['preservedCountDenominatorChecks']} raw-denominator distances at frozen tolerances. All {audit['priorBytesPreserved']} prior data files/raw sources/fits/predictions/adjudications/operational selections remain byte-identical. Actual party-reader candidate-outcome mutations leave movement unchanged; held-out outcome mutations change error diagnostics only with the exact same saved prediction/membership arrays. Final test/CI status is recorded separately in PROJECT_STATE.md/PR.",
        'The evidence is consistent with movement relating to S advantage in constructed-input within-election diagnostics, but attenuated/inconsistent in the observed-input sensitivity. It does not establish a unique mechanism, causal recency, adaptive weights or operational validation. Only four reused development environments, selected exact-seat samples, differing slate/feature support, algorithmic linkage, constrained coefficients and oracle national inputs remain limitations.',
        'Choose A now: bounded dated-input readiness/replay retaining S/S+R/R/baseline. If a separately authorized blend later becomes worthwhile, it must have a fixed blend control, one coherent slate-wide weight, separate national/local adaptation hypotheses, earlier out-of-time expert predictions and explicit scarcity of chronological meta-training (2014 is the first trained expert fold), plus uncertainty in weights beyond national support. A neat four-point relationship alone cannot justify it. No fit/acquisition/forecast/integration begins automatically.']
    return '\n\n'.join(lines)+'\n'


def write_text(path, value, check):
    if check:
        if path.read_text()!=value:
            raise ValueError('Changed Stage34 presentation '+str(path))
    else:
        path.write_text(value)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); a = p.parse_args()
    verify_inputs()
    for name in ('movement', 'analysis', 'verification'):
        verify_phase(name)
    data, movement, audit = local('analysis.json'), local('movement.json'), local('independent-verification.json')
    write_text(DEST/'contest-diagnostics.csv', csv_table(data['folds']), a.check)
    for name, field in [('constructed-movement.svg','constructedLocalDistance'), ('observed-movement.svg','observedLocalDistance')]:
        write_text(DEST/name, scatter(data['folds'], field), a.check)
    write_text(PATH, build(data, movement, audit), a.check)
    phase('presentation', ['contest-diagnostics.csv', 'constructed-movement.svg', 'observed-movement.svg'], ['presentation', 'report'], a.check)
    print('Stage34 report/tables/scatters reproduced; prior', preserve())


if __name__ == '__main__':
    main()
