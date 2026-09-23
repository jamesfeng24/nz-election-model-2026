"""Matched-universe, leave-one-contest-out descriptive normalization."""
from collections import defaultdict
import math

from scripts.models.candidate_overperformance.inputs import REGIMES

METHODS = ('additive', 'proportional', 'log_odds')


def expected(method, local_party, candidate_ref, party_ref):
    """One parameterized reference transform; undefined domains stay missing."""
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in (local_party, candidate_ref, party_ref)):
        raise ValueError('Invalid reference share')
    if method == 'additive':
        raw = local_party + candidate_ref - party_ref
    elif method == 'proportional':
        if party_ref == 0:
            return {'expectedRaw': None, 'expectedBounded': None, 'outOfRange': None, 'unavailableReason': 'zero_party_reference'}
        raw = local_party * candidate_ref / party_ref
    elif method == 'log_odds':
        if not (0 < candidate_ref < 1 and 0 < party_ref < 1):
            return {'expectedRaw': None, 'expectedBounded': None, 'outOfRange': None, 'unavailableReason': 'reference_odds_undefined'}
        odds = candidate_ref * (1 - party_ref) / (party_ref * (1 - candidate_ref))
        raw = local_party * odds / (1 - local_party + local_party * odds)
    else:
        raise ValueError('Unknown normalization method')
    return {'expectedRaw': raw, 'expectedBounded': min(1, max(0, raw)),
            'outOfRange': raw < 0 or raw > 1, 'unavailableReason': None}


def totals(rows):
    return {k: sum(r[k] for r in rows) for k in
            ('sourcePublishedCandidateVotes', 'validCandidateVotes', 'localPartyVotes', 'validPartyVotes')}


def reference(t, n):
    if n == 0:
        return {'contestCount': 0, **t, 'candidateShare': None, 'partyShare': None, 'offset': None}
    c = t['sourcePublishedCandidateVotes'] / t['validCandidateVotes']
    p = t['localPartyVotes'] / t['validPartyVotes']
    return {'contestCount': n, **t, 'candidateShare': c, 'partyShare': p, 'offset': c-p}


def validate_rows(rows):
    ids = set()
    for r in rows:
        if r['candidateOccurrenceId'] in ids:
            raise ValueError('Duplicate occurrence')
        ids.add(r['candidateOccurrenceId'])
        if r['year'] not in REGIMES or r['boundaryRegime'] != REGIMES[r['year']] or r['inputClass'] != 'observed':
            raise ValueError('Non-observed/future/boundary input')
        if r['personId'] is not None or any(k in r for k in ('incumbent', 'candidateStatus', 'personHistory', 'polling')):
            raise ValueError('Later-stage identity/status input')
        if not r['eligible']:
            if not r['exclusionReason'] or r['rawPremium'] is not None:
                raise ValueError('Invalid excluded occurrence')
            continue
        if r['candidateContestStatus'] != 'held' or r['exclusionReason'] is not None:
            raise ValueError('Invalid eligible contest')
        for numerator, denominator, share in [('sourcePublishedCandidateVotes', 'validCandidateVotes', 'candidateShare'),
                                               ('localPartyVotes', 'validPartyVotes', 'localPartyShare')]:
            a, b = r[numerator], r[denominator]
            if type(a) is not int or type(b) is not int or not 0 <= a <= b or b <= 0:
                raise ValueError('Invalid counts/denominator')
            if r[share] is None or not math.isfinite(r[share]) or abs(r[share] - a/b) > 1e-10:
                raise ValueError('Share/count mismatch')
        if r['partyKey'] != r['candidateAffiliationKey'] or not r['partyKey']:
            raise ValueError('Report grouping or unmatched identity')
        if abs(r['rawPremium'] - (r['candidateShare']-r['localPartyShare'])) > 1e-10:
            raise ValueError('Invalid raw premium')


def normalize(rows, electorate_counts):
    validate_rows(rows)
    groups = defaultdict(list)
    for r in rows:
        if r['eligible']:
            groups[r['year'], r['partyKey']].append(r)
    refs = []
    by_id = {}
    for (year, party), rs in sorted(groups.items()):
        seats = [r['electorateId'] for r in rs]
        if len(set(seats)) != len(seats):
            raise ValueError('Multiple candidates share a matched contest')
        t = totals(rs)
        rid = f'{year}:{party}'
        ref = {'id': rid, 'year': year, 'partyKey': party, 'sourcePartyLabels': sorted({r['sourcePartyLabel'] for r in rs}),
               'electorateIds': sorted(seats), 'candidateOccurrenceIds': sorted(r['candidateOccurrenceId'] for r in rs),
               'electionElectorateCount': electorate_counts[year], 'coverageFraction': len(rs)/electorate_counts[year],
               'scopeCounts': {s: sum(r['electorateType'] == s for r in rs) for s in ('general', 'maori')},
               'normalizationAvailable': len(rs) >= 2, **reference(t, len(rs))}
        refs.append(ref)
        by_id[rid] = ref
    out = []
    for r in rows:
        x = {**r, 'referenceId': None, 'leaveOneOutReference': None, 'normalizedPremium': None,
             'normalizationMethod': 'additive_national_centered', 'normalizationReason': r['exclusionReason'], 'methods': {}}
        if r['eligible']:
            rid = f"{r['year']}:{r['partyKey']}"
            ref = by_id[rid]
            remaining = {k: ref[k]-r[k] for k in totals([r])}
            loo = reference(remaining, ref['contestCount']-1)
            x.update(referenceId=rid, leaveOneOutReference=loo,
                     referenceCoverage={'contestCount': ref['contestCount'], 'coverageFraction': ref['coverageFraction'],
                                        'electionElectorateCount': ref['electionElectorateCount']},
                     normalizationReason=None if ref['contestCount'] >= 2 else 'insufficient_reference_contests')
            if ref['contestCount'] >= 2:
                for method in METHODS:
                    m = expected(method, r['localPartyShare'], loo['candidateShare'], loo['partyShare'])
                    m['residual'] = None if m['expectedRaw'] is None else r['candidateShare']-m['expectedRaw']
                    x['methods'][method] = m
                x['normalizedPremium'] = x['methods']['additive']['residual']
        out.append(x)
    return refs, out
