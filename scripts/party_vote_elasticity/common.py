"""Stage81 paths, constants and artifact saving. The design contract is the single source of every threshold."""
from scripts.maori_seat_layer.common import ROOT, read, equivalent
import hashlib
from scripts.transport.common import digest, encode

PREFIX = 'data/processed/party-vote-elasticity'
DESIGN = PREFIX + '/design-contract.json'
DESIGN_DOC = 'docs/stage81-party-vote-elasticity-design.md'
RECORDS = 'data/processed/models/party-vote-transform/backtest-records.json'
PRIMARY = ((2014, 2017), (2017, 2020), (2020, 2023))
SECONDARY = ((2008, 2011), (2011, 2014))
ARMS = ('P', 'A', 'L', 'H')
PROFILE = (('P', 'P'), ('0.25', 0.25), ('H', 'H'), ('0.75', 0.75), ('A', 'A'))
EPSILON = 1e-6


def save(name, value, check=False, tolerance=1e-8):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage81 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def file_sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
