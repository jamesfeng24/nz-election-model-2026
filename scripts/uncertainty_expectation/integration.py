"""Convergence-controlled Gaussian conditional locations on active simplex faces."""
from functools import lru_cache
import numpy as np
from scipy.linalg import helmert
from scipy.special import roots_hermitenorm, softmax, logsumexp
from scipy.stats import norm, qmc

SOLVER_TOLERANCE = .002 / 100
REFERENCE_TOLERANCE = .01 / 100
AGREEMENT_TOLERANCE = .02 / 100
COMPARISON_TOLERANCE = .05 / 100
QMC_COUNTS = (512, 2048, 8192, 32768, 131072)
GH_ORDERS = (15, 25, 41, 61)


def contrast_covariance(tags, shared, seat):
    """Covariance of raw option effects relative to the final option."""
    k = len(tags)
    if not np.isfinite([shared, seat]).all() or min(shared, seat) < 0:
        raise ValueError('Invalid Gaussian scales')
    raw = shared**2 * np.equal.outer(tags, tags) + seat**2 * np.eye(k)
    difference = np.column_stack((np.eye(k-1), -np.ones(k-1)))
    return np.einsum('ij,jk,lk->il', difference, raw, difference, optimize=False)


@lru_cache(maxsize=128)
def factor(tags, shared, seat):
    k = len(tags)
    if k < 2:
        return np.zeros((k, 0))
    contrast = contrast_covariance(tags, shared, seat)
    values, vectors = np.linalg.eigh(contrast)
    if np.min(values) < -1e-12:
        raise ValueError('Nonpositive Gaussian covariance')
    active = values > 1e-14
    result = np.zeros((k, int(active.sum())))
    result[:-1] = vectors[:, active] * np.sqrt(values[active])
    return result


@lru_cache(maxsize=128)
def rule(tags, shared, seat, size, seed=470047, tensor=False):
    f = factor(tuple(tags), shared, seat)
    dimension = f.shape[1]
    if not dimension:
        return np.zeros((1, len(tags))), np.ones(1)
    if tensor or dimension == 1:
        x, w = roots_hermitenorm(size)
        w = w / np.sqrt(2*np.pi)
        points = np.stack(np.meshgrid(*([x]*dimension), indexing='ij'), axis=-1).reshape(-1, dimension)
        weights = np.prod(np.stack(np.meshgrid(*([w]*dimension), indexing='ij'), axis=-1), axis=-1).ravel()
    else:
        if size < 2 or size & (size-1):
            raise ValueError('QMC size must be power of two')
        u = qmc.Sobol(dimension, scramble=True, bits=30, seed=seed+dimension).random_base2(int(np.log2(size))-1)
        u = u + .5/2**30
        points = norm.ppf(np.concatenate((u, 1-u)))
        weights = np.full(size, 1/size)
    return np.einsum('ij,kj->ik', points, f, optimize=False), weights


def expectation(p, offset, nodes, weights, jacobian=False, block=16):
    """Evaluate Gaussian softmax means; weighted derivatives use the same law."""
    p = np.asarray(p, float)
    one = p.ndim == 1
    if one:
        p = p[None, :]
    offset = np.broadcast_to(offset, p.shape)
    logs = np.log(p)
    result = np.empty_like(p)
    jac = np.empty((len(p), p.shape[1]-1, p.shape[1]-1)) if jacobian else None
    for start in range(0, len(p), block):
        end = min(start+block, len(p))
        q = softmax(logs[start:end, None, :] + offset[start:end, None, :] + nodes[None, :, :], axis=-1)
        e = np.einsum('bni,n->bi', q, weights, optimize=False)
        result[start:end] = e
        if jacobian:
            reduced = q[:, :, :-1]
            second = np.einsum('bni,bnj,n->bij', reduced, reduced, weights, optimize=False)
            diagonal = np.zeros_like(second)
            index = np.arange(p.shape[1]-1)
            diagonal[:, index, index] = e[:, :-1]
            jac[start:end] = diagonal-second
    if one:
        return (result[0], jac[0]) if jacobian else result[0]
    return (result, jac) if jacobian else result


