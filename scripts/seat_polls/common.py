"""Stage79 paths and artifact saving. Frozen stages are imported read-only."""
from scripts.maori_seat_layer.common import ROOT, read, equivalent, fold
from scripts.transport.common import digest, encode

PREFIX = 'data/processed/seat-polls'
DESIGN_DOC = 'docs/stage79-seat-poll-design.md'
DESIGN = PREFIX + '/design-contract.json'
POLLS = 'data/source-plans/seat-polls/polls.json'
RAW = 'data/raw/polling/seat-polls/2026-10-09'
REGISTRY = PREFIX + '/source-registry.json'
INVENTORY = 'data/processed/uncertainty/inventory.json'
SCALES = 'data/processed/uncertainty-revision/scales.json'
YEARS = (2014, 2017, 2020, 2023)


def save(name, value, check=False, tolerance=1e-9):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage79 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def parameters(design):
    """Numbers frozen in the contract's text fields (the contract is not edited after the freeze)."""
    import re
    rule = design['scoring']['adoptionRule']['adopt']
    band = [float(x) for x in re.search(r'\[(0\.\d+), (0\.\d+)\]', rule).groups()]
    return {'cap': float(re.search(r'min\((\d\.\d+),', design['update']['weight']).group(1)),
            'halfLifeWeeks': float(re.search(r'/ (\d+(?:\.\d+)?)\)', design['update']['ageFactor']).group(1)),
            'gainNats': float(re.search(r'>= (\d+(?:\.\d+)?) nat', rule).group(1)), 'coverageBand': band,
            'later': float(re.search(r'multiplied by (\d+(?:\.\d+)?)', design['pollError']['sameSourceMerge']).group(1)),
            'mergeDays': int(re.search(r'within (\d+) days', design['pollError']['sameSourceMerge']).group(1))}
