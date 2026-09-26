"""Build source-year origin pools without target outcomes or identity claims."""

from collections import Counter, defaultdict
from math import isfinite

from scripts.models.conditional_candidate_ledger.geometry import PROB_TOL, LedgerGeometryError
from scripts.transform.historical import key


INFORMAL_ORIGIN = 'informalpartyvotes'
INFORMAL_DESTINATION = 'informal_candidate'
PARTY_ONLY_DESTINATION = 'party_vote_only'
DISALLOWED_DESTINATION = 'candidate_disallowed_other'
NONCANDIDATE_DESTINATIONS = (INFORMAL_DESTINATION, PARTY_ONLY_DESTINATION,
                             DISALLOWED_DESTINATION)


def cell_bounds(reported):
    if reported is None or not isfinite(reported) or not 0 <= reported <= 100:
        raise LedgerGeometryError('Missing or invalid positive-row split percentage')
    return [max(0.0, (reported - 0.005) / 100),
            min(1.0, (reported + 0.005) / 100)]


def row_cells(row, candidates):
    cells = []
    seen_candidates = set()
    noncandidate = Counter()
    for cell in row['cells']:
        category = cell['category']
        if category == 'candidate':
            cid = cell['candidateId']
            if cid not in candidates or cid in seen_candidates:
                raise LedgerGeometryError('Missing or duplicate source candidate cell')
            seen_candidates.add(cid)
            party = candidates[cid]['partyKey']
            destination = ('unmapped_independent' if party == 'independent'
                           else f'party:{party}')
        elif category == 'informal':
            noncandidate[category] += 1
            destination = INFORMAL_DESTINATION
        elif category == 'party-vote-only':
            noncandidate[category] += 1
            destination = PARTY_ONLY_DESTINATION
        else:
            raise LedgerGeometryError('Unknown source destination category')
        cells.append({'category': destination, 'candidateId': cell['candidateId'],
                      'publishedCategory': category,
                      'reportedPercent': cell['reportedPercent'],
                      'bounds': cell_bounds(cell['reportedPercent'])})
    if (seen_candidates != set(candidates) or noncandidate !=
            Counter({'informal': 1, 'party-vote-only': 1})):
        raise LedgerGeometryError('Incomplete source candidate/noncandidate columns')
    if (sum(cell['bounds'][0] for cell in cells) > 1 + PROB_TOL or
            sum(cell['bounds'][1] for cell in cells) < 1 - PROB_TOL):
        raise LedgerGeometryError('Source rounded cells cannot sum to one')
    return cells


def build_source_pools(year, election, split):
    """Include every complete positive held general source origin row."""
    seats = {seat['id']: seat for seat in election['electorates']
             if seat['kind'] == 'general'}
    matrices = split['matrices']
    if len({matrix['electorateId'] for matrix in matrices}) != len(matrices):
        raise LedgerGeometryError('Duplicate source matrix electorate')
    if {matrix['electorateId'] for matrix in matrices} != set(seats):
        raise LedgerGeometryError('Missing or extra general source matrix')
    pools = defaultdict(list)
    exclusions = []
    for matrix in sorted(matrices, key=lambda item: item['electorateId']):
        seat = seats[matrix['electorateId']]
        if matrix['year'] != year:
            raise LedgerGeometryError('Wrong source election for split matrix')
        if matrix.get('behaviouralEvidence') is False:
            exclusions.append({'matrixId': matrix['id'], 'reason': 'cancelled_nonbehavioural_matrix'})
            continue
        candidates = {candidate['id']: candidate for candidate in seat['candidates']}
        by_party = {party['partyKey']: party['votes'] for party in seat['parties']}
        by_party[INFORMAL_ORIGIN] = seat['partyBallot']['informalVotes']
        seen_origins = set()
        for row in matrix['rows'][:-1]:
            origin = key(row['partyLabel'])
            if origin in seen_origins:
                raise LedgerGeometryError('Duplicate source origin row')
            seen_origins.add(origin)
            mass = row['totalPartyVotes']
            if origin not in by_party or mass != by_party[origin] or mass < 0:
                exclusions.append({'matrixId': matrix['id'], 'origin': origin,
                                   'mass': mass, 'reason': 'source_origin_count_mismatch'})
                continue
            if mass == 0:
                exclusions.append({'matrixId': matrix['id'], 'origin': origin,
                                   'mass': 0, 'reason': 'zero_mass_origin'})
                continue
            try:
                cells = row_cells(row, candidates)
            except LedgerGeometryError as error:
                exclusions.append({'matrixId': matrix['id'], 'origin': origin,
                                   'mass': mass, 'reason': str(error)})
                continue
            pools[origin].append({'matrixId': matrix['id'],
                                  'sourceIds': matrix['sourceIds'], 'mass': mass,
                                  'cells': cells})
        missing = set(by_party) - seen_origins
        for origin in sorted(missing):
            exclusions.append({'matrixId': matrix['id'], 'origin': origin,
                               'mass': by_party[origin], 'reason': 'missing_source_origin_row'})
    result = {}
    for origin, rows in sorted(pools.items()):
        support = sorted({cell['category'] for row in rows for cell in row['cells']
                          if cell['category'].startswith('party:')})
        result[origin] = {'id': f'{year}:{origin}', 'sourceYear': year,
                          'totalMass': sum(row['mass'] for row in rows),
                          'includedRows': len(rows), 'supportedDestinations': support,
                          'rows': rows}
    return {'sourceYear': year, 'pools': result,
            'exclusions': exclusions,
            'summary': {'heldMatrices': len(matrices) - sum(
                item['reason'] == 'cancelled_nonbehavioural_matrix' for item in exclusions),
                        'includedRows': sum(len(pool['rows']) for pool in result.values()),
                        'includedMass': sum(pool['totalMass'] for pool in result.values()),
                        'excludedRowsByReason': dict(sorted(Counter(
                            item['reason'] for item in exclusions).items())),
                        'excludedKnownMass': sum(item.get('mass', 0) for item in exclusions)}}