def solve_rule(p, nodes, weights, initial=None):
    """Unique active-face location, fixing the final option's additive gauge."""
    p = np.asarray(p, float)
    one = p.ndim == 1
    if one:
        p = p[None, :]
    offset = np.zeros_like(p) if initial is None else np.array(initial, copy=True).reshape(p.shape)
    offset -= offset[:, -1, None]
    iterations = 0
    for iterations in range(40):
        mean, jac = expectation(p, offset, nodes, weights, True)
        gap = np.max(np.abs(mean-p), axis=1)
        active = gap > SOLVER_TOLERANCE
        if not np.any(active):
            break
        desired = p[active]
        gradient = (mean-p)[active, :-1]
        scale = np.sqrt(desired[:, :-1])
        normalized = jac[active] / scale[:, :, None] / scale[:, None, :]
        try:
            step = np.linalg.solve(normalized, (gradient/scale)[..., None])[..., 0] / scale
        except np.linalg.LinAlgError as error:
            raise ValueError('Numerically unidentified active-face location') from error
        step = np.clip(step, -10, 10)
        old = offset[active].copy()
        chosen = old.copy()
        accepted = np.zeros(len(old), bool)
        for power in range(12):
            proposal = old.copy()
            proposal[:, :-1] -= step / 2**power
            expected = expectation(desired, proposal, nodes, weights)
            better = np.max(np.abs(expected-desired), axis=1) < gap[active]
            take = better & ~accepted
            chosen[take] = proposal[take]
            accepted |= better
            if np.all(accepted):
                break
        if not np.all(accepted):
            raise ValueError('Gaussian location Newton step did not improve')
        offset[active] = chosen
    else:
        raise ValueError('Gaussian conditional location iteration cap')
    return (offset[0] if one else offset), iterations+1


def solve_locations(base, tags, shared, seat, tensor=False):
    """Solve and independently assess every supplied vector; zeros remain locked."""
    b = np.asarray(base, float)
    one = b.ndim == 1
    if one:
        b = b[None, :]
    if b.shape[1] != len(tags) or np.any(b < 0) or not np.isfinite(b).all() or not np.allclose(b.sum(axis=1), 1, atol=1e-12, rtol=0):
        raise ValueError('Invalid conditional simplex')
    output = np.zeros_like(b)
    audits = []
    faces, inverse = np.unique(b > 0, axis=0, return_inverse=True)
    for face_index, face in enumerate(faces):
        rows = np.flatnonzero(inverse == face_index)
        columns = np.flatnonzero(face)
        p = b[np.ix_(rows, columns)]
        if len(columns) < 2:
            audits.extend({'index':int(i), 'passed':True, 'size':1, 'solverGapPP':0., 'referenceChangePP':0., 'referenceDisagreementPP':0., 'conditionalGapPP':0.} for i in rows)
            continue
        active_tags = tuple(tags[i] for i in columns)
        dimension = factor(active_tags, shared, seat).shape[1]
        use_tensor = tensor and dimension <= 3
        schedule = (41, 81, 161) if dimension == 1 else GH_ORDERS if use_tensor else QMC_COUNTS
        pending = np.arange(len(p))
        offsets = np.zeros_like(p)
        for level, size in enumerate(schedule):
            nodes, weights = rule(active_tags, shared, seat, size, tensor=use_tensor)
            found, iterations = solve_rule(p[pending], nodes, weights, offsets[pending])
            offsets[pending] = found
            if dimension == 1:
                ref_size = min(size*2-1, 321)
                first, fw = rule(active_tags, shared, seat, size, tensor=True)
                second, sw = rule(active_tags, shared, seat, ref_size, tensor=True)
                third, tw = rule(active_tags, shared, seat, min(ref_size+40, 361), tensor=True)
            elif use_tensor:
                ref_size = min(81, schedule[min(level+1, len(schedule)-1)])
                first, fw = nodes, weights
                second, sw = rule(active_tags, shared, seat, ref_size, tensor=True)
                third, tw = rule(active_tags, shared, seat, 81, tensor=True)
            else:
                ref_size = min(size*2, 262144)
                first, fw = rule(active_tags, shared, seat, size, 470147)
                second, sw = rule(active_tags, shared, seat, ref_size, 470147)
                third, tw = rule(active_tags, shared, seat, ref_size, 470247)
            a = expectation(p[pending], found, first, fw)
            c = expectation(p[pending], found, second, sw)
            d = expectation(p[pending], found, third, tw)
            reference_change = np.max(np.abs(c-a), axis=1)
            disagreement = np.max(np.abs(c-d), axis=1)
            gap = np.maximum(np.max(np.abs(c-p[pending]), axis=1), np.max(np.abs(d-p[pending]), axis=1))
            solver = np.max(np.abs(expectation(p[pending], found, nodes, weights)-p[pending]), axis=1)
            passed = (reference_change <= REFERENCE_TOLERANCE) & (disagreement <= REFERENCE_TOLERANCE) & (gap <= AGREEMENT_TOLERANCE)
            finish = passed | (level == len(schedule)-1)
            for j in np.flatnonzero(finish):
                audits.append({'index':int(rows[pending[j]]), 'passed':bool(passed[j]), 'size':size, 'method':'tensor_GH' if use_tensor or dimension==1 else 'antithetic_RQMC',
                               'dimension':dimension,'iterations':iterations,'referenceSize':ref_size, 'solverGapPP':float(100*solver[j]),
                               'referenceChangePP':float(100*reference_change[j]),'referenceDisagreementPP':float(100*disagreement[j]),'conditionalGapPP':float(100*gap[j])})
            pending = pending[~finish]
            if not len(pending):
                break
        output[np.ix_(rows, columns)] = offsets
    audits.sort(key=lambda a:a['index'])
    return (output[0] if one else output), audits
