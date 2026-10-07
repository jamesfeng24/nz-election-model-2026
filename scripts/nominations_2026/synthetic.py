"""SYNTHETIC FIXTURES for tests and the release rehearsal only: a stand-in official nomination list and its registry.

The stand-in list is the 2026-10-05 party announcements plus one invented Labour and one invented independent
candidate per electorate, under a clearly fictitious elections.nz URL. It is never written to the repository's data,
never published and never mistaken for the official list (every invented id and name starts with "Synthetic").
"""
from scripts.readiness.registry import PARTIES
from scripts.uncertainty_revision.common import read
from . import refresh

PUBLISHED = '2026-10-08T15:00:00+13:00'
ACQUISITION = {'schemaVersion': 1, 'snapshotDateNZ': '2026-10-08', 'acquisitionCutoffUTC': '2026-10-08T03:00:00Z',
               'sourceRegistryPath': 'synthetic-test-registry.json', 'tables': []}


def table():
    names = {s['targetElectorateId']: s['canonicalName'] for s in read(refresh.PREVIOUS + 'target-frame.json')['records']}
    registered = {key: name for key, name, _ in PARTIES}
    rows = []
    for o in read(refresh.PREVIOUS + 'snapshot.json')['occurrences']:
        rows.append({'electorateLabel': names[o['targetElectorateId']], 'displayName': o['displayedName'],
                     'affiliationLabel': registered[o['originalAffiliation']], 'locator': f'synthetic-row-{len(rows)}'})
    for seat, name in sorted(names.items()):
        rows.append({'electorateLabel': name, 'displayName': f'Synthetic Labour {seat[-3:]}', 'affiliationLabel': 'Labour Party',
                     'locator': f'synthetic-row-{len(rows)}'})
        rows.append({'electorateLabel': name, 'displayName': f'Synthetic Independent {seat[-3:]}', 'affiliationLabel': 'Independent',
                     'locator': f'synthetic-row-{len(rows)}'})
    return {'schemaVersion': 1, 'sourceId': 'synthetic-official-nominations', 'publishedAt': PUBLISHED, 'rows': rows}


def registry():
    previous = {s['key']: s for s in read(refresh.STAGE40_MANIFEST)['sources']}
    raw = previous['nominations']
    return {'sources': [{'id': 'synthetic-official-nominations', 'resource': 'synthetic-official',
                         'url': 'https://elections.nz/synthetic-test-fixture', 'retrievedAt': '2026-10-08T02:30:00Z',
                         'rawPath': raw['rawPath'], 'sha256': raw['sha256']}]}


def refreshed():
    """In-memory Stage50 refresh outputs for the stand-in list."""
    return refresh.build(ACQUISITION, registry=registry(), tables=[('synthetic-official', table())])
