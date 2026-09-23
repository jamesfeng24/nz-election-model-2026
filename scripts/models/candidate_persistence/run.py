"""Build or verify the pinned, offline Stage 8 persistence outputs."""

import argparse
import hashlib
import json
from pathlib import Path

from scripts.models.candidate_persistence.identity import build_identity
from scripts.models.candidate_persistence.model import analyze, select
from scripts.models.candidate_persistence.official import parse_members, project_members
from scripts.models.candidate_persistence.pairs import build_pairs
from scripts.validate.source_files import verify_source_files


ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'data/processed/models/candidate-persistence'
YEARS = (2008, 2011, 2014, 2017, 2020, 2023)
OFFICIAL_PATHS = ('data/raw/identity-parliament-former.html',
                  'data/raw/identity-parliament-current.html')
SOURCE_PLAN = 'data/source-plans/candidate-persistence-sources.json'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs(contract):
    for name, expected in contract.items():
        path = ROOT / name
        if not name.startswith('data/') or '..' in Path(name).parts or not path.is_file():
            raise ValueError(f'Forbidden or missing Stage8 input: {name}')
        if digest(path) != expected:
            raise ValueError(f'Changed pinned Stage8 input: {name}')


def elected_ids():
    elected = set()
    for year in YEARS:
        data = json.loads((ROOT / f'data/processed/elections/{year}.json').read_bytes())
        for seat in data['electorates']:
            for candidate in seat['candidates']:
                if candidate['elected'] is True:
                    elected.add(candidate['id'])
    return elected


def build():
    contract = json.loads((DEST / 'input-contract.json').read_bytes())
    verify_inputs(contract)
    expected = {'data/processed/models/candidate-overperformance/occurrences.json',
                'data/processed/models/candidate-persistence/specification.json',
                SOURCE_PLAN, *OFFICIAL_PATHS,
                *(f'data/processed/elections/{year}.json' for year in YEARS)}
    if set(contract) != expected:
        raise ValueError('Stage8 input contract incomplete or expanded')
    spec = json.loads((DEST / 'specification.json').read_bytes())
    if spec['stage'] != 8 or not spec['frozenBeforeFitting'] or spec['primaryTransitions'] != [[2008, 2011], [2014, 2017], [2020, 2023]]:
        raise ValueError('Stage8 specification changed')
    source_plan = json.loads((ROOT / SOURCE_PLAN).read_bytes())
    verify_source_files(ROOT, source_plan)
    if {record['rawPath'] for record in source_plan['sources']} != set(OFFICIAL_PATHS):
        raise ValueError('Stage8 source plan does not match pinned official inputs')
    required = {'id', 'organisation', 'url', 'retrievedAt', 'rawPath', 'processingScript',
                'limitations', 'sha256', 'licence'}
    if any(not required.issubset(record) or not all(record[field] for field in required)
           for record in source_plan['sources']):
        raise ValueError('Incomplete Stage8 source provenance')
    records = json.loads((ROOT / 'data/processed/models/candidate-overperformance/occurrences.json').read_bytes())['records']
    members = []
    for name in OFFICIAL_PATHS:
        members.extend(parse_members((ROOT / name).read_bytes()))
    official = project_members(records, members, elected_ids())
    identity = build_identity(records, official)
    pair_data = build_pairs(records, identity['links'])
    pairs = pair_data['pairs']
    primary = analyze(pairs)
    sensitivity = [analyze(pairs, scale=scale) for scale in ('proportional', 'log_odds')]
    sensitivity.append(analyze(pairs, include_probable=True))
    maori = analyze(pairs, scope='maori')
    maori_probable = analyze(pairs, scope='maori', include_probable=True)
    selection = select(primary, sensitivity[:2], identity['coverage'])
    outputs = {
        'person-links.json': {'schemaVersion': 1, 'links': identity['links'],
                              'unresolved': identity['unresolved'], 'persons': identity['persons'],
                              'coverage': identity['coverage']},
        'history-status.json': {'schemaVersion': 1, 'records': identity['historyStatus'],
                                'interpretation': 'Election-dated evidence only. Unknown and left-censored are explicit; leadership is orthogonal. No candidate-status effect is fitted.'},
        'pairs.json': {'schemaVersion': 1, **pair_data,
                       'usage': 'Target residuals are historical evaluation outcomes, never same-election predictors.'},
        'analysis.json': {'schemaVersion': 1, 'primary': primary, 'sensitivity': sensitivity,
                          'maoriDescriptive': maori, 'maoriProbableSensitivity': maori_probable,
                          'dependence': 'Shared party/election reference offsets, repeated people and three transition clusters preclude candidate-pair iid inference.',
                          'selection': 'Conditional on returning candidacy, MP-focused confirmation, held contests and unchanged seat geography.'},
        'selection.json': selection,
    }
    code = sorted([*(ROOT / 'scripts/models/candidate_persistence').glob('*.py'),
                   ROOT / 'scripts/validate/source_files.py'])
    outputs['manifest.json'] = {
        'schemaVersion': 1, 'branchBase': 'fa1dda369f1cccbb9b2494c7ebac0db72f4177d9',
        'inputHashes': contract,
        'codeHashes': {str(path.relative_to(ROOT)): digest(path) for path in code},
        'outputHashes': {name: hashlib.sha256(encode(value)).hexdigest() for name, value in outputs.items()},
        'counts': {'occurrences': len(records), 'confirmed': identity['coverage']['confirmedCount'],
                   'probable': identity['coverage']['probableCount'],
                   'unresolved': identity['coverage']['unresolvedCount'],
                   'primaryPairs': pair_data['diagnostics']['primaryPairs']},
    }
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, value in build().items():
        raw = encode(value)
        path = DEST / name
        if args.check:
            if not path.is_file() or path.read_bytes() != raw:
                raise ValueError(f'Stale Stage8 output: {name}')
        else:
            path.write_bytes(raw)
    print('Stage8 pinned outputs verified' if args.check else 'Stage8 outputs generated')


if __name__ == '__main__':
    main()
