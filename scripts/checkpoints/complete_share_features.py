"""Stage 20 outcome-blind Stage 11/18 party-category feature joins."""

from collections import Counter, defaultdict
from fractions import Fraction

from scripts.transform.historical import key


SOURCE_YEARS = (2008, 2014, 2020)
TARGET_YEARS = (2011, 2017, 2023)


def unique(rows, field):
    indexed = {row[field]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f'Duplicate {field}')
    return indexed


def continuity_index(rows):
    indexed = {}
    for row in rows:
        target = row.get('target')
        if target is None:
            continue
        lookup = (row['sourceYear'], row['targetYear'], target['sourceKey'])
        if lookup in indexed:
            raise ValueError('Ambiguous cross-election party category')
        indexed[lookup] = row
    return indexed


def source_rows(matrix, seat):
    rows = unique([{'partyKey': key(row['partyLabel']), **row}
                   for row in matrix['rows'][:-1]], 'partyKey')
    parties = unique(seat['parties'], 'partyKey')
    expected = set(parties) | {'informalpartyvotes'}
    if set(rows) != expected:
        raise ValueError('Incomplete source split party-row population')
    for party, result in parties.items():
        if rows[party]['totalPartyVotes'] != result['votes']:
            raise ValueError('Source split row and party votes disagree')
    if rows['informalpartyvotes']['totalPartyVotes'] != seat['partyBallot']['informalVotes']:
        raise ValueError('Source split informal row disagrees with ballot')
    return rows


def coupled_cell_percent(row, candidate_id):
    """Feasible selected-cell range under *all* rounded row cells summing to 100."""
    cells = row['cells']
    matching = [i for i, cell in enumerate(cells)
                if cell['category'] == 'candidate' and cell['candidateId'] == candidate_id]
    if len(matching) != 1:
        raise ValueError('Missing or ambiguous source candidate destination')
    bounds = []
    for cell in cells:
        value = cell['reportedPercent']
        if value is None:
            raise ValueError('Missing rounded source cell')
        printed = Fraction(str(value))
        if not 0 <= printed <= 100:
            raise ValueError('Source percentage outside 0–100')
        bounds.append((max(Fraction(0), printed - Fraction(1, 200)),
                       min(Fraction(100), printed + Fraction(1, 200))))
    if sum(low for low, _ in bounds) > 100 or sum(high for _, high in bounds) < 100:
        raise ValueError('Rounded source row has no coupled feasible allocation')
    i = matching[0]
    low = max(bounds[i][0], 100 - sum(high for j, (_, high) in enumerate(bounds) if j != i))
    high = min(bounds[i][1], 100 - sum(low for j, (low, _) in enumerate(bounds) if j != i))
    if low > high:
        raise ValueError('Selected cell has no coupled feasible allocation')
    return cells[i]['reportedPercent'], low, high


def coupled_row_witness(row, candidate_id, endpoint):
    """Complete an exact rounded row at one selected cell's feasible endpoint."""
    if endpoint not in ('lower', 'upper'):
        raise ValueError('Unknown rounding endpoint')
    _, low, high = coupled_cell_percent(row, candidate_id)
    cells = row['cells']
    selected = next(i for i, cell in enumerate(cells)
                    if cell['category'] == 'candidate' and cell['candidateId'] == candidate_id)
    bounds = [(max(Fraction(0), Fraction(str(cell['reportedPercent'])) - Fraction(1, 200)),
               min(Fraction(100), Fraction(str(cell['reportedPercent'])) + Fraction(1, 200)))
              for cell in cells]
    witness = [part[0] for part in bounds]
    witness[selected] = low if endpoint == 'lower' else high
    remaining = 100 - sum(witness)
    for i, (_, cap) in enumerate(bounds):
        if i == selected:
            continue
        add = min(remaining, cap - witness[i])
        witness[i] += add
        remaining -= add
    if remaining or sum(witness) != 100 or any(
            not lower <= value <= upper for value, (lower, upper) in zip(witness, bounds)):
        raise ValueError('Cannot complete coupled rounding witness')
    return witness


