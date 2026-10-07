"""Per-candidate share summaries carried in the bank: mean and central 50/80/90 intervals sharing one median."""
import numpy as np

LEVELS = (0.5, 0.8, 0.9)


def share_summaries(ids, q):
    """Linear-interpolated quantiles of each candidate's simulated share across the bank rows."""
    q = np.asarray(q, dtype=float)
    out = []
    for i, candidate in enumerate(ids):
        x = q[:, i]
        median = float(np.quantile(x, 0.5))
        out.append({'candidateId': candidate, 'mean': float(x.mean()),
                    'intervals': [{'level': level, 'lower': float(np.quantile(x, (1 - level) / 2)), 'median': median,
                                   'upper': float(np.quantile(x, 1 - (1 - level) / 2))} for level in LEVELS]})
    return out
