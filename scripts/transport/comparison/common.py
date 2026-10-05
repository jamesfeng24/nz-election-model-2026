"""Separate Stage43 companions and pinned consumed-input verification."""
from scripts.transport.common import ROOT, read, digest, encode
PREFIX = 'data/processed/continuous-candidate-comparison'
MODELS = {'S': 'baseline_plus_S', 'joint': 'baseline_plus_S_plus_R'}
BRANCHES = ('S', 'joint', 'joint_strict')


def save(name, value, check=False):
    path = ROOT / PREFIX / name
    raw = encode(value)
    if check:
        if not path.exists() or path.read_bytes() != raw:
            raise ValueError('Stale Stage43 companion: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed consumed input: ' + path)
    hashes = read(PREFIX + '/preservation.json')['priorDataHashes']
    for path, expected in hashes.items():
        if digest(path) != expected:
            raise ValueError('Changed prior data: ' + path)
    return len(hashes)
