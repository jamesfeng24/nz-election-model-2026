"""One composed block per seat: Stage47 inversion with a substituted scramble, Stage48 rebalance for K and F."""
import numpy as np
from scripts.balance_scale.simulate import compact, major_columns, rebalance, scaled
from scripts.uncertainty_expectation.simulation import invert, upstream
from scripts.uncertainty_revision.coordinates import partition
from scripts.uncertainty_tails.metrics import record
from .common import RESTRICTIONS
from .stream import scrambled

LEVELS = (50, 80, 90)


def winner_probabilities(q):
    """Share of draws in which each candidate has the maximum; ties split, as the Stage46 ranking."""
    tied = np.abs(q - q.max(axis=1, keepdims=True)) <= 1e-12
    return (tied / tied.sum(axis=1, keepdims=True)).mean(axis=0)


def summarize_bank(row, q, point, rb_mean=None):
    """Lean record of one bank; the control also keeps every per-candidate vector."""
    rec = record(row, q, point)
    major = major_columns(row)
    n, l, _ = partition(row['groups'])
    win = winner_probabilities(q)
    pick = lambda values: float(np.mean([values[i] for i in major]))
    out = {'majorCRPSPP': pick(rec['crpsPP']), 'energyPP': float(rec['energyPP']),
           'intervalScorePP': [pick(rec[f'interval{v}']['scores']) for v in LEVELS],
           'majorWidthPP': [pick(rec[f'interval{v}']['widths']) for v in LEVELS],
           'majorCovered': [int(sum(bool(rec[f'interval{v}']['covered'][i]) for i in major)) for v in LEVELS],
           'majorMeanPP': [float(100 * rec['simulatedMean'][n[0]]), float(100 * rec['simulatedMean'][l[0]])],
           'majorWin': [float(win[n[0]]), float(win[l[0]])]}
    if rb_mean is not None:
        out.update({'crpsPP': [float(v) for v in rec['crpsPP']], 'meanPP': [float(100 * v) for v in rec['simulatedMean']],
                    'rbMeanPP': [float(100 * v) for v in rb_mean], 'win': [float(v) for v in win],
                    **{f'width{v}': [float(x) for x in rec[f'interval{v}']['widths']] for v in LEVELS}})
    return out, compact(rec)


def composed_bank(row, party, national, party_scales, fit, multipliers, scramble, restrictions=RESTRICTIONS, check_full=False):
    """Banks of the requested restrictions on one block (national draws fixed, layer stream ``scramble``)."""
    with scrambled(scramble):
        _, conditional, control_input, _ = upstream(party, row, national, party_scales)
        count = len(national)
        base, _ = invert(conditional, row, fit, count)
        banks, checks = {'control': base}, {}
        for r in restrictions[1:]:
            banks[r] = rebalance(base, conditional, row, scaled(fit, multipliers[r]), count)
            if check_full:
                full, _ = invert(conditional, row, scaled(fit, multipliers[r]), count)
                checks[r + 'FullInvertMaxAbs'] = float(np.max(np.abs(full - banks[r])))
    return banks, np.asarray(control_input), conditional.mean(axis=0), checks
