"""Stage66 paths, seat inventory, artifact saving and tolerance-based equivalence."""
import math
import re
import unicodedata
from scripts.transport.common import ROOT, digest, encode

PREFIX = 'data/processed/maori-seat-layer'
PLANS = 'data/source-plans/maori-seat-layer'
HISTORICAL_POLLS = PLANS + '/historical-polls.json'
CURRENT_POLLS = PLANS + '/polls-2026.json'
REGISTRY = PREFIX + '/source-registry.json'
DESIGN_DOC = 'docs/stage66-maori-seat-layer-design.md'
DESIGN = PREFIX + '/design-contract.json'
RAW = 'data/raw/polling/maori-electorate-historical/2026-10-06'

SEATS = ('Hauraki-Waikato', 'Ikaroa-Rāwhiti', 'Tāmaki Makaurau', 'Te Tai Hauāuru', 'Te Tai Tokerau', 'Te Tai Tonga', 'Waiariki')
ELECTION_DATES = {2014: '2014-09-20', 2017: '2017-09-23', 2020: '2020-10-17', 2023: '2023-10-14', 2026: '2026-11-07'}
YEARS = (2014, 2017, 2020, 2023)
# Official party labels (Electoral Commission files) to the frozen party codes. Unlisted labels map to 'OTH'.
PARTY_CODES = {'Labour Party': 'LAB', 'Māori Party': 'MP', 'Te Pāti Māori': 'MP', 'MANA Movement': 'MANA', 'MANA': 'MANA', 'Mana Party': 'MANA',
               'Green Party': 'GRN', 'National Party': 'NAT', 'Aotearoa Legalise Cannabis Party': 'ALC',
               'New Zealand First Party': 'NZF', 'Independent': 'IND'}
GROUP = {'MP': 'MP', 'LAB': 'LAB'}  # every other code is group OTH


def group(code):
    return GROUP.get(code, 'OTH')


def fold(text):
    """Lower-case ASCII key: macrons and punctuation removed, so Māori/Maori and Hauāuru/Hauauru agree."""
    text = unicodedata.normalize('NFKD', text)
    return re.sub(r'[^a-z0-9]+', '', ''.join(c for c in text if not unicodedata.combining(c)).lower())


def read(path):
    import json
    return json.loads((ROOT / path).read_bytes())


def equivalent(expected, actual, tolerance=1e-10):
    if isinstance(expected, dict):
        return (isinstance(actual, dict) and expected.keys() == actual.keys()
                and all(equivalent(v, actual[k], tolerance) for k, v in expected.items()))
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(expected) == len(actual)
                and all(equivalent(a, b, tolerance) for a, b in zip(expected, actual)))
    if isinstance(expected, float) and isinstance(actual, (float, int)) and not isinstance(actual, bool):
        return math.isfinite(actual) and abs(expected - actual) <= tolerance
    return type(expected) == type(actual) and expected == actual


def save(name, value, check=False, tolerance=1e-10):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage66 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))
