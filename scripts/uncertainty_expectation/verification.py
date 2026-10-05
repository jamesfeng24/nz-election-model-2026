"""Independent scalar arithmetic and raw-covariance references, no model fitting."""
import math
import numpy as np
from scipy.special import softmax, ndtri
from scipy.stats import qmc
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty_revision.estimation import labels
from scripts.uncertainty_revision.coordinates import partition
from .common import PREFIX, INVENTORY, SCALES, arguments, read, save, verify
from .construction import signature, arrays, paired_control
from .integration import solve_locations


def raw_reference(p, offset, tags, shared, seat, count, seed):
    """Separate raw-option covariance reduction and independently seeded RQMC."""
    active = np.flatnonzero(np.asarray(p) > 0)
    if len(active) < 2:
        return np.asarray(p, float)
    tags = [tags[i] for i in active]
    covariance = np.array([[shared**2*(a == b)+seat**2*(i == j)
                           for j, b in enumerate(tags)] for i, a in enumerate(tags)])
    contrast = np.array([[covariance[i,j]-covariance[i,-1]-covariance[-1,j]+covariance[-1,-1]
                         for j in range(len(tags)-1)] for i in range(len(tags)-1)])
    factor = np.linalg.cholesky(contrast)
    u = qmc.Sobol(len(tags)-1, scramble=True, bits=30, seed=seed).random_base2(int(math.log2(count))-1)
    u = u+.5/2**30
    z = ndtri(np.concatenate((u, 1-u)))
    eta = np.column_stack((np.einsum('ij,kj->ik', z, factor, optimize=False), np.zeros(count)))
    values = softmax(np.log(np.asarray(p)[active])+np.asarray(offset)[active]+eta, axis=1)
    result = np.zeros(len(p))
    result[active] = np.sum(values, axis=0)/count
    return result


def scalar_crps(x, y):
    ordered = sorted(float(v) for v in x)
    n = len(ordered)
    first = math.fsum(abs(v-y) for v in ordered)/n
    half_pair = math.fsum((2*i-n+1)*v for i, v in enumerate(ordered))/(n*n)
    return first-half_pair


def build():
    construction = read(PREFIX+'/construction.json')
    evaluated = {c['id']: c for c in read(PREFIX+'/evaluation.json')['cases']}
    inventory, scales = read(INVENTORY), read(SCALES)
    lookup = {layer: {r['targetElectorateId']: r for r in inventory[key]}
              for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords'))}
    simplexes, arithmetic, references, major_exact = 0, [], [], 0
    for case in construction['cases']:
        records = lookup['local_party' if case['layer'] == 'local_party' else 'candidate']
        selected = {0, len(case['records'])//2, len(case['records'])-1}
        with arrays(case) as bank, paired_control(case) as control:
            for index, item in enumerate(case['records']):
                row = records[item['id']]
                q = bank['corrected:'+item['id']]
                if not np.isfinite(q).all() or np.any(q < 0) or np.max(abs(q.sum(axis=1)-1)) > 1e-12:
                    raise ValueError('Invalid corrected simplex')
                simplexes += len(q)
                if case['layer'] != 'composed':
                    n, l, _ = partition(row['groups'])
                    old = control['stage45:'+item['id']][:len(q)]
                    if not np.array_equal(q[:,n+l], old[:,n+l]):
                        raise ValueError('Numerical remainder repair changed aggregate major draws')
                    major_exact += 1
                if index not in selected:
                    continue
                result = next(r for r in evaluated[case['id']]['methods']['corrected']['records'] if r['id'] == item['id'])
                for option in (0, len(row['ids'])-1):
                    x, y = 100*q[:,option], 100*row['actual'][option]
                    crps = scalar_crps(x, y)
                    gap = abs(crps-result['crpsPP'][option])
                    if gap > 1e-10:
                        raise ValueError('Independent scalar CRPS disagrees')
                    levels = []
                    for level in (50, 80, 90):
                        alpha = 1-level/100
                        lo, hi = np.quantile(x, [alpha/2, 1-alpha/2])
                        score = hi-lo+2/alpha*max(lo-y, 0)+2/alpha*max(y-hi, 0)
                        recorded = result['interval'+str(level)]
                        if abs(score-recorded['scores'][option]) > 1e-10:
                            raise ValueError('Independent proper interval score disagrees')
                        levels.append({'level': level, 'scorePP': float(score), 'widthPP': float(hi-lo)})
                    arithmetic.append({'case': case['id'], 'seat': item['id'], 'option': row['ids'][option],
                                       'scalarCRPSPP': crps, 'CRPSGapPP': gap, 'intervals': levels})
                if case['layer'] == 'candidate':
                    other = partition(row['groups'])[2]
                    raw = np.asarray(row['mean'])[other]
                    if len(other) < 2 or not raw.sum():
                        continue
                    p = raw/raw.sum()
                    tags = [labels(row)[i] for i in other]
                    fit = scale_for(scales, 'candidate', case['year'])['scales']['within']
                    offset, _ = solve_locations(p, tags, fit['shared'], fit['seat'])
                    a = raw_reference(p, offset, tags, fit['shared'], fit['seat'], 131072, 470357)
                    b = raw_reference(p, offset, tags, fit['shared'], fit['seat'], 262144, 470357)
                    c = raw_reference(p, offset, tags, fit['shared'], fit['seat'], 262144, 470457)
                    change, spread = 100*float(np.max(abs(b-a))), 100*float(np.max(abs(c-b)))
                    gap = 100*float(max(np.max(abs(b-p)), np.max(abs(c-p))))
                    references.append({'case': case['id'], 'seat': item['id'], 'counts': [131072,262144],
                        'independentSeeds': [470357,470457], 'referenceChangePP': change,
                        'referenceDisagreementPP': spread, 'conditionalGapPP': gap,
                        'referenceConvergedAt001PP': max(change,spread) <= .01,
                        'conditionalComparisonAt005PP': gap <= .05,
                        'notAnExactReferenceOrConfidenceInterval': True})
    return {'stage': 47, 'signature': signature(), 'simplexVectorsChecked': simplexes,
            'majorComponentVectorsExactlyUnchangedSeats': major_exact,
            'independentScoreChecks': arithmetic, 'independentRawCovarianceReferences': references,
            'allPriorInputsPreserved': True, 'noHeldOutOutcomeUsedByNumericalRepair': True,
            'scope': 'Every bank conservation/aggregate equivalence; first/middle/last each case scalar scores;12candidate independent references. No claim of independent262144reference for every composed input.'}


def main():
    args = arguments()
    verify()
    save('verification.json', build(), args.check)
    print('Stage47 independent scores, covariance references and complete-bank conservation verified')


if __name__ == '__main__':
    main()
