"""Exact-code membership joins; unknown meshblocks remain explicitly unresolved."""
import csv
import io
import zipfile


def index_rows(rows, key):
    result = {}
    for row in rows:
        code = row[key]
        if not code or code in result:
            raise ValueError('Missing or duplicate membership identity: ' + code)
        result[code] = row
    return result


def read_csv_zip(raw, member, key):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt source archive')
        rows = csv.DictReader(io.StringIO(archive.read(member).decode('utf-8-sig')))
        return index_rows(rows, key)


def join_memberships(population, concordance, source_controls, lineage=None):
    """No prefix matching, spatial guesses, suppressed-value filling or weights."""
    records = []
    for code, row in sorted(population.items()):
        source = concordance.get(code)
        predecessor = code if source else None
        status = 'official_exact_code' if source else 'unresolved'
        if source is None and lineage is not None and code in lineage:
            link = lineage[code]
            predecessor = link['MB2025_code']
            source = concordance.get(predecessor)
            if source is None:
                raise ValueError('Official predecessor absent from concordance: ' + code)
            for prefix in ('GED', 'MED'):
                if (link[f'{prefix}2025_code'] != row[f'{prefix}2025_V1_00'] or
                        link[f'{prefix}2025_name'] != row[f'{prefix}2025_V1_00_NAME']):
                    raise ValueError('Lineage target electorate mismatch: ' + code)
            status = 'official_historical_code'
        memberships = {}
        for kind, prefix in [('general', 'GED'), ('maori', 'MED')]:
            source_code = source[f'{prefix}2020_code'] if source else None
            source_name = source[f'{prefix}2020_name'] if source else None
            if source and source_controls[kind].get(source_code) != source_name:
                raise ValueError('Source electorate code/name mismatch: ' + code)
            memberships[kind] = {
                'sourceCode': source_code, 'sourceName': source_name,
                'targetCode': row[f'{prefix}2025_V1_00'],
                'targetName': row[f'{prefix}2025_V1_00_NAME'],
            }
        records.append({'meshblockId': code,
                        'membershipStatus': status,
                        'sourceConcordanceMeshblockId': predecessor,
                        'memberships': memberships})
    return records
