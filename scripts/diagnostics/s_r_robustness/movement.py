"""Candidate-outcome-independent full-party movement and input-error records."""
import argparse
from scripts.models.complete_party_vector.inventory import evidence
from .common import *
from .alignment import align, total_variation


def shares(seat):
    votes = {k: p['votes'] for k, p in seat['parties'].items()}
    denominator = seat['validVotes']
    if denominator <= 0 or sum(votes.values()) != denominator:
        raise ValueError('Party-vote denominator mismatch')
    expected = {k: v/denominator for k, v in votes.items()}
    if expected != {k: p['share'] for k, p in seat['parties'].items()}:
        raise ValueError('Party counts/share disagreement')
    return expected


def national_record(audit, elections):
    sy, ty = audit['sourceYear'], audit['targetYear']
    a, b = elections[sy], elections[ty]
    source = {k: p['share'] for k, p in a['parties'].items()}
    target = {k: p['share'] for k, p in b['parties'].items()}
    for data in (a, b):
        if sum(p['votes'] for p in data['parties'].values()) != data['nationalValidVotes']:
            raise ValueError('National valid-party denominator mismatch')
    x, y = align(audit['categories'], source, target)
    return {'sourceYear': sy, 'targetYear': ty, 'sourceNationalValidVotes': a['nationalValidVotes'],
        'targetNationalValidVotes': b['nationalValidVotes'], 'sourceAlignedShares': x,
        'targetAlignedShares': y, 'totalVariationFraction': total_variation(x, y),
        'information': 'full_population_observed_target_national_support_conditional_input'}


def contest_record(frame, vector, audit, elections, geography):
    sy, ty = frame['sourceYear'], frame['targetYear']
    if not geography['certifiedTwoSidedExact'] or geography['scope'] != 'general':
        raise ValueError('Nonexact geography cannot enter movement comparison')
    if geography['dominantPredecessorId'] != frame['sourceElectorateId'] or geography['targetElectorateId'] != frame['targetElectorateId']:
        raise ValueError('Unvalidated source/target geographic join')
    source_seats = keyed(list(elections[sy]['scopes']['general'].values()), 'id')
    target_seats = keyed(list(elections[ty]['scopes']['general'].values()), 'id')
    source, target = source_seats[frame['sourceElectorateId']], target_seats[frame['targetElectorateId']]
    if (vector['sourceElectorateId'], vector['sourceYear'], vector['targetYear']) != (source['id'], sy, ty):
        raise ValueError('Constructed vector source ID mismatch')
    cats = audit['categories']
    expected_groups = {c['categoryId']: c['targetPartyKey'] for c in cats if c['relationship'] != 'exit'}
    if vector['targetPartyGroupKeys'] != expected_groups:
        raise ValueError('Constructed vector ballot-group mapping mismatch')
    source_observed, target_observed = shares(source), shares(target)
    source_aligned, constructed_aligned = align(cats, source_observed, vector['localPartyShares'])
    _, actual_aligned = align(cats, source_observed, target_observed)
    errors = {k: 100*(vector['localPartyShares'][k]-v) for k, v in target_observed.items()}
    major = {}
    for key in ('nationalparty', 'labourparty'):
        cid = next((k for k, v in expected_groups.items() if v == key), None)
        major[key] = None if cid is None else {'signedErrorPP': errors[cid], 'absoluteErrorPP': abs(errors[cid])}
    return {'geographyId': frame['geographyId'], 'sourceYear': sy, 'targetYear': ty,
        'sourceElectorateId': source['id'], 'targetElectorateId': target['id'], 'sourceSeatName': source['name'],
        'targetSeatName': target['name'], 'contestStatus': frame['contestStatus'],
        'sourceValidPartyVotes': source['validVotes'], 'targetValidPartyVotesEvaluationOnly': target['validVotes'],
        'status': 'available', 'diagnosticExclusion': None, 'sourceAlignedShares': source_aligned,
        'constructedTargetAlignedShares': constructed_aligned, 'observedTargetAlignedSharesEvaluationOnly': actual_aligned,
        'constructedLocalDistance': total_variation(source_aligned, constructed_aligned),
        'observedLocalDistance': total_variation(source_aligned, actual_aligned),
        'partyInputError': {'completeVectorMaePP': sum(abs(v) for v in errors.values())/len(errors),
            'categories': len(errors), 'byCategorySignedPP': errors, 'majorParty': major},
        'sourcePublicationByCutoff': 'unknown_retrospective', 'candidateOutcomesConsumed': False}


def build(inventory=None, party_inventory=None, vectors=None, elections=None, geography=None):
    inventory = local('inventory.json') if inventory is None else inventory
    party_inventory = read(S31+'input-inventory.json') if party_inventory is None else party_inventory
    vectors = read(S31+'party-vectors.json') if vectors is None else vectors
    elections = evidence()[0] if elections is None else elections
    geography = read(GEO+'geography.json')['records'] if geography is None else geography
    audits = {(r['sourceYear'], r['targetYear']): r for r in inventory['categoryAudit']}
    geos = keyed(geography, 'geographyId'); predicted = keyed(vectors['records'], 'targetElectorateId')
    national = [national_record(a, elections) for a in inventory['categoryAudit']]
    records = []
    for f in party_inventory['partyFrame']:
        base = {k: f[k] for k in ('geographyId', 'sourceYear', 'targetYear', 'targetElectorateId', 'scope', 'contestStatus')}
        if f['partyInputStatus'] != 'available':
            records.append({**base, 'status': 'coverage_only', 'diagnosticExclusion': f['reason']}); continue
        try:
            r = contest_record(f, predicted[f['targetElectorateId']], audits[(f['sourceYear'], f['targetYear'])], elections, geos[f['geographyId']])
        except (ValueError, KeyError) as exc:
            r = {**base, 'status': 'diagnostic_exclusion', 'diagnosticExclusion': str(exc)}
        records.append(r)
    return {'stage': 34, 'national': national, 'records': records,
        'role': 'party_only_movement; observed_local_version_and_party_error_explanatory_only',
        'candidatePerformanceSamplesUnchanged': True, 'operationalSelection': None}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); a = p.parse_args()
    verify_inputs(); result = build(); save('movement.json', result, a.check)
    phase('movement', ['movement.json'], ['movement'], a.check)
    print('Stage34 movement records', len(result['records']), 'available', sum(r['status']=='available' for r in result['records']), 'prior', preserve())


if __name__ == '__main__':
    main()
