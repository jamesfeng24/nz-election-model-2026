"""Stage27 companion IO and pinned historical inputs; no historical writes."""
import argparse
from hashlib import sha256, sha1
import json
from pathlib import Path
import subprocess

from scripts.checkpoints import stage25_availability as availability

ROOT = Path(__file__).resolve().parents[3]
DEST = 'data/processed/models/exact-geography-retests/'
GEO = 'data/processed/checkpoints/stage25-historical-geography/'
OLD_RESPONSE = 'data/processed/models/conditional-nat-lab-response/'
OLD_SHARE = 'data/processed/checkpoints/stage22-shared-group-experiment/'
INPUTS = [GEO + name for name in ('geography.json', 'availability.json', 'fold-plan.json',
                                'experiment-register.json', 'source-contract.json')]
INPUTS += list(availability.ELECTIONS.values()) + list(availability.SPLITS.values())
INPUTS += [availability.MAPPING, availability.CONTINUITY,
           OLD_RESPONSE + 'specification.json', OLD_RESPONSE + 'numerical-inputs.json',
           OLD_RESPONSE + 'analysis.json', OLD_SHARE + 'fitted-parameters.json',
           OLD_SHARE + 'predictions.json',
           'data/processed/checkpoints/stage22-shared-group-prefit/amended-features.json',
           'data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json',
           'scripts/checkpoints/stage22_fit.py', 'scripts/checkpoints/complete_share_features.py',
           'scripts/checkpoints/complete_share_feature_rank.py',
           'scripts/checkpoints/stage22_evaluation.py',
           'scripts/models/conditional_nat_lab_response/model.py']
BASE = '09fbf34d968e3f743872f7e76ab885b766004c7b'
METHODS = ('baseline', 'baseline_plus_S')
PROTOCOLS = ('expanding_window', 'more_separated')


def read(path):
    return json.loads((ROOT / path).read_text())


def encode(doc):
    return (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode()


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def keyed(rows, field):
    result = {r[field]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError(f'Duplicate {field}')
    return result


def verify_inputs():
    contract = read(DEST + 'input-contract.json')
    for path, expected in contract['inputSha256'].items():
        if digest(path) != expected:
            raise ValueError(f'Changed required input {path}')
    availability.verify_contract(read(GEO + 'source-contract.json'))


def preservation_snapshot():
    entries = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE, 'data'], cwd=ROOT)
    blobs = {}
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        blobs[path.decode()] = metadata.split()[2].decode()
    return {'baseCommit': BASE, 'gitBlobSha1': blobs}


def verify_preservation(snapshot=None):
    snapshot = snapshot or read(DEST + 'prior-data-contract.json')
    for path, blob in snapshot['gitBlobSha1'].items():
        raw = (ROOT / path).read_bytes()
        actual = sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if actual != blob:
            raise ValueError(f'Changed prior data {path}')
    return len(snapshot['gitBlobSha1'])


def save_outputs(outputs, check):
    (ROOT / DEST).mkdir(parents=True, exist_ok=True)
    for name, doc in outputs.items():
        path = ROOT / DEST / name
        raw = encode(doc)
        if check:
            if path.read_bytes() != raw:
                raise ValueError(f'Non-deterministic Stage27 {name}')
        else:
            path.write_bytes(raw)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    return parser.parse_args().check


def phase_manifest(inputs, outputs):
    return {'inputSha256': {p: digest(p) for p in inputs},
            'outputSha256': {name: sha256(encode(doc)).hexdigest()
                             for name, doc in outputs.items()}}
