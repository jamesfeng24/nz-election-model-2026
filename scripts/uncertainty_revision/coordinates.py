"""Arithmetic aggregate balances, unaffected by remainder coordinate count."""
import numpy as np
from scipy.special import expit, logit, softmax
from scipy.special import roots_hermitenorm
from scripts.uncertainty.transforms import validate, EPSILON


def partition(groups):
    national = [i for i, g in enumerate(groups) if g == 'national']
    labour = [i for i, g in enumerate(groups) if g == 'labour']
    if len(national) > 1 or len(labour) > 1:
        raise ValueError('Duplicate major destination')
    major = national + labour
    return national, labour, [i for i in range(len(groups)) if i not in major]


def coordinates(x, groups, replace=True):
    x = validate(x)
    if replace:
        x = (x + EPSILON) / (1 + x.shape[-1] * EPSILON)
    n, l, other = partition(groups)
    major = n + l
    result = {'balance': None, 'mass': None, 'within': None}
    if n and l and np.all(x[..., major] > 0):
        result['balance'] = np.log(x[..., n[0]]) - np.log(x[..., l[0]])
    if major and other:
        a, b = x[..., major].sum(axis=-1), x[..., other].sum(axis=-1)
        if np.all(a > 0) and np.all(b > 0):
            result['mass'] = np.log(a) - np.log(b)
    if len(other) > 1 and np.all(x[..., other] > 0):
        z = np.log(x[..., other])
        result['within'] = z - z.mean(axis=-1, keepdims=True)
    return result


def mean_logit_location(probability, sd, order=41, tolerance=1e-12):
    """Outcome-free Gauss-Hermite location with conditional arithmetic mean."""
    p = np.asarray(probability, dtype=float)
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)) or not np.isfinite(sd) or sd < 0:
        raise ValueError('Invalid conditional probability/scale')
    active = (p > 0) & (p < 1)
    location = np.zeros_like(p)
    if not np.any(active):
        return location
    nodes, weights = roots_hermitenorm(order)
    weights = weights / np.sqrt(2 * np.pi)
    target = p[active]
    center = logit(target)
    low, high = center - 2 * sd * sd - 20, center + 2 * sd * sd + 20
    for _ in range(100):
        midpoint = (low + high) / 2
        expected = np.sum(expit(midpoint[:, None] + sd * nodes) * weights, axis=1)
        low = np.where(expected < target, midpoint, low)
        high = np.where(expected >= target, midpoint, high)
        if np.max(high - low) < tolerance:
            break
    location[active] = (low + high) / 2
    return location


def binary_draw(probability, eta, sd):
    p = np.asarray(probability, dtype=float)
    location = mean_logit_location(p, sd)
    q = expit(location + eta)
    return np.where(p == 0, 0., np.where(p == 1, 1., q))


def within_adjust(base, weight, eta, target, tolerance=1e-10):
    """Remainder marginal adjustment; top-level responses stay untouched."""
    positive = np.any(base > 0, axis=0)
    logbase = np.full(base.shape, -np.inf)
    np.log(base, out=logbase, where=base > 0)
    offset = np.zeros(base.shape[1])
    goal = np.asarray(target) * np.mean(weight)
    for iteration in range(1000):
        q = softmax(logbase + eta + offset, axis=-1)
        expected = np.mean(weight[:, None] * q, axis=0)
        gap = float(np.max(np.abs(expected - goal)))
        if gap <= tolerance:
            return q, {'locationOffset': offset.tolist(), 'iterations': iteration,
                       'maximumMarginalGapPP': 100 * gap,
                       'scope': 'remainder marginal only; per-input remainder allocation not preserved'}
        if np.any(expected[positive] <= 0):
            raise ValueError('Within-remainder underflow')
        offset[positive] += np.log(goal[positive]) - np.log(expected[positive])
        offset[positive] -= offset[positive].mean()
    raise ValueError('Within-remainder adjustment failed')


def inverse(base, groups, noise, scales):
    """Independent aggregate balances plus all remainder options; zero lock."""
    b = validate(base)
    draws = len(noise['balance'])
    if b.ndim == 1:
        b = np.broadcast_to(b, (draws, len(b)))
    if len(b) != draws:
        raise ValueError('Draw dimensions differ')
    n, l, other = partition(groups)
    major = n + l
    q = np.zeros_like(b)
    mass = b[:, major].sum(axis=1) if major else np.zeros(draws)
    if major and other:
        mass = binary_draw(mass, noise['mass'], scales['mass'])
    elif major:
        mass = np.ones(draws)
    if n and l:
        original_mass = b[:, major].sum(axis=1)
        ratio = np.divide(b[:, n[0]], original_mass, out=np.zeros(draws), where=original_mass > 0)
        ratio = binary_draw(ratio, noise['balance'], scales['balance'])
        q[:, n[0]], q[:, l[0]] = mass * ratio, mass * (1 - ratio)
    elif major:
        q[:, major[0]] = mass
    location = None
    if other:
        original = b[:, other]
        original_mass = original.sum(axis=1)
        within = np.divide(original, original_mass[:, None], out=np.zeros_like(original), where=original_mass[:, None] > 0)
        # Empty remainder faces must stay empty; a dummy ratio is never assigned positive mass.
        empty = original_mass == 0
        within[empty, 0] = 1
        target = original.mean(axis=0)
        target = target / target.sum() if target.sum() else np.eye(1, len(other), 0)[0]
        conditional, location = within_adjust(within, 1 - mass, noise['within'], target)
        q[:, other] = (1 - mass)[:, None] * conditional
    validate(q)
    return q, {'withinLocation': location,
               'topLocation': 'conditional Gauss-Hermite41 arithmetic expectation',
               'zeroFacePreserved': bool(np.all(q[:, np.all(b == 0, axis=0)] == 0))}
