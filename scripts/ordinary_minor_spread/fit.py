"""Stage83 earlier-trained ordinary-seat multipliers on the candidate within and mass noise (closed form, penalty-free)."""
import numpy as np
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty_revision.coordinates import coordinates, partition
from scripts.uncertainty_revision.estimation import labels
from scripts.balance_shrink.evaluation import candidate_rows
from scripts.layer_audit.analysis import scalar_frame
from .common import YEARS, INVENTORY, SCALES, read, save, verify, arguments, design, is_flagged, check_flags_present


def within_residuals(row, scales):
    """(squared-ratio, standardised residuals) for one seat's non-major candidates; None when undefined."""
    n, l, other = partition(row['groups'])
    if len(other) < 2:
        return None
    observed = coordinates(np.asarray(row['actual']), row['groups'])['within']
    mean = coordinates(np.asarray(row['mean']), row['groups'])['within']
    if observed is None or mean is None:
        return None
    e = observed - mean
    tags = np.array([labels(row)[i] for i in other])
    k = len(other)
    sigma = scales['seat'] ** 2 * np.eye(k) + scales['shared'] ** 2 * (tags[:, None] == tags[None, :])
    centring = np.eye(k) - 1.0 / k
    covariance = centring @ sigma @ centring
    return float(e @ e / np.trace(covariance)), (e / np.sqrt(np.diag(covariance))).tolist()


def election_ratios(year, rows, mass):
    """{kind: {component: {'ratios', 'z', 'skipped'}}} for the ordinary seats of one election."""
    scales = scale_for(read(SCALES), 'candidate', year)['scales']
    out = {}
    for kind in ('primary', 'sensitivity'):
        ordinary = {r['targetElectorateId'] for r in rows if not is_flagged(r, kind)}
        within, z_within, skipped_w = [], [], 0
        for r in rows:
            if r['targetElectorateId'] in ordinary:
                value = within_residuals(r, scales['within'])
                if value is None:
                    skipped_w += 1
                else:
                    within.append(value[0])
                    z_within.extend(value[1])
        ids = mass[year]['ids']['mass']
        e = mass[year]['e']['mass']
        total = mass[year]['sd']['mass']['total']
        z_mass = [float(v / total) for i, v in zip(ids, e) if i in ordinary]
        out[kind] = {'within': {'ratios': within, 'z': z_within, 'skipped': skipped_w},
                     'mass': {'ratios': [v * v for v in z_mass], 'z': z_mass, 'skipped': len(ordinary) - len(z_mass)}}
    return out


def multiplier(per_election, years, robust=False):
    """m = min(1, sqrt(mean over the training elections of rho_y)); control when none.

    rho_y is the equal-seat mean squared ratio (moment) or (median |z| / 0.6745)^2 over the election's pooled
    standardised residuals (robust, amendment 1)."""
    if not years:
        return {'multiplier': 1.0, 'estimate': None, 'status': 'no earlier candidate residual: control'}
    if robust:
        r = {str(y): float((np.median(np.abs(per_election[y])) / 0.6744897501960817) ** 2) for y in years}
    else:
        r = {str(y): float(np.mean(per_election[y])) for y in years}
    estimate = float(np.sqrt(np.mean(list(r.values()))))
    return {'multiplier': float(min(1.0, estimate)), 'estimate': estimate, 'ratioByElection': r,
            'capped': bool(estimate > 1.0)}


def both(data, kind, years):
    return {c: {'moment': multiplier({y: data[y][kind][c]['ratios'] for y in years}, years),
                'robust': multiplier({y: data[y][kind][c]['z'] for y in years}, years, robust=True)} for c in ('within', 'mass')}


def build():
    spec = design()
    inventory = read(INVENTORY)['candidateRecords']
    rows = {y: candidate_rows(y) for y in YEARS}
    check_flags_present(rows)
    mass, _ = scalar_frame('candidate')
    data = {y: election_ratios(y, rows[y], mass) for y in YEARS}
    result = {'stage': 83, 'estimator': spec['fit']['estimator'], 'folds': {}}
    for year in YEARS:
        earlier = spec['folds'][str(year)]
        record = {'targetYear': year, 'trainingYears': earlier}
        for kind in ('primary', 'sensitivity'):
            record[kind] = both(data, kind, earlier)
            record[kind]['ordinarySeatsUsed'] = {str(y): {c: len(data[y][kind][c]['ratios']) for c in ('within', 'mass')} for y in earlier}
            record[kind]['skipped'] = {str(y): {c: data[y][kind][c]['skipped'] for c in ('within', 'mass')} for y in earlier}
        result['folds'][str(year)] = record
    descriptive = {'trainingYears': list(YEARS), 'scored': False}
    for kind in ('primary', 'sensitivity'):
        descriptive[kind] = both(data, kind, YEARS)
    result['descriptive2026Refit'] = descriptive
    result['recordsRead'] = len(inventory)
    return result


def main():
    args = arguments()
    verify()
    save('fit.json', build(), args.check, tolerance=1e-9)
    print('Stage83 fits ' + ('reproduced' if args.check else 'written'))


if __name__ == '__main__':
    main()
