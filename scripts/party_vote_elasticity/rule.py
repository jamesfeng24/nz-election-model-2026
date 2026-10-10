"""The frozen Stage81 adoption rule. Every threshold is read from the design contract."""
import itertools


def losses(block, transitions, bound, metric, arm):
    out = []
    for t in transitions:
        bounds = block[t]['bounds']
        use = bounds[bound] if bound in bounds else bounds['lower']
        arm_scores = use['arms'][arm]
        out.append(arm_scores['M1']['mae'] if metric == 'M1' else arm_scores['M2']['macroMinorMae'])
    return out


def beats(x, y, threshold):
    """X beats Y: lower on average by at least the threshold and lower in at least two of the three transitions."""
    mean_gain = sum(b - a for a, b in zip(x, y)) / len(x)
    return mean_gain >= threshold and sum(a < b for a, b in zip(x, y)) >= 2


def comparison_matrix(block, transitions, bound, arms, thresholds):
    return {metric: {f'{x}>{y}': beats(losses(block, transitions, bound, metric, x), losses(block, transitions, bound, metric, y), thresholds[metric])
                     for x, y in itertools.permutations(arms, 2)} for metric in ('M1', 'M2')}


def retained(matrix, arms):
    return [x for x in arms if not any(matrix[m][f'{y}>{x}'] for m in ('M1', 'M2') for y in arms if y != x)]


def classify(block, transitions, arms, thresholds, invariance=None):
    matrices = {b: comparison_matrix(block, transitions, b, arms, thresholds) for b in ('lower', 'upper')}
    consistent = matrices['lower'] == matrices['upper']
    keep = retained(matrices['lower'], arms)
    if not consistent:
        base = 'mixed_report_to_james'
    elif len(keep) == 1:
        base = 'adopt_' + keep[0]
    elif len(keep) >= 2:
        base = 'carry_mixture'
    else:
        base = 'mixed_report_to_james'
    cls = 'materially_invariant' if invariance and invariance['invariant'] else base
    return {'class': cls, 'ruleClassBeforeOverride': base, 'retainedArms': keep, 'boundsAgree': consistent,
            'comparisons': matrices['lower'], 'comparisonsAtUpperBound': matrices['upper'],
            'pooledM1': {a: sum(losses(block, transitions, 'lower', 'M1', a)) / len(transitions) for a in arms},
            'pooledM2': {a: sum(losses(block, transitions, 'lower', 'M2', a)) / len(transitions) for a in arms}}
