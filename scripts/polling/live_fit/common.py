"""Stage62 live 2026 national poll fit: shared paths and deterministic I/O. Internal outputs only."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/processed/polling/live-fit-2026-10'
EXT = ROOT / 'data/processed/polling/external-comparison'
RAW38 = ROOT / 'data/raw/polling/stage38'
RAW52 = ROOT / 'data/raw/polling/current-2026-primary'
WIKI2026 = RAW52 / 'wikipedia-opinion-polling-2026.html'
PANEL = ROOT / 'data/processed/polling/panel-update-2026-10/panel.json'
UPSTREAM = ROOT / '.cache/stage38/upstream'
CACHE = ROOT / '.cache/stage62'
LOCK = ROOT / 'requirements-external.lock'
PIN = 'ef76cf6562e1d028b4fff46d063f4b93945299de'

TARGET_YEAR = 2026
CUTOFF = '2026-10-06'
WINDOWED_YEARS = (2014, 2017, 2020, 2023)
SEED = 2034
PRIMARY = {'chains': 4, 'warmup': 2000, 'samples': 2000, 'target_accept': .95, 'max_tree_depth': 12}
RETRY = {**PRIMARY, 'warmup': 4000, 'target_accept': .99, 'max_tree_depth': 15}
CODES = {'National': 'NAT', 'Labour': 'LAB', 'Green': 'GRN', 'ACT': 'ACT', 'NZ First': 'NZF',
         'Te Pāti Māori': 'TPM', 'TOP': 'TOP', 'Other': 'OTH'}
# Pre-registered arms (docs/stage62-live-poll-fit-design.md section 5). Order is the execution order.
ARMS = {
    'A': {'seed': SEED},
    'A2': {'seed': SEED + 1},
    'B1': {'seed': SEED, 'window': '2026-06-01'},
    'B2': {'seed': SEED, 'window': '2026-08-11'},
    'E': {'seed': SEED, 'drop_aggregator_only': True},
    'T': {'seed': SEED, 'merge_anacta': True},
}
DATASET_OF = {'A': 'A', 'A2': 'A', 'B1': 'B1', 'B2': 'B2', 'E': 'E', 'T': 'T'}
ENV_CHECK = 'ENV2017'


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    p = Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())


def save(path, value, check=False):
    p = OUT / path
    raw = encode(value)
    if p.suffix == '.gz':
        raw = bytearray(gzip.compress(raw, mtime=0)); raw[9] = 255; raw = bytes(raw)
    if check:
        if p.read_bytes() != raw:
            raise ValueError('Changed deterministic artifact ' + str(path))
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp'); tmp.write_bytes(raw); tmp.replace(p)


def lock_versions():
    out = {}
    for line in LOCK.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            name, version = line.split('==')
            out[name.lower().replace('_', '-')] = version
    return out
