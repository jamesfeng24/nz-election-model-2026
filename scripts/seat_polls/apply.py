"""Apply one seat's poll to the conditional candidate vectors before the frozen Stage47 inversion.

The inversion draws the balance as expit(location + eta) with eta ~ N(0, hypot(shared, seat)^2) and a location chosen
so that the draw mean equals the conditional probability. A poll changes the location (shift = rho * w * (y - mu)) and
the seat scale (so the total SD becomes the posterior SD). The conditional probability is rewritten so that the
unchanged inversion recovers exactly that location and SD. National, local-party and Maori layers are not touched.
"""
from copy import deepcopy
import numpy as np
from scripts.uncertainty_revision.coordinates import partition, mean_logit_location
from . import model


def apply(conditional, candidate, scales, multiplier, poll):
    """Return (conditional', scales', record). `scales` are the unscaled 2026 candidate scales; `multiplier` the D107 class."""
    n, l, _ = partition(candidate['groups'])
    if not (n and l):
        raise ValueError('a seat poll needs both a National and a Labour candidate')
    b = np.asarray(conditional, dtype=float)
    major = b[:, n[0]] + b[:, l[0]]
    probability = np.divide(b[:, n[0]], major, out=np.zeros(len(b)), where=major > 0)
    shared = scales['balance']['shared']
    seat = scales['balance']['seat'] * float(multiplier)
    sigma2, shared2 = shared ** 2 + seat ** 2, shared ** 2
    location = mean_logit_location(probability, sigma2 ** 0.5)
    active = (probability > 0) & (probability < 1)
    mu = float(location[active].mean())
    centre, variance, weight = model.update(mu, sigma2, shared2, poll['value'], poll['variance'], poll['rho'], poll['cap'])
    shift = centre - mu
    new_seat = float(np.sqrt(variance - shared2))
    sd = float(np.sqrt(variance))
    moved = np.where(active, model.logit_normal_mean(location + shift, sd), probability)
    out = b.copy()
    out[:, n[0]] = major * moved
    out[:, l[0]] = major * (1 - moved)
    new_scales = deepcopy(scales)
    new_scales['balance']['seat'] = new_seat / float(multiplier) if multiplier else new_seat
    record = {'pollIds': poll['pollIds'], 'pollValue': poll['value'], 'pollVariance': poll['variance'], 'ageWeeks': poll['ageWeeks'], 'rho': poll['rho'],
              'weight': weight, 'modelCentre': mu, 'modelSD': sigma2 ** 0.5, 'shift': shift, 'posteriorSD': sd, 'sharedSD': shared}
    return out, new_scales, record
