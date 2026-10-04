"""Small deterministic readers for companion artifacts, never inference."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/processed/polling/category-interface'
NATIONAL = ROOT / 'data/processed/polling/national-backtest'
RAW = ROOT / 'data/raw/polling/stage37'
CORE = {'NAT': 'nationalparty', 'LAB': 'labourparty', 'GRN': 'greenparty',
        'ACT': 'actnewzealand', 'NZF': 'newzealandfirstparty', 'MRI': 'maoriparty',
        'TOP': 'theopportunitiespartytop'}


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable_gzip(raw):
    """Canonical unknown-platform marker; compressed content is unchanged."""
    encoded = gzip.compress(raw, mtime=0)
    return encoded[:9] + bytes([255]) + encoded[10:]


def save(name, value, check=False):
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False) + '\n').encode()
    if name.endswith('.gz'):
        raw = portable_gzip(raw)
    path = OUT / name
    if check:
        if path.read_bytes() != raw:
            raise ValueError('Stale Stage37 ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def verify_inputs():
    ledger = read(RAW / 'acquisition-ledger.json')
    attempts = ledger['attempts']
    if len({r['url'] for r in attempts}) != ledger['distinctResources'] or ledger['distinctResources'] > 20:
        raise ValueError('External acquisition budget accounting')
    for row in attempts:
        if sha(ROOT / row['rawPath']) != row['sha256']:
            raise ValueError('Changed acquired resource: ' + row['rawPath'])
    for path, expected in read(OUT / 'input-contract.json')['inputSha256'].items():
        if sha(ROOT / path) != expected:
            raise ValueError('Changed consumed input: ' + path)


def simplex(values, tolerance=1e-12):
    import math
    if not values or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid simplex values')
    if abs(math.fsum(values) - 1) > tolerance:
        raise ValueError('Nonconserving simplex')
