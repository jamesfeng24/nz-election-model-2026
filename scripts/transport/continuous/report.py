"""Bounded transport findings from saved evaluation/readiness, no new selection search."""
import argparse
from .common import ROOT,read,verify,PREFIX


def build():
    e=read(PREFIX+'/evaluation.json');ready=read(PREFIX+'/readiness-2026.json');lines=[
        '# Stage42 continuous predecessor-weighted transport findings','',
        'Frozen audit/contract66b033a preceded construction8365b92, which was pushed before scoring. No acquisition, refitting, MCMC or live forecast. Earlier numerical outputs/adjudications/operational records remain unchanged.','',
        '## Within-seat evidence and assumptions','',
        'Preserved evidence cannot identify a transferred residential fragment as more National- or Labour-leaning. Acquired voting-place files contain candidate ballots, not party-by-residence detail. Advance sites outside the home seat and aggregated special/overseas votes preclude booth catchment inference. See the [audit](stage42-within-seat-evidence-audit.md). Zero discovery queries/resources; no finer-flow implementation.','',
        'The unchanged Stage41 feasible population witness supplies `F=source party votes × source-outgoing population weight`, explicitly uniform voting within source electorates. Lambda uses every predecessor party mass, including unsupported components. S and same-person R are centered with each earlier saved training mean **before** weighting; missing evidence contributes a neutral exponent and is never renormalized away. R uses one accepted source in any genuine predecessor, not an outgoing replacement bonus. Party weighting of candidate-normalized residuals is a modelling assumption.','',
        '## Historical paired full-frame diagnostic','',
        'Only saved primary expanding-window Stage33 S+R parameters, observed target local party inputs and complete retrospective slates. All policies share identical IDs; strict changes R availability only, not fitted parameters. Errors/gains are percentage points; positive gain means lower error than the comparator.','',
        '| Election | Contests / candidates | Exact fallback MAE / RMSE | Stage41 90 MAE / RMSE | Continuous MAE / RMSE | Gain vs fallback / 90 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for f in e['folds']:
        s=f['samples']['full'];m=s['metrics'];c=m['continuous']
        lines.append(f"| {f['targetYear']} | {c['contests']} / {c['candidates']} | {m['exact_fallback']['maePP']:.4f} / {m['exact_fallback']['rmsePP']:.4f} | {m['stage41_90']['maePP']:.4f} / {m['stage41_90']['rmsePP']:.4f} | {c['maePP']:.4f} / {c['rmsePP']:.4f} | {s['pairs']['continuous_versus_exact_fallback']['maeGainPP']:+.4f} / {s['pairs']['continuous_versus_stage41_90']['maeGainPP']:+.4f} |")
    lines+=['','Pooling weights each of129 contests equally (64/129 and65/129 election weights). Primary pooled MAE: '+', '.join(f"{b}={e['pooled']['metrics'][b]['maePP']:.4f}pp" for b in ('exact_fallback','stage41_90','continuous'))+'. Full-slate signed bias cancels by conservation and is accounting, not calibration. Seven Māori targets per year remain coverage-only. No held general contest is excluded.','',
        '### Exclusive overlap bands and strict sensitivity','',
        '| Election / band | Contests | Continuous gain vs fallback | Continuous gain vs Stage41 90 |',
        '| --- | ---: | ---: | ---: |']
    for f in e['folds']:
        for band in ('exact','approximate_95','approximate_90','fallback'):
            s=f['samples'][band]
            lines.append(f"| {f['targetYear']} / {'below90 or ambiguous' if band=='fallback' else band} | {s['metrics']['continuous']['contests']} | {s['pairs']['continuous_versus_exact_fallback']['maeGainPP']:+.4f} | {s['pairs']['continuous_versus_stage41_90']['maeGainPP']:+.4f} |")
    lines+=['','These are paired effects within each band, not a comparison of different tier populations. Exact features and Stage41 predictions on original37/47 common samples reproduce within1e-12. Continuous versus90 on those original samples is −0.0044pp (2014) and +0.0059pp (2020): most gain comes from avoiding neutral fallback below90, not a dramatic reweighting improvement on already admitted seats.','',
        '| Election | Strict continuous MAE / RMSE | Gain vs strict fallback / 90 |',
        '| --- | ---: | ---: |']
    for f in e['folds']:
        s=f['samples']['full'];m=s['metrics']['continuous_strict']
        lines.append(f"| {f['targetYear']} | {m['maePP']:.4f} / {m['rmsePP']:.4f} | {s['pairs']['continuous_strict_versus_exact_fallback_strict']['maeGainPP']:+.4f} / {s['pairs']['continuous_strict_versus_stage41_90_strict']['maeGainPP']:+.4f} |")
    lines+=['','### Feature support and unsupported mass','',
        '| Election | S / R / strict R positive-mass support | Mean unsupported S / R weight |',
        '| --- | ---: | ---: |']
    for f in e['folds']:
        c=f['samples']['full']['continuousFeatureSupport']
        lines.append(f"| {f['targetYear']} | {c['S']['positiveSupportedMass']} / {c['R']['positiveSupportedMass']} / {c['RStrict']['positiveSupportedMass']} | {c['S']['meanUnsupportedWeightCandidateEqual']:.4f} / {c['R']['meanUnsupportedWeightCandidateEqual']:.4f} |")
    lines+=['','Support counts mean positive party mass with evidence, not linked-only scoring. Unsupported weights average over all member candidates, including undefined no-group/entrant fallbacks. Complete slates stay primary. Missing support is not observed zero strength.','',
        '### National/Labour and other-category errors','',
        'Candidate-equal subgroup metrics retain the original valid-candidate denominator. These averages do not sum to the contest-equal whole-slate metric.','',
        '| Election / category | Candidates | Fallback MAE / bias | 90 MAE / bias | Continuous MAE / bias |',
        '| --- | ---: | ---: | ---: | ---: |']
    for f in e['folds']:
        for group,g in f['samples']['full']['categoryMetrics'].items():
            ms=g['metrics'];values=[' / '.join(f'{ms[b][k]:+.4f}' if k=='biasPP' else f'{ms[b][k]:.4f}' for k in ('maePP','biasPP')) for b in ('exact_fallback','stage41_90','continuous')]
            lines.append(f"| {f['targetYear']} / {group} | {g['candidates']} | "+' | '.join(values)+' |')
    lines+=['','### Largest individual losses versus Stage41 90','',
        '| Election | Seat | Paired MAE gain |','| --- | --- | ---: |']
    for f in e['folds']:
        for loss in f['samples']['full']['pairs']['continuous_versus_stage41_90']['largestFiveLosses']:
            lines.append(f"| {f['targetYear']} | {loss['targetName']} | {loss['gainPP']:+.4f} |")
    lines+=['','All observations remain in scores. Largest gains and every paired error are retained in `evaluation.json`.2014 National share MAE worsens despite overall gains;2020 National/Labour improve. Do not interpret a pooled gain as universal seat/party improvement.','',
        '## 2026 readiness companion','',
        f"All{ready['coverage']['seats']} seats and{ready['coverage']['knownCandidates']} known candidates retained;{ready['coverage']['completeSlates']} complete slates. No partial-slate normalization or2026candidate shares.",
        '',f"Known general candidates: S{ready['coverage']['candidateFeatureSupport']['general']['S']}, R{ready['coverage']['candidateFeatureSupport']['general']['R']}, strict R{ready['coverage']['candidateFeatureSupport']['general']['RStrict']}; source party-seat S{ready['coverage']['sourcePartySeatSSupport']['general']} independently of announcements. Stage41 corresponding90 counts were68/16/7 and183.",
        '',f"Partially supported known general features: S{ready['coverage']['candidatePartialSupport']['S']}, R{ready['coverage']['candidatePartialSupport']['R']}, strict R{ready['coverage']['candidatePartialSupport']['RStrict']}. Every component retains its mass, weight, source, centered value and missing reason. Latest saved2023general training means are a named readiness transformation reference, not a new fit or live forecast.",
        '', 'All seven Māori party-flow records remain, source S matrices unavailable and one source R relationship evidence-only. General candidate coefficients are not extended; national TPM support remains distinct from Māori candidate votes. Complete nominations/target ballot roster, national scenarios and Māori polling/unpolled baseline remain separate dependencies.','',
        '## Development decision and stopping point','',
        'Retain continuous transport as the preferred mean-feature development scenario, with Stage41 frozen90 and exact fallback preserved as reproducible controls. It improves full-frame errors in both reused environments and under strict linkage, while individual failures and fragment-composition uncertainty remain material. This is forecasting-oriented development evidence, not causal identification, as-of validation or calibrated probabilities. No coefficient/threshold/flow changed after scores.','',
        'The next separately authorized implementation is coherent local-party/candidate uncertainty, covering uniform population-to-vote allocation, feature transport, missing histories, candidate/local errors, parameter uncertainty and shared dependence. National forecast error enters once. Overlap and finite feasible bounds are not calibrated error variances. Official nominations and Māori polling remain separately bounded. Stop further mean-feature searches here.']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify();text=build()
    path=ROOT/'docs/stage42-continuous-transport-findings.md'
    if a.check:
        if path.read_text()!=text:raise ValueError('Stale Stage42 findings')
    else:path.write_text(text)
    print('Stage42 findings reproducible')


if __name__=='__main__':main()
