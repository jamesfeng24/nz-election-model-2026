"""Pinned inputs and deterministic serialization for practical linkage."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'data/processed/evidence/practical-candidate-linkage'
OCCURRENCES = 'data/processed/models/candidate-overperformance/occurrences.json'
GEOGRAPHY = 'data/processed/checkpoints/stage25-historical-geography/geography.json'
CONTINUITY = 'data/processed/models/party-vote-transform/party-continuity.json'
LINKS = 'data/processed/models/candidate-persistence/person-links.json'
HISTORY = 'data/processed/models/candidate-persistence/history-status.json'
TENURE = 'data/processed/models/freshman-incumbency/inventory.json'
PROFILES = 'data/processed/models/freshman-incumbency/tenure-evidence.json'
DISTINCT = 'data/processed/models/replacement-candidate/identity-review.json'
STAGE13 = 'data/processed/checkpoints/identity-evidence-pass/final/relations.json'
STAGE21 = 'data/processed/checkpoints/stage21-identity-pilot/adjudication.json'
MAPPING = 'data/processed/checkpoints/stage22-shared-group-prefit/amended-mapping.json'
INPUTS = (OCCURRENCES, GEOGRAPHY, CONTINUITY, LINKS, HISTORY, TENURE, PROFILES,
          DISTINCT, STAGE13, STAGE21, MAPPING,
          'data/processed/checkpoints/stage25-historical-geography/availability.json',
          'data/processed/checkpoints/stage25-historical-geography/fold-plan.json')


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode()


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def unique(rows, field):
    indexed = {}
    for row in rows:
        key = row[field]
        if key in indexed and indexed[key] != row:
            raise ValueError(f'Conflicting repeated {field}: {key}')
        indexed[key] = row
    return indexed


def verify_inputs(root=ROOT, registry=None, raw_reader=None):
    contract = read('data/processed/evidence/practical-candidate-linkage/input-contract.json')
    for path, expected in contract['inputSha256'].items():
        if sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Changed consumed input: {path}')
    indexes = {}
    for dependency in contract['requiredSources']:
        path, required = dependency['registryPath'], dependency['record']
        if path not in indexes:
            document = registry if registry is not None and path == 'data/sources.json' else json.loads((root / path).read_bytes())
            live = document['sources']
            if len(live) != len({r['id'] for r in live}):
                raise ValueError('Duplicate source ID')
            indexes[path] = {r['id']: r for r in live}
        indexed = indexes[path]
        if indexed.get(required['id']) != required:
            raise ValueError(f'Changed or missing required source: {required["id"]}')
        raw = raw_reader(required['rawPath']) if raw_reader else (root / required['rawPath']).read_bytes()
        if sha256(raw).hexdigest() != required['sha256']:
            raise ValueError(f'Changed required raw bytes: {required["id"]}')
    return contract
