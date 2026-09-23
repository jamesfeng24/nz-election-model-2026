"""Generate or verify offline Stage 9 freshman diagnostics."""

import argparse
import hashlib
import json

from scripts.models.freshman_incumbency.model import analyze, prepare_rows, select
from scripts.models.freshman_incumbency.outcome_audit import audit
from scripts.models.freshman_incumbency.run import (DEST, ROOT, YEARS, build as build_inventory,
                                                    digest, encode)


INPUT_NAMES = ['data/processed/models/freshman-incumbency/inventory.json',
               'data/processed/models/freshman-incumbency/tenure-evidence.json',
               'data/processed/models/freshman-incumbency/input-contract.json',
               'data/processed/models/freshman-incumbency/manifest.json',
               'data/processed/models/freshman-incumbency/specification.json',
               'data/processed/models/freshman-incumbency/postfit-audit-amendment.json',
               'data/processed/models/candidate-persistence/pairs.json',
               'data/processed/models/candidate-overperformance/occurrences.json',
               'data/source-plans/candidate-persistence-sources.json',
               'data/raw/identity-parliament-former.html',
               'data/raw/identity-parliament-current.html',
               *(f'data/processed/elections/{year}.json' for year in YEARS)]


def validate_tenure_source_plan(plan):
    required = {'schemaVersion', 'id', 'organisation', 'url', 'dateOrElection',
                'resource', 'retrievedAt', 'rawPath', 'processingScript',
                'limitations', 'sha256', 'licence'}
    sources = plan.get('sources', [])
    if plan.get('schemaVersion') != 1 or len(sources) != 108:
        raise ValueError('Unexpected Stage 9 tenure source inventory')
    for source in sources:
        if (not required.issubset(source) or
                any(not source[field] for field in required) or
                not isinstance(source['limitations'], list) or
                source['processingScript'] != 'scripts/models/freshman_incumbency/tenure.py'):
            raise ValueError('Incomplete Stage 9 source provenance')
    if len({source['url'] for source in sources}) != len(sources):
        raise ValueError('Duplicate Stage 9 source URL')


def verify_inventory():
    plan = json.loads((ROOT / 'data/source-plans/freshman-incumbency-tenure-sources.json').read_bytes())
    validate_tenure_source_plan(plan)
    for name, value in build_inventory().items():
        if (DEST / name).read_bytes() != encode(value):
            raise ValueError(f'Changed pinned Stage 9 pre-fit inventory: {name}')


def target_winners():
    elected = set()
    for year in YEARS:
        election = json.loads((ROOT / f'data/processed/elections/{year}.json').read_bytes())
        for seat in election['electorates']:
            elected.update(row['id'] for row in seat['candidates'] if row['elected'])
    return elected


def composition(rows, inventory, elected):
    by_id = {row['pairId']: row for row in inventory}
    return [{'targetYear': year,
             'n': len(subset),
             'targetWinners': sum(by_id[row['pairId']]['targetOccurrenceId'] in elected for row in subset),
             'targetLosers': sum(by_id[row['pairId']]['targetOccurrenceId'] not in elected for row in subset),
             'confirmedTargetLosers': sum(by_id[row['pairId']]['targetOccurrenceId'] not in elected and
                                          row['targetIdentityStatus'] == 'confirmed' for row in subset)}
            for year in (2011, 2017, 2023)
            for subset in [[row for row in rows if row['targetYear'] == year]]]


