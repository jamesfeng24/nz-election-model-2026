"""Separated descriptive support audit and reporting; not a simulation producer."""
import argparse
import numpy as np
from scripts.uncertainty_tails.common import PREFIX,INVENTORY,ROOT,read,save,verify
from scripts.uncertainty_tails.diagnosis import summary


def support_audit():
    inventory=read(INVENTORY);lookup={r['targetElectorateId']:r for r in inventory['candidateRecords']}
    records=[]
    for record in read(PREFIX+'/diagnosis.json')['layers']['candidate']['records']['balance']:
        row=lookup[record['id']]
        support=sum(row['features'][i]['supportedMass']['R']>0 for i,g in enumerate(row['groups']) if g in ('national','labour'))
        records.append({**record,'history':{0:'neither_R',1:'one_R',2:'both_R'}[support],
                        'geographyClass':'exact' if row['geography']=='exact' else 'nonexact'})
    by_year={str(y):{h:summary([r for r in records if r['year']==y and r['history']==h])
             for h in ('both_R','one_R','neither_R')} for y in sorted({r['year'] for r in records})}
    standardized={}
    for fields in (('history',),('history','geographyClass')):
        strata={tuple([r['year']]+[r[k] for k in fields]) for r in records};values=[]
        for key in sorted(strata):
            subset=[r for r in records if tuple([r['year']]+[r[k] for k in fields])==key]
            rms=float(np.sqrt(np.mean([r['seatResidual']**2 for r in subset]))) if len(subset)>=8 else None
            for r in subset:
                sd=rms or r['electionRMS'];values.append({**r,'seatResidual':r['seatResidual']/sd if sd else 0.,'electionRMS':1.,'earlierSeatSD':1.})
        standardized['+'.join(fields)]=summary(values)
    return {'stage':46,'purpose':'independent competing-scale-heterogeneity audit, completed before predictive scoring',
            'groups':'prediction-time R support both/one/neither, exact versus nonexact; no residual-selected admission',
            'byElection':by_year,'standardized':standardized,'retainedAll257Seats':len(records)==257,
            'warning':'scale heterogeneity moderates, does not eliminate tails; no universal tail law or identified nu',
            'noVariancePredictorOrSampleChange':True}


def text():
    evaluation=read(PREFIX+'/evaluation.json');v=read(PREFIX+'/verification.json');lines=[
        '# Stage46 bounded robust centre/tail findings','',
        'Post-Stage45 development test; all historical observations retained. Student nu4 is assumed, not estimated. Shared Gaussian effects and frozen continuous S+R mean coefficients remain unchanged.',
        '', '| Layer / election | Stage45 CRPS | Robust Gaussian | Student | Point | Student − Gaussian |',
        '|---|---:|---:|---:|---:|---:|']
    for case in evaluation['cases']:
        s={m:r['summary']['contestEqualCRPSPP'] for m,r in case['methods'].items()}
        lines.append(f"| {case['layer']} {case['year']} | {s['stage45']:.4f} | {s['robust_gaussian']:.4f} | {s['student']:.4f} | {s['point']:.4f} | {s['student']-s['robust_gaussian']:+.4f} |")
    lines += ['', 'CRPS is in percentage points, lower is better. Equal contests within each election; pooled and equal-election views are saved separately. Gaussian/Student share robust central MAD and conditional remainder integration. Their difference isolates the tail law; differences from Stage45 include the disclosed numerical location correction.',
              '',f"Representative draw-doubling status: **{evaluation['precisionStatus']}**, {evaluation['draws']} draws. Independent conditional-location maximum gap **{v['maximumConditionalIntegrationGapPP']:.4f}pp**, separate .05pp gate {'passed' if v['conditionalIntegrationPassed'] else '**unmet**'}. Maximum energy pair-estimate difference {v['maximumEnergyPairDifferencePP']:.4f}pp. No tolerance relaxation.",
              '', 'Full per-candidate records, 50/80/90 intervals, group counts, proper interval and energy scores, margin/winner diagnostics and substantial misses are in evaluation.json. Winner frequencies are finite-bank diagnostics, not calibrated probabilities. Zero observed-winner frequency is not mathematically zero probability; no floor.',
              '', 'National draws are shared once. Composed cases use a fixed chain-balanced4096 cached national bank with repeated local scenarios, not additional independent national forecasts. No national inference, mean refit, transport variance, coefficient jitter, sources or retrospective overrides. Cross-layer independence, omitted scale/parameter uncertainty, uniform fragment flow, fine-party scenarios and national reconciliation remain limitations.',
              '', 'The analysis has only four reused candidate-election environments and three composed environments. Prior-driven2014 is explicit. Limited replication and remaining conditional quadrature error restrict fine claims and deployment; wider intervals or better coverage alone do not establish success.', '']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--audit-only',action='store_true');args=p.parse_args();verify()
    save('support-audit.json',support_audit(),args.check)
    if args.audit_only:return
    value=text();path=ROOT/'docs/stage46-uncertainty-findings.md'
    if args.check:
        if path.read_text()!=value:raise ValueError('Stale Stage46 deterministic report')
    else:path.write_text(value)


if __name__=='__main__':main()
