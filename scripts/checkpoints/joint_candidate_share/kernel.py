"""Design arithmetic only: historical callers use centering/rank, never shares."""
from math import fsum, log, exp, isfinite, sqrt
import numpy as np
from scripts.checkpoints.stage22_fit import source_s
from scripts.checkpoints.complete_share_feature_rank import rank_details, PROBES

METHODS = {'baseline': (), 'baseline_plus_S': ('S',), 'baseline_plus_R': ('R',),
           'baseline_plus_S_plus_R': ('S', 'R')}


def feature(candidate, name, view, scenario):
    if name == 'S':
        return source_s(candidate, scenario)
    if name != 'R' or view not in ('broad', 'strict'):
        raise ValueError('Unknown feature or linkage view')
    return candidate['R'][view]['valueFraction']


def means(rows, view='broad', scenario='printed'):
    result = {}
    for name in ('S', 'R'):
        numerator, denominator = [], []
        for row in rows:
            weight = 1 / len(row['candidates'])
            for c in row['candidates']:
                value = feature(c, name, view, scenario)
                if value is not None:
                    if not isfinite(value):
                        raise ValueError('Nonfinite feature')
                    numerator.append(weight*value); denominator.append(weight)
        result[name] = fsum(numerator)/fsum(denominator) if denominator else None
    return result


def centered(c, name, center, view, scenario):
    value = feature(c, name, view, scenario)
    if value is None:
        return 0.0
    if center[name] is None:
        raise ValueError('Feature lacks earlier training center')
    return value-center[name]


def support(c, regime):
    if regime not in ('constructed', 'observed'):
        raise ValueError('Unknown input regime')
    value = c['constructedPartySupport' if regime == 'constructed' else 'observedPartySupport']
    if value is None or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Missing or invalid party input')
    return value


def synthetic_shares(candidates, center, kappa, coefficients, view='broad', scenario='printed', regime='constructed'):
    """Only synthetic tests call this; no historical prediction runner is authorized."""
    if not 0.0001 <= kappa <= 0.1 or set(coefficients)-{'S', 'R'}:
        raise ValueError('Parameters outside frozen family')
    if any(not isfinite(v) or abs(v) > 4 for v in coefficients.values()):
        raise ValueError('Coefficient outside bounds')
    logits = [log(support(c, regime)+kappa) + fsum(theta*centered(c, name, center, view, scenario)
              for name, theta in coefficients.items()) for c in candidates]
    if not logits or not all(isfinite(x) for x in logits):
        raise ValueError('Invalid intensity slate')
    shifted = [exp(x-max(logits)) for x in logits]; total = fsum(shifted)
    return [w/total for w in shifted]


def designs(rows, center, view, scenario, regime, kappa):
    blocks = []
    for row in rows:
        vals = [[1/(support(c, regime)+kappa), centered(c,'S',center,view,scenario),
                 centered(c,'R',center,view,scenario)] for c in row['candidates']]
        block = np.asarray(vals)
        blocks.extend((block-block.mean(axis=0))/sqrt(len(block)))
    return np.asarray(blocks) if blocks else np.empty((0,3))


def rank_audit(rows, center, view, scenario, regime):
    if not rows:
        return {'status':'no_earlier_training', 'methods':{m:{'estimable':False,'reason':'no_earlier_training'} for m in METHODS}}
    probes = []
    for kappa in PROBES:
        matrix = designs(rows, center, view, scenario, regime, kappa)
        methods = {m:rank_details(matrix,[0]+[1 if f=='S' else 2 for f in names]) for m,names in METHODS.items()}
        probes.append({'kappa':kappa,'methods':methods})
    return {'status':'audited_not_fitted','probes':probes,'methods':{
        m:{'estimable':all(p['methods'][m]['rank']==len(METHODS[m])+1 for p in probes),
           'conditioningWarning':any(p['methods'][m]['weakCondition'] for p in probes)} for m in METHODS}}
