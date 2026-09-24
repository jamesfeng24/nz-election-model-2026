"""Stage 5 party-input sensitivity; conditional on observed target turnout."""

from collections import Counter
from fractions import Fraction

from scripts.models.historical_split_ticket.analysis import (
    _candidate_cell, _party_map, _rows, _score)
from scripts.transform.split_intervals import add_intervals, envelope


def _scale_nonnegative(a, b):
    return a[0] * b[0], a[1] * b[1]


def evaluate(applicability, elections, splits, continuity, backtest):
    """Use Stage 5 predictions only as valid-party group sizes, never fit them here."""
    source_key = _party_map(continuity)
    canonical = {(row['sourceYear'], row['targetYear'], row['target']['sourceKey']):
                 row['canonicalPartyId'] for row in continuity if row['status'] == 'eligible'}
    by_backtest = {(row['sourceYear'], row['targetYear'], row['electorateId'],
                    row['canonicalPartyId']): row for row in backtest}
    by_name = {year: {(seat['kind'], seat['name']): seat for seat in doc['electorates']}
               for year, doc in elections.items()}
    matrices = {year: {matrix['electorateId']: matrix for matrix in doc['matrices']}
                for year, doc in splits.items()}
    records = []
    excluded = Counter()
    for row in applicability['records']:
        if not row['conditionalPartialApplicability']:
            continue
        source_year, target_year = row['sourceYear'], row['targetYear']
        source = by_name[source_year][('general', row['electorateName'])]
        target = by_name[target_year][('general', row['electorateName'])]
        source_rows = _rows(matrices[source_year][source['id']])
        target_rows = _rows(matrices[target_year][target['id']])
        output = {'additive': [], 'proportional': [], 'actual': [], 'observedInput': []}
        valid_party_mass = 0
        missing = False
        for party, target_row in sorted(target_rows.items()):
            if party == 'informalpartyvotes' or target_row['totalPartyVotes'] == 0:
                continue
            mapped = source_key.get((source_year, target_year, party))
            if mapped not in source_rows:
                continue
            stage5 = by_backtest.get((source_year, target_year, target['id'],
                                      canonical.get((source_year, target_year, party))))
            if stage5 is None or not stage5['primary']:
                missing = True
                break
            source_p = envelope(100, _candidate_cell(source_rows[mapped],
                                                      row['sourceCandidateIds'][0])['reportedPercent'])
            probability = (source_p[0] / 100, source_p[1] / 100)
            actual = envelope(target_row['totalPartyVotes'], _candidate_cell(
                target_row, row['targetOccurrenceId'])['reportedPercent'])
            output['actual'].append(actual)
            output['observedInput'].append(envelope(
                target_row['totalPartyVotes'], _candidate_cell(
                    source_rows[mapped], row['sourceCandidateIds'][0])['reportedPercent']))
            valid_party_mass += target_row['totalPartyVotes']
            for formula in ('additive', 'proportional'):
                prediction = stage5['predictions'][formula]
                group = (Fraction(str(prediction['lower'])) * target['validPartyVotes'],
                         Fraction(str(prediction['upper'])) * target['validPartyVotes'])
                output[formula].append(_scale_nonnegative(group, probability))
        if missing or not valid_party_mass:
            excluded['missing_stage5_valid_party_input'] += 1
            continue
        merged = {name: add_intervals(parts) for name, parts in output.items()}
        records.append({'targetOccurrenceId': row['targetOccurrenceId'],
                        'sourceYear': source_year, 'targetYear': target_year,
                        'targetPartyBallots': target['validPartyVotes'] + target['partyBallot']['informalVotes'],
                        'matchedValidPartyBallots': valid_party_mass,
                        'actualMatchedVotes': merged['actual'],
                        'observedInput': merged['observedInput'],
                        'additive': merged['additive'], 'proportional': merged['proportional']})
    scores = []
    for year in (2011, 2017, 2023):
        selected = [row for row in records if row['targetYear'] == year]
        scores.append({'targetYear': year, 'n': len(selected),
                       'observedValidPartyInput': _score(selected, 'observedInput'),
                       'additiveStage5Input': _score(selected, 'additive'),
                       'proportionalStage5Input': _score(selected, 'proportional')})
    return {'schemaVersion': 1, 'scores': scores, 'excluded': dict(excluded),
            'interpretation': 'Stage5 valid-party share predictions use observed target national party support and are scaled by observed target valid-party turnout. Informal-party rows, unmatched groups, target turnout forecasting and candidate denominator remain unresolved. Not a complete pre-election forecast or Stage5 transform selection.'}
