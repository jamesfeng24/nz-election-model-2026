"""Chronological split-component prediction with explicit rounding and missing mass."""

from collections import Counter, defaultdict
from fractions import Fraction
from math import sqrt

from scripts.models.historical_split_ticket.evidence import YEARS, UNCHANGED
from scripts.transform.historical import key
from scripts.transform.split_intervals import add_intervals, envelope


def _party_map(continuity):
    return {(row['sourceYear'], row['targetYear'], row['target']['sourceKey']):
            row['source']['sourceKey'] for row in continuity if row['status'] == 'eligible'}


def _source_to_target(continuity):
    return {(row['sourceYear'], row['targetYear'], row['source']['sourceKey']):
            row['target']['sourceKey'] for row in continuity if row['status'] == 'eligible'}


def _rows(matrix):
    return {key(row['partyLabel']): row for row in matrix['rows'][:-1]}


def _candidate_cell(row, candidate_id):
    cells = [cell for cell in row['cells'] if cell['candidateId'] == candidate_id]
    if len(cells) != 1 or cells[0]['category'] != 'candidate':
        raise ValueError('Missing or ambiguous candidate destination cell')
    return cells[0]


def _pool(election, split):
    """Source-year general origin/destination pattern; no target information."""
    seats = {seat['id']: seat for seat in election['electorates']}
    totals = Counter()
    cells = defaultdict(list)
    for matrix in split['matrices']:
        if matrix.get('behaviouralEvidence') is False:
            continue
        candidates = {row['id']: row for row in seats[matrix['electorateId']]['candidates']}
        for row in matrix['rows'][:-1]:
            origin, n = key(row['partyLabel']), row['totalPartyVotes']
            if n == 0:
                continue
            totals[origin] += n
            for cell in row['cells']:
                if cell['category'] == 'candidate':
                    cells[origin, candidates[cell['candidateId']]['partyKey']].append(
                        envelope(n, cell['reportedPercent']))
    return {pair: tuple(value / totals[pair[0]] for value in add_intervals(intervals))
            for pair, intervals in cells.items() if totals[pair[0]]}


def _multiply(interval, n):
    return tuple(value * n for value in interval)


def _error(predicted, actual):
    low = max(Fraction(0), actual[0] - predicted[1], predicted[0] - actual[1])
    high = max(abs(predicted[0] - actual[1]), abs(predicted[1] - actual[0]))
    return low, high, predicted[0] - actual[1], predicted[1] - actual[0]


def _score(records, model):
    if not records:
        return None
    abs_low, abs_high, sq_low, sq_high = [], [], [], []
    bias_low, bias_high = [], []
    for record in records:
        pred = record[model]
        actual = record['actualMatchedVotes']
        a, b, c, d = _error(pred, actual)
        scale = Fraction(100, record['targetPartyBallots'])
        a, b, c, d = (value * scale for value in (a, b, c, d))
        abs_low.append(a)
        abs_high.append(b)
        sq_low.append(a * a)
        sq_high.append(b * b)
        bias_low.append(c)
        bias_high.append(d)
    n = len(records)
    return {'n': n, 'maeLowerPP': float(sum(abs_low) / n),
            'maeUpperPP': float(sum(abs_high) / n),
            'rmseLowerPP': sqrt(float(sum(sq_low) / n)),
            'rmseUpperPP': sqrt(float(sum(sq_high) / n)),
            'biasLowerPP': float(sum(bias_low) / n),
            'biasUpperPP': float(sum(bias_high) / n)}


