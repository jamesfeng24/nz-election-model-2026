"""Source-backed Māori winner overlay; never supplies cross-election identity."""

import hashlib
from pathlib import Path

from scripts.transform.historical import candidate_table as historical_candidates, count, key, read_csv
from scripts.transform.modern_tables import candidate_table as modern_candidates


YEARS = (2008, 2014, 2020)


def required_records(root, occurrences, registry):
    """Freeze exactly the preserved official files consumed by this overlay."""
    paths = {row['provenance']['inputPath'] for row in occurrences
             if row['year'] in YEARS and row['electorateType'] == 'maori'}
    paths.update(f'data/raw/elections/{year}/' +
                 ('e9/csv/e9_part6.csv' if year != 2020 else
                  'statistics/csv/winning-electorate-candidates.csv') for year in YEARS)
    by_path = {}
    ids = set()
    for record in registry['sources']:
        if record['rawPath'] in paths:
            if record['rawPath'] in by_path or record['id'] in ids:
                raise ValueError('Duplicate required source path or ID')
            by_path[record['rawPath']] = record
            ids.add(record['id'])
    if set(by_path) != paths:
        raise ValueError('Missing required Māori winner source record')
    for path, record in by_path.items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Changed required Māori winner raw bytes')
    return sorted(by_path.values(), key=lambda row: row['id'])


def verify_snapshot(root, occurrences, registry, snapshot):
    current = required_records(root, occurrences, registry)
    if current != snapshot['sources']:
        raise ValueError('Changed or deleted pinned Māori winner source record')
    registry_ids = [row['id'] for row in registry['sources']]
    if len(registry_ids) != len(set(registry_ids)):
        raise ValueError('Ambiguous source ID in registry')
    return current


def build_overlay(root: Path, occurrences, records):
    """Join unique official electorate winner labels to exact source occurrences."""
    by_path = {row['rawPath']: row for row in records}
    result = []
    for year in YEARS:
        summary_path = f'data/raw/elections/{year}/' + (
            'e9/csv/e9_part6.csv' if year != 2020 else
            'statistics/csv/winning-electorate-candidates.csv')
        summary_rows, _ = read_csv((root / summary_path).read_bytes())
        summary = {key(row[0]): row for row in summary_rows[2:] if len(row) >= 5}
        selected = [row for row in occurrences if row['year'] == year and
                    row['electorateType'] == 'maori']
        seats = {row['electorateName'] for row in selected}
        if len(seats) != 7 or len({key(s) for s in seats}) != 7:
            raise ValueError('Expected seven unique Māori electorates')
        for seat in sorted(seats):
            rows = [row for row in selected if row['electorateName'] == seat]
            paths = {row['provenance']['inputPath'] for row in rows}
            if len(paths) != 1:
                raise ValueError('Ambiguous Māori candidate table')
            path = paths.pop()
            raw = (root / path).read_bytes()
            if year == 2020:
                election_seats = {row['electorateName'] for row in occurrences
                                  if row['year'] == 2020}
                parsed = modern_candidates(raw, electorate_names=election_seats)
            else:
                parsed = historical_candidates(raw)
            official = summary.get(key(seat))
            expected_label = f"{seat} {rows[0]['sourceElectorateNumber']}"
            if official is None or key(parsed['sourceElectorateLabel']) != key(expected_label):
                raise ValueError('Māori winner electorate join failed')
            winner = [row for row in rows if row['sourceCandidateName'] == official[1] and
                      row['sourcePublishedCandidateVotes'] == count(official[3])]
            if len(winner) != 1 or parsed['winnerName'] != official[1] or parsed['majority'] != count(official[4]):
                raise ValueError('Māori winner name, votes or majority failed to reconcile')
            if len(rows) != len(parsed['candidates']):
                raise ValueError('Māori candidate occurrence count mismatch')
            for row in rows:
                matches = [candidate for candidate in parsed['candidates']
                           if candidate['name'] == row['sourceCandidateName'] and
                           candidate['votes'] == row['sourcePublishedCandidateVotes']]
                if len(matches) != 1:
                    raise ValueError('Māori candidate occurrence join failed')
            result.append({'year': year, 'electorateName': seat,
                           'winnerOccurrenceId': winner[0]['candidateOccurrenceId'],
                           'winnerName': official[1], 'winnerVotes': count(official[3]),
                           'majority': count(official[4]),
                           'candidateSourceId': by_path[path]['id'],
                           'summarySourceId': by_path[summary_path]['id']})
    return {'schemaVersion': 1, 'records': result}