def _feature(candidate, source_seat, target_seat, source_rows, matrix,
             continuity, source_year, target_year):
    party = candidate['partyKey']
    result = {'targetOccurrenceId': candidate['candidateOccurrenceId'],
              'targetPartyKey': party, 'mappingStatus': candidate['mappingStatus'],
              'sourcePartyKey': None, 'sourceCandidateId': None,
              'sourcePartyRowMass': None, 'sourceMatrixId': matrix['id'],
              'splitSourceIds': matrix['sourceIds'],
              'reportedSamePartyPercent': None, 'coupledSamePartyPercent': None,
              's0Reported': None, 's0CoupledBounds': None, 'v0': None,
              'sourceCandidateShare': None, 'sourcePartyShare': None,
              'sourceCandidateVotes': None, 'sourceValidCandidateVotes': None,
              'sourcePartyVotes': None, 'sourceValidPartyVotes': None,
              'sEvidenceTier': 'unavailable', 'vEvidenceTier': 'unavailable',
              'fallbackReasons': [],
              'sourceFactTiming': 'source_election_result_before_target_election',
              'sourcePublicationByTargetNominationCutoff': 'unknown',
              'sourceRetrievalTiming': 'retrospective_registered_source',
              'targetPartyInputTiming': 'observed_after_target_result_conditional_only'}
    if candidate['noRegisteredPartyGroup']:
        result['targetPartySupport'] = 0
        result['fallbackReasons'].append('affirmative_no_party_group')
        return result
    parties = unique(target_seat['parties'], 'partyKey')
    if party not in parties or target_seat['validPartyVotes'] <= 0:
        raise ValueError('Incomplete target party support')
    result['targetPartySupport'] = parties[party]['votes'] / target_seat['validPartyVotes']
    record = continuity.get((source_year, target_year, party))
    if record is None:
        result['fallbackReasons'].append('no_supported_cross_election_party_continuity')
        return result
    if record['status'] == 'entrant':
        result['fallbackReasons'].append('documented_party_category_entry')
        return result
    if record['status'] != 'eligible' or not record['source']:
        raise ValueError('Ambiguous target party continuity')
    source_party = record['source']['sourceKey']
    result['sourcePartyKey'] = source_party
    source_parties = unique(source_seat['parties'], 'partyKey')
    if source_party not in source_parties:
        raise ValueError('Continuing party missing source party result')
    if source_party not in source_rows:
        raise ValueError('Continuing party missing source split row')
    source_row = source_rows[source_party]
    result['sourcePartyRowMass'] = source_row['totalPartyVotes']
    result['sourcePartyVotes'] = source_parties[source_party]['votes']
    result['sourceValidPartyVotes'] = source_seat['validPartyVotes']
    if source_row['totalPartyVotes'] != source_parties[source_party]['votes']:
        raise ValueError('Source split row and party votes disagree')
    prior = [row for row in source_seat['candidates']
             if row['partyKey'] == source_party]
    if len(prior) > 1:
        raise ValueError('Ambiguous source same-party candidate destination')
    if not prior:
        result['fallbackReasons'].append('source_party_without_candidate_destination')
        return result
    source_candidate = prior[0]
    result['sourceCandidateId'] = source_candidate['id']
    if source_seat['validCandidateVotes'] <= 0 or source_seat['validPartyVotes'] <= 0:
        raise ValueError('Source valid-vote denominator unavailable')
    c0 = source_candidate['votes'] / source_seat['validCandidateVotes']
    p0 = source_parties[source_party]['votes'] / source_seat['validPartyVotes']
    result.update({'sourceCandidateShare': c0, 'sourcePartyShare': p0, 'v0': c0 - p0,
                   'sourceCandidateVotes': source_candidate['votes'],
                   'sourceValidCandidateVotes': source_seat['validCandidateVotes'],
                   'vEvidenceTier': 'official_source_candidate_and_party_totals_distinct_denominators'})
    if source_row['totalPartyVotes'] == 0:
        result['fallbackReasons'].append('zero_mass_source_party_row_s_unavailable')
        return result
    printed, low, high = coupled_cell_percent(source_row, source_candidate['id'])
    result.update({'reportedSamePartyPercent': printed,
                   'coupledSamePartyPercent': [str(low), str(high)],
                   's0Reported': printed / 100,
                   's0CoupledBounds': [float(low / 100), float(high / 100)],
                   'sEvidenceTier': 'official_source_local_party_row_rounded_candidate_destination'})
    return result


