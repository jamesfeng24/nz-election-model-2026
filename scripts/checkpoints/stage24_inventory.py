"""Freeze Stage22 fit/feature and Stage23 party-input joins before substitution."""
import argparse
from collections import Counter

from scripts.checkpoints.stage24_common import (
    INPUTS, PREFIX, PREFIT, STAGE22, STAGE23, digest, read,
    verify_contract, verify_sources, write_or_check,
)

SCENARIOS = ('printed', 'selected_lower', 'selected_upper')
METHODS = ('baseline', 'baseline_plus_S')


def unique(rows, key, label):
    index = {key(row): row for row in rows}
    if len(index) != len(rows):
        raise ValueError(f'Duplicate {label}')
    return index


def candidate_inputs(feature, mapping, party):
    if feature['targetOccurrenceId'] != mapping['candidateOccurrenceId']:
        raise ValueError('Candidate occurrence mapping mismatch')
    if (feature['targetPartyKey'] != mapping['partyKey'] or
            feature['mappingStatus'] != mapping['mappingStatus'] or
            feature['originalAffiliation'] != mapping['sourceAffiliation']):
        raise ValueError('Stage22 candidate mapping changed')
    group = feature['targetPartyKey']
    if group is None:
        if not feature['mappingStatus'].startswith('verified_no_party_group_') or feature['targetPartySupport'] != 0:
            raise ValueError('No-group status is not affirmative')
        predicted = 0.0
    else:
        if group not in party:
            raise ValueError('Missing target ballot group in Stage23 vector')
        predicted = party[group]
    return {
        'candidateOccurrenceId': feature['targetOccurrenceId'],
        'originalAffiliation': feature['originalAffiliation'],
        'partyBallotGroupKey': group,
        'mappingStatus': feature['mappingStatus'],
        'observedTargetPartySupport': feature['targetPartySupport'],
        'predictedTargetPartySupport': predicted,
        's0Reported': feature['s0Reported'],
        'coupledSamePartyPercent': feature['coupledSamePartyPercent'],
        'sEvidenceTier': feature['sEvidenceTier'],
        'fallbackReasons': feature['fallbackReasons'],
        'sourcePartyRowMass': feature['sourcePartyRowMass'],
    }


