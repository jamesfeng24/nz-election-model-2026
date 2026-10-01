"""Outcome-blind Stage22 shared-group mapping, features and amended fit contract."""

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from scripts.checkpoints.complete_share_feature_rank import build as rank_build
from scripts.checkpoints.complete_share_features import build_feature_inventory
from scripts.checkpoints.stage22_mapping import amend_inventory
from scripts.validate.source_files import verify_source_files


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/processed/checkpoints/stage22-shared-group-prefit'
FRAME = 'data/processed/checkpoints/complete-candidate-baseline/input-inventory.json'
ORIGINAL_MAPPING = 'data/processed/models/conditional-candidate-share/inventory.json'
ORIGINAL_FEATURES = 'data/processed/checkpoints/complete-share-feature-applicability/feature-inventory.json'
ORIGINAL_CONTRACT = 'data/processed/checkpoints/complete-share-feature-applicability/fit-contract.json'
STAGE20_SOURCES = 'data/processed/checkpoints/complete-share-feature-applicability/source-contract.json'
OVERLAY = 'data/processed/checkpoints/stage21-alliance-mapping/overlay.json'
STAGE21_SOURCES = 'data/processed/checkpoints/stage21-alliance-mapping/source-contract.json'
CONTINUITY = 'data/processed/models/party-vote-transform/party-continuity.json'
ELECTIONS = {year: f'data/processed/elections/{year}.json'
             for year in (2008, 2011, 2014, 2017, 2020, 2023)}
SPLITS = {year: f'data/processed/split-votes/{year}.json'
          for year in (2008, 2014, 2020)}
INPUTS = (FRAME, ORIGINAL_MAPPING, ORIGINAL_FEATURES, ORIGINAL_CONTRACT,
          STAGE20_SOURCES, OVERLAY, STAGE21_SOURCES, CONTINUITY,
          *ELECTIONS.values(), *SPLITS.values())


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def source_contract(registry, contracts):
    """Pin only inherited consumed records and their raw bytes."""
    old = {}
    for contract in contracts:
        for row in contract['sources']:
            if row['id'] in old and old[row['id']] != row:
                raise ValueError('Conflicting inherited source record')
            old[row['id']] = row
    live = registry['sources']
    indexed = {row['id']: row for row in live}
    if len(indexed) != len(live):
        raise ValueError('Ambiguous live source ID')
    for sid, record in old.items():
        if indexed.get(sid) != record:
            raise ValueError(f'Changed or missing consumed source record: {sid}')
    result = {'schemaVersion': 1, 'stage': 22, 'sources': [old[k] for k in sorted(old)]}
    verify_source_files(ROOT, result)
    return result


def continuity_audit(rows, overlay):
    """No constituent inherits an alliance's cross-election category by implication."""
    affected = {(r['year'], r['sharedPartyKey']) for r in overlay['records']}
    eligible = [r for r in rows if r['status'] == 'eligible' and r.get('source') and
                (r['sourceYear'], r['source']['sourceKey']) in affected]
    if eligible:
        raise ValueError('Eligible source shared-group continuation needs explicit source destination adapter')
    recorded = [r for r in rows if r.get('source') and
                (r['sourceYear'], r['source']['sourceKey']) in affected]
    return {'eligibleSharedSourceContinuities': [],
            'recordedSharedSourceTransitions': [
                {'sourceYear': r['sourceYear'], 'targetYear': r['targetYear'],
                 'sourceKey': r['source']['sourceKey'], 'status': r['status']}
                for r in recorded],
            'interpretation': '2014 Internet MANA exits; later Internet Party/MANA target categories are entrants. No source alliance S/V is transferred to a constituent.'}


def annotate_features(features, mapping):
    by_seat = {(r['targetYear'], r['targetElectorateId']): r
               for r in mapping['frame']}
    for row in features['records']:
        if row['status'] != 'constructed':
            continue
        source = by_seat[(row['targetYear'], row['targetElectorateId'])]
        mapped = {r['candidateOccurrenceId']: r for r in source['candidates']}
        for candidate in row['candidates']:
            evidence = mapped[candidate['targetOccurrenceId']]
            candidate['originalAffiliation'] = evidence['sourceAffiliation']
            candidate['originalAffiliationKey'] = evidence['sourcePartyKey']
            candidate['electionLocalPartyBallotGroup'] = evidence['partyKey']
            candidate['sharedGroupEvidence'] = evidence.get('sharedPartyGroupEvidence')


def differences(original, amended, decisions):
    old = {r['targetElectorateId']: r for r in original['records']}
    new = {r['targetElectorateId']: r for r in amended['records']}
    if set(old) != set(new):
        raise ValueError('Fixed frame changed')
    newly = [r for key, r in new.items()
             if old[key]['status'] != 'constructed' and r['status'] == 'constructed']
    common = [r for key, r in new.items()
              if old[key]['status'] == r['status'] == 'constructed']
    corrected = []
    for row in common:
        previous = {c['targetOccurrenceId']: c for c in old[row['targetElectorateId']]['candidates']}
        for candidate in row['candidates']:
            before = previous[candidate['targetOccurrenceId']]
            if any(before[key] != candidate[key] for key in
                   ('mappingStatus', 'targetPartyKey', 'targetPartySupport',
                    'fallbackReasons', 's0Reported', 'v0')):
                corrected.append({'targetYear': row['targetYear'],
                                  'targetElectorateId': row['targetElectorateId'],
                                  'candidateOccurrenceId': candidate['targetOccurrenceId'],
                                  'oldMappingStatus': before['mappingStatus'],
                                  'newMappingStatus': candidate['mappingStatus'],
                                  'oldTargetPartySupport': before['targetPartySupport'],
                                  'newTargetPartySupport': candidate['targetPartySupport'],
                                  'oldFallbackReasons': before['fallbackReasons'],
                                  'newFallbackReasons': candidate['fallbackReasons']})
    if any(old[k]['status'] == 'constructed' and new[k]['status'] != 'constructed' for k in old):
        raise ValueError('Previously constructed contest lost coverage')
    return {'newlyAdmittedContestIds': [r['targetElectorateId'] for r in newly],
            'newlyAdmittedCandidateOccurrenceIds': [c['targetOccurrenceId']
                                                     for r in newly for c in r['candidates']],
            'originalCommonContestIds': [r['targetElectorateId'] for r in common],
            'correctedExistingCandidateInputs': corrected,
            'mappingDecisions': decisions,
            'oldSummary': original['summary'], 'amendedSummary': amended['summary']}


