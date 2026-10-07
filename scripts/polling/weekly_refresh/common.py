"""Stage70 weekly national poll refresh: shared paths, constants and deterministic I/O. Internal outputs only."""
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'data/raw/polling/weekly-refresh'
OUT = ROOT / 'data/processed/polling/weekly-refresh'
INDEX = OUT / 'index.json'
FRAGMENTS = ROOT / 'handoff.d'
# The chain starts from the Stage59 panel and the Stage62 primary live fit (arm A); neither is ever edited.
BASE_PANEL = ROOT / 'data/processed/polling/panel-update-2026-10/panel.json'
BASE_ESTIMATE = ROOT / 'data/processed/polling/live-fit-2026-10/summary/A.json'
WIKI_URL = 'https://en.wikipedia.org/api/rest_v1/page/html/Opinion_polling_for_the_2026_New_Zealand_general_election'
USER_AGENT = 'nz-election-model-research/1.0'
CAPTURE = 'wikipedia-opinion-polling-2026.html'
TARGET_YEAR = 2026
ELECTION_DAY = date(2026, 11, 7)
TIMEZONE = 'Pacific/Auckland'
CORE = ('NAT', 'LAB', 'GRN', 'ACT', 'NZF')
ESTIMATE_SHIFT_PP = 1.0     # Stage62 descriptive materiality threshold for NAT or LAB (design section 7)
SPAN_FACTOR = 1.25          # a fieldwork span above 1.25x the pollster's longest span in the cycle is flagged
SPAN_FLOOR_DAYS = 14
LATE_DAYS = 14


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n').encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_bytes(encode(value))
    tmp.replace(p)


def rel(path):
    return str(Path(path).relative_to(ROOT))


def load_index():
    return read(INDEX) if INDEX.exists() else {'schemaVersion': 1, 'runs': []}


def previous_base():
    """(panel path, estimate record or path, label) of the latest published run, else the Stage59/Stage62 base."""
    runs = load_index()['runs']
    if runs:
        d = OUT / runs[-1]['date']
        return d / 'panel.json', d / 'estimate.json', runs[-1]['date']
    return BASE_PANEL, BASE_ESTIMATE, None
