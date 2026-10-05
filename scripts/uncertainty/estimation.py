"""Earlier-only equal-environment pooled shared/seat moments, not mean fitting."""
import numpy as np
from scipy.linalg import helmert
from .common import *
from .transforms import residual


def classes(layer):
    return read(PREFIX + '/specification.json')['sharedClasses'][layer]


def design(groups, labels):
    h = np.array([[float(g == label) for label in labels] for g in groups])
    return h-h.mean(axis=0, keepdims=True)


def environment(rows, layer):
    labels = classes(layer)
    contrast = helmert(len(labels), full=False).T
    matrices, values = [], []
    for row in rows:
        k = len(row['ids'])
        x = design(row['groups'], labels)@contrast
        e = residual(row['actual'], row['mean'])
        matrices.append(x/np.sqrt(k))
        values.append(e/np.sqrt(k))
    x, y = np.concatenate(matrices), np.concatenate(values)
    singular = np.linalg.svd(x, compute_uv=False)
    full_rank = singular[-1] > 1e-10*singular[0] and singular[-1] > 1e-12
    if full_rank:
        beta = np.linalg.solve(x.T@x, x.T@y)
        effects = contrast@beta
        shared = float(effects@effects/(len(labels)-1))
    else:
        effects = np.zeros(len(labels))
        shared = None
    seat = []
    for row in rows:
        e = residual(row['actual'], row['mean'])
        leftover = e-design(row['groups'], labels)@effects
        seat.append(float(leftover@leftover/(len(e)-1)))
    return {'targetYear': rows[0]['targetYear'], 'contests': len(rows),
        'sharedRank': int(np.sum(singular > max(1e-12, singular[0]*1e-10))),
        'sharedColumns': len(labels)-1, 'sharedIdentifiable': bool(full_rank),
        'classEffects': dict(zip(labels, effects.tolist())), 'sharedSecondMoment': shared,
        'seatSecondMoment': float(np.mean(seat)), 'sharedSingularValues': singular.tolist()}


def fit(rows, layer, target_year=None):
    eligible = [r for r in rows if target_year is None or r['targetYear'] < target_year]
    years = sorted({r['targetYear'] for r in eligible})
    moments = [environment([r for r in eligible if r['targetYear'] == y], layer) for y in years]
    spec = read(PREFIX + '/specification.json')
    prior, weight = spec['priorScales'][layer], spec['priorPseudoEnvironments']
    scales = {}
    for name, key in (('shared', 'sharedSecondMoment'), ('seat', 'seatSecondMoment')):
        values = [m[key] for m in moments if m[key] is not None]
        scales[name] = float(np.sqrt((sum(values)+weight*prior[name]**2)/(len(values)+weight)))
    return {'layer': layer, 'targetYear': target_year, 'trainingYears': years,
        'trainingIds': [r['targetElectorateId'] for r in eligible], 'environments': len(years),
        'status': 'assumed_prior_no_earlier_residuals' if not years else 'strongly_pooled_earlier_moments',
        'scales': scales, 'moments': moments, 'priorPseudoEnvironments': weight,
        'covarianceFamily': 'projected shared coarse-class plus isotropic seat log-ratio effects',
        'parameterDrawUncertainty': 'omitted; fixed fits preserved'}


def association(inventory):
    party = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    result = []
    for name in ('national', 'labour'):
        records = []
        for c in inventory['candidateRecords']:
            p = party[c['targetElectorateId']]
            if name not in c['groups'] or name not in p['groups']:
                continue
            i, j = p['groups'].index(name), c['groups'].index(name)
            records.append({'year': c['targetYear'], 'seat': c['targetElectorateId'],
                'party': float(residual(p['actual'],p['mean'])[i]),
                'candidate': float(residual(c['actual'],c['mean'])[j])})
        x = np.array([r['party'] for r in records]);y = np.array([r['candidate'] for r in records])
        centered_x, centered_y = x.copy(), y.copy()
        for year in sorted({r['year'] for r in records}):
            mask = np.array([r['year'] == year for r in records])
            centered_x[mask] -= x[mask].mean();centered_y[mask] -= y[mask].mean()
        def corr(a,b):
            return None if np.std(a)==0 or np.std(b)==0 else float(np.corrcoef(a,b)[0,1])
        result.append({'group': name, 'pairs': len(records), 'environments': len({r['year'] for r in records}),
            'pearson': corr(x,y), 'withinElectionCenteredPearson': corr(centered_x,centered_y),
            'interpretation': 'descriptive association; independent-layer approximation not established'})
    return result


def build(inventory=None):
    inv = read(PREFIX+'/inventory.json') if inventory is None else inventory
    return {'stage':44,'folds':{layer:[fit(inv[key],layer,y) for y in YEARS if any(r['targetYear']==y for r in inv[key])]
        for layer,key in (('local_party','partyRecords'),('candidate','candidateRecords'))},
        'descriptive': {layer:fit(inv[key],layer) for layer,key in (('local_party','partyRecords'),('candidate','candidateRecords'))},
        'crossLayerAssociation': association(inv), 'operationalSelection':None}


def main():
    args=arguments();verify();value=build();save('scales.json',value,args.check)
    print('Earlier-only scales frozen; no candidate mean fitting',value['crossLayerAssociation'])


if __name__=='__main__':main()
