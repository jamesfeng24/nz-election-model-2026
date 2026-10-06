"""Unique voting-place venues of the 65 general-electorate files, and the 2020 seat polygons they must fall in."""
import re
import unicodedata

from shapely.geometry import Point

from scripts.boundaries.geometry import decode_layer

from .common import GEOMETRY_2020, GEOMETRY_2025, ROOT, read
from .nztm import forward
from .parse import candidate_path, general_numbers, nfc, parse_file

STREET = re.compile(r'^\d+[A-Za-z]?(?:[-/]\d+[A-Za-z]?)?\s+\D')
TAKEN = re.compile(r'^Taken in ')
ROVING = re.compile(r'\bTeams?\b|Pop-up Voting|Care Homes?|Mobile', re.I)


def fold(text):
    return unicodedata.normalize('NFC', text).casefold()


def street_part(venue):
    """The first comma-separated component that looks like '<number> <street ...>' (a ranged number keeps its first)."""
    for piece in (p.strip() for p in venue.split(',')):
        if STREET.match(piece):
            piece = re.sub(r'^(\d+[A-Za-z]?)[-/]\d+[A-Za-z]?\s', r'\1 ', piece)
            return re.sub(r'\s*\(.*$', '', piece).strip()
    return None


def venue_name(venue):
    """The venue text with bracketed notes removed and capped at the first two components."""
    text = re.sub(r'\([^)]*\)', ' ', venue)
    parts = [p.strip() for p in text.split(',') if p.strip()]
    return ', '.join(parts[:2])


def is_roving(row):
    """Rows with no physical address (care homes, hospital and similar teams, `Taken in X`)."""
    return bool(TAKEN.match(row['locality']) or ROVING.search(row['venue']))


def load_polygons(path, year):
    data = read(path)
    field = 'GED%d_V1_00' % year
    layer = decode_layer(data, field, field + '_NAME', len(data['features']))
    return {code: (attrs[field + '_NAME'], poly) for code, (attrs, poly) in layer.items()}


def seat_codes(polygons, tables):
    """Map each general file number to its 2020 polygon code by NFC-folded exact name, asserting a unique match."""
    by_name = {}
    for code, (name, _) in polygons.items():
        key = fold(name)
        if key in by_name:
            raise ValueError('Duplicate 2020 electorate name ' + name)
        by_name[key] = code
    mapping = {}
    for number, table in tables.items():
        key = fold(table['name'])
        if key not in by_name:
            raise ValueError('No 2020 polygon for file seat %s (%d)' % (table['name'], number))
        mapping[number] = by_name[key]
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Two files map to one 2020 polygon')
    return mapping


def load_tables(numbers=None):
    return {n: parse_file(candidate_path(n)) for n in (numbers or general_numbers())}


def venues(tables):
    """venue string -> {'localities': [...], 'files': [numbers]} over every general-file place row."""
    found = {}
    for number, table in tables.items():
        for row in table['places']:
            entry = found.setdefault(row['venue'], {'localities': [], 'files': []})
            if row['locality'] not in entry['localities']:
                entry['localities'].append(row['locality'])
            if number not in entry['files']:
                entry['files'].append(number)
    return found


def point_in_seats(x, y, polygons, codes, buffer_m):
    p = Point(x, y)
    return [c for c in codes if polygons[c][1].distance(p) <= buffer_m]


def project(lat, lon):
    return forward(lat, lon)
