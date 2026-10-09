"""Located voting-place sites from the cached geocodes, and the split of a vote table into site votes and non-place votes."""
import numpy as np

from .geocode import read_cache, select
from .places import is_roving, load_polygons, load_tables, seat_codes, venues
from .common import GEOMETRY_2020

SIGMA = {'house': 50.0, 'street': 250.0, 'other': 100.0, 'locality': 1500.0}  # metres per axis, stated assumptions


def sigma_of(record):
    if record['houseNumber']:
        return SIGMA['house']
    if record['osmClass'] == 'highway':
        return SIGMA['street']
    if record['tier'] == 'locality':
        return SIGMA['locality']
    return SIGMA['other']


def locate(tables, cache=None):
    """venue -> located record (with `sigma`), omitting roving and unaccepted venues; also the polygons and seat codes."""
    cache = cache if cache is not None else read_cache()
    polygons = load_polygons(GEOMETRY_2020, 2020)
    codes = seat_codes(polygons, tables)
    located, unlocated = {}, []
    for venue, entry in sorted(venues(tables).items()):
        if is_roving({'locality': entry['localities'][0], 'venue': venue}):
            continue
        record = select(venue, entry['localities'], entry['files'], polygons, codes, cache)
        if record is None:
            unlocated.append(venue)
        else:
            located[venue] = {**record, 'sigma': sigma_of(record)}
    return located, unlocated, polygons, codes


def split_table(table, located):
    """(site venues, site vote matrix [S x C], non-place vote vector [C], unlocated-place vote vector [C]).

    Non-place votes = special rows + the fewer-than-six row + roving and unlocated place rows.
    """
    width = len(table['total'])
    sites, rows = [], {}
    other = np.zeros(width, dtype=np.int64)
    unlocated = np.zeros(width, dtype=np.int64)
    for row in table['places']:
        votes = np.array(row['votes'], dtype=np.int64)
        if row['venue'] in located:
            if row['venue'] not in rows:
                rows[row['venue']] = np.zeros(width, dtype=np.int64)
                sites.append(row['venue'])
            rows[row['venue']] += votes
        else:
            unlocated += votes
            other += votes
    for votes in list(table['specials'].values()) + ([table['suppressed']] if table['suppressed'] else []):
        other += np.array(votes, dtype=np.int64)
    matrix = np.array([rows[v] for v in sites], dtype=np.int64).reshape(len(sites), width)
    return sites, matrix, other, unlocated
