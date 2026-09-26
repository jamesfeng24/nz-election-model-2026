"""Inventory preserved inputs for a future complete candidate baseline; never score votes."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = Path('data/processed/checkpoints/complete-candidate-baseline')
SPEC = BASE / 'specification.json'
CONTRACTS = BASE / 'contracts.json'
COHORT = Path('data/processed/checkpoints/evidence-repair/cohort-inventory.json')
YEARS = (2008, 2011, 2014, 2017, 2020, 2023)
SOURCE_YEARS = (2008, 2014, 2020)
TARGET_YEARS = (2011, 2017, 2023)
INPUTS = (COHORT,) + tuple(Path(f'data/processed/elections/{year}.json') for year in TARGET_YEARS) + tuple(
    Path(f'data/processed/split-votes/{year}.json') for year in SOURCE_YEARS)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def sha(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def unique_by(rows, field):
    indexed = {row[field]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f'Duplicate {field} in preserved input')
    return indexed


def inventory(frame, elections, splits):
    """Use contest IDs and availability only; never read votes or winners."""
    election_seats = {year: unique_by(data['electorates'], 'id')
                      for year, data in elections.items()}
    matrices = {year: {key: row['id'] for key, row in unique_by(data['matrices'], 'electorateId').items()}
                for year, data in splits.items()}
    supporting = {year: {key: row['id'] for key, row in
                         unique_by(data.get('supportingMatrices', []), 'electorateId').items()}
                  for year, data in splits.items()}
    records = []
    for seat in frame:
        source_year, target_year = seat['sourceYear'], seat['targetYear']
        source_ids, target_ids = seat['sourceOccurrenceIds'], seat['targetOccurrenceIds']
        source_electorate_id = f'nz-general-{source_year}-electorate-{seat["sourceElectorateNumber"]:02d}'
        target_electorate_id = target_ids[0].rsplit('-candidate-', 1)[0] if target_ids else None
        if len(source_ids) != len(set(source_ids)) or len(target_ids) != len(set(target_ids)):
            raise ValueError('Duplicate candidate occurrence in contest frame')
        if any(not candidate_id.startswith(source_electorate_id + '-candidate-') for candidate_id in source_ids):
            raise ValueError('Source occurrence/electorate mismatch')
        if target_electorate_id and any(not candidate_id.startswith(target_electorate_id + '-candidate-') for candidate_id in target_ids):
            raise ValueError('Target occurrence/electorate mismatch')
        target = election_seats[target_year].get(target_electorate_id)
        if seat['scope'] == 'general' and target is None:
            raise ValueError('Missing processed general target contest')
        if target is not None:
            recorded_ids = {candidate['id'] for candidate in target['candidates']}
            if set(target_ids) != recorded_ids:
                raise ValueError('Target candidature does not match official processed contest')
        source_matrix_id = matrices[source_year].get(source_electorate_id)
        supporting_matrix_id = supporting[source_year].get(source_electorate_id)
        held = seat['contestStatus'] == 'held_both'
        conditional = held and seat['scope'] == 'general' and bool(source_matrix_id) and target is not None
        records.append({
            'sourceYear': source_year, 'targetYear': target_year, 'scope': seat['scope'],
            'sourceElectorateId': source_electorate_id, 'targetElectorateId': target_electorate_id,
            'sourceSeatLabel': seat['sourceSeatLabel'], 'targetSeatLabel': seat['targetSeatLabel'],
            'boundaryRegime': seat['boundaryRegime'], 'contestStatus': seat['contestStatus'],
            'sourceOccurrenceIds': source_ids, 'targetOccurrenceIds': target_ids,
            'sourceLocalSplitMatrixId': source_matrix_id,
            'sourceSupportingMaoriMatrixId': supporting_matrix_id,
            'targetPublishedPartyGroups': 'observed_processed_post_election' if target else 'raw_source_only_not_assembled',
            'targetPublishedPartyInformalAndTurnout': 'observed_processed_post_election' if target else 'raw_source_only_not_assembled',
            'targetPublishedCandidateTotals': 'evaluation_only_processed' if target else 'evaluation_only_stage7_supporting_observed',
            'targetSplitCells': 'evaluation_only_general' if seat['scope'] == 'general' and held else 'not_comparable',
            'historicalNominationCloseDate': None,
            'nominationPublicationByCutoff': 'unknown',
            'asOfLocalPartyForecast': 'missing',
            'asOfNationalSupportForecast': 'missing',
            'asOfTurnoutAndBallotValidityForecast': 'missing',
            'conditionalObservedInputEligible': conditional,
            'strictPreElectionInputReady': False,
            'limitation': ('cancelled_or_unheld' if not held else
                           'maori_local_split_and_processed_party_group_gap' if seat['scope'] == 'maori' else
                           'as_of_inputs_and_complete_routing_unverified'),
        })
    if len(records) != 213 or len({(row['sourceYear'], row['scope'], row['sourceElectorateId'])
                                    for row in records}) != 213:
        raise ValueError('Changed validated 213-contest frame')
    return {'schemaVersion': 1, 'checkpoint': 'complete-candidate-baseline-specification',
            'selection': 'all validated unchanged-boundary seat-transition clusters; no identity sampling',
            'outcomeFieldsUsed': [], 'records': records,
            'summary': {'frameContests': len(records),
                        'conditionalObservedInputEligible': sum(row['conditionalObservedInputEligible'] for row in records),
                        'strictPreElectionInputReady': 0,
                        'byTransitionScopeStatus': [
                            {'sourceYear': year, 'targetYear': target, 'scope': scope,
                             'status': status, 'n': count}
                            for (year, target, scope, status), count in sorted(Counter(
                                (row['sourceYear'], row['targetYear'], row['scope'], row['contestStatus'])
                                for row in records).items())]}}


def contest_bounds(groups, destinations, candidate_destinations):
    """Synthetic-only simplex bounds for a shared ballot ledger, not a fitted model.

    groups: {group_id: {'mass': nonnegative number, 'routes': {destination: [lo, hi]}}}.
    Missing routes are an error: callers must explicitly allow uncertainty [0,1].
    """
    if (not destinations or not set(candidate_destinations) <= set(destinations)
            or len(candidate_destinations) != len(set(candidate_destinations))):
        raise ValueError('Invalid destination set')
    if len(destinations) != len(set(destinations)):
        raise ValueError('Duplicate ballot destination')
    totals = {destination: [0.0, 0.0] for destination in destinations}
    denominator = [0.0, 0.0]
    mass_total = 0.0
    for group in groups.values():
        mass, routes = group['mass'], group['routes']
        if not isfinite(mass) or mass < 0 or set(routes) != set(destinations):
            raise ValueError('Negative ballot mass or incomplete destination routing')
        if any(len(bounds) != 2 or not all(isfinite(value) for value in bounds)
               or not 0 <= bounds[0] <= bounds[1] <= 1
               for bounds in routes.values()):
            raise ValueError('Invalid routing interval')
        lows = sum(bounds[0] for bounds in routes.values())
        highs = sum(bounds[1] for bounds in routes.values())
        if lows > 1 + 1e-12 or highs < 1 - 1e-12:
            raise ValueError('Routing cannot conserve ballot mass')
        mass_total += mass
        for destination, (low, high) in routes.items():
            totals[destination][0] += mass * max(low, 1 - (highs - high))
            totals[destination][1] += mass * min(high, 1 - (lows - low))
        candidate_low = sum(routes[d][0] for d in candidate_destinations)
        candidate_high = sum(routes[d][1] for d in candidate_destinations)
        other_low = lows - candidate_low
        other_high = highs - candidate_high
        denominator[0] += mass * max(candidate_low, 1 - other_high)
        denominator[1] += mass * min(candidate_high, 1 - other_low)
    return {'ballotMass': mass_total, 'destinationVoteBounds': totals,
            'validCandidateDenominatorBounds': denominator,
            'pointCandidateVotesAvailable': all(abs(low - high) < 1e-12
                                                for d, (low, high) in totals.items()
                                                if d in candidate_destinations)}


def build():
    frame = read(COHORT)['frame']
    elections = {year: read(Path(f'data/processed/elections/{year}.json')) for year in TARGET_YEARS}
    splits = {year: read(Path(f'data/processed/split-votes/{year}.json')) for year in SOURCE_YEARS}
    result = inventory(frame, elections, splits)
    manifest = {'schemaVersion': 1, 'inputSha256': {str(path): sha(path) for path in INPUTS + (SPEC, CONTRACTS)},
                'generatorSha256': sha(Path('scripts/checkpoints/complete_candidate_baseline.py')),
                'inventorySha256': sha256(encode(result)).hexdigest()}
    return result, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result, manifest = build()
    for name, payload in [('input-inventory.json', result), ('manifest.json', manifest)]:
        path = ROOT / BASE / name
        expected = encode(payload)
        if args.check:
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit(f'Changed or missing checkpoint file: {name}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    print(f'Inventoried {result["summary"]["frameContests"]} contests; '
          f'{result["summary"]["conditionalObservedInputEligible"]} have assembled observed party inputs')


if __name__ == '__main__':
    main()