def build():
    verify_inventory()
    spec = json.loads((DEST / 'specification.json').read_bytes())
    if (spec['stage'] != 9 or spec['status'] !=
            'frozen before fitting after the committed pre-fit inventory' or
            spec['inventoryCommit'] != '6ddec50'):
        raise ValueError('Stage 9 frozen specification changed')
    inventory = json.loads((DEST / 'inventory.json').read_bytes())['records']
    profiles = json.loads((DEST / 'tenure-evidence.json').read_bytes())['profiles']
    amendment = json.loads((DEST / 'postfit-audit-amendment.json').read_bytes())
    if amendment['status'] != 'post-fit cohort correction; not part of the pre-fit freeze':
        raise ValueError('Unrecognized Stage 9 post-fit amendment')
    cohort_audit, kept, evaluated = audit(ROOT, inventory, profiles)
    if cohort_audit['counts']['lostPrimaryPairIds'] != amendment['excludedPairIds']:
        raise ValueError('Counterfactual cohort audit disagrees with documented amendment')
    pairs = json.loads((ROOT / 'data/processed/models/candidate-persistence/pairs.json').read_bytes())['pairs']
    rows = prepare_rows(inventory, pairs, allowed_pair_ids=evaluated)
    primary = analyze(rows)
    scale = {name: analyze(prepare_rows(inventory, pairs, scale=name, allowed_pair_ids=evaluated))
             for name in ('proportional', 'log_odds')}
    prior_list = analyze(prepare_rows(inventory, pairs, extra='prior_list', allowed_pair_ids=kept))
    off_cycle = analyze(prepare_rows(inventory, pairs, extra='off_cycle', allowed_pair_ids=kept))
    both_confirmed = analyze(prepare_rows(inventory, pairs, extra='both_confirmed', allowed_pair_ids=evaluated))
    superseded = analyze(prepare_rows(inventory, pairs))
    outcome_composition = composition(rows, inventory, target_winners())
    decision = select(primary, [*scale.values(), prior_list], both_confirmed['n'],
                      outcome_composition)
    outputs = {
        'analysis-input-contract.json': {name: digest(ROOT / name) for name in INPUT_NAMES},
        'cohort-audit.json': cohort_audit,
        'analysis.json': {'schemaVersion': 1, 'primary': primary,
                          'normalizationSensitivity': scale,
                          'priorListSensitivity': prior_list,
                          'offCycleSensitivity': off_cycle,
                          'bothConfirmedRetrospectiveWinnerSelected': both_confirmed,
                          'supersededPreAuditOutcomeDependentCohort': {
                              'status': 'audit trail only; not operational validation',
                              'analysis': superseded},
                          'targetOutcomeCompositionRetrospective': outcome_composition,
                          'maoriClassifiedSourceWinnerPairs': sum(
                              row['electorateType'] == 'maori' and row['sourceWasElected'] and
                              'not_comparable_stage8_pair' not in row['exclusionReasons']
                              for row in inventory),
                          'selectionAndDependence': 'Corrected link eligibility survives target/later winner counterfactuals. Source-winner and recontesting selection, retrospective profile publication, probable target links, repeated people, shared party/election reference offsets and three transition clusters still limit inference. Observed target win rate alone does not prove target-outcome selection. No candidate-pair iid p-values.'},
        'selection.json': decision,
    }
    code = [ROOT / f'scripts/models/freshman_incumbency/{name}.py'
            for name in ('model', 'analysis_run', 'outcome_audit')]
    code.extend(ROOT / f'scripts/models/candidate_persistence/{name}.py'
                for name in ('identity', 'official', 'pairs'))
    code.append(ROOT / 'scripts/models/freshman_incumbency/inventory.py')
    outputs['analysis-manifest.json'] = {'schemaVersion': 1, 'stage': 9,
        'specificationCommit': 'c5560f7',
        'inputHashes': outputs['analysis-input-contract.json'],
        'codeHashes': {str(path.relative_to(ROOT)): digest(path) for path in code},
        'outputHashes': {name: hashlib.sha256(encode(value)).hexdigest()
                         for name, value in outputs.items()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, value in outputs.items():
            if (DEST / name).read_bytes() != encode(value):
                raise ValueError(f'Changed Stage 9 analysis output: {name}')
        print('Stage 9 analysis reproducible')
        return
    for name, value in outputs.items():
        (DEST / name).write_bytes(encode(value))
    print('Stage 9 analysis written')


if __name__ == '__main__':
    main()
