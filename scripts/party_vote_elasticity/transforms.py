"""Stage81 transforms: previous local party vote and national change -> closed local party vector.

Pure numpy, no fitted parameter, no randomness. `x = (p^theta + P1^theta - P0^theta)_+^(1/theta)` is the one power
family: theta = 1 is same points (A), theta -> 0 is proportional (P) and theta = 0.5 is H; L is the odds-scale shift.
A category with p = 0 keeps zero in every arm, clipping is at zero only, and the result is closed to sum one.
"""
import numpy as np

ARMS = ('P', 'A', 'L', 'H')
THETA = {'A': 1.0, 'H': 0.5}


def unclosed(arm, p, p0, p1):
    """Unclosed value for each category. `p` and `p1` may be (K,) or (n, K); `p0` is (K,)."""
    p, p0, p1 = (np.asarray(v, dtype=float) for v in (p, p0, p1))
    if not (np.isfinite(p).all() and np.isfinite(p0).all() and np.isfinite(p1).all()):
        raise ValueError('Non-finite transform input')
    if (p < 0).any() or (p > 1).any() or (p0 < 0).any() or (p0 >= 1).any() or (p1 < 0).any() or (p1 > 1).any():
        raise ValueError('Share outside the unit interval')
    if ((p0 == 0) & (p > 0)).any():
        raise ValueError('Local share without national share')
    if arm == 'P':
        x = np.divide(p * p1, p0, out=np.zeros(np.broadcast(p, p1).shape), where=p0 > 0)
    elif arm == 'L':
        with np.errstate(divide='ignore', invalid='ignore'):
            odds = np.where(p0 > 0, p1 * (1 - p0) / (p0 * (1 - p1)), 0.0)
            x = np.where(p1 >= 1, 1.0, p * odds / (1 - p + p * odds))
        x = np.where(p > 0, x, 0.0)
    elif arm in THETA or isinstance(arm, float):
        theta = THETA[arm] if arm in THETA else float(arm)
        if not 0 < theta <= 1:
            raise ValueError('theta must be in (0, 1]; theta -> 0 is arm P')
        base = p ** theta + p1 ** theta - p0 ** theta
        x = np.maximum(base, 0.0) ** (1 / theta)
    else:
        raise ValueError(f'Unknown arm {arm!r}')
    return np.where(p > 0, x, 0.0)


def swing(arm, p, p0, p1):
    """Closed local party vectors, shape (n, K), for one arm."""
    x = np.atleast_2d(unclosed(arm, p, p0, p1))
    total = x.sum(axis=1)
    if not np.isfinite(total).all() or np.any(total <= 0):
        raise ValueError('No supported local party mass')
    return x / total[:, None]


def swing_mixture(arms, assignment, p, p0, p1):
    """Rows use the arm named in `assignment` (length n, one arm per national draw); p1 must be (n, K)."""
    p1 = np.atleast_2d(np.asarray(p1, dtype=float))
    assignment = np.asarray(assignment)
    if len(assignment) != len(p1) or not set(assignment.tolist()) <= set(arms):
        raise ValueError('Assignment does not match the rows or the arms')
    out = np.empty(p1.shape)
    for arm in arms:
        rows = assignment == arm
        if rows.any():
            out[rows] = swing(arm, p, p0, p1[rows])
    return out
