"""Write the Stage69 standalone dated source registry (data/sources.json is frozen and untouched).

python -m scripts.voting_place_notionals.registry
"""
import json

from .common import GEOCODE_RAW, NOMINATIM, PREFIX, ROOT, USER_AGENT, digest, encode

PARTY_URL = 'https://www.electionresults.govt.nz/electionresults_2023/statistics/csv/party-votes-by-voting-place-%d.csv'
PARTY_PATH = 'data/raw/elections/2023/statistics/csv/party-votes-by-voting-place-%d.csv'
LICENCE = 'Crown copyright; accurate reproduction with source acknowledgement permitted: https://www.electionresults.govt.nz/about.html'


def build():
    sources = []
    for n in range(1, 73):
        sources.append({
            'id': 'stage69-ec-2023-party-votes-by-voting-place-%d' % n,
            'organisation': 'New Zealand Electoral Commission', 'url': PARTY_URL % n,
            'dateOrElection': '2023 general election',
            'resource': 'party-votes-by-voting-place-%d.csv (%s)' % (n, 'general electorate' if n <= 65 else 'Māori electorate; not allocated by voting place in Stage69'),
            'retrievedAt': '2026-10-06T22:07:51Z to 2026-10-06T22:09:19Z',
            'acquisition': 'Downloaded unchanged by James through a normal browser from the official site (the site blocks the cloud environment) into a local folder, then staged byte-for-byte into the repository; no re-saving or encoding change.',
            'rawPath': PARTY_PATH % n, 'processingScript': 'scripts/voting_place_notionals/run.py',
            'sha256': digest(PARTY_PATH % n), 'licence': LICENCE, 'schemaVersion': 1})
    sources.append({
        'id': 'stage69-nominatim-voting-place-geocodes',
        'organisation': 'OpenStreetMap contributors via the public Nominatim service (nominatim.openstreetmap.org)',
        'url': NOMINATIM, 'dateOrElection': 'Queried 2026-10-06 to 2026-10-07 for the 2023 voting-place venues',
        'resource': 'Raw JSON responses, one line per query (query text, tier, HTTP status, retrieval time, response body)',
        'rawPath': GEOCODE_RAW, 'processingScript': 'scripts/voting_place_notionals/geocode.py',
        'sha256': digest(GEOCODE_RAW),
        'role': 'locations_of_voting_places_input_not_a_vote_source',
        'limitations': [
            'Venue addresses come from the Electoral Commission voting-place files, which publish no coordinates; positions are geocoded, so they carry error (assumed standard deviations in docs/stage69-voting-place-notionals.md).',
            'Queries ran one at a time with User-Agent "%s" (Nominatim usage policy: at most one request per second).' % USER_AGENT,
            'A venue is accepted only if the result lies inside, or within a stated buffer of, a 2020 electorate listing it; unaccepted venues are treated as non-place votes.'],
        'licence': 'Data © OpenStreetMap contributors, ODbL 1.0 (https://osm.org/copyright). Raw responses are retained as provenance; attribution required.',
        'schemaVersion': 1})
    return {'schemaVersion': 1, 'stage': 69,
            'note': 'Standalone dated registry (data/sources.json is frozen and untouched). Existing 2023 candidate-by-voting-place files, meshblock frame inputs, Stage64 baseline and the Tally Room sheet are registered elsewhere (data/sources.json, Stage64 registry).',
            'sources': sources}


if __name__ == '__main__':
    path = ROOT / PREFIX / 'source-registry.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode(build()))
    print('wrote', path.relative_to(ROOT))
