"""A faster, numerically equivalent Stage47 Gaussian-softmax expectation for the live assembly.

The frozen `scripts.uncertainty_expectation.integration.expectation` evaluates E[softmax(log p + offset + node)] and
its Jacobian with unoptimised `einsum` and SciPy's softmax. This version computes the same quantities with BLAS
matrix products and an in-place softmax; only floating-point summation order differs (agreement to about 1e-13,
tested). It is substituted for the frozen function only inside `accelerated()`, the same module-level substitution
pattern Stage63 used for the noise stream, so the frozen solver, its schedules, tolerances and audits run unchanged.
"""
import contextlib
import numpy as np
from scripts.uncertainty_expectation import integration

BLOCK = 8


def expectation(p, offset, nodes, weights, jacobian=False, block=BLOCK):
    p = np.asarray(p, float)
    one = p.ndim == 1
    if one:
        p = p[None, :]
    offset = np.broadcast_to(offset, p.shape)
    logs = np.log(p)
    k = p.shape[1]
    result = np.empty_like(p)
    jac = np.empty((len(p), k - 1, k - 1)) if jacobian else None
    w = np.asarray(weights, float)
    ones = np.ones(k)
    # Softmax is invariant to the stabilising shift; an upper bound of each row (row max of log p + offset plus
    # node max) avoids overflow like the exact max, without a slow reduction over the short last axis.
    node_max = nodes.max(axis=1)
    for start in range(0, len(p), block):
        end = min(start + block, len(p))
        base = logs[start:end] + offset[start:end]
        z = base[:, None, :] + nodes[None, :, :]
        z -= (base.max(axis=1)[:, None] + node_max[None, :])[:, :, None]
        np.exp(z, out=z)
        z /= np.matmul(z, ones)[:, :, None]
        e = np.matmul(w, z)
        result[start:end] = e
        if jacobian:
            reduced = z[:, :, :-1]
            second = np.matmul(np.swapaxes(reduced * w[None, :, None], 1, 2), reduced)
            index = np.arange(k - 1)
            second = -second
            second[:, index, index] += e[:, :-1]
            jac[start:end] = second
    if one:
        return (result[0], jac[0]) if jacobian else result[0]
    return (result, jac) if jacobian else result


@contextlib.contextmanager
def accelerated():
    original = integration.expectation
    integration.expectation = expectation
    try:
        yield
    finally:
        integration.expectation = original
