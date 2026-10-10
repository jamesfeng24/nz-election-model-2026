"""Stage84 site map: land-only outlines of the 2026 electorates for the public site's clickable map.

The Stats NZ electorate polygons run out to sea (a seat can include miles of water), which makes a map of blobs. This
builds each seat from the preserved 2025 meshblocks instead: only meshblocks with land area (the clipped coastline),
dissolved by general and by Maori electorate, simplified together so neighbouring seats keep a shared border, and written
as compact SVG path data. A seat on several islands stays one shape with several parts. Nothing here is an analysis
boundary: it is a drawing. Needs the offline boundary environment (`requirements-boundaries.txt`: shapely).

    python3 -m scripts.site_map.build
    python3 -m scripts.site_map.build --check      # re-derives from the raw files (about a minute) and compares
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARTS = sorted((ROOT / 'data/raw/boundaries/2020-2025/meshblock-export').glob('original.zip.part*'))
OUT = ROOT / 'data/processed/site-map/2026/map.json'
TABLE = '"2023_census_electoral_population_meshblock_2025_version_2"'
UNIT = 50.0                    # metres per drawing unit
SIMPLIFY_METRES = 300.0        # shared-border simplification tolerance
MIN_PART_KM2 = 1.0             # islets smaller than this are not drawn (the largest part of a seat always is)
MIN_HOLE_KM2 = 8.0             # smaller holes (inland water) are filled
# The drawn frame is the mainland: the Chatham Islands and the subantarctic islands would shrink the rest of the country.
FRAME = (1_050_000, 4_780_000, 2_200_000, 6_200_000)   # west, south, east, north in NZTM
# Zoom windows (x, y, width, height) in drawing units, chosen to show seats too small to click on the national map.
INSETS = {'Auckland': (12950, 5200, 1000, 760), 'Hamilton': (14030, 7360, 320, 360),
          'Wellington': (12880, 14880, 900, 820), 'Christchurch': (9200, 19950, 640, 580)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry_wkb(blob: bytes) -> bytes:
    """The WKB inside a GeoPackage geometry blob: skip the 8-byte header and the optional envelope."""
    envelope = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(blob[3] >> 1) & 7]
    return blob[8 + envelope:]


def land_meshblocks(gpkg: Path):
    """(general name, general code, maori name, maori code, WKB) for every meshblock with land."""
    con = sqlite3.connect(gpkg)
    try:
        yield from con.execute(f'select GED2025_V1_00_NAME, GED2025_V1_00, MED2025_V1_00_NAME, MED2025_V1_00, geom from {TABLE} where LAND_AREA_SQ_KM > 0')
    finally:
        con.close()


def dissolve() -> dict[tuple[str, str], tuple[str, object]]:
    """(kind, name) to (code, land polygon) for every seat."""
    import shapely
    groups: dict[tuple[str, str], tuple[str, list]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / 'meshblocks.zip'
        with zip_path.open('wb') as out:
            for part in PARTS:
                out.write(part.read_bytes())
        with zipfile.ZipFile(zip_path) as z:
            name = next(n for n in z.namelist() if n.endswith('.gpkg'))
            z.extract(name, tmp)
        for gname, gcode, mname, mcode, blob in land_meshblocks(Path(tmp) / name):
            geom = shapely.from_wkb(geometry_wkb(blob))
            groups.setdefault(('general', gname), (gcode, []))[1].append(geom)
            groups.setdefault(('maori', mname), (mcode, []))[1].append(geom)
    return {key: (code, shapely.union_all(geoms)) for key, (code, geoms) in groups.items()}


def parts_of(geometry):
    return list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]


def clean(geometry, kind_frame=FRAME):
    """Keep the parts that are in frame and big enough, and fill small holes."""
    import shapely
    west, south, east, north = kind_frame
    kept = []
    for part in parts_of(geometry):
        x, y = part.representative_point().x, part.representative_point().y
        if not (west <= x <= east and south <= y <= north):
            continue
        holes = [r for r in part.interiors if shapely.Polygon(r).area >= MIN_HOLE_KM2 * 1e6]
        kept.append(shapely.Polygon(part.exterior, holes))
    kept.sort(key=lambda p: p.area, reverse=True)
    big = [p for p in kept if p.area >= MIN_PART_KM2 * 1e6]
    return big or kept[:1]


def simplified(shapes: dict[tuple[str, str], list]) -> dict[tuple[str, str], list]:
    """Simplify each kind's seats as one coverage, so shared borders stay shared."""
    import shapely
    out = {}
    for kind in ('general', 'maori'):
        keys = sorted(k for k in shapes if k[0] == kind)
        collection = [shapely.MultiPolygon(shapes[k]) for k in keys]
        result = shapely.coverage_simplify(collection, SIMPLIFY_METRES)
        for k, geom in zip(keys, result):
            out[k] = [p for p in parts_of(geom) if not p.is_empty]
    return out


def path_for(polygons, origin) -> tuple[str, list[int]]:
    x0, y1 = origin
    parts, box = [], [10**9, 10**9, -10**9, -10**9]
    for polygon in polygons:
        for ring in [polygon.exterior, *polygon.interiors]:
            pts = [(round((x - x0) / UNIT), round((y1 - y) / UNIT)) for x, y in ring.coords[:-1]]
            pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
            if len(pts) < 3:
                continue
            px, py = pts[0]
            seg = [f'M{px} {py}']
            for qx, qy in pts[1:]:
                if (qx, qy) != (px, py):
                    seg.append(f'l{qx - px} {qy - py}')
                px, py = qx, qy
            parts.append(''.join(seg) + 'z')
            for qx, qy in pts:
                box = [min(box[0], qx), min(box[1], qy), max(box[2], qx), max(box[3], qy)]
    return ''.join(parts), box


def build() -> dict:
    dissolved = dissolve()
    cleaned = {k: clean(poly) for k, (_, poly) in dissolved.items()}
    flat = simplified(cleaned)
    xs = [x for polys in flat.values() for p in polys for x, _ in p.exterior.coords]
    ys = [y for polys in flat.values() for p in polys for _, y in p.exterior.coords]
    origin = (min(xs), max(ys))
    seats = []
    for (kind, name), polys in sorted(flat.items()):
        code = dissolved[(kind, name)][0]
        path, box = path_for(polys, origin)
        assert path, f'{name}: nothing left after simplification'
        seats.append({'id': f'nz-{kind}-2026-boundary-{code}', 'name': name, 'kind': kind, 'path': path, 'box': box})
    seats.sort(key=lambda s: (s['kind'], s['id']))
    return {'schemaVersion': 2, 'unitMetres': UNIT, 'width': round((max(xs) - origin[0]) / UNIT), 'height': round((origin[1] - min(ys)) / UNIT),
            'insets': [{'name': n, 'box': list(b)} for n, b in INSETS.items()], 'seats': seats,
            'source': 'Stats NZ 2023 Census electoral population meshblocks (2025 version 2): land meshblocks dissolved by 2025 electorate and simplified for drawing; the Chatham and subantarctic islands are not shown',
            'inputs': {p.relative_to(ROOT).as_posix(): sha256(p) for p in PARTS}}


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + '\n'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    text = render(build())
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            print(f'MISMATCH: {OUT.relative_to(ROOT)} differs from a fresh derivation', file=sys.stderr)
            return 1
        print(f'ok: {OUT.relative_to(ROOT)} reproduced')
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    print(f'wrote {OUT.relative_to(ROOT)}: {len(text) / 1024:.0f} KB')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
