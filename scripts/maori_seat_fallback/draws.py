"""Stage80: per-draw shares of the chosen Stage78 fallback (arm F, 2023 result carried forward, no polls) for any set of seats.

The registered model is exactly Stage78's arm F: `forecast.fallback_parameters` (estimators, entrant pools, parameter draws, split-incumbent
fraction) and `model.simulate_seat`, unchanged. Only the seed differs: the assembly derives it from the configured seed namespace, so the draws
are independent of the Stage78 readout streams. With the Stage78 contract seed and draw count this reproduces the stored arm F exactly (tested).
"""
import numpy as np
from scripts.maori_seat_fallback import forecast, history, inputs2026, model
from scripts.maori_seat_fallback.common import SEATS, read, DESIGN


def f_shares(seats, draws, seed=None, res=None):
    """{seat: (inputs, share)}: closed shares (draws x candidates, official 2026 slate order) of arm F. Seats are drawn from separate streams,
    so the result for a seat does not depend on which other seats are requested; the shared shift and noise variance are common to all seats."""
    contract = {'seed': read(DESIGN)['seed'] if seed is None else seed}
    res = res or history.results()
    _, pools, s2, t2, z, phi = forecast.fallback_parameters(contract, res, draws)
    u = np.sqrt(t2) * z
    slates = inputs2026.slates()
    out = {}
    for seat in seats:
        if seat not in SEATS:
            raise ValueError('Not a Maori seat: ' + seat)
        inp = inputs2026.seat_inputs(seat, slates[seat], res)
        rng = np.random.default_rng(np.random.SeedSequence([contract['seed'], 2026, 10 + SEATS.index(seat)]))
        out[seat] = (inp, model.simulate_seat(inp, s2, u, pools, rng, phi if inp['split'] else None))
    return out
