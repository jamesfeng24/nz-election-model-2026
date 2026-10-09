"""Stage84 site map: simplified 2026 electorate outlines for the public site's clickable map.

Reads the preserved Stats NZ 2025 electoral boundaries (general and Maori, NZTM) and writes one compact JSON file of
SVG path data. Each outline is simplified with a tolerance that scales with the seat's own size, so city seats keep
their shape and large rural seats stay light. Nothing here is a boundary dataset for analysis: it is a drawing.

    python3 -m scripts.site_map.build
    python3 -m scripts.site_map.build --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {'general': ROOT / 'data/raw/boundaries/2020-2025/general-2025-geometry.json',
           'maori': ROOT / 'data/raw/boundaries/2020-2025/maori-2025-geometry.json'}
OUT = ROOT / 'data/processed/site-map/2026/map.json'
UNIT = 50.0                  # metres per drawing unit
MAINLAND_MAX_X = 2_300_000   # drops the Chatham Islands, which would shrink the map of the rest of the country
# Zoom windows (x, y, width, height) in drawing units, chosen to show the seats that are too small to click on the national map.
INSETS = {'Auckland': (13420, 6150, 620, 640), 'Hamilton': (14480, 8320, 360, 420),
          'Wellington': (12950, 15550, 1250, 1450), 'Christchurch': (9650, 20880, 1000, 520)}




def ring_area(ring):
    return abs(sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(len(ring) - 1))) / 2


def douglas_peucker(points, tolerance):
    """Iterative Douglas-Peucker on an open or closed list of (x, y); keeps the endpoints."""
    n = len(points)
    if n < 3:
        return list(points)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    t2 = tolerance * tolerance
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]
        bx, by = points[b]
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        far, far_d = -1, t2
        for i in range(a + 1, b):
            px, py = points[i]
            if length2 == 0:
                d = (px - ax) ** 2 + (py - ay) ** 2
            else:
                u = ((px - ax) * dx + (py - ay) * dy) / length2
                u = max(0.0, min(1.0, u))
                d = (px - (ax + u * dx)) ** 2 + (py - (ay + u * dy)) ** 2
            if d > far_d:
                far, far_d = i, d
        if far >= 0:
            keep[far] = True
            stack.append((a, far))
            stack.append((far, b))
    return [p for p, k in zip(points, keep) if k]


def tolerance_for(rings) -> float:
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    size = ((max(xs) - min(xs)) * (max(ys) - min(ys))) ** 0.5
    return max(15.0, min(450.0, 0.004 * size))


def outline(rings, origin) -> tuple[str, list[int]]:
    """A relative-coordinate SVG path for the mainland rings, and the bounding box in drawing units."""
    x0, y1 = origin
    tol = tolerance_for(rings)
    parts, box = [], [10**9, 10**9, -10**9, -10**9]
    for ring in sorted(rings, key=ring_area, reverse=True):
        if ring_area(ring) < 6 * tol * tol or sum(p[0] for p in ring) / len(ring) > MAINLAND_MAX_X:
            continue
        simple = douglas_peucker([(p[0], p[1]) for p in ring], tol)
        if len(simple) < 4:
            continue
        pts = [(round((x - x0) / UNIT), round((y1 - y) / UNIT)) for x, y in simple[:-1]]
        px, py = pts[0]
        seg = [f'M{px} {py}']
        for qx, qy in pts[1:]:
            seg.append(f'l{qx - px} {qy - py}')
            px, py = qx, qy
        parts.append(''.join(seg) + 'z')
        for qx, qy in pts:
            box = [min(box[0], qx), min(box[1], qy), max(box[2], qx), max(box[3], qy)]
    return ''.join(parts), box


def build() -> dict:
    data = {k: json.loads(p.read_text(encoding='utf-8')) for k, p in SOURCES.items()}
    xs = [p[0] for d in data.values() for f in d['features'] for r in f['geometry']['rings'] for p in r if p[0] < MAINLAND_MAX_X]
    ys = [p[1] for d in data.values() for f in d['features'] for r in f['geometry']['rings'] for p in r if p[0] < MAINLAND_MAX_X]
    origin = (min(xs), max(ys))
    seats = []
    for kind, d in data.items():
        code_field = next(f['name'] for f in d['fields'] if f['name'].endswith('_V1_00'))
        for feature in d['features']:
            attrs = feature['attributes']
            code = str(attrs[code_field]).lstrip('0') if kind == 'maori' else str(attrs[code_field])
            path, box = outline(feature['geometry']['rings'], origin)
            assert path, f'{attrs[code_field + "_NAME"]}: nothing left after simplification'
            seats.append({'id': f'nz-{kind}-2026-boundary-{code}', 'name': attrs[code_field + '_NAME'], 'kind': kind, 'path': path, 'box': box})
    seats.sort(key=lambda s: (s['kind'], s['id']))
    width, height = round((max(xs) - origin[0]) / UNIT), round((origin[1] - min(ys)) / UNIT)
    insets = [{'name': name, 'box': list(box)} for name, box in INSETS.items()]
    return {'schemaVersion': 1, 'unitMetres': UNIT, 'width': width, 'height': height, 'insets': insets, 'seats': seats,
            'source': 'Stats NZ electoral boundaries as at 2025 (NZTM), simplified for drawing; the Chatham Islands are not shown',
            'inputs': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES.values()}}


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
