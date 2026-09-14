"""2020→2025 source adapter: immutable official membership and disclosure bounds."""
import csv
import hashlib
import io
import json
from pathlib import Path
from scripts.boundaries.membership import index_rows, read_csv_zip, join_memberships
from scripts.boundaries.population import population_interval
from scripts.boundaries.feasible import aggregate

ROOT = Path(__file__).resolve().parents[2]


def load():
    registry = json.loads((ROOT / 'data/sources.json').read_bytes())['sources']
    hashes = {}

    def read(path, registered=True):
        raw = (ROOT / path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if registered:
            matches = [s for s in registry if s['rawPath'] == path]
            if len(matches) != 1 or matches[0]['sha256'] != digest:
                raise ValueError('Unregistered or altered source: ' + path)
        hashes[path] = digest
        return raw

    folder = 'data/raw/boundaries/2020-2025/'
    population = index_rows(csv.DictReader(io.StringIO(read(folder + 'population-2025.csv').decode('utf-8-sig'))), 'MB2025_V2_00')
    source_table = read_csv_zip(read(folder + 'geographic-areas-table-2025.zip'), 'geographic-areas-table-2025.csv', 'MB2025_code')
    lineage = read_csv_zip(read(folder + 'geographic-areas-table-2026.zip'), 'geographic-areas-table-2026.csv', 'MB2026_code')
    source_names, target_names = {}, {}
    for kind, prefix in [('general', 'GED'), ('maori', 'MED')]:
        for year, names in [(2020, source_names), (2025, target_names)]:
            features = json.loads(read(folder + f'{kind}-{year}-geometry.json'))['features']
            names[kind] = {f['attributes'][f'{prefix}{year}_V1_00']: f['attributes'][f'{prefix}{year}_V1_00_NAME'] for f in features}
    memberships = join_memberships(population, source_table, source_names, lineage)
    controls = json.loads(read('data/controls/boundaries/2025-population-controls.json', False))
    read(folder + 'schedule-c.pdf')
    changes = json.loads(read('data/controls/boundaries/2025-change-controls.json', False))
    read(folder + 'schedule-b.pdf')
    totals = {'general': {}, 'maori': {}}
    for control in controls['electorates']:
        kind, code = control['electorateType'], control['sourceCode']
        if code in totals[kind] or target_names[kind][code] != control['name']:
            raise ValueError('Invalid or duplicate official target control')
        totals[kind][code] = control['electoralPopulation']
    cells = {'general': [], 'maori': []}
    for membership in memberships:
        if membership['membershipStatus'] == 'unresolved':
            raise ValueError('Unresolved source membership')
        code = membership['meshblockId']
        for kind, field in [('general', 'GENERAL_ELECTORAL_POPULATION'), ('maori', 'MAORI_ELECTORAL_POPULATION')]:
            links = membership['memberships'][kind]
            if target_names[kind][links['targetCode']] != links['targetName']:
                raise ValueError('Target code/name mismatch')
            cells[kind].append({'meshblockId': code, 'source': links['sourceCode'],
                                'target': links['targetCode'], 'population': population_interval(population[code][field]),
                                'membershipMethod': membership['membershipStatus'],
                                'sourceConcordanceMeshblockId': membership['sourceConcordanceMeshblockId']})
    return {'cells': cells, 'controls': totals, 'sourceNames': source_names,
            'targetNames': target_names, 'changes': changes, 'inputHashes': hashes}

