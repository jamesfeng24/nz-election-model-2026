"""Stage39 consumed-source and deterministic companion contracts."""
import json
import hashlib
from pathlib import Path
from scripts.polling.category_interface.common import portable_gzip, read

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/processed/polling/candidate-integration'
EXTERNAL = ROOT / 'data/processed/polling/external-comparison'
CANDIDATE = ROOT / 'data/processed/models/joint-candidate-share'
DESIGN = ROOT / 'data/processed/checkpoints/joint-candidate-share-design'
PARTY = ROOT / 'data/processed/models/expanded-party-substitution'
CATEGORY = ROOT / 'data/processed/polling/category-interface'
YEARS = (2017, 2020, 2023)
METHODS = ('baseline', 'baseline_plus_S', 'baseline_plus_S_plus_R')
POLICIES = ('recent_report_prior', 'prior_only')
PAIRS = ((METHODS[1], METHODS[0]), (METHODS[2], METHODS[0]), (METHODS[2], METHODS[1]))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def save(name, value, check=False):
    raw = encode(value)
    if name.endswith('.gz'):
        raw = portable_gzip(raw)
    path = OUT / name
    if check:
        if path.read_bytes() != raw:
            raise ValueError('Changed Stage39 output: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def verify_inputs():
    for path, expected in read(OUT / 'input-contract.json')['sha256'].items():
        if sha(ROOT / path) != expected:
            raise ValueError('Changed consumed source: ' + path)


def preserve():
    contract = read(OUT / 'prior-data-contract.json')
    for path, expected in contract['sha256'].items():
        if sha(ROOT / path) != expected:
            raise ValueError('Changed historical artifact: ' + path)
    return len(contract['sha256'])


def seal(name, files, code, check=False):
    save(name + '-manifest.json', {'outputs': {p: sha(OUT / p) for p in files},
         'code': {p: sha(ROOT / p) for p in code}}, check)


def verify_phase(name):
    manifest = read(OUT / (name + '-manifest.json'))
    for p, expected in manifest['outputs'].items():
        if sha(OUT / p) != expected:
            raise ValueError('Changed sealed output ' + p)
    for p, expected in manifest['code'].items():
        if sha(ROOT / p) != expected:
            raise ValueError('Changed sealed code ' + p)
