"""Audit preserved final meshblock geometry, population and published controls."""
import argparse
import csv
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path
from scripts.boundaries.archive import archive_bytes
from scripts.boundaries.geopackage import read_polygons
from scripts.boundaries.membership import index_rows
from scripts.boundaries.population import population_interval

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'data/processed/boundaries/2020-2025/population-validation.json'


def build():
    plan_path = ROOT / 'data/source-plans/meshblock-2025-export.json'
    plan = json.loads(plan_path.read_bytes())
    raw = archive_bytes(plan, root=ROOT)
    folder = ROOT / 'data/raw/boundaries/2020-2025'
    population_raw = (folder / 'population-2025.csv').read_bytes()
    population = index_rows(csv.DictReader(io.StringIO(population_raw.decode('utf-8-sig'))), 'MB2025_V2_00')
    groups = {}
    for row in population.values():
        for kind, prefix, field in [('general', 'GED', 'GENERAL_ELECTORAL_POPULATION'),
                                     ('maori', 'MED', 'MAORI_ELECTORAL_POPULATION')]:
            key = kind, row[prefix + '2025_V1_00']
            cell = population_interval(row[field])
            group = groups.setdefault(key, {'lower': 0, 'upper': 0, 'releasedSum': 0,
                                           'suppressedMeshblocks': 0, 'meshblocks': 0})
            for bound in ('lower', 'upper'):
                group[bound] += cell[bound]
            group['releasedSum'] += cell['value'] if cell['value'] is not None else 0
            group['suppressedMeshblocks'] += cell['value'] is None
            group['meshblocks'] += 1
    # Zero here is an accumulator of released values only, never an imputed cell.
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError('Meshblock archive CRC mismatch')
        for member in plan['members']:
            content = archive.read(member['name'])
            if len(content) != member['bytes'] or hashlib.sha256(content).hexdigest() != member['sha256']:
                raise ValueError('Archive member checksum mismatch')
        csv_member = next(m['name'] for m in plan['members'] if m['name'].endswith('-data.csv'))
        if archive.read(csv_member) != population_raw:
            raise ValueError('Export CSV differs from preserved population CSV')
        gpkg_member = next(m['name'] for m in plan['members'] if m['name'].endswith('.gpkg'))
        seen = set()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'meshblocks.gpkg'
            path.write_bytes(archive.read(gpkg_member))
            for attributes, geometry in read_polygons(path):
                code = attributes['MB2025_V2_00']
                if code in seen or code not in population or geometry is None or geometry.is_empty:
                    raise ValueError('Missing/duplicate meshblock geometry')
                seen.add(code)
                for field, value in population[code].items():
                    if field.startswith(('MB', 'GED', 'MED')) or field.endswith('ELECTORAL_POPULATION'):
                        if str(attributes[field]) != value:
                            raise ValueError('GeoPackage/CSV attribute mismatch: ' + code + '/' + field)
        if seen != population.keys():
            raise ValueError('Incomplete geometry inventory')
    controls_path = ROOT / 'data/controls/boundaries/2025-population-controls.json'
    controls = json.loads(controls_path.read_bytes())
    registry = {s['id']: s for s in json.loads((ROOT / 'data/sources.json').read_bytes())['sources']}
    source = registry[controls['sourceId']]
    if hashlib.sha256((ROOT / source['rawPath']).read_bytes()).hexdigest() != source['sha256']:
        raise ValueError('Schedule C checksum mismatch')
    results = []
    keys = set()
    for control in controls['electorates']:
        key = control['electorateType'], control['sourceCode']
        if key in keys:
            raise ValueError('Duplicate population control')
        keys.add(key)
        group = groups[key]
        if not group['lower'] <= control['electoralPopulation'] <= group['upper']:
            raise ValueError('Population control outside disclosure bounds: ' + control['name'])
        results.append({**control, **group, 'withinDisclosureBounds': True})
    if keys != groups.keys():
        raise ValueError('Population control coverage mismatch')
    return {'schemaVersion': 1, 'status': 'inventory_and_disclosure_controls_validated',
            'isVoteTransferOutput': False, 'meshblockCount': len(seen),
            'allGeometriesValidWithoutRepair': True, 'allPopulationAndTargetFieldsMatch': True,
            'originalArchiveSha256': plan['originalSha256'],
            'populationCsvSha256': hashlib.sha256(population_raw).hexdigest(),
            'controlSha256': hashlib.sha256(controls_path.read_bytes()).hexdigest(),
            'officialControlSourceId': controls['sourceId'], 'officialControlSha256': source['sha256'],
            'targetControls': results,
            'limitations': ['Disclosure intervals are not confidence intervals or exact recovered counts.',
                            'Suppressed cells remain unavailable; releasedSum excludes them without imputing zero.',
                            'No population allocation weights or notional votes have been estimated.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build()
    raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != raw:
            raise SystemExit('Stale population audit')
    else:
        OUTPUT.write_bytes(raw)
    print(f"Validated {result['meshblockCount']} meshblocks and {len(result['targetControls'])} population controls")


if __name__ == '__main__':
    main()
