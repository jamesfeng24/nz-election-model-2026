"""Offline, strict Esri polygon decoding; never repairs authoritative coordinates.

Esri exterior rings are clockwise and holes counterclockwise. Ring order does
not establish containment. All calculations here use the source NZTM CRS.
"""
import math
from shapely.geometry import LinearRing, MultiPolygon, Polygon
from shapely.validation import explain_validity


def decode_polygon(rings):
    """Preserve multipart islands and holes, rejecting malformed topology."""
    shells, holes = [], []
    for points in rings:
        if len(points) < 4 or points[0] != points[-1]:
            raise ValueError('Unclosed or underspecified ring')
        if any(len(p) != 2 or any(not math.isfinite(x) for x in p) for p in points):
            raise ValueError('Invalid two-dimensional coordinate')
        ring = LinearRing(points)
        polygon = Polygon(ring)
        if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
            raise ValueError('Invalid ring: ' + explain_validity(polygon))
        (holes if ring.is_ccw else shells).append(polygon)
    if not shells:
        raise ValueError('No exterior shell')
    interiors = [[] for _ in shells]
    for hole in holes:
        parents = [i for i, shell in enumerate(shells) if shell.covers(hole)]
        if not parents:
            raise ValueError('Hole has no containing shell')
        parent = min(parents, key=lambda i: shells[i].area)
        interiors[parent].append(list(hole.exterior.coords))
    geometry = MultiPolygon([
        Polygon(shell.exterior.coords, interiors[i]) for i, shell in enumerate(shells)
    ])
    if not geometry.is_valid:
        raise ValueError('Invalid multipart polygon: ' + explain_validity(geometry))
    return geometry


def decode_layer(data, code_field, name_field, expected_count, expected_crs=2193):
    """Return source attributes and topology-validated geometry keyed by code."""
    if data.get('error') or data.get('exceededTransferLimit'):
        raise ValueError('Error or truncated source response')
    if data.get('spatialReference', {}).get('wkid') != expected_crs:
        raise ValueError('Unexpected source CRS')
    features = data.get('features', [])
    if len(features) != expected_count:
        raise ValueError('Unexpected feature count')
    result = {}
    for feature in features:
        attributes = feature['attributes']
        code = attributes[code_field]
        if not code or code in result or not attributes[name_field]:
            raise ValueError('Missing/duplicate electorate identity')
        result[code] = (attributes, decode_polygon(feature['geometry']['rings']))
    return result
