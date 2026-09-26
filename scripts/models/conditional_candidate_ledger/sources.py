"""Stage-specific raw-source dependencies for the conditional ledger."""

import argparse
import json
from pathlib import Path

from scripts.validate.source_files import verify_source_files


ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = Path('data/source-plans/stage15-conditional-ledger-sources.json')
SOURCE_YEARS = (2008, 2014, 2020)
TARGET_YEARS = (2011, 2017, 2023)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def consumed_ids(elections, splits):
    """Use every general source seat and target seat actually read by Stage 15."""
    ids = set()
    for year in SOURCE_YEARS + TARGET_YEARS:
        ids.update(sid for seat in elections[year]['electorates']
                   if seat['kind'] == 'general' for sid in seat['sourceIds'])
    for year in SOURCE_YEARS:
        ids.update(sid for matrix in splits[year]['matrices']
                   for sid in matrix['sourceIds'])
    return ids


def snapshot(registry, elections, splits):
    records = registry['sources']
    indexed = {record['id']: record for record in records}
    if len(indexed) != len(records):
        raise ValueError('Duplicate registry source ID')
    required = consumed_ids(elections, splits)
    if required - indexed.keys():
        raise ValueError('Missing consumed registry source ID')
    return {'schemaVersion': 1, 'stage': 15,
            'selection': 'all source/target general seat source IDs and source local split matrix source IDs; unrelated registry additions allowed',
            'sources': [indexed[sid] for sid in sorted(required)]}


def verify_snapshot(saved, registry, elections, splits):
    if saved != snapshot(registry, elections, splits):
        raise ValueError('Changed, deleted or ambiguous consumed registry record')
    verify_source_files(ROOT, {'schemaVersion': 1, 'sources': saved['sources']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    elections = {year: read(f'data/processed/elections/{year}.json')
                 for year in SOURCE_YEARS + TARGET_YEARS}
    splits = {year: read(f'data/processed/split-votes/{year}.json')
              for year in SOURCE_YEARS}
    expected = snapshot(read('data/sources.json'), elections, splits)
    if args.check:
        if (ROOT / SNAPSHOT).read_bytes() != encode(expected):
            raise ValueError('Changed Stage 15 source snapshot')
        verify_snapshot(expected, read('data/sources.json'), elections, splits)
    else:
        (ROOT / SNAPSHOT).write_bytes(encode(expected))
    print(f'Stage 15 required raw sources: {len(expected["sources"])}')


if __name__ == '__main__':
    main()