def build_feature_inventory(frame, mapping, elections, splits, continuity_rows):
    """Return all fixed contests without reading target candidate outcomes."""
    if len(frame['records']) != 213 or len(mapping['frame']) != 213:
        raise ValueError('Changed fixed 213-contest frame')
    mapped = unique(mapping['frame'], 'targetElectorateId')
    party_continuity = continuity_index(continuity_rows)
    seats = {year: unique(elections[year]['electorates'], 'id')
             for year in (*SOURCE_YEARS, *TARGET_YEARS)}
    matrices = {year: unique(splits[year]['matrices'], 'electorateId')
                for year in SOURCE_YEARS}
    output = []
    for item in frame['records']:
        year, target_id = item['targetYear'], item['targetElectorateId']
        source_year, source_id = item['sourceYear'], item['sourceElectorateId']
        classified = mapped[target_id]
        if classified['targetYear'] != year or classified['sourceYear'] != source_year:
            raise ValueError('Frame and mapping transition mismatch')
        row = {'sourceYear': source_year, 'targetYear': year,
               'sourceElectorateId': source_id, 'targetElectorateId': target_id,
               'scope': item['scope'], 'boundaryRegime': item['boundaryRegime'],
               'candidateCount': classified['candidateCount'],
               'targetOccurrenceIds': item['targetOccurrenceIds'],
               'sourceMatrixId': item['sourceLocalSplitMatrixId'],
               'sourceElectionSourceIds': (seats[source_year][source_id]['sourceIds']
                                            if item['scope'] == 'general' else []),
               'targetElectionSourceIds': (seats[year][target_id]['sourceIds']
                                            if item['scope'] == 'general' else []),
               'status': None, 'reason': None, 'candidates': []}
        if item['scope'] != 'general':
            row.update(status='coverage_only', reason='maori_source_local_split_unavailable')
        elif item['contestStatus'] != 'held_both' or classified['status'] == 'cancelled_or_unheld':
            row.update(status='abstained', reason='cancelled_or_unheld')
        elif classified['status'] != 'complete':
            row.update(status='abstained', reason='stage18_ambiguous_mapping')
        elif (source_year, year) not in ((2008, 2011), (2014, 2017), (2020, 2023)):
            row.update(status='abstained', reason='changed_boundary')
        else:
            source = seats[source_year][source_id]
            target = seats[year][target_id]
            matrix = matrices[source_year].get(source_id)
            if matrix is None or matrix.get('behaviouralEvidence') is False:
                row.update(status='abstained', reason='missing_or_nonbehavioural_source_matrix')
            elif matrix['id'] != item['sourceLocalSplitMatrixId']:
                raise ValueError('Source matrix does not match fixed frame')
            else:
                try:
                    party_rows = source_rows(matrix, source)
                    candidates = [_feature(c, source, target, party_rows, matrix,
                                           party_continuity, source_year, year)
                                  for c in classified['candidates']]
                    if [c['targetOccurrenceId'] for c in candidates] != item['targetOccurrenceIds']:
                        raise ValueError('Changed fixed candidate slate')
                except ValueError as exc:
                    reason = str(exc)
                    if reason in ('Continuing party missing source split row',
                                  'Incomplete source split party-row population',
                                  'Ambiguous target party continuity',
                                  'Ambiguous source same-party candidate destination',
                                  'Incomplete target party support'):
                        row.update(status='abstained', reason=reason)
                    else:
                        raise
                else:
                    row.update(status='constructed', candidates=candidates)
        output.append(row)
    return {'schemaVersion': 1, 'stage': 20,
            'role': 'preserved_source_feature_applicability_no_fit_or_target_outcomes',
            'informationSet': 'retrospective_slate_and_observed_target_local_party',
            'records': output,
            'summary': summarize(output)}


def summarize(records):
    by_year = defaultdict(list)
    for row in records:
        by_year[row['targetYear']].append(row)
    result = {}
    for year, group in sorted(by_year.items()):
        candidates = [c for row in group if row['status'] == 'constructed'
                      for c in row['candidates']]
        result[str(year)] = {
            'frameContests': len(group),
            'constructedContests': sum(row['status'] == 'constructed' for row in group),
            'constructedCandidates': len(candidates),
            'withS': sum(c['s0Reported'] is not None for c in candidates),
            'withV': sum(c['v0'] is not None for c in candidates),
            'withBoth': sum(c['s0Reported'] is not None and c['v0'] is not None
                            for c in candidates),
            'contestsWithS': sum(any(c['s0Reported'] is not None for c in row['candidates'])
                                 for row in group if row['status'] == 'constructed'),
            'statusReasons': dict(sorted(Counter(row['reason'] or row['status']
                                                 for row in group).items())),
            'fallbackReasons': dict(sorted(Counter(reason for c in candidates
                                                   for reason in c['fallbackReasons']).items())),
            'featurePartyCounts': dict(sorted(Counter(c['targetPartyKey'] for c in candidates
                                                      if c['s0Reported'] is not None).items())),
            'mappingStatusCounts': dict(sorted(Counter(c['mappingStatus'] for c in candidates).items())),
            'sEvidenceTierCounts': dict(sorted(Counter(c['sEvidenceTier'] for c in candidates).items())),
            'vEvidenceTierCounts': dict(sorted(Counter(c['vEvidenceTier'] for c in candidates).items())),
            'partyCategoryCoverage': [
                {'partyKey': party, 'candidates': len(members),
                 'withS': sum(c['s0Reported'] is not None for c in members),
                 'withV': sum(c['v0'] is not None for c in members),
                 'fallbackReasons': dict(sorted(Counter(reason for c in members
                                                        for reason in c['fallbackReasons']).items()))}
                for party, members in ((party, [c for c in candidates
                                                if c['targetPartyKey'] == party])
                                       for party in sorted(
                                           {c['targetPartyKey'] for c in candidates},
                                           key=lambda value: '' if value is None else value))]}
    return result