def _candidate_prediction(row, source, target, source_matrix, target_matrix,
                          party_map, pooled):
    source_candidates = {candidate['id']: candidate for candidate in source['candidates']}
    target_candidates = {candidate['id']: candidate for candidate in target['candidates']}
    candidate = target_candidates[row['targetOccurrenceId']]
    source_ids = row['sourceCandidateIds']
    if len(source_ids) != 1 or source_candidates[source_ids[0]]['partyKey'] != row['sourcePartyKey']:
        raise ValueError('Ambiguous source candidate party destination')
    source_rows, target_rows = _rows(source_matrix), _rows(target_matrix)
    if sum(r['totalPartyVotes'] for r in target_rows.values()) != (
            target['validPartyVotes'] + target['partyBallot']['informalVotes']):
        raise ValueError('Target party ballot accounting changed')
    intervals = {model: [] for model in ('local', 'pooled', 'partyOnly', 'actual')}
    missing = 0
    matched = 0
    matched_rows = []
    for target_party, target_row in sorted(target_rows.items()):
        source_party = (target_party if target_party == 'informalpartyvotes' else
                        party_map.get((row['sourceYear'], row['targetYear'], target_party)))
        source_row = source_rows.get(source_party)
        n = target_row['totalPartyVotes']
        if n == 0:
            continue
        if source_row is None:
            missing += n
            continue
        matched += n
        matched_rows.append(target_party)
        source_cell = _candidate_cell(source_row, source_ids[0])
        actual_cell = _candidate_cell(target_row, candidate['id'])
        intervals['local'].append(envelope(n, source_cell['reportedPercent']))
        intervals['actual'].append(envelope(n, actual_cell['reportedPercent']))
        intervals['partyOnly'].append((Fraction(n if source_party == row['sourcePartyKey'] else 0),) * 2)
        intervals['pooled'].append(_multiply(
            pooled.get((source_party, row['sourcePartyKey']), (Fraction(0), Fraction(0))), n))
    if not matched:
        raise ValueError('Eligible candidate has no matched party-ballot group')
    result = {model: add_intervals(values) for model, values in intervals.items()}
    total = matched + missing
    observed = candidate['votes']
    full = (result['local'][0], result['local'][1] + missing)
    return {'targetOccurrenceId': candidate['id'], 'sourceCandidateId': source_ids[0],
            'sourceYear': row['sourceYear'], 'targetYear': row['targetYear'],
            'electorateName': row['electorateName'], 'partyKey': candidate['partyKey'],
            'candidateMapping': row['candidateMapping'], 'sourceMatrixId': source_matrix['id'],
            'targetMatrixId': target_matrix['id'], 'matchedTargetPartyRows': matched_rows,
            'matchedPartyBallots': matched, 'unallocatedPartyBallots': missing,
            'targetPartyBallots': total, 'observedCandidateVotes': observed,
            'observedValidCandidateVotes': target['validCandidateVotes'],
            'localMatchedVotes': result['local'], 'pooledMatchedVotes': result['pooled'],
            'partyOnlyMatchedVotes': result['partyOnly'],
            'actualMatchedVotes': result['actual'],
            'fullCandidateVoteBounds': full,
            'publishedCandidateShareBoundsEvaluationOnly':
                tuple(float(value / target['validCandidateVotes']) for value in full),
            'fullBoundsContainObservedCandidateVotes': full[0] <= observed <= full[1]}


def _joint_accounting(selected, by_name, matrix, continuity):
    """Keep unavailable party groups and absent destinations outside predictions."""
    source_to_target = _source_to_target(continuity)
    target_to_source = _party_map(continuity)
    groups = {(row['sourceYear'], row['targetYear'], row['electorateName'])
              for row in selected}
    result = []
    for source_year, target_year, name in sorted(groups):
        source = by_name[source_year][('general', name)]
        target = by_name[target_year][('general', name)]
        source_matrix = matrix[source_year][source['id']]
        source_rows = _rows(source_matrix)
        source_candidates = {candidate['id']: candidate for candidate in source['candidates']}
        target_parties = Counter(candidate['partyKey'] for candidate in target['candidates'])
        counts = {'targetCandidate': [], 'absentTargetDestination': [],
                  'nonCandidate': []}
        unmatched = 0
        matched = 0
        for party in target['parties'] + [{'partyKey': 'informalpartyvotes',
                                           'votes': target['partyBallot']['informalVotes']}]:
            target_key, n = party['partyKey'], party['votes']
            if n == 0:
                continue
            source_key = (target_key if target_key == 'informalpartyvotes' else
                          target_to_source.get((source_year, target_year, target_key)))
            row = source_rows.get(source_key)
            if row is None:
                unmatched += n
                continue
            matched += n
            for cell in row['cells']:
                if cell['category'] != 'candidate':
                    category = 'nonCandidate'
                else:
                    source_party = source_candidates[cell['candidateId']]['partyKey']
                    target_party = source_to_target.get((source_year, target_year, source_party))
                    category = ('targetCandidate' if target_parties[target_party] == 1 else
                                'absentTargetDestination')
                counts[category].append(envelope(n, cell['reportedPercent']))
        intervals = {category: add_intervals(values) for category, values in counts.items()}
        accounted = add_intervals(intervals.values())
        if not accounted[0] <= matched <= accounted[1]:
            raise ValueError('Local rounded joint mass does not enclose matched ballots')
        result.append({'sourceYear': source_year, 'targetYear': target_year,
                       'electorateName': name, 'matchedPartyBallots': matched,
                       'unmatchedPartyBallots': unmatched,
                       'targetPartyBallots': matched + unmatched,
                       'matchedCandidateMassBounds': tuple(float(x) for x in intervals['targetCandidate']),
                       'absentTargetDestinationMassBounds': tuple(float(x) for x in intervals['absentTargetDestination']),
                       'nonCandidateMassBounds': tuple(float(x) for x in intervals['nonCandidate']),
                       'roundingEnclosure': tuple(float(x) for x in accounted)})
    return result


