"""One-at-a-time common-stream width diagnostics and valid total variance."""
from copy import deepcopy
import numpy as np
from scipy.special import expit, roots_hermitenorm
from scripts.uncertainty.construction import scale_for, national_case
from scripts.uncertainty_revision.coordinates import partition, mean_logit_location
from scripts.uncertainty_tails.metrics import record
from .common import INVENTORY, SCALES, PREFIX, read, save, verify, arguments
from .construction import signature, arrays, national_inputs
from .simulation import composed, upstream
from .audits import width_summary


def policy_scales(policy, party, candidate):
    """Change only one declared shock block; inverse locations follow covariance."""
    p, c = deepcopy(party), deepcopy(candidate)
    for prefix, layer in (('local', p), ('candidate', c)):
        for kind in ('shared', 'seat'):
            if policy == f'no_{prefix}_{kind}':
                for coordinate in layer:
                    layer[coordinate][kind] = 0.
    for coordinate in ('balance', 'mass', 'within'):
        if policy == 'no_candidate_'+coordinate:
            c[coordinate] = {'shared': 0., 'seat': 0.}
    known = read(PREFIX+'/companion-contract.json')['attribution']['policies']
    if policy not in known:
        raise ValueError('Undeclared width attribution policy')
    return p, c


def vector_moments(p, sd):
    p = np.asarray(p, float)
    location = mean_logit_location(p, sd)
    nodes, weights = roots_hermitenorm(81)
    q = expit(location[:, None]+sd*nodes)
    q = np.where(p[:, None] == 0, 0., np.where(p[:, None] == 1, 1., q))
    weights /= np.sqrt(2*np.pi)
    mean = np.einsum('ij,j->i', q, weights, optimize=False)
    second = np.einsum('ij,j->i', q*q, weights, optimize=False)
    return mean, np.maximum(0., second-mean*mean)


def total_variance(conditional, groups, scales, draws):
    n, l, other = partition(groups)
    if not n or not l:
        return {'status': 'unavailable', 'reason': 'unique National/Labour pair absent'}
    mass = conditional[:, n[0]]+conditional[:, l[0]]
    ratio = np.divide(conditional[:, n[0]], mass, out=np.zeros(len(mass)), where=mass > 0)
    m, vm = vector_moments(mass, np.hypot(*scales['mass'].values()) if other else 0.)
    r, vr = vector_moments(ratio, np.hypot(*scales['balance'].values()))
    results = {}
    for label, ix, a in (('national', n[0], r), ('labour', l[0], 1-r)):
        conditional_mean = m*a
        conditional_variance = m*m*vr+a*a*vm+vm*vr
        ordinary = float(conditional_variance.mean())
        upstream_variance = float(np.var(conditional_mean))
        results[label] = {'expectedConditionalCandidateVariancePP2': 10000*ordinary,
            'upstreamConditionalMeanVariancePP2': 10000*upstream_variance,
            'totalVariancePP2': 10000*(ordinary+upstream_variance),
            'finiteSimulationVariancePP2': 10000*float(np.var(draws[:, ix])),
            'conditionalArithmeticMeanErrorPP': float(100*np.max(abs(conditional_mean-conditional[:, ix])))}
    return {'status': 'finite-upstream law of total variance', 'groups': results,
            'conditioning': 'cached national scenario AND generated local vector; independent candidate shocks integrated analytically',
            'limitation': 'Finite512 upstream bank, not an independent national/local variance decomposition. Quantile widths are not additive.'}


def build():
    construction = read(PREFIX+'/construction.json')
    if construction['signature'] != signature():
        raise ValueError('Changed numerical producer')
    inventory, scales = read(INVENTORY), read(SCALES)
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    candidates = {r['targetElectorateId']: r for r in inventory['candidateRecords']}
    spec = read(PREFIX+'/companion-contract.json')
    count = spec['composedDraws']
    results = []
    for case in construction['cases']:
        if case['layer'] != 'composed':
            continue
        selected = [case['records'][i] for i in sorted({0, len(case['records'])//2, len(case['records'])-1})]
        year = case['year']
        ps = scale_for(scales, 'local_party', year)['scales']
        cs = scale_for(scales, 'candidate', year)['scales']
        with arrays(case) as bank:
            for item in selected:
                row, party = candidates[item['id']], parties[item['id']]
                national, ids = national_inputs(year, party, count)
                base, _, _ = national_case(year, party['ids'], 4096)
                policies = {}
                point = np.asarray(item['metadata']['deterministicNationalOnlyMean'])
                for policy in spec['attribution']['policies']:
                    pfit, cfit = policy_scales(policy, ps, cs)
                    if policy == 'full':
                        q, meta = bank['corrected:'+item['id']], item['metadata']
                    else:
                        inputs = np.broadcast_to(base.mean(axis=0), national.shape) if policy == 'national_at_mean' else national
                        q, meta = composed(party, row, inputs, pfit, cfit)
                    scored = record(row, q, point)
                    policies[policy] = {'record': scored, 'metadata': meta,
                        'widths': {g: width_summary([scored], g) for g in ('national', 'labour', 'other', 'forecast_pair')}}
                _, conditional, _, _ = upstream(party, row, national, ps)
                variance = total_variance(conditional, row['groups'], cs, bank['corrected:'+item['id']])
                results.append({'id': item['id'], 'name': row['name'], 'year': year,
                    'policies': policies, 'totalVariance': variance, 'drawIdentity': ids,
                    'nationalAtMeanUses4096Mean': True})
                print('Attributed Stage47', year, row['name'], flush=True)
    return {'stage': 47, 'signature': signature(), 'draws': count, 'records': results,
            'fullFrameAnalyticMajorVariance': PREFIX+'/prior-audit.json',
            'sharedEffectsRetainedInFull': True, 'widthChangesAreNotVarianceShares': True,
            'scope': 'nine prespecified representative composed seats; no claim of full-frame ablation coverage',
            'nationalAtMeanCaveat': '4096-bank mean vs selected512 scenarios; sampling difference remains, no national refit',
            'newVarianceOrMeanFit': False}


def main():
    args = arguments()
    verify()
    save('attribution.json', build(), args.check)


if __name__ == '__main__':
    main()
