"""Stage79 poll update on the candidate National/Labour balance (the Stage45/47 logit coordinate).

Pure functions shared by the historical scoring and the 2026 assembly. Everything is on the log(N/L) scale.
The frozen form is in data/processed/seat-polls/design-contract.json.
"""
import math
import numpy as np
from scipy.special import expit
from scipy.stats import norm
from scipy.special import roots_hermitenorm

NODES, WEIGHTS = roots_hermitenorm(41)
WEIGHTS = WEIGHTS / np.sqrt(2 * np.pi)


def eligible(shares):
    """The poll publishes National and Labour and its two highest published candidate shares are those two."""
    if 'NAT' not in shares or 'LAB' not in shares:
        return False
    ranked = sorted(shares.values(), reverse=True)
    top = {k for k, v in shares.items() if v >= ranked[1]}
    return top == {'NAT', 'LAB'} and (len(ranked) < 3 or ranked[2] < ranked[1])


def poll_value(shares):
    return math.log(shares['NAT'] / shares['LAB'])


def sampling_variance(shares, n):
    return 1 / (n * shares['NAT'] / 100) + 1 / (n * shares['LAB'] / 100)


def fit_inflation(errors, variances):
    """c = max(1, mean(e^2 / v)): one constant, no bias term."""
    if not errors:
        raise ValueError('no polls to fit the inflation')
    return max(1.0, float(np.mean([e * e / v for e, v in zip(errors, variances)])))


def update(mu, sigma2, shared2, y, poll_variance, rho, cap):
    """Centre and variance after one poll. weight w, age factor rho, cap on w, floor at the shared variance."""
    w = min(cap, sigma2 / (sigma2 + poll_variance))
    k = rho * w
    centre = mu + k * (y - mu)
    variance = sigma2 - 2 * k * rho * sigma2 + k * k * (sigma2 + poll_variance)
    return centre, max(variance, shared2), w


def merge_same_source(entries, later_factor):
    """[(y, variance)] ordered by date; later variances are multiplied by later_factor; inverse-variance merge."""
    v = [var * (1 if i == 0 else later_factor) for i, (_, var) in enumerate(entries)]
    precision = sum(1 / x for x in v)
    return sum(y / x for (y, _), x in zip(entries, v)) / precision, 1 / precision


def age_factor(age_weeks, half_life):
    return 0.5 ** (max(0.0, age_weeks) / half_life)


def interval_covered(z, centre, variance, level):
    return abs(z - centre) <= norm.ppf(0.5 + level / 200) * math.sqrt(variance)


def log_density(z, centre, variance):
    return float(norm.logpdf(z, centre, math.sqrt(variance)))


def crps(z, centre, variance):
    s = math.sqrt(variance)
    t = (z - centre) / s
    return float(s * (t * (2 * norm.cdf(t) - 1) + 2 * norm.pdf(t) - 1 / math.sqrt(math.pi)))


def logit_normal_mean(centre, sd):
    """E[expit(centre + sd * Z)]: the conditional probability whose mean-logit location is `centre`."""
    return np.sum(expit(np.asarray(centre)[..., None] + sd * NODES) * WEIGHTS, axis=-1)