def analyze(applicability, elections, splits, continuity):
    """Predict with source elections only; target joint cells evaluate afterward."""
    party_map = _party_map(continuity)
    by_seat = {year: {seat['id']: seat for seat in elections[year]['electorates']}
               for year in YEARS}
    by_name = {year: {(seat['kind'], seat['name']): seat for seat in elections[year]['electorates']}
               for year in YEARS}
    matrix = {year: {row['electorateId']: row for row in splits[year]['matrices']}
              for year in YEARS}
    pools = {year: _pool(elections[year], splits[year]) for year in (2008, 2014, 2020)}
    result = []
    for row in applicability['records']:
        if not row['conditionalPartialApplicability']:
            continue
        source_year, target_year = row['sourceYear'], row['targetYear']
        if (source_year, target_year) not in UNCHANGED:
            raise ValueError('Changed-boundary row entered split evaluation')
        source = by_name[source_year][('general', row['electorateName'])]
        target = by_name[target_year][('general', row['electorateName'])]
        result.append(_candidate_prediction(row, source, target,
                      matrix[source_year][source['id']], matrix[target_year][target['id']],
                      party_map, pools[source_year]))
    counts = Counter((row['sourceYear'], row['targetYear'], row['candidateMapping']) for row in result)
    joint = _joint_accounting(result, by_name, matrix, continuity)
    scores = []
    for source_year, target_year in sorted(UNCHANGED):
        selected = [row for row in result if row['sourceYear'] == source_year]
        by_party = Counter(row['partyKey'] for row in selected)
        party_scores = [{'partyKey': party, 'n': n,
                         'local': _score([row for row in selected if row['partyKey'] == party], 'localMatchedVotes') if n >= 5 else None,
                         'pooled': _score([row for row in selected if row['partyKey'] == party], 'pooledMatchedVotes') if n >= 5 else None,
                         'partyOnly': _score([row for row in selected if row['partyKey'] == party], 'partyOnlyMatchedVotes') if n >= 5 else None}
                        for party, n in sorted(by_party.items())]
        mapping_scores = [{'candidateMapping': mapping, 'n': len(group),
                           'local': _score(group, 'localMatchedVotes'),
                           'pooled': _score(group, 'pooledMatchedVotes'),
                           'partyOnly': _score(group, 'partyOnlyMatchedVotes')}
                          for mapping in sorted({row['candidateMapping'] for row in selected})
                          for group in [[row for row in selected if row['candidateMapping'] == mapping]]]
        scores.append({'sourceYear': source_year, 'targetYear': target_year,
                       'candidates': len(selected),
                       'probableContinuations': sum(row['candidateMapping'].startswith('probable') for row in selected),
                       'unresolvedSamePartyPredecessors': sum(row['candidateMapping'].startswith('unresolved') for row in selected),
                       'partyCounts': dict(sorted(by_party.items())),
                       'partyScoresAtLeastFive': party_scores,
                       'candidateMappingScores': mapping_scores,
                       'unallocatedPartyBallots': sum(row['unallocatedPartyBallots'] for row in selected),
                       'medianUnallocatedFraction': sorted(row['unallocatedPartyBallots'] / row['targetPartyBallots'] for row in selected)[len(selected)//2] if selected else None,
                       'fullBoundsContainObserved': sum(row['fullBoundsContainObservedCandidateVotes'] for row in selected),
                       'local': _score(selected, 'localMatchedVotes'),
                       'pooled': _score(selected, 'pooledMatchedVotes'),
                       'partyOnly': _score(selected, 'partyOnlyMatchedVotes')})
    return {'schemaVersion': 1, 'records': result,
            'jointAccounting': joint,
            'transitionScores': scores,
            'candidateMappingCounts': [{'sourceYear': a, 'targetYear': b,
                                        'candidateMapping': mapping, 'count': n}
                                       for (a, b, mapping), n in sorted(counts.items())],
            'interpretation': 'Scores concern matched party-ballot components only; full candidate vote intervals retain unmatched mass. These are conditional diagnostics using observed target party ballots, not pre-election forecasts.'}
