"""Official nomination table -> Stage40 claim events and complete-slate declarations.

The official table is a normalised, line-for-line transcription of the preserved Electoral Commission publication:
`{"schemaVersion": 1, "sourceId", "publishedAt", "rows": [{"electorateLabel", "displayName", "affiliationLabel",
"locator"}]}`. It is written by a publication-specific extractor once the format is known, and it carries no
judgement: every row becomes an `official_nomination` claim, and every seat in it is declared complete, because the
official list is the complete set of electorate nominations (James, 2026-10-07: the official list replaces party
announcements in the live roster).
"""
from collections import defaultdict
from datetime import datetime
from scripts.evidence.practical_candidate_linkage.names import normalize
from scripts.readiness.registry import PARTIES, occurrence_id, seat_key

INDEPENDENT = 'independent'
# Official affiliation labels that differ from the registered names. Extend only from the preserved publication.
ALIASES = {'independent': INDEPENDENT, 'national party': 'nationalparty', 'labour party': 'labourparty',
           'green party': 'greenparty', 'green party of aotearoa new zealand': 'greenparty', 'act': 'actnewzealand',
           'nz first': 'newzealandfirstparty', 'new zealand first': 'newzealandfirstparty',
           'the opportunity party': 'opportunity', 'top': 'opportunity', 'te pati maori': 'tepatimaori',
           'maori party': 'tepatimaori', 'alliance party': 'alliancepartyofaotearoanewzealand'}
# Affiliations printed in the 2026-10-10 official electorate list that are not registered parties (none appears in
# the party-list publication). Such a candidate has no party list and no party vote: like an independent, it has no
# ballot group. Each keeps its own key so the published label is not lost. Extend only from a preserved publication.
UNREGISTERED = ('Progressive Party of Aotearoa New Zealand', 'Money Free Party NZ', 'NAP', "People's Party New Zealand",
                'Economic Euthenics', 'New World Order McCann Party', 'Jobseeker Party', 'Socialist Equality Group',
                'Te Pāti Hira', 'Balance New Zealand', 'Your PIC Party')


class OfficialTableError(ValueError):
    pass


def affiliation_key(label):
    """Map an official affiliation label to a 2026 registered-party key, `independent`, or fail closed."""
    key = normalize(label)
    for target, name, _ in PARTIES:
        if key in (normalize(name), target):
            return target
    if key in ALIASES:
        return ALIASES[key]
    if key in {normalize(label) for label in UNREGISTERED}:
        return 'unregistered:' + key
    raise OfficialTableError(f'Unmapped official affiliation label: {label!r} (add an alias from the publication)')


def check_table(table):
    if table.get('schemaVersion') != 1 or not table.get('sourceId') or not table.get('rows'):
        raise OfficialTableError('Official table needs schemaVersion 1, a sourceId and rows')
    datetime.fromisoformat(table['publishedAt'].replace('Z', '+00:00'))
    seen = set()
    for i, row in enumerate(table['rows']):
        if set(row) != {'electorateLabel', 'displayName', 'affiliationLabel', 'locator'}:
            raise OfficialTableError(f'row {i}: fields must be electorateLabel, displayName, affiliationLabel, locator')
        if not all(isinstance(row[k], str) and row[k].strip() for k in row):
            raise OfficialTableError(f'row {i}: empty field')
        key = (seat_key(row['electorateLabel']), normalize(row['displayName']))
        if key in seen:
            raise OfficialTableError(f'row {i}: duplicate candidate in one electorate')
        seen.add(key)


def claims(table, source_key):
    """Stage40 claim events (status official_nomination, dated by the publication)."""
    check_table(table)
    return [{'sourceKey': source_key, 'displayName': row['displayName'].strip(),
             'sourceElectorateLabel': row['electorateLabel'].strip(), 'affiliationKey': affiliation_key(row['affiliationLabel']),
             'status': 'official_nomination', 'factDate': table['publishedAt'], 'publicationDate': table['publishedAt'],
             'passage': f"{row['displayName']} | {row['affiliationLabel']} | {row['electorateLabel']}", 'locator': row['locator'],
             'qualification': 'Official Electoral Commission nomination publication.'} for row in table['rows']]


def completeness(table, frame):
    """One official complete-slate declaration per electorate in the publication; every frame seat must appear."""
    seats = {seat_key(s['canonicalName']): s['targetElectorateId'] for s in frame}
    members = defaultdict(list)
    for row in table['rows']:
        label = seat_key(row['electorateLabel'])
        if label not in seats:
            raise OfficialTableError(f"Unresolved electorate label: {row['electorateLabel']!r}")
        seat = seats[label]
        members[seat].append(occurrence_id(seat, affiliation_key(row['affiliationLabel']), row['displayName'].strip()))
    missing = sorted(set(seats.values()) - set(members))
    if missing:
        raise OfficialTableError(f'{len(missing)} electorates have no official nomination: {missing[:5]}')
    return [{'targetElectorateId': seat, 'status': 'official_complete_nominations', 'sourceId': table['sourceId'],
             'publishedAt': table['publishedAt'], 'candidateOccurrenceIds': sorted(ids)} for seat, ids in sorted(members.items())]
