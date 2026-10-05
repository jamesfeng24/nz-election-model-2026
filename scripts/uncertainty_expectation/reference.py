"""Independent low-dimensional Gaussian contrast quadrature for synthetic checks.

These numerical references use a raw-covariance Cholesky factor, separately from
producer eigendecomposition and QMC. The finite-order differences are reported;
no finite quadrature rule is claimed to be exact.
"""
import numpy as np
from scipy.special import roots_hermitenorm, softmax


def cholesky_expectation(p, offset, tags, shared, seat, order):
    """Integrate an active-face Gaussian expectation in final-option contrasts."""
    p = np.asarray(p, dtype=float)
    offset = np.asarray(offset, dtype=float)
    active = np.flatnonzero(p > 0)
    result = np.zeros_like(p)
    if len(active) < 2:
        result[active] = p[active]
        return result
    labels = [tags[i] for i in active]
    count = len(active)
    raw = np.empty((count, count))
    for i in range(count):
        for j in range(count):
            raw[i, j] = shared**2 * (labels[i] == labels[j]) + seat**2 * (i == j)
    covariance = np.empty((count - 1, count - 1))
    for i in range(count - 1):
        for j in range(count - 1):
            covariance[i, j] = raw[i, j] - raw[i, -1] - raw[-1, j] + raw[-1, -1]
    if np.count_nonzero(covariance) == 0:
        result[active] = softmax(np.log(p[active]) + offset[active])
        return result
    factor = np.linalg.cholesky(covariance)
    nodes, weights = roots_hermitenorm(order)
    weights = weights / np.sqrt(2 * np.pi)
    mesh = np.stack(np.meshgrid(*([nodes] * (count - 1)), indexing='ij'), axis=-1)
    points = mesh.reshape(-1, count - 1)
    weighted_mesh = np.stack(np.meshgrid(*([weights] * (count - 1)), indexing='ij'), axis=-1)
    joint_weights = np.prod(weighted_mesh, axis=-1).ravel()
    contrast = np.einsum('ij,kj->ik', points, factor, optimize=False)
    raw_noise = np.column_stack((contrast, np.zeros(len(contrast))))
    probabilities = softmax(np.log(p[active]) + offset[active] + raw_noise, axis=-1)
    result[active] = np.einsum('ni,n->i', probabilities, joint_weights, optimize=False)
    return result


def assess_reference(p, offset, tags, shared, seat, orders=(41, 81)):
    """Report finite-reference convergence separately from conditional error."""
    first = cholesky_expectation(p, offset, tags, shared, seat, orders[0])
    second = cholesky_expectation(p, offset, tags, shared, seat, orders[1])
    return {'orders': list(orders), 'referenceChangePP': float(100 * np.max(np.abs(first-second))),
            'conditionalGapPP': float(100 * np.max(np.abs(second-np.asarray(p)))),
            'referenceMean': second.tolist(), 'referenceMethod': 'raw_covariance_Cholesky_tensor_GH',
            'referenceDifferenceIsNotRigorousErrorBound': True}
