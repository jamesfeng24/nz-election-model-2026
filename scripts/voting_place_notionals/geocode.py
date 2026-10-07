"""Acquire OpenStreetMap Nominatim geocodes for the 2023 voting-place venues (acquisition step; resumable).

python -m scripts.voting_place_notionals.geocode

Queries run strictly one at a time with an identifying User-Agent and a 0.6 s pause after each (request latency keeps the total above 1 s, per the Nominatim usage policy). Every raw response is appended to the
JSONL cache before it is used. A venue gets up to three queries in a fixed order (street address, venue name, locality)
and the first query whose best result lands inside (a buffer around) a 2020 seat that lists the venue is accepted; the
2020 polygon test uses only the known election-day geography, never any vote count. Selection from the cached responses
is deterministic and is redone offline by `build` (`select`), so regeneration never touches the network.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .common import GEOCODE_RAW, NOMINATIM, ROOT, USER_AGENT, GEOMETRY_2020
from .places import (is_roving, load_polygons, load_tables, point_in_seats, project, seat_codes, street_part, venue_name,
                     venues)

BUFFERS = {'address': 1500.0, 'venue': 1500.0, 'locality': 5000.0}  # metres around the listing seats' 2020 polygons
SLEEP = 0.6


def queries(venue, locality):
    """Fixed-order query ladder for one venue: (tier, query text)."""
    ladder = []
    street = street_part(venue)
    if street:
        ladder.append(('address', '%s, %s, New Zealand' % (street, locality)))
        ladder.append(('address', '%s, New Zealand' % street))
    ladder.append(('venue', '%s, %s, New Zealand' % (venue_name(venue), locality)))
    ladder.append(('locality', '%s, New Zealand' % locality))
    return ladder


def read_cache():
    path = ROOT / GEOCODE_RAW
    cache = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            record = json.loads(line)
            cache[record['query']] = record
    return cache


def fetch(query):
    params = urllib.parse.urlencode({'q': query, 'format': 'jsonv2', 'countrycodes': 'nz', 'limit': 5, 'addressdetails': 1})
    request = urllib.request.Request(NOMINATIM + '?' + params, headers={'User-Agent': USER_AGENT, 'Accept-Language': 'en'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, response.read().decode('utf-8')
        except Exception as error:  # pragma: no cover - network behaviour
            time.sleep(5 * (attempt + 1))
            last = str(error)
    return 0, json.dumps({'error': last})


def results_of(record):
    try:
        body = json.loads(record['body'])
    except ValueError:
        return []
    return body if isinstance(body, list) else []


def select(venue, localities, files, polygons, codes, cache):
    """Deterministic acceptance over cached responses; returns a record or None. Never fetches."""
    allowed = [codes[n] for n in files]
    for locality in localities:
        for tier, query in queries(venue, locality):
            record = cache.get(query)
            if record is None:
                return None  # the ladder is strictly ordered: an unqueried earlier step is tried first
            for rank, hit in enumerate(results_of(record)):
                x, y = project(float(hit['lat']), float(hit['lon']))
                inside = point_in_seats(x, y, polygons, allowed, BUFFERS[tier])
                if inside:
                    return {'tier': tier, 'query': query, 'rank': rank, 'lat': float(hit['lat']), 'lon': float(hit['lon']),
                            'x': x, 'y': y, 'osmType': hit.get('osm_type'), 'osmId': hit.get('osm_id'),
                            'osmClass': hit.get('category', hit.get('class')), 'osmKind': hit.get('type'),
                            'houseNumber': (hit.get('address') or {}).get('house_number'),
                            'insideSeats': inside}
    return None


def main():
    tables = load_tables()
    polygons = load_polygons(GEOMETRY_2020, 2020)
    codes = seat_codes(polygons, tables)
    found = venues(tables)
    cache = read_cache()
    path = ROOT / GEOCODE_RAW
    path.parent.mkdir(parents=True, exist_ok=True)
    todo = [v for v in sorted(found) if not is_roving({'locality': found[v]['localities'][0], 'venue': v})]
    done = 0
    with path.open('a', encoding='utf-8') as out:
        for venue in todo:
            entry = found[venue]
            if select(venue, entry['localities'], entry['files'], polygons, codes, cache):
                continue
            for locality in entry['localities']:
                for tier, query in queries(venue, locality):
                    if query not in cache:
                        status, body = fetch(query)
                        record = {'query': query, 'tier': tier, 'status': status,
                                  'retrievedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'body': body}
                        cache[query] = record
                        out.write(json.dumps(record, ensure_ascii=False) + '\n')
                        out.flush()
                        time.sleep(SLEEP)
                    if select(venue, [locality], entry['files'], polygons, codes, cache):
                        break
                else:
                    continue
                break
            done += 1
            if done % 50 == 0:
                print('venues processed', done, 'of', len(todo), flush=True)
    print('geocode acquisition finished; cached queries', len(cache))


if __name__ == '__main__':
    main()
