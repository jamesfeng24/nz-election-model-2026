"""Meshblock frame for the general electorates: 2020 source seat, 2025 target seat, electoral population, centroid.

Built from the preserved 2025 meshblock export (original archive reassembled from verified segments) and the Stage4 membership
join; nothing is imputed. Population is the released random-rounded general electoral population; suppressed cells (<6)
enter as 0 and are counted, since their total is bounded by 5 per meshblock (see audit).
"""
import csv
import gzip
import io
import json
import tempfile
import zipfile
from pathlib import Path

from scripts.boundaries.archive import archive_bytes
from scripts.boundaries.current_inputs import load
from scripts.boundaries.geopackage import read_polygons

from .common import ROOT, PREFIX

FRAME = PREFIX + '/meshblock-frame.csv.gz'
FIELDS = ['meshblock', 'source', 'target', 'population', 'suppressed', 'x', 'y']


def build_rows():
    inputs = load()
    plan = json.loads((ROOT / 'data/source-plans/meshblock-2025-export.json').read_bytes())
    raw = archive_bytes(plan, root=ROOT)
    cells = {c['meshblockId']: c for c in inputs['cells']['general']}
    centroid = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive, tempfile.TemporaryDirectory() as temp:
        gpkg = next(m['name'] for m in plan['members'] if m['name'].endswith('.gpkg'))
        path = Path(temp) / 'meshblocks.gpkg'
        path.write_bytes(archive.read(gpkg))
        for attributes, geometry in read_polygons(path):
            point = geometry.centroid
            centroid[attributes['MB2025_V2_00']] = (round(point.x, 1), round(point.y, 1))
    if centroid.keys() != cells.keys():
        raise ValueError('Meshblock geometry and membership inventories differ')
    rows = []
    for code in sorted(cells):
        cell = cells[code]
        population = cell['population']
        rows.append({'meshblock': code, 'source': cell['source'], 'target': cell['target'],
                     'population': population['value'] or 0, 'suppressed': int(population['value'] is None),
                     'x': centroid[code][0], 'y': centroid[code][1]})
    return rows, inputs['inputHashes']


def encode(rows):
    text = io.StringIO()
    writer = csv.DictWriter(text, FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return gzip.compress(text.getvalue().encode(), mtime=0)


def read_rows():
    with gzip.open(ROOT / FRAME, 'rt') as handle:
        return [{**r, 'population': int(r['population']), 'suppressed': int(r['suppressed']),
                 'x': float(r['x']), 'y': float(r['y'])} for r in csv.DictReader(handle)]


if __name__ == '__main__':
    rows, hashes = build_rows()
    (ROOT / FRAME).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / FRAME).write_bytes(encode(rows))
    print(len(rows), 'meshblocks', sum(r['population'] for r in rows), 'general electoral population')
