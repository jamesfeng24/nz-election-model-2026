"""Stage71 arm P for the live nowcast (audit J1, D127): the control fit on all four elections and the bootstrap of the variance inflation lambda.

Exactly the parameters Stage71's 2026 readout used for arm P (`run.readout_2026`): `model.fit_arm` on every calibration election and
`model.bootstrap` with the frozen contract seed stream `[seed, 2026, 1]` and replicate count. Nothing is refitted or re-chosen; the stored
`forecast-2026.json` interval is reproduced (tested).
"""
import numpy as np
from scripts.maori_seat_layer.data import calibration_rows
from scripts.maori_seat_calibration import model
from scripts.maori_seat_calibration.common import read, DESIGN


def arm_p():
    """(control estimate, replicate lambdas): draw a lambda per simulated draw from the replicates, as Stage71's arm P does."""
    contract = read(DESIGN)
    rows = calibration_rows()
    units = model.units_from_rows(rows, sorted({r['year'] for r in rows}))
    est = model.fit_arm(units, False)
    rng = np.random.default_rng(np.random.SeedSequence([contract['seed'], 2026, 1]))
    lam, skipped = model.bootstrap(units, False, contract['bootstrapReplicates'], rng)
    if skipped / contract['bootstrapReplicates'] > contract['bootstrapMaxSkipFraction']:
        raise ValueError('Stage71 bootstrap skipped too many replicates')
    return est, np.asarray(lam, float)
