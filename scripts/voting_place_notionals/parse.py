"""Parse the Electoral Commission 2023 per-electorate "votes recorded at each voting place" CSVs.

One layout serves candidate and (to be confirmed on receipt) party files: a header row of vote columns, then
`Advance Voting Places` and `Voting Places` sections of place rows, then special-vote rows, a row for places with fewer
than six votes, a total row and the electorate result block. Place rows carry the locality only on the first row of a group.
"""
import csv
import io
import re
import unicodedata

from .common import CSV_2023, ROOT

ADVANCE, ELECTION_DAY = 'Advance Voting Places', 'Voting Places'
SPECIAL_PREFIXES = ('Overseas Special Votes', 'Special Votes BEFORE', 'Special Votes ON', 'Votes Allowed for Party Only')
SUPPRESSED_PREFIX = 'Voting places where less than 6 votes'
RESULT_MARKERS = ('Electorate Candidate Valid Votes', 'Electorate Party Valid Votes')


def nfc(text):
    return unicodedata.normalize('NFC', text)


def to_int(cell):
    cell = cell.strip().replace(',', '')
    return int(cell) if cell else 0


def parse_file(path):
    """Return the structured table of one electorate file. Raises on any row that does not fit the layout."""
    rows = list(csv.reader(io.StringIO((ROOT / path).read_text(encoding='utf-8-sig'))))
    title = rows[1][0]
    found = re.match(r'^(.*?) (\d+)(?:\s*\(.*\))?$', title.strip(), re.S)
    if found is None:
        raise ValueError('Unrecognised title in %s: %r' % (path, title))
    name, number = found.group(1), found.group(2)
    header = rows[2]
    columns = header[2:]
    width = len(columns)
    section, locality = None, ''
    places, specials, suppressed, total = [], {}, None, None
    result_rows = []
    for row in rows[3:]:
        if not row or all(not c.strip() for c in row):
            continue
        if row[0] in RESULT_MARKERS:
            result_rows = rows[rows.index(row) + 1:] if row[0] == RESULT_MARKERS[0] else []
            break
        if row[0] in (ADVANCE, ELECTION_DAY) and all(not c for c in row[1:]):
            section = row[0]
            continue
        if len(row) == 1 or all(not c.strip() for c in row[1:]):
            continue  # grouping heading used by the Māori files
        label = row[1]
        if 'plus Informal' in label:
            continue
        values = [to_int(c) for c in row[2:2 + width]]
        if len(values) != width:
            raise ValueError('Row width mismatch in %s: %r' % (path, row[:2]))
        if label.startswith(SPECIAL_PREFIXES):
            specials[label] = values
        elif label.startswith(SUPPRESSED_PREFIX):
            suppressed = values
        elif label.endswith(' Total'):
            total = values
        else:
            if section is None:
                raise ValueError('Place row outside a section in %s' % path)
            if row[0].strip():
                locality = nfc(row[0].strip())
            places.append({'section': section, 'locality': locality, 'venue': nfc(label), 'votes': values})
    if total is None:
        raise ValueError('No total row in ' + path)
    result = []
    for row in result_rows:
        if len(row) < 3 or not row[0].strip():
            break
        result.append({'name': nfc(row[0]), 'party': nfc(row[1]), 'votes': to_int(row[2])})
    return {'name': nfc(name), 'number': int(number), 'columns': [nfc(c) for c in columns],
            'places': places, 'specials': specials, 'suppressed': suppressed, 'total': total, 'result': result}


def reconcile(table):
    """Places + specials + suppressed-places row must equal the total row, column by column."""
    width = len(table['total'])
    sums = [0] * width
    for place in table['places']:
        sums = [a + b for a, b in zip(sums, place['votes'])]
    for values in list(table['specials'].values()) + ([table['suppressed']] if table['suppressed'] else []):
        sums = [a + b for a, b in zip(sums, values)]
    return sums == table['total'], sums


def candidate_path(number, folder=CSV_2023):
    return '%scandidate-votes-by-voting-place-%d.csv' % (folder, number)


def general_numbers():
    return range(1, 66)
