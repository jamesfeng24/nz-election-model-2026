"""Reproduce frozen Stage 11 diagnostics on certified-geography applicability."""

from copy import deepcopy
import json
from fractions import Fraction

from scripts.models.historical_split_ticket.analysis import _score, analyze
from scripts.models.historical_split_ticket.correction import certified_pair_for_row
from scripts.models.historical_split_ticket.sensitivity import evaluate


def certified_name_bridge(corrected, elections):
    """Adapt the original name-keyed scorers using certified source/target IDs.

    The returned election documents are copies. An in-memory name alias is
    installed only after resolving both seats through the certified ID fields.
    The original election record and its observed source label stay unchanged.
    """
    view = deepcopy(elections)
    pairs = set()
    for row in corrected['records']:
        if not row['conditionalPartialApplicability']:
            continue
        source, target = certified_pair_for_row(row, elections)
        if source['name'] != target['name']:
            pairs.add((row['sourceYear'], source['id'], target['name']))
    for year, source_id, target_name in sorted(pairs):
        source_view = {seat['id']: seat for seat in view[year]['electorates']}[source_id]
        if any(seat['id'] != source_id and seat['kind'] == 'general' and
               seat['name'] == target_name for seat in view[year]['electorates']):
            raise ValueError('Certified alias collides with another source seat')
        source_view['name'] = target_name
    return view


def _score_by_fold(records):
    output = []
    for year in (2011, 2017, 2023):
        group = [row for row in records if row['targetYear'] == year]
        output.append({'targetYear': year, 'n': len(group),
                       'local': _score(group, 'localMatchedVotes'),
                       'pooled': _score(group, 'pooledMatchedVotes'),
                       'partyOnly': _score(group, 'partyOnlyMatchedVotes')})
    return output


def corrected_diagnostics(original, corrected, elections, splits, continuity,
                          backtest, stage10, original_predictions, original_sensitivity):
    """Apply the original equations and gates; do not tune Stage 11 rules."""
    bridged = certified_name_bridge(corrected, elections)
    results = analyze(corrected, bridged, splits, continuity)
    identity = []
    for record in results['records']:
        event = record['sourceCandidateId'] + '->' + record['targetOccurrenceId']
        status = stage10.get(event, {}).get('identityClass', 'not_in_stage10_party_seat_inventory')
        record['inheritedStage10IdentityDiagnostic'] = status
        identity.append(status)
    identity_diagnostics = {'schemaVersion': 1,
                            'counts': {status: identity.count(status) for status in sorted(set(identity))},
                            'scores': [{'identityClass': status, 'n': len(group),
                                        'local': _score(group, 'localMatchedVotes') if len(group) >= 5 else None}
                                       for status in sorted(set(identity))
                                       for group in [[row for row in results['records']
                                                      if row['inheritedStage10IdentityDiagnostic'] == status]]],
                            'caveat': 'Inherited Stage10 identity evidence was retrospectively acquired with outcome-related selection. Status never admits or excludes Stage11 predictions; small supported replacement groups are descriptive only.'}
    full_sensitivity = evaluate(corrected, bridged, splits, continuity, backtest)
    original_ids = {row['targetOccurrenceId'] for row in original['records']
                    if row['conditionalPartialApplicability']}
    corrected_by_id = {row['targetOccurrenceId']: row for row in results['records']}
    historical = {row['targetOccurrenceId']: row for row in original_predictions['records']}
    if set(historical) != original_ids or not original_ids <= set(corrected_by_id):
        raise ValueError('Original Stage 11 common sample changed')
    for candidate_id, record in historical.items():
        normalized = json.loads(json.dumps(corrected_by_id[candidate_id],
                                         default=lambda value: str(value) if isinstance(value, Fraction)
                                         else (_ for _ in ()).throw(TypeError(type(value)))))
        if normalized != record:
            raise ValueError(f'Original common-sample Stage 11 prediction changed: {candidate_id}')
    new_ids = set(corrected_by_id) - original_ids
    new_applicability = {'records': [row for row in corrected['records']
                                   if row['targetOccurrenceId'] in new_ids]}
    new_sensitivity = evaluate(new_applicability, bridged, splits, continuity, backtest)
    original_sensitivity_check = evaluate(original, elections, splits, continuity, backtest)
    if original_sensitivity_check != original_sensitivity:
        raise ValueError('Original Stage 11 Stage5 sensitivity changed')
    benchmark = all(
        row['local']['maeUpperPP'] < min(row['pooled']['maeLowerPP'],
                                        row['partyOnly']['maeLowerPP']) and
        row['local']['rmseUpperPP'] < min(row['pooled']['rmseLowerPP'],
                                         row['partyOnly']['rmseLowerPP'])
        for row in results['transitionScores'])
    complete = bool(results['records']) and all(
        row['unallocatedPartyBallots'] == 0 for row in results['records'])
    selection = {'schemaVersion': 1, 'selectedOperationalSplitView': None,
                 'gates': {'matchedComponentImprovesBothBenchmarksEachHoldout': benchmark,
                           'completePartyBallotMassMapping': complete,
                           'candidateIdentityTransferValidated': False,
                           'outcomeIndependentComputationalEligibility': True},
                 'reason': 'Corrected matched-component diagnostics remain conditional on observed target party ballots. Incomplete matched mass and unvalidated candidate transfer prevent operational selection.'}
    original_records = [corrected_by_id[candidate_id] for candidate_id in sorted(original_ids)]
    new_records = [corrected_by_id[candidate_id] for candidate_id in sorted(new_ids)]
    comparison = {'schemaVersion': 1, 'originalCommonCandidateCount': len(original_records),
                  'newlyAdmittedCandidateCount': len(new_records),
                  'correctedFullCandidateCount': len(results['records']),
                  'originalCommonScores': _score_by_fold(original_records),
                  'newAdmissionScores': _score_by_fold(new_records),
                  'correctedFullScores': _score_by_fold(results['records']),
                  'originalCommonStage5Sensitivity': original_sensitivity,
                  'newAdmissionStage5Sensitivity': new_sensitivity,
                  'correctedFullStage5Sensitivity': full_sensitivity,
                  'originalRecordValuesPreserved': True,
                  'status': 'retrospective_conditional_matched_party_ballot_component_only'}
    return {'corrected-predictions.json': results,
            'corrected-party-input-sensitivity.json': full_sensitivity,
            'corrected-identity-diagnostics.json': identity_diagnostics,
            'corrected-selection.json': selection,
            'correction-comparison.json': comparison}
