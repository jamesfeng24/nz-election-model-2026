"""Pinned offline inputs and deterministic checkpoint IO."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'data/processed/models/conditional-nat-lab-response'
PARTIES = ('nationalparty', 'labourparty')
YEARS = (2008, 2011, 2014, 2017, 2020, 2023)
TRANSITIONS = ((2008, 2011), (2014, 2017), (2020, 2023))
INPUTS = (
    'data/processed/models/nat-lab-elasticity/records.json',
    'data/processed/models/nat-lab-elasticity/specification.json',
    'data/processed/models/nat-lab-elasticity/backtests.json',
    'data/processed/models/party-vote-transform/backtest-records.json',
    'data/processed/models/party-vote-transform/specification.json',
    'data/processed/models/candidate-overperformance/occurrences.json',
    'data/processed/models/candidate-persistence/person-links.json',
    'data/processed/models/candidate-persistence/pairs.json',
    'data/processed/models/freshman-incumbency/inventory.json',
    'data/processed/models/replacement-candidate/inventory.json',
    'data/processed/checkpoints/identity-evidence-pass/final/occurrence-evidence.json',
    'data/processed/checkpoints/identity-evidence-pass/final/relations.json',
    'data/processed/models/conditional-candidate-ledger/diagnostics.json',
    *(f'data/processed/elections/{year}.json' for year in YEARS),
    'data/source-plans/stage15-conditional-ledger-sources.json',
    'data/source-plans/candidate-persistence-sources.json',
    'data/source-plans/freshman-incumbency-tenure-sources.json',
    'data/source-plans/stage10-identity-sources.json',
    'data/source-plans/stage13-identity-sources.json',
)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write_or_check(outputs, check):
    for name, value in outputs.items():
        expected = encode(value)
        path = DEST / name
        if check:
            if not path.exists() or path.read_bytes() != expected:
                raise ValueError(f'Changed Stage 16 artifact: {name}')
        else:
            path.write_bytes(expected)


def validate_inputs():
    from scripts.validate.source_files import verify_source_files
    contract = json.loads((DEST / 'input-contract.json').read_bytes())
    if set(contract) != set(INPUTS):
        raise ValueError('Changed Stage 16 dependency set')
    for path, expected in contract.items():
        if digest(path) != expected:
            raise ValueError(f'Changed Stage 16 input: {path}')
    sources = {}
    for path in INPUTS:
        if not path.startswith('data/source-plans/'):
            continue
        for source in read(path)['sources']:
            if source['id'] in sources and sources[source['id']] != source:
                raise ValueError('Conflicting preserved source record')
            sources[source['id']] = source
    live = read('data/sources.json')['sources']
    if len(live) != len({row['id'] for row in live}):
        raise ValueError('Duplicate live registry ID')
    by_id = {row['id']: row for row in live}
    for row in read('data/source-plans/stage15-conditional-ledger-sources.json')['sources']:
        if by_id.get(row['id']) != row:
            raise ValueError('Changed required shared source record')
    verify_source_files(ROOT, {'schemaVersion': 1, 'sources': list(sources.values())})
    return len(sources)
