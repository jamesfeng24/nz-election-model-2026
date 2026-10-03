"""Exact preserved aggregation inputs; no crossings or response parameters."""
from fractions import Fraction

from scripts.transform.historical import key

PARTIES = ('labourparty', 'nationalparty')


def unique(rows, field):
    values = {row[field]: row for row in rows}
    if len(values) != len(rows):
        raise ValueError(f'Duplicate {field}')
    return values


def election_inputs(election):
    controls = election['nationalControls']
    general = [s for s in election['electorates'] if s['kind'] == 'general']
    unique(general, 'id')
    held = [s for s in general if s['validCandidateVotes'] > 0]
    excluded = [s['id'] for s in general if s not in held]
    total_national = controls['party']['national']['validVotes']
    if (total_national <= 0 or total_national != sum(
            controls['party'][scope]['validVotes'] for scope in ('general', 'maori'))):
        raise ValueError('Incompatible national party population')
    national = unique([{'partyKey': key(r['name']), **r} for r in controls['parties']], 'partyKey')
    if sum(r['partyVotes'] or 0 for r in national.values()) != total_national:
        raise ValueError('Incomplete national valid-party counts')
    if not held or any(s['validPartyVotes'] <= 0 for s in held):
        raise ValueError('Missing held general ballot denominator')
    candidate_denominator = sum(s['validCandidateVotes'] for s in held)
    party_denominator = sum(s['validPartyVotes'] for s in held)
    if candidate_denominator != controls['candidate']['general']['validVotes']:
        raise ValueError('General candidate denominator does not reconcile')
    result = []
    for party in PARTIES:
        candidate_votes = party_votes = 0
        occurrence_ids = []
        for seat in held:
            candidates = [c for c in seat['candidates'] if c['partyKey'] == party]
            parties = [p for p in seat['parties'] if p['partyKey'] == party]
            if len(candidates) != 1 or len(parties) != 1:
                raise ValueError('Incomplete/ambiguous matched general aggregate; never zero-fill')
            candidate_votes += candidates[0]['votes']
            party_votes += parties[0]['votes']
            occurrence_ids.append(candidates[0]['id'])
        c = Fraction(candidate_votes, candidate_denominator)
        p = Fraction(party_votes, party_denominator)
        result.append({'id': f'{election["year"]}:{party}', 'year': election['year'],
            'party': party, 'generalContestIds': [s['id'] for s in held],
            'candidateOccurrenceIds': occurrence_ids, 'excludedGeneralContestIds': excluded,
            'candidateVotes': candidate_votes, 'validCandidateVotes': candidate_denominator,
            'partyVotesMatchedGeneral': party_votes, 'validPartyVotesMatchedGeneral': party_denominator,
            'nationalPartyVotes': national[party]['partyVotes'], 'nationalValidPartyVotes': total_national,
            'nationalSupport': str(Fraction(national[party]['partyVotes'], total_national)),
            'generalCandidateShare': str(c), 'generalPartyShare': str(p), 'generalPremium': str(c-p),
            'reportedAllGeneralValidPartyVotes': controls['party']['general']['validVotes'],
            'partyPopulationOmittedVotes': controls['party']['general']['validVotes']-party_denominator,
            'nationalControlSourceId': national[party]['sourceId'], 'sourceIds': election['sourceIds'],
            'historicalFactYear': election['year'], 'historicalFactDate': None,
            'factDateGranularity': 'completed_election_year; exact_date_not_ingested_here',
            'publicationByForecastCutoff': 'unknown_not_verified',
            'retrievalTiming': 'refer_to_pinned_registry_records_not_historical_availability',
            'interpretation': 'raw_observed_aggregate_input_not_anchor_estimate'})
    return result


def fold_inventory(folds, response_rows, aggregates):
    rows = unique(response_rows, 'id')
    output = []
    for f in folds:
        if f['family'] != 'nat_lab_response':
            continue
        train, evaluation = [rows[i] for i in f['trainingIds']], [rows[i] for i in f['evaluationIds']]
        if set(f['trainingIds']) & set(f['evaluationIds']):
            raise ValueError('Training/holdout overlap')
        if any(r['targetYear'] >= f['targetYear'] or r['targetYear'] > f['sourceYear'] or
               (f['chronologyProtocol'] == 'more_separated' and r['targetYear'] >= f['sourceYear'])
               for r in train):
            raise ValueError('Forbidden target/later response training')
        if any(r['targetYear'] != f['targetYear'] for r in evaluation):
            raise ValueError('Wrong evaluation year')
        for party in PARTIES:
            snapshots = [r for r in aggregates if r['party'] == party and
                         r['year'] < f['targetYear'] and
                         (r['year'] <= f['sourceYear'] if f['chronologyProtocol']=='expanding_window'
                          else r['year'] < f['sourceYear'])]
            tr = [r for r in train if r['party'] == party]
            ev = [r for r in evaluation if r['party'] == party]
            environments = sorted({f'{r["sourceYear"]}-{r["targetYear"]}:{party}' for r in tr})
            count_feasible = len(snapshots) >= 4 and len(environments) >= 4 and len(tr) >= 15
            output.append({'id': f'{f["foldId"]}:{party}', 'stage25FoldId': f['foldId'],
                'protocol': f['chronologyProtocol'], 'party': party, 'sourceYear': f['sourceYear'],
                'targetYear': f['targetYear'], 'permittedAnchorSnapshotIds': [r['id'] for r in snapshots],
                'nationalScenarioInputId': f'{f["targetYear"]}:{party}',
                'anchorSnapshotCount': len(snapshots), 'trainingEnvironmentIds': environments,
                'trainingEnvironmentCount': len(environments), 'trainingIds': [r['id'] for r in tr],
                'evaluationIds': [r['id'] for r in ev], 'trainingCount': len(tr), 'evaluationCount': len(ev),
                'countGatesPotentiallyFeasible': count_feasible,
                'comparisonStatus': 'anchor_and_regime_gates_not_estimated' if count_feasible else 'abstain_count_gate',
                'unassessedGates': ['anchor_crossing_stability', 'two_environments_each_regime',
                                   'regime_nonzero_rows', 'asymmetric_design_rank_condition'],
                'trainingRegimeLabels': None, 'evaluationRegimeLabels': None,
                'historicalForecastPublication': 'unknown', 'wholePartyFoldAbstentionOnGateFailure': True})
    return output
