"""Read-only polygon GeoPackage adapter using SQLite and OGC binary headers.

Header specification: https://www.geopackage.org/spec/#gpb_format
No database updates, spatial extensions, geometry repairs or source rewriting.
"""
import sqlite3
import struct
from shapely import from_wkb


def decode_geometry(raw, expected_crs):
    if raw is None:
        return None
    if len(raw) < 9 or raw[:3] != b'GP\x00':
        raise ValueError('Invalid GeoPackage binary header')
    flags = raw[3]
    envelope = (flags >> 1) & 7
    if flags & 0b11100000 or envelope > 4:
        raise ValueError('Unsupported GeoPackage flags/envelope')
    endian = '<' if flags & 1 else '>'
    if struct.unpack(endian + 'i', raw[4:8])[0] != expected_crs:
        raise ValueError('Geometry CRS does not match layer')
    offset = 8 + (0, 32, 48, 48, 64)[envelope]
    geometry = from_wkb(raw[offset:])
    if bool(flags & 16) != geometry.is_empty:
        raise ValueError('Empty geometry flag mismatch')
    if geometry.geom_type not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Expected polygon geometry')
    if not geometry.is_valid:
        raise ValueError('Invalid source geometry; no automatic repair')
    return geometry


def quote_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def read_polygons(path, expected_crs=2193):
    """Yield unchanged attributes and decoded polygons from a single-layer file."""
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        layers = conn.execute('SELECT * FROM gpkg_geometry_columns').fetchall()
        if len(layers) != 1:
            raise ValueError('Expected exactly one geometry layer')
        meta = dict(layers[0])
        if meta['srs_id'] != expected_crs or meta['z'] != 0 or meta['m'] != 0:
            raise ValueError('Unexpected layer CRS/dimensionality')
        if meta['geometry_type_name'] not in ('POLYGON','MULTIPOLYGON'):
            raise ValueError('Unexpected layer geometry type')
        table = meta['table_name']
        content = conn.execute('SELECT srs_id FROM gpkg_contents WHERE table_name=?', (table,)).fetchone()
        if content is None or content[0] != expected_crs:
            raise ValueError('Inconsistent GeoPackage content CRS')
        for row in conn.execute('SELECT * FROM ' + quote_identifier(table)):
            attributes = dict(row)
            geometry = decode_geometry(attributes.pop(meta['column_name']), expected_crs)
            yield attributes, geometry
