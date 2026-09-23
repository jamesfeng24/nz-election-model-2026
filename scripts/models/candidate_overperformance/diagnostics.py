"""Descriptive checks only: no fitted normalization or historical person ranking."""
from collections import Counter
import math
from statistics import mean, median, pstdev
from scripts.models.candidate_overperformance.normalize import METHODS


def quantile(values, q):
    xs = sorted(values)
    position = (len(xs)-1)*q
    lo = int(position)
    hi = min(lo+1, len(xs)-1)
    return xs[lo] + (position-lo)*(xs[hi]-xs[lo])


def distribution(values):
    xs = [100*x for x in values if x is not None]
    if not xs:
        return {'n': 0}
    return {'n': len(xs), 'meanPP': mean(xs), 'medianPP': median(xs), 'sdPP': pstdev(xs),
            'minPP': min(xs), 'p10PP': quantile(xs, .1), 'p90PP': quantile(xs, .9), 'maxPP': max(xs)}


def correlation(a, b):
    if len(a) < 2:
        return None
    ma, mb = mean(a), mean(b)
    da = [x-ma for x in a]
    db = [x-mb for x in b]
    denominator = math.sqrt(sum(x*x for x in da)*sum(x*x for x in db))
    return sum(x*y for x, y in zip(da, db))/denominator if denominator else None


def describe(rows):
    return {'occurrenceCount': len(rows), 'eligibleCount': sum(r['eligible'] for r in rows),
            'normalizedCount': sum(r['normalizedPremium'] is not None for r in rows),
            'exclusions': dict(sorted(Counter(r['exclusionReason'] for r in rows if not r['eligible']).items())),
            'normalizationUnavailable': dict(sorted(Counter(r['normalizationReason'] for r in rows if r['normalizationReason']).items())),
            'rawPremium': distribution([r['rawPremium'] for r in rows]),
            'normalizedPremium': distribution([r['normalizedPremium'] for r in rows])}


def sensitivity(rows):
    rs = [r for r in rows if r['normalizedPremium'] is not None]
    result = {}
    for method in METHODS:
        defined = [r for r in rs if r['methods'][method]['residual'] is not None]
        outside = [r for r in defined if r['methods'][method]['outOfRange']]
        additive = [r['normalizedPremium'] for r in defined]
        residual = [r['methods'][method]['residual'] for r in defined]
        result[method] = {
            'referenceEligibleCount': len(rs), 'definedCount': len(defined),
            'undefinedReasons': dict(sorted(Counter(r['methods'][method]['unavailableReason'] for r in rs if r['methods'][method]['unavailableReason']).items())),
            'outOfRangeCount': len(outside), 'outOfRangeFraction': len(outside)/len(defined) if defined else None,
            'maximumBoundedAdjustmentPP': max((100*abs(r['methods'][method]['expectedRaw']-r['methods'][method]['expectedBounded']) for r in defined), default=None),
            'rawResidualDistribution': distribution(residual),
            'differenceFromAdditive': distribution([x-y for x, y in zip(residual, additive)]),
            'correlationWithAdditive': correlation(additive, residual),
            'correlations': {field: correlation(residual, [r[field] for r in defined]) for field in ('localPartyShare', 'candidateShare')},
            'correlationWithLOOPartyReferenceShare': correlation(residual, [r['leaveOneOutReference']['partyShare'] for r in defined]),
        }
    return result


def build(rows, refs):
    years = sorted({r['year'] for r in rows})
    parties = sorted({r['candidateAffiliationKey'] for r in rows})
    cells = [(ref['year'], ref['partyKey']) for ref in refs]
    diagnostics = {
        'schemaVersion': 1, 'overall': describe(rows),
        'byElection': {str(y): describe([r for r in rows if r['year'] == y]) for y in years},
        'byScope': {s: describe([r for r in rows if r['electorateType'] == s]) for s in ('general', 'maori')},
        'byAffiliation': {p: describe([r for r in rows if r['candidateAffiliationKey'] == p]) for p in parties},
        'majorParties': {p: {s: describe([r for r in rows if r['partyKey'] == p and r['electorateType'] == s]) for s in ('general', 'maori')} for p in ('nationalparty', 'labourparty')},
        'referenceCoverage': [{'referenceId': r['id'], 'contestCount': r['contestCount'], 'coverageFraction': r['coverageFraction'], 'scopeCounts': r['scopeCounts']} for r in sorted(refs, key=lambda r: (r['contestCount'], r['id']))],
        'coverageInterpretation': 'Full coverage ranking, no fitted cutoff or additional exclusion. Two is the only hard contest minimum; a two-contest slate has one other reference contest.',
        'excludedAffiliations': [{'year': y, 'affiliation': p, 'count': n} for (y, p), n in sorted(Counter((r['year'], r['sourceAffiliation']) for r in rows if r['exclusionReason'] == 'no_exact_party_vote_counterpart').items())],
    }
    sens = {'schemaVersion': 1, 'overall': sensitivity(rows),
            'byScope': {s: sensitivity([r for r in rows if r['electorateType'] == s]) for s in ('general', 'maori')},
            'byElectionParty': {f'{y}:{p}': sensitivity([r for r in rows if r['year'] == y and r['partyKey'] == p]) for y, p in cells},
            'interpretation': 'Descriptive correlations are not fitting targets. Expected raw references and residuals remain unbounded for additive/proportional; no pseudocounts. Sensitivity is not three separate downstream models.'}
    return diagnostics, sens
