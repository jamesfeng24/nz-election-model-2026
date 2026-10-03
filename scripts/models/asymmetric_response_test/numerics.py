"""Small deterministic OLS systems with independent numerical verification."""
from fractions import Fraction
from math import isfinite

import numpy as np
from scripts.checkpoints.complete_share_feature_rank import rank_details
from scripts.models.conditional_nat_lab_response.model import solve_normal_equations
from scripts.models.asymmetric_response.design import anchor_guard, regime_rank_guard

RESTRICTIONS = ('beta_one', 'constant', 'asymmetric')


def checked_ols(design, outcome):
    coefficients = solve_normal_equations(design, outcome)
    if coefficients is None:
        return {'status':'abstain','reason':'rational_solver_rank_failure'}
    x, y = np.asarray(design, dtype=float), np.asarray(outcome, dtype=float)
    independent = np.linalg.lstsq(x, y, rcond=None)[0]
    if not all(isfinite(v) for v in coefficients):
        return {'status':'abstain','reason':'nonfinite_solver'}
    difference = max(float(np.max(np.abs(independent-coefficients))),
                     float(np.max(np.abs(x@independent-x@coefficients))))
    if not isfinite(difference) or difference > 1e-8:
        return {'status':'abstain','reason':'independent_solver_disagreement'}
    return {'status':'available','coefficients':coefficients,
            'independentAgreementWithin1eMinus8':True}


def anchor_estimate(snapshots, omitted):
    rows = [r for r in snapshots if r['year'] != omitted]
    support = [Fraction(r['nationalSupport']) for r in rows]
    mean = sum(support)/len(support)
    design = [[Fraction(1), n-mean] for n in support]
    outcome = [Fraction(r['generalPremium']) for r in rows]
    details = rank_details(np.asarray(design,dtype=float), [0,1])
    fitted = checked_ols(design, outcome)
    result = {'omittedYear':omitted, 'retainedSnapshotIds':[r['id'] for r in rows],
              'nationalRange':[float(min(support)),float(max(support))],
              'meanNationalSupport':float(mean), 'rank':details['rank'],
              'scaledCondition':details['conditionRatio'], 'design':details,
              'numericalStatus':fitted['status']}
    if fitted['status'] != 'available':
        return {**result,'reason':fitted['reason'],'slope':None,'anchor':None}
    intercept, slope = fitted['coefficients']
    root = float(mean)-intercept/slope if abs(slope)>1e-12 else None
    return {**result,'interceptAtMean':intercept,'slope':slope,'anchor':root,
            'extrapolated':root is None or not float(min(support))<=root<=float(max(support)),
            'independentAgreementWithin1eMinus8':True}


def estimate_anchor(snapshots):
    """All snapshot deletion fits are reported even when the final guard fails."""
    if len(snapshots)<4:
        return {'status':'abstain','reason':'fewer_than_four_completed_elections',
                'snapshotIds':[r['id'] for r in snapshots],'estimates':[]}
    estimates = [anchor_estimate(snapshots, y) for y in [None]+[r['year'] for r in snapshots]]
    result = {'snapshotIds':[r['id'] for r in snapshots], 'estimates':estimates}
    if any(r['numericalStatus']!='available' or r['anchor'] is None or r['scaledCondition'] is None
           for r in estimates):
        return {**result,'status':'abstain','reason':'weak_or_nonfinite_anchor_design_or_zero_slope'}
    return {**result, **anchor_guard(snapshots, estimates)}


def response_design(rows, restriction):
    if restriction=='beta_one':
        return [[1.0] for r in rows], [r['y']-r['x'] for r in rows]
    if restriction=='constant':
        return [[1.0,r['x']] for r in rows], [r['y'] for r in rows]
    if restriction=='asymmetric':
        return [[1.0,r['x'],r['x']*r['T']] for r in rows], [r['y'] for r in rows]
    raise ValueError('Unregistered restriction')


def fit_restrictions(rows):
    gate = regime_rank_guard(rows)
    if gate['status']!='available':
        return {'status':'abstain','reason':gate['reason'],'regimeRankGate':gate,'fits':{}}
    return {**solve_restrictions(rows), 'regimeRankGate':gate}


def solve_restrictions(rows):
    """Solve registered restrictions; callers apply their explicitly labelled gates."""
    fits = {}
    for name in RESTRICTIONS:
        design, outcome = response_design(rows, name)
        fit = checked_ols(design, outcome)
        if fit['status']!='available':
            return {'status':'abstain','reason':fit['reason'],'failedRestriction':name,'fits':{}}
        values = fit['coefficients']
        beta = 1.0 if name=='beta_one' else values[1]
        delta = values[2] if name=='asymmetric' else 0.0
        fits[name] = {'alpha':values[0],'betaAway':beta,'delta':delta,'betaToward':beta+delta,
                      'hypothesizedOrdering':bool(0<beta<1<beta+delta),
                      'independentAgreementWithin1eMinus8':True}
    return {'status':'available','fits':fits}


def prediction(row, fit):
    return row['c0']+fit['alpha']+fit['betaAway']*row['x']+fit['delta']*row['x']*row['T']
