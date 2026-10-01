"""Canonical, outcome-blind historical target-seat geography applicability."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from scripts.transform.historical import key


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/processed/checkpoints/stage25-historical-geography'
FRAME = 'data/processed/checkpoints/complete-candidate-baseline/input-inventory.json'
OCCURRENCES = 'data/processed/models/candidate-overperformance/occurrences.json'
CROSSWALKS = ('2011-2014', '2017-2020')
INPUTS = (FRAME, OCCURRENCES) + tuple(
    f'data/processed/boundaries/{stem}/{name}'
    for stem in CROSSWALKS for name in ('crosswalk.json', 'manifest.json'))


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode()


def write_or_check(name, value, check):
    path = DEST / name
    raw = encode(value)
    if check:
        if not path.exists() or path.read_bytes() != raw:
            raise ValueError(f'Stale Stage25 geography artifact: {name}')
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def fraction(value):
    return Fraction(value['numerator'], value['denominator'])


def unit():
    return {'numerator': 1, 'denominator': 1}


def zero():
    return {'numerator': 0, 'denominator': 1}


def tier(exact, target_lower, source_lower):
    """Use separate target-only and jointly guaranteed source/target bands."""
    if exact:
        return 'exact'
    if target_lower >= Fraction(95, 100) and source_lower >= Fraction(95, 100):
        return 'approximate_two_sided_95'
    if target_lower >= Fraction(90, 100) and source_lower >= Fraction(90, 100):
        return 'approximate_two_sided_90_only'
    return 'not_two_sided_90'


def local_ids(occurrences):
    index = {}
    for row in occurrences:
        lookup = (row['year'], row['electorateType'], key(row['electorateName']))
        prior = index.setdefault(lookup, row['electorateId'])
        if prior != row['electorateId']:
            raise ValueError('Ambiguous election-local electorate name')
        number_lookup = (row['year'], row['electorateType'],
                         f"number:{row['sourceElectorateNumber']}")
        number_prior = index.setdefault(number_lookup, row['electorateId'])
        if number_prior != row['electorateId']:
            raise ValueError('Ambiguous election-local electorate number')
    return index


def seat_id(year, scope, code, name, occurrence_index):
    if scope == 'general':
        result = f'nz-general-{year}-electorate-{int(code):02d}'
        # An election-local official number joins the processed occurrence ID.
        # Crosswalk labels retain source encoding, including one 2014 mojibake
        # label; names never certify cross-election geography.
        if occurrence_index.get((year, scope, f'number:{int(code)}')) != result:
            raise ValueError('General electorate code/ID mismatch')
        return result
    result = occurrence_index.get((year, scope, key(name)))
    if result is None:
        raise ValueError('Missing Māori election-local electorate ID')
    return result


def verify_crosswalk(stem):
    base = f'data/processed/boundaries/{stem}/'
    saved = read(base + 'manifest.json')
    if digest(base + 'crosswalk.json') != saved['outputSha256']:
        raise ValueError('Changed certified boundary crosswalk')
    for path, expected in {**saved['inputHashes'], **saved['codeHashes']}.items():
        if digest(path) != expected:
            raise ValueError(f'Changed certified boundary dependency: {path}')
    crosswalk = read(base + 'crosswalk.json')
    if crosswalk['status'] != 'validated_feasible_crosswalk':
        raise ValueError('Unvalidated boundary source')
    return crosswalk


def original_rows(frame):
    rows = []
    for item in frame:
        source_id, target_id = item['sourceElectorateId'], item['targetElectorateId']
        if target_id is None:
            raise ValueError('Original certified geography lacks target ID')
        row = {
            'geographyId': f"{item['sourceYear']}-{item['targetYear']}:{item['scope']}:{target_id}",
            'sourceYear': item['sourceYear'], 'targetYear': item['targetYear'],
            'sourceBoundaryVersion': item['boundaryRegime'],
            'targetBoundaryVersion': item['boundaryRegime'],
            'scope': item['scope'], 'targetElectorateId': target_id,
            'targetElectorateName': item['targetSeatLabel'],
            'originalFrame': True, 'contestStatus': item['contestStatus'],
            'reportedIncomingMembershipIdentity': True,
            'certifiedTwoSidedExact': True,
            'certificationEvidence': 'validated_stage14_same_boundary_regime_pair',
            'uncertaintyClass': 'none_for_geographic_membership_not_voter_identity',
            'dominantPredecessorId': source_id,
            'dominantTargetInheritanceLower': unit(),
            'dominantTargetInheritanceUpper': unit(),
            'dominantSourceRetentionLower': unit(),
            'dominantSourceRetentionUpper': unit(),
            'predecessors': [{
                'sourceElectorateId': source_id,
                'sourceElectorateName': item['sourceSeatLabel'],
                'targetInheritanceLower': unit(), 'targetInheritanceUpper': unit(),
                'sourceRetentionLower': unit(), 'sourceRetentionUpper': unit(),
            }],
            'targetOverlap95': True, 'targetOverlap90': True,
            'twoSided95': True, 'twoSided90': True,
            'exclusiveTier': 'exact',
            'units': 'electoral_population_fraction_not_ballots_or_candidate_vote_share',
            'provenancePaths': [FRAME],
            'unresolvedReasons': [],
        }
        rows.append(row)
    return rows


def crosswalk_rows(stem, occurrences):
    data = verify_crosswalk(stem)
    transition = data['transition']
    source_year = transition['sourceElectionYear']
    target_year = transition['targetElectionYear']
    source_version = transition.get('sourceBoundaryVersion', transition.get('sourceBoundaryId'))
    target_version = transition.get('targetBoundaryVersion', transition.get('targetBoundaryId'))
    rows = []
    for scope in ('general', 'maori'):
        part = data['scopes'][scope]
        sources = {row['code']: row for row in part['sources']}
        outgoing = defaultdict(list)
        edges = {}
        for edge in part['edges']:
            pair = (edge['source'], edge['target'])
            if pair in edges:
                raise ValueError('Duplicate crosswalk predecessor edge')
            edges[pair] = edge
            outgoing[edge['source']].append(edge)
        for target in part['targets']:
            target_id = seat_id(target_year, scope, target['code'], target['name'], occurrences)
            predecessors = []
            for component in target['composition']:
                source_code = component['source']
                source = sources[source_code]
                edge = edges[source_code, target['code']]
                predecessors.append({
                    'sourceElectorateId': seat_id(source_year, scope, source_code, source['name'], occurrences),
                    'sourceElectorateName': source['name'],
                    'sourceElectionLocalLabelMatch': occurrences.get(
                        (source_year, scope, key(source['name']))) == seat_id(
                            source_year, scope, source_code, source['name'], occurrences),
                    'targetInheritanceLower': component['shareLower'],
                    'targetInheritanceUpper': component['shareUpper'],
                    'sourceRetentionLower': edge['weightLower'],
                    'sourceRetentionUpper': edge['weightUpper'],
                })
            predecessors.sort(key=lambda row: row['sourceElectorateId'])
            dominant_code = target['dominantPredecessor']
            dominant_id = (seat_id(source_year, scope, dominant_code, sources[dominant_code]['name'], occurrences)
                           if dominant_code is not None else None)
            dominant = next((row for row in predecessors if row['sourceElectorateId'] == dominant_id), None)
            incoming_identity = (target.get('membershipIdentity') is True if stem == '2011-2014'
                                 else target.get('unchangedMembershipStatus') == 'identity')
            exact = (incoming_identity and len(predecessors) == 1 and dominant is not None and
                     len(outgoing[dominant_code]) == 1 and
                     fraction(dominant['targetInheritanceLower']) == 1 and
                     fraction(dominant['sourceRetentionLower']) == 1)
            target_lower = fraction(dominant['targetInheritanceLower']) if dominant else Fraction(0)
            source_lower = fraction(dominant['sourceRetentionLower']) if dominant else Fraction(0)
            reasons = []
            if not exact:
                reasons.append('not_certified_two_sided_identical_membership')
            if incoming_identity and not exact:
                reasons.append('incoming_identity_but_predecessor_has_other_successor')
            if dominant is None:
                reasons.append('no_guaranteed_dominant_predecessor')
            if target.get('unchangedMembershipStatus') in (
                    'rounded_technical_uncertainty', 'suppressed_technical_uncertainty'):
                reasons.append('technical_membership_uncertainty')
            rows.append({
                'geographyId': f'{source_year}-{target_year}:{scope}:{target_id}',
                'sourceYear': source_year, 'targetYear': target_year,
                'sourceBoundaryVersion': source_version,
                'targetBoundaryVersion': target_version,
                'scope': scope, 'targetElectorateId': target_id,
                'targetElectorateName': target['name'], 'originalFrame': False,
                'targetElectionLocalLabelMatch': occurrences.get(
                    (target_year, scope, key(target['name']))) == target_id,
                'contestStatus': 'not_adjudicated_in_geography_layer',
                'reportedIncomingMembershipIdentity': incoming_identity,
                'certifiedTwoSidedExact': exact,
                'certificationEvidence': f'{stem}_crosswalk_joint_membership_and_outgoing_edges',
                'uncertaintyClass': ('none_for_geographic_membership_not_voter_identity' if exact
                                     else 'coupled_population_bounds_not_candidate_ballot_bounds'),
                'dominantPredecessorId': dominant_id,
                'dominantTargetInheritanceLower': (dominant['targetInheritanceLower'] if dominant else zero()),
                'dominantTargetInheritanceUpper': (dominant['targetInheritanceUpper'] if dominant else unit()),
                'dominantSourceRetentionLower': (dominant['sourceRetentionLower'] if dominant else zero()),
                'dominantSourceRetentionUpper': (dominant['sourceRetentionUpper'] if dominant else unit()),
                'predecessors': predecessors,
                'targetOverlap95': target_lower >= Fraction(95, 100),
                'targetOverlap90': target_lower >= Fraction(90, 100),
                'twoSided95': target_lower >= Fraction(95, 100) and source_lower >= Fraction(95, 100),
                'twoSided90': target_lower >= Fraction(90, 100) and source_lower >= Fraction(90, 100),
                'exclusiveTier': tier(exact, target_lower, source_lower),
                'units': 'electoral_population_fraction_not_ballots_or_candidate_vote_share',
                'provenancePaths': [f'data/processed/boundaries/{stem}/crosswalk.json',
                                    f'data/processed/boundaries/{stem}/manifest.json'],
                'unresolvedReasons': reasons,
            })
    return rows


def build():
    frame = read(FRAME)['records']
    occurrences = local_ids(read(OCCURRENCES)['records'])
    rows = original_rows(frame)
    for stem in CROSSWALKS:
        rows.extend(crosswalk_rows(stem, occurrences))
    rows.sort(key=lambda row: (row['targetYear'], row['scope'], row['targetElectorateId']))
    if len(rows) != 356 or len({row['geographyId'] for row in rows}) != len(rows):
        raise ValueError('Canonical target-seat coverage or uniqueness changed')
    summary = []
    for year in (2011, 2014, 2017, 2020, 2023):
        for scope in ('general', 'maori'):
            group = [row for row in rows if row['targetYear'] == year and row['scope'] == scope]
            summary.append({'targetYear': year, 'scope': scope, 'targets': len(group),
                            'reportedIncomingIdentity': sum(row['reportedIncomingMembershipIdentity'] for row in group),
                            'certifiedTwoSidedExact': sum(row['certifiedTwoSidedExact'] for row in group),
                            'targetOverlap95': sum(row['targetOverlap95'] for row in group),
                            'targetOverlap90': sum(row['targetOverlap90'] for row in group),
                            'twoSided95': sum(row['twoSided95'] for row in group),
                            'twoSided90': sum(row['twoSided90'] for row in group),
                            'exclusiveTiers': dict(sorted(Counter(row['exclusiveTier'] for row in group).items()))})
    result = {'schemaVersion': 1, 'stage': 25,
              'role': 'canonical_outcome_independent_target_seat_geography_not_model_eligibility',
              'records': rows, 'summary': summary,
              'interpretation': 'bounds concern electoral population under preserved joint constraints, not voters, turnout or candidate ballots'}
    manifest = {'schemaVersion': 1, 'stage': 25, 'phase': 'geography',
                'inputSha256': {path: digest(path) for path in INPUTS},
                'sourceProtection': 'both crosswalk manifests verify consumed raw and code bytes',
                'outputSha256': sha256(encode(result)).hexdigest()}
    return result, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    geography, manifest = build()
    write_or_check('geography.json', geography, args.check)
    write_or_check('geography-manifest.json', manifest, args.check)
    print(geography['summary'])


if __name__ == '__main__':
    main()
