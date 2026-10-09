"""Stage78 paths and artifact saving. Stage66 and Stage71 modules are imported read-only."""
from scripts.maori_seat_layer.common import ROOT, read, equivalent, SEATS, fold, YEARS
from scripts.transport.common import digest, encode

PREFIX = 'data/processed/maori-seat-fallback'
PLANS = 'data/source-plans/maori-seat-fallback'
DESIGN_DOC = 'docs/stage78-maori-fallback-design.md'
DESIGN = PREFIX + '/design-contract.json'
INPUTS = PLANS + '/inputs-2026.json'
STAGE66 = 'data/processed/maori-seat-layer'
STAGE71 = 'data/processed/maori-seat-calibration'
RESULTS = STAGE66 + '/historical-results.json'
HISTORICAL_POLLS = 'data/source-plans/maori-seat-layer/historical-polls.json'
CURRENT_POLLS = 'data/source-plans/maori-seat-layer/polls-2026.json'
ESTABLISHED_DEFAULT = ('MP', 'LAB', 'GRN', 'NAT', 'NZF', 'ALC', 'MANA')


def save(name, value, check=False, tolerance=1e-8):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage78 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))
