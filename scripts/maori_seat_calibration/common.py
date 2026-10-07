"""Stage71 paths, eras and artifact saving. Stage66 modules are imported read-only."""
from scripts.maori_seat_layer.common import ROOT, read, equivalent, YEARS
from scripts.transport.common import digest, encode

PREFIX = 'data/processed/maori-seat-calibration'
DESIGN_DOC = 'docs/stage71-maori-seat-calibration-design.md'
DESIGN = PREFIX + '/design-contract.json'
STAGE66 = 'data/processed/maori-seat-layer'


def era(pollster):
    return 'Reid' if 'Reid' in pollster else 'Curia'


def save(name, value, check=False, tolerance=1e-8):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage71 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))
