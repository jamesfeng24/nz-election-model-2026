"""Earlier-only scalar aggregate moments and pooled remainder effects."""
import numpy as np
from scipy.linalg import helmert
from .common import PREFIX, OLD, read, save, arguments, verify
from .coordinates import coordinates, partition


def labels(row):
    if row['layer'] == 'local_party':
        return row['ballotGroupKeys']
    return [feature['group'] or 'no_group' for feature in row['features']]


def environment(rows):
    moments = {}
    values = {name: [] for name in ('balance', 'mass')}
    remainder = []
    for row in rows:
        actual = coordinates(row['actual'], row['groups'])
        mean = coordinates(row['mean'], row['groups'])
        for name in values:
            if actual[name] is not None and mean[name] is not None:
                values[name].append(float(actual[name] - mean[name]))
        other = partition(row['groups'])[2]
        if actual['within'] is not None:
            remainder.append((actual['within'] - mean['within'], [labels(row)[i] for i in other]))
    for name, data in values.items():
        if not data:
            moments[name] = {'shared': None, 'seat': None, 'records': 0}
            continue
        x = np.array(data)
        center = float(x.mean())
        moments[name] = {'shared': center * center, 'seat': float(np.mean((x - center) ** 2)),
                         'records': len(x), 'descriptiveElectionEffect': center,
                         'units': 'raw log odds; one scalar degree of freedom'}
    unique = sorted({label for _, tags in remainder for label in tags})
    if len(unique) < 2:
        moments['within'] = {'shared': None, 'seat': None, 'records': len(remainder), 'rank': 0}
    else:
        h = helmert(len(unique), full=False).T
        matrices, response = [], []
        for e, tags in remainder:
            x = np.array([[float(t == u) for u in unique] for t in tags])
            x -= x.mean(axis=0)
            matrices.append(x @ h / np.sqrt(len(e) - 1))
            response.append(e / np.sqrt(len(e) - 1))
        x, y = np.concatenate(matrices), np.concatenate(response)
        singular = np.linalg.svd(x, compute_uv=False)
        full = singular[-1] > max(1e-12, singular[0] * 1e-10)
        effects = h @ np.linalg.solve(x.T @ x, x.T @ y) if full else np.zeros(len(unique))
        seat = []
        for e, tags in remainder:
            b = np.array([effects[unique.index(t)] for t in tags])
            left = e - (b - b.mean())
            seat.append(float(left @ left / (len(e) - 1)))
        moments['within'] = {'shared': float(effects @ effects / (len(unique) - 1)) if full else None,
                             'seat': float(np.mean(seat)), 'records': len(remainder),
                             'rank': int(np.sum(singular > max(1e-12, singular[0] * 1e-10))),
                             'columns': len(unique) - 1, 'classEffects': dict(zip(unique, effects.tolist())),
                             'units': 'projected exchangeable remainder log intensity; K_remainder-1 df'}
    return {'year': rows[0]['targetYear'], 'contests': len(rows), 'moments': moments}


def fit(rows, layer, target=None):
    eligible = [r for r in rows if target is None or r['targetYear'] < target]
    years = sorted({r['targetYear'] for r in eligible})
    moments = [environment([r for r in eligible if r['targetYear'] == year]) for year in years]
    spec = read(PREFIX + '/specification.json')
    pseudo = spec['priorPseudoEnvironments']
    scales, contributions = {}, {}
    for coordinate in ('balance', 'mass', 'within'):
        scales[coordinate], contributions[coordinate] = {}, {}
        for kind in ('shared', 'seat'):
            historical = [m['moments'][coordinate][kind] for m in moments if m['moments'][coordinate][kind] is not None]
            prior = spec['priors'][layer][coordinate][kind]
            variance = (sum(historical) + pseudo * prior ** 2) / (len(historical) + pseudo)
            scales[coordinate][kind] = float(np.sqrt(variance))
            contributions[coordinate][kind] = {'historicalVarianceContribution': sum(historical) / (len(historical) + pseudo),
                'priorVarianceContribution': pseudo * prior ** 2 / (len(historical) + pseudo),
                'environments': len(historical), 'priorSD': prior}
    return {'layer': layer, 'targetYear': target, 'trainingYears': years,
            'trainingIds': [r['targetElectorateId'] for r in eligible], 'moments': moments,
            'scales': scales, 'contributions': contributions,
            'status': 'assumed_prior_only' if not years else 'strongly_pooled_earlier_elections'}


def build():
    inventory = read(OLD + '/inventory.json')
    return {'stage': 45, 'folds': {layer: [fit(inventory[key], layer, year)
             for year in sorted({r['targetYear'] for r in inventory[key]})]
             for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords'))},
            'descriptive': {layer: fit(inventory[key], layer)
             for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords'))}}


def main():
    args = arguments(); verify(); save('scales.json', build(), args.check)
    print('Stage45 earlier-only aggregate/within scales reproduced')


if __name__ == '__main__':
    main()
