"""CLR residual coordinates and outcome-free arithmetic mean adjustment."""
import numpy as np
from scipy.special import softmax

EPSILON = 1e-6


def validate(x):
    x = np.asarray(x, dtype=float)
    if x.ndim not in (1, 2) or x.shape[-1] < 2 or not np.isfinite(x).all() or (x < 0).any() or not np.allclose(x.sum(axis=-1), 1, rtol=0, atol=1e-12):
        raise ValueError('Invalid complete simplex')
    return x


def clr(x):
    x = validate(x)
    positive = (x + EPSILON)/(1 + x.shape[-1]*EPSILON)
    z = np.log(positive)
    return z-z.mean(axis=-1, keepdims=True)


def inverse(z):
    z = np.asarray(z, dtype=float)
    if not np.isfinite(z).all():
        raise ValueError('Nonfinite log coordinates')
    return softmax(z, axis=-1)


def residual(actual, prediction):
    return clr(actual)-clr(prediction)


def preserve_mean(base, noise, tolerance=1e-10, maximum=1000):
    """Calibrate one finite-bank marginal location; retain every zero face."""
    b = validate(base)
    eta = np.asarray(noise, dtype=float)
    if eta.ndim != 2 or not np.isfinite(eta).all() or eta.shape[-1] != b.shape[-1]:
        raise ValueError('Invalid residual noise bank')
    if b.ndim == 1:
        b = np.broadcast_to(b, eta.shape)
    if b.shape != eta.shape:
        raise ValueError('Draw/category dimensions differ')
    target = b.mean(axis=0)
    active = target > 0
    if np.any((b[:, active] == 0).all(axis=1)):
        raise ValueError('Empty positive draw face')
    logb = np.full(b.shape, -np.inf)
    np.log(b, out=logb, where=b>0)
    offset = np.zeros(len(target))
    for iteration in range(maximum):
        x = softmax(logb+offset+eta, axis=1)
        expectation = x.mean(axis=0)
        gap = float(np.max(np.abs(expectation-target)))
        if gap <= tolerance:
            validate(x)
            return x, {'locationOffset': offset.tolist(), 'iterations': iteration,
                'maximumMeanGapPP': 100*gap, 'targetArithmeticMean': target.tolist(),
                'zeroMeanLockedOptions': np.flatnonzero(~active).tolist(),
                'preservation': 'finite-bank marginal mean; per-national-draw conditional mean not guaranteed for varying inputs'}
        if np.any(expectation[active] <= 0):
            raise ValueError('Underflow in mean adjustment')
        offset[active] += np.log(target[active])-np.log(expectation[active])
        offset[active] -= offset[active].mean()
    raise ValueError('Mean-preservation iteration failure')