def build():
    contract = read(PREFIT + 'amended-fit-contract.json')
    features = unique(read(PREFIT + 'amended-features.json')['records'],
                      lambda row: row['targetElectorateId'], 'feature contest')
    mapped = unique(read(PREFIT + 'amended-mapping.json')['frame'],
                    lambda row: row['targetElectorateId'], 'candidate mapping contest')
    fits = unique(read(STAGE22 + 'fitted-parameters.json')['folds'],
                  lambda row: row['targetYear'], 'fit fold')
    saved = unique(read(STAGE22 + 'predictions.json')['folds'],
                   lambda row: row['targetYear'], 'saved prediction fold')
    party = unique(read(STAGE23 + 'construction.json')['records'],
                   lambda row: (row['targetYear'], row['targetElectorateId']),
                   'party-vector contest')
    if {f['targetYear'] for f in contract['folds']} != {2017, 2023}:
        raise ValueError('Expected exactly two trained holdouts')
    folds = []
    for fold in contract['folds']:
        year = fold['targetYear']
        fit, prediction = fits[year], saved[year]
        ids = fold['commonEvaluationContestIds']
        if (ids != prediction['evaluationContestIds'] or fit['targetYear'] != year or
                fold['commonEvaluationCandidateOccurrenceIds'] != prediction['evaluationCandidateOccurrenceIds']):
            raise ValueError('Stage22 exact common sample changed')
        if set(fit['scenarios']) != set(SCENARIOS) or set(prediction['scenarios']) != set(SCENARIOS):
            raise ValueError('Saved rounding scenarios changed')
        contests = []
        for cid in ids:
            row, mapping, vector = features[cid], mapped[cid], party[year, cid]
            if (row['status'] != 'constructed' or mapping['status'] != 'complete' or
                    vector['applicability'] != 'constructed' or row['targetYear'] != year or
                    vector['scope'] != 'general' or vector['contestStatus'] != 'held_both'):
                raise ValueError('Common contest not supported in all four cells')
            key_to_category = {v: k for k, v in vector['targetPartyGroupKeys'].items()}
            if len(key_to_category) != len(vector['targetPartyGroupKeys']):
                raise ValueError('Duplicate target party group in vector')
            if set(vector['targetPartyGroupKeys']) != set(vector['localPartyShares']):
                raise ValueError('Incomplete Stage23 category vector')
            ballot_shares = {ballot: vector['localPartyShares'][canonical]
                             for ballot, canonical in key_to_category.items()}
            if abs(sum(ballot_shares.values()) - 1) > 1e-12:
                raise ValueError('Stage23 party vector lost mass')
            linked = unique(mapping['candidates'],
                            lambda candidate: candidate['candidateOccurrenceId'],
                            'candidate mapping')
            candidates = []
            seen_groups = set()
            for feature in row['candidates']:
                candidate = candidate_inputs(feature, linked[feature['targetOccurrenceId']], ballot_shares)
                group = candidate['partyBallotGroupKey']
                if group is not None:
                    if group in seen_groups:
                        raise ValueError('Duplicate candidate destination for one party group')
                    seen_groups.add(group)
                candidates.append(candidate)
            occurrence_ids = [c['candidateOccurrenceId'] for c in candidates]
            if (len(set(occurrence_ids)) != len(occurrence_ids) or
                    occurrence_ids != row['targetOccurrenceIds'] or
                    set(occurrence_ids) != set(c['candidateOccurrenceId'] for c in mapping['candidates'])):
                raise ValueError('Candidate slate changed')
            contests.append({'targetElectorateId': cid, 'targetYear': year,
                             'candidateOccurrenceIds': occurrence_ids,
                             'partyBallotGroupShares': dict(sorted(ballot_shares.items())),
                             'candidates': candidates})
        if [c['targetElectorateId'] for c in contests] != ids:
            raise ValueError('Contest order changed')
        if [candidate['candidateOccurrenceId'] for seat in contests for candidate in seat['candidates']] != fold['commonEvaluationCandidateOccurrenceIds']:
            raise ValueError('Candidate order changed')
        scenarios = {}
        for scenario in SCENARIOS:
            block = fit['scenarios'][scenario]
            if set(block['fits']) != {'baseline', 'baseline_plus_S', 'baseline_plus_V', 'baseline_plus_S_plus_V'}:
                raise ValueError('Saved fitted restrictions changed')
            scenarios[scenario] = {
                'trainingOnlyMeans': block['trainingOnlyMeans'],
                'parameters': {method: block['fits'][method] for method in METHODS},
            }
        folds.append({'targetYear': year,
                      'trainingContestIds': fold['trainingContestIds'],
                      'trainingTargetYears': fold['trainingTargetYears'],
                      'commonEvaluationContestIds': ids,
                      'commonEvaluationCandidateOccurrenceIds': fold['commonEvaluationCandidateOccurrenceIds'],
                      'scenarios': scenarios, 'contests': contests})
    summary = [{'targetYear': fold['targetYear'],
                'contests': len(fold['contests']),
                'candidates': sum(len(row['candidates']) for row in fold['contests']),
                'byMappingStatus': dict(sorted(Counter(candidate['mappingStatus']
                    for row in fold['contests'] for candidate in row['candidates']).items())),
                'supportedS': sum(candidate['s0Reported'] is not None
                    for row in fold['contests'] for candidate in row['candidates'])}
               for fold in folds]
    return {'schemaVersion': 1, 'stage': 24,
            'role': 'precalculation_common_input_inventory_no_new_candidate_predictions_or_scores',
            'fullFrameContests': 213,
            'evaluationOnlyActualsPath': STAGE22 + 'actuals.json',
            'folds': folds, 'summary': summary,
            'informationSet': 'observed_target_local_reference_versus_Stage23_conditional_observed_target_national_party_support'}, {
                'schemaVersion': 1, 'stage': 24,
                'inputSha256': {path: digest(path) for path in INPUTS},
                'sourceValidation': 'Stage22_consumed_registry_records_and_raw_bytes_plus_Stage23_pinned_inputs',
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--init-contract', action='store_true')
    args = parser.parse_args()
    inventory, contract = build()
    if args.init_contract:
        verify_sources()
        write_or_check('input-contract.json', contract)
    else:
        verify_contract()
    write_or_check('input-inventory.json', inventory, args.check)
    print(inventory['summary'])


if __name__ == '__main__':
    main()