def fold_contract(fold, features):
    by_id = {r['targetElectorateId']: r for r in features['records']}
    training = [by_id[k] for k in fold['trainingContestIds']]
    evaluation = [by_id[k] for k in fold['evaluationContestIds']]
    def candidates(contests):
        return [c['targetOccurrenceId'] for row in contests for c in row['candidates']]
    return {'targetYear': fold['targetYear'],
            'trainingTargetYears': fold['trainingTargetYears'],
            'trainingContestIds': fold['trainingContestIds'],
            'trainingCandidateOccurrenceIds': candidates(training),
            'commonEvaluationContestIds': fold['evaluationContestIds'],
            'commonEvaluationCandidateOccurrenceIds': candidates(evaluation),
            'trainingOnlyFeatureMeansFromAudit': fold['trainingOnlyMeans'],
            'trainingContests': len(training), 'evaluationContests': len(evaluation),
            'trainingCandidates': len(candidates(training)),
            'evaluationCandidates': len(candidates(evaluation))}


def amended_contract(original, audit, features, diff):
    contract = deepcopy(original)
    contract['stage'] = 22
    contract['status'] = 'amended_shared_group_sample_frozen_before_fit_or_score'
    contract['authorization'] = 'stage22_four_restrictions_only_after_all_prefit_gates'
    contract['folds'] = [fold_contract(row, features) for row in audit['folds']]
    contract['amendment'] = {
        'originalContractSha256': digest(ORIGINAL_CONTRACT),
        'sharedGroupRule': 'one_official_election_local_group_share_once_for_its_unique_standing_constituent_candidate',
        'sourceAllianceContinuity': 'no_unverified_cross_election_constituent_transfer',
        'newContestIds': diff['newlyAdmittedContestIds'],
        'correctedExistingCandidateIds': [r['candidateOccurrenceId']
                                          for r in diff['correctedExistingCandidateInputs']],
        'commonSubset': 'intersection_with_original_constructed_contests_scored_from_same_amended_fits',
        'operationalSelection': None}
    return contract


def build():
    frame, original_mapping, old_features, original_contract, overlay, continuity = map(read, (
        FRAME, ORIGINAL_MAPPING, ORIGINAL_FEATURES, ORIGINAL_CONTRACT, OVERLAY, CONTINUITY))
    elections = {year: read(path) for year, path in ELECTIONS.items()}
    splits = {year: read(path) for year, path in SPLITS.items()}
    sources = source_contract(read('data/sources.json'),
                              (read(STAGE20_SOURCES), read(STAGE21_SOURCES)))
    mapping, decisions = amend_inventory(original_mapping, overlay, elections)
    prior = continuity_audit(continuity['records'], overlay)
    features = build_feature_inventory(frame, mapping, elections, splits,
                                       continuity['records'])
    annotate_features(features, mapping)
    delta = differences(old_features, features, decisions)
    audit = rank_build(features)
    if not audit['allFittingGatesPass']:
        raise ValueError('Frozen amended pre-fit coverage or training-rank gate failed')
    contract = amended_contract(original_contract, audit, features, delta)
    checkpoint = {'schemaVersion': 1, 'stage': 22,
                  'role': 'before_any_stage22_fit_or_score',
                  'continuityAudit': prior, 'differences': delta,
                  'fittingGatesPass': True,
                  'heldGeneralFrameContests': 191,
                  'mappingsByYear': {str(y): dict(sorted(Counter(
                      d['decision'] for d in decisions if d['year'] == y).items()))
                      for y in (2014, 2023)}}
    outputs = {'amended-mapping.json': mapping,
               'amended-features.json': features,
               'amended-design-audit.json': audit,
               'amended-fit-contract.json': contract,
               'coverage-differences.json': checkpoint,
               'source-contract.json': sources}
    outputs['manifest.json'] = {
        'schemaVersion': 1, 'stage': 22,
        'phase': 'committed_before_any_stage22_fitting_or_scoring',
        'inputSha256': {path: digest(path) for path in INPUTS},
        'generatorSha256': {name: digest('scripts/checkpoints/' + name)
                            for name in ('stage22_mapping.py', 'stage22_prefit.py')},
        'outputSha256': {name: sha256(encode(value)).hexdigest()
                         for name, value in outputs.items()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    DEST.mkdir(parents=True, exist_ok=True)
    for name, value in outputs.items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != encode(value):
                raise ValueError(f'Changed Stage22 pre-fit {name}')
        else:
            path.write_bytes(encode(value))
    print(json.dumps({'mapping': outputs['coverage-differences.json']['mappingsByYear'],
                      'featureSummary': outputs['amended-features.json']['summary'],
                      'gates': outputs['amended-design-audit.json']['allFittingGatesPass']},
                     sort_keys=True))


if __name__ == '__main__':
    main()
