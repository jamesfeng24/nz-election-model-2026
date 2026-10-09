"""Stage50 part 2: transcribe the preserved 2026-10-10 official publications into the Stage50 tables.

python -m scripts.nominations_2026.extract [--check]

Publication-specific and standard-library only (the .xlsx is read as its OOXML parts, so no spreadsheet package):
- `Electorate-Candidates-2026.xlsx`, sheet 1 (Name, Electorate, Party), one row per published electorate candidate,
  becomes `official-table.json`. A published name `SURNAME, Given names` becomes the display name
  `Given names SURNAME` (letters unchanged), because the Stage40 identity linkage parses given-then-surname order.
- `Party-lists-for-the-2026-General-Election.pdf`: only its party headings, transcribed by hand below with their
  page, become `party-lists.json`. They must be exactly the Stage40 party register: every registered party lodged a
  list, so every registered party is a 2026 ballot group. The list rankings are preserved, not transcribed.
Every value is checked against the preserved bytes' registry entry first.
"""
import argparse
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from scripts.balance_scale.common import equivalent
from scripts.readiness.registry import PARTIES
from scripts.uncertainty_revision.common import ROOT, read, encode
from scripts.validate.source_files import verify_source_files

DATE = '2026-10-10'
REGISTRY = 'data/processed/nominations-2026/source-registry.json'
OUT = f'data/processed/nominations-2026/{DATE}/'
CANDIDATES = 'stage50-2026-electorate-candidates'
LISTS = 'stage50-2026-party-lists'
# The publication carries no time; its embedded modification time (registry `embeddedTimestamps`) is the earliest
# moment it can have been published, so claims are dated by it.
PUBLISHED = '2026-10-09T00:22:58Z'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
# Party headings as printed in the party-list PDF (line breaks joined), with page, mapped to the register.
LIST_HEADINGS = [('ACT NEW ZEALAND', 1, 'actnewzealand'), ('ALLIANCE PARTY', 1, 'alliancepartyofaotearoanewzealand'),
                 ('CONSERVATIVE PARTY NZ', 1, 'conservativepartynz'), ('FREE PALESTINE', 1, 'freepalestine'),
                 ('ANIMAL JUSTICE PARTY AOTEAROA NEW ZEALAND', 1, 'animaljusticeparty'), ('GREEN PARTY', 1, 'greenparty'),
                 ('AOTEAROA LEGALISE CANNABIS PARTY', 1, 'aotearoalegalisecannabisparty'), ('LABOUR PARTY', 1, 'labourparty'),
                 ('NATIONAL PARTY', 2, 'nationalparty'), ('NEW ZEALAND FIRST PARTY', 2, 'newzealandfirstparty'),
                 ('NEW ZEALAND LOYAL', 3, 'newzealandloyal'), ('OPPORTUNITY PARTY', 3, 'opportunity'),
                 ('TE PĀTI MĀORI', 3, 'tepatimaori'), ('TE TAI TOKERAU PARTY', 3, 'tetaitokerauparty'),
                 ('VISION NEW ZEALAND', 3, 'visionnewzealand'), ('NZ OUTDOORS & FREEDOM PARTY', 3, 'nzoutdoorsfreedomparty'),
                 ("WOMEN'S RIGHTS PARTY", 3, 'womensrightsparty')]


def source(registry, source_id):
    return next(s for s in registry['sources'] if s['id'] == source_id)


def sheet_rows(path):
    """[(row number, [cell strings])] of the first worksheet, from the OOXML parts."""
    with zipfile.ZipFile(path) as z:
        shared = [''.join(t.text or '' for t in si.iter('{%s}t' % NS['m']))
                  for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS)]
        sheet = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    rows = []
    for row in sheet.find('m:sheetData', NS).findall('m:row', NS):
        cells = {}
        for c in row.findall('m:c', NS):
            column = re.match(r'[A-Z]+', c.get('r')).group()
            if c.get('t') == 's':
                value = shared[int(c.find('m:v', NS).text)]
            elif c.get('t') == 'inlineStr':
                value = ''.join(t.text or '' for t in c.iter('{%s}t' % NS['m']))
            else:
                v = c.find('m:v', NS)
                value = v.text if v is not None else ''
            cells[column] = value
        rows.append((int(row.get('r')), [cells.get(k, '') for k in 'ABC']))
    return rows


def display_name(published):
    """'SURNAME, Given names' -> 'Given names SURNAME'; anything else fails closed."""
    parts = [p.strip() for p in published.split(',')]
    if len(parts) != 2 or not all(parts):
        raise ValueError(f'Unexpected published name form: {published!r}')
    return f'{parts[1]} {parts[0]}'


def official_table(registry):
    record = source(registry, CANDIDATES)
    rows = sheet_rows(ROOT / record['rawPath'])
    if rows[0] != (1, ['Name', 'Electorate', 'Party']):
        raise ValueError(f'Unexpected header {rows[0]}')
    out = []
    for number, (name, electorate, party) in rows[1:]:
        if not (name.strip() and electorate.strip() and party.strip()):
            raise ValueError(f'row {number}: empty cell')
        out.append({'electorateLabel': electorate.strip(), 'displayName': display_name(name),
                    'affiliationLabel': party.strip(), 'locator': f'Candidates!A{number}:C{number}'})
    return {'schemaVersion': 1, 'sourceId': CANDIDATES, 'publishedAt': PUBLISHED,
            'publishedAtBasis': 'embedded file modification time (earliest possible publication); no publication time is printed',
            'nameRule': "published 'SURNAME, Given names' rendered as 'Given names SURNAME', letters unchanged", 'rows': out}


def party_lists():
    keys = [k for _, _, k in LIST_HEADINGS]
    if sorted(keys) != sorted(k for k, _, _ in PARTIES) or len(set(keys)) != len(keys):
        raise ValueError('Party-list headings are not exactly the Stage40 register')
    return {'schemaVersion': 1, 'sourceId': LISTS, 'transcription': 'party headings only, by hand, with page; rankings not transcribed',
            'parties': [{'heading': h, 'page': p, 'targetGroupKey': k} for h, p, k in LIST_HEADINGS],
            'finding': 'all 17 registered parties lodged a party list, so each is a 2026 ballot group'}


def build(registry=None):
    registry = read(REGISTRY) if registry is None else registry
    return {OUT + 'official-table.json': official_table(registry), OUT + 'party-lists.json': party_lists()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    registry = read(REGISTRY)
    verify_source_files(ROOT, registry)
    outputs = build(registry)
    for path, value in outputs.items():
        if args.check:
            if not equivalent(read(path), value, 0):
                raise SystemExit('Stale ' + path)
        else:
            (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
            (ROOT / path).write_bytes(encode(value))
    table = outputs[OUT + 'official-table.json']
    print('Stage50 extract', 'reproduced' if args.check else 'written', len(table['rows']), 'rows,',
          len(Counter(r['electorateLabel'] for r in table['rows'])), 'electorates')


if __name__ == '__main__':
    main()
