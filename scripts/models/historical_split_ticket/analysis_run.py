"""Generate or verify Stage 11 chronological split-component diagnostics."""

import argparse
import hashlib
import json
from copy import deepcopy
from fractions import Fraction

from scripts.models.historical_split_ticket.analysis import _score, analyze
from scripts.models.historical_split_ticket.evidence import YEARS, candidate_inventory
from scripts.models.historical_split_ticket.run import (
    DEST, ROOT, build as build_evidence, digest)
from scripts.models.historical_split_ticket.sensitivity import evaluate


INPUTS = (
    'data/processed/models/historical-split-ticket/evidence.json',
    'data/processed/models/historical-split-ticket/applicability.json',
    'data/processed/models/historical-split-ticket/input-contract.json',
    'data/processed/models/historical-split-ticket/manifest.json',
    'data/processed/models/historical-split-ticket/specification.json',
    'data/processed/models/party-vote-transform/party-continuity.json',
    'data/processed/models/party-vote-transform/backtest-records.json',
    'data/processed/models/replacement-candidate/inventory.json',
    *(f'data/processed/elections/{year}.json' for year in YEARS),
    *(f'data/processed/split-votes/{year}.json' for year in YEARS),
)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False,
                       default=lambda obj: str(obj) if isinstance(obj, Fraction) else
                       (_ for _ in ()).throw(TypeError(type(obj)))) + '\n').encode()


def read(name):
    return json.loads((ROOT / name).read_bytes())


def build():
    for name, value in build_evidence().items():
        if (DEST / name).read_bytes() != encode(value):
            raise ValueError(f'Changed committed pre-fit split evidence: {name}')
    specification = read('data/processed/models/historical-split-ticket/specification.json')
    if (specification['stage'] != 11 or specification['evidenceCommit'] != '6939dbd' or
            not specification['freezeStatus'].startswith('frozen after committed evidence')):
        raise ValueError('Stage 11 split specification freeze invalid')
    elections = {year: read(f'data/processed/elections/{year}.json') for year in YEARS}
    splits = {year: read(f'data/processed/split-votes/{year}.json') for year in YEARS}
    applicability = read('data/processed/models/historical-split-ticket/applicability.json')
    continuity = read('data/processed/models/party-vote-transform/party-continuity.json')['records']
    changed_winners = deepcopy(elections)
    toggled = 0
    for year in YEARS:
        for seat in changed_winners[year]['electorates']:
            seat['winnerCandidateId'] = None
            for candidate in seat['candidates']:
                candidate['elected'] = not candidate['elected']
                toggled += 1
    rebuilt = candidate_inventory(changed_winners, splits, continuity)
    if rebuilt != applicability:
        raise ValueError('Target/later winner flags changed Stage 11 applicability')
    outcome_audit = {'schemaVersion': 1, 'winnerFlagsToggled': toggled,
                     'applicabilityChanged': False,
                     'caveat': 'Computational invariance does not prove source-acquisition neutrality or candidate-party transferability.'}
    results = analyze(applicability, elections, splits, continuity)
    stage10 = {row['eventId']: row for row in
               read('data/processed/models/replacement-candidate/inventory.json')['records']}
    inherited = []
    for record in results['records']:
        event = record['sourceCandidateId'] + '->' + record['targetOccurrenceId']
        status = stage10.get(event, {}).get('identityClass', 'not_in_stage10_party_seat_inventory')
        record['inheritedStage10IdentityDiagnostic'] = status
        inherited.append(status)
    identity_diagnostics = {'schemaVersion': 1,
                            'counts': {status: inherited.count(status) for status in sorted(set(inherited))},
                            'scores': [{'identityClass': status, 'n': len(group),
                                        'local': _score(group, 'localMatchedVotes') if len(group) >= 5 else None}
                                       for status in sorted(set(inherited))
                                       for group in [[row for row in results['records']
                                                      if row['inheritedStage10IdentityDiagnostic'] == status]]],
                            'caveat': 'Inherited Stage10 identity evidence was retrospectively acquired with outcome-related selection. Status never admits or excludes Stage11 predictions; small supported replacement groups are descriptive only.'}
    sensitivity = evaluate(
        applicability, elections, splits, continuity,
        read('data/processed/models/party-vote-transform/backtest-records.json')['records'])
    rows = results['transitionScores']
    benchmark = all(
        row['local']['maeUpperPP'] < min(row['pooled']['maeLowerPP'],
                                         row['partyOnly']['maeLowerPP']) and
        row['local']['rmseUpperPP'] < min(row['pooled']['rmseLowerPP'],
                                         row['partyOnly']['rmseLowerPP'])
        for row in rows)
    complete = bool(results['records']) and all(
        row['unallocatedPartyBallots'] == 0 for row in results['records'])
    selection = {
        'schemaVersion': 1, 'selectedOperationalSplitView': None,
        'gates': {'matchedComponentImprovesBothBenchmarksEachHoldout': benchmark,
                  'completePartyBallotMassMapping': complete,
                  'candidateIdentityTransferValidated': False,
                  'outcomeIndependentComputationalEligibility': not outcome_audit['applicabilityChanged']},
        'reason': 'The matched ballot component improves both benchmarks, but every comparable target contest has unmatched source party groups; candidate-party transfer to uncertain replacements is unvalidated. No complete pre-election candidate forecast is established.'}
    inputs = {name: digest(ROOT / name) for name in INPUTS}
    outputs = {'predictions.json': results, 'party-input-sensitivity.json': sensitivity,
               'identity-diagnostics.json': identity_diagnostics,
               'outcome-audit.json': outcome_audit,
               'selection.json': selection, 'analysis-input-contract.json': inputs}
    code = [ROOT / 'scripts/models/historical_split_ticket' / name
            for name in ('analysis.py', 'sensitivity.py', 'analysis_run.py')]
    outputs['analysis-manifest.json'] = {
        'schemaVersion': 1, 'stage': 11, 'phase': 'chronological_analysis',
        'evidenceCommit': specification['evidenceCommit'],
        'inputHashes': inputs,
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
                raise ValueError(f'Changed Stage 11 split analysis: {name}')
        print('Stage 11 split analysis reproducible')
        return
    for name, value in outputs.items():
        (DEST / name).write_bytes(encode(value))
    print('Stage 11 chronological split diagnostics written')


if __name__ == '__main__':
    main()
