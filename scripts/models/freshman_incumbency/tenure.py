"""Read pinned Parliament profiles as dated electorate and list-service evidence."""

from datetime import datetime
from html import unescape
import re

from scripts.models.candidate_persistence.official import MEMBER, ROW


TABLE = re.compile(r'<table\b[^>]*>(.*?)</table>', re.S | re.I)
ROW_HTML = re.compile(r'<tr\b[^>]*>(.*?)</tr>', re.S | re.I)
CELL = re.compile(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', re.S | re.I)
TAG = re.compile(r'<[^>]+>')
FIRST_ELECTED = re.compile(r'Date first elected:\s*([^<]+)', re.I)
ENTERED = re.compile(r'Entered Parliament:\s*([^<]+)', re.I)
PUBLISHED = re.compile(r'<span class="publish-date">\s*<strong>Published date:</strong>\s*([^<]+)</span>', re.I)
TITLE = re.compile(r'<title>([^<]+)</title>', re.I)
SLASH_DATE = re.compile(r'^\d{1,2}/\d{1,2}/\d{4}$')
WRITTEN_DATE = r'\d{1,2} [A-Za-z]+ \d{4}'
DATE_RANGE = re.compile(rf'^({WRITTEN_DATE})\s*-\s*({WRITTEN_DATE})$')


def _text(raw):
    return unescape(TAG.sub('', raw)).strip()


def _date(value, formats):
    value = value.replace('\u00a0', ' ')
    for pattern in formats:
        try:
            return datetime.strptime(value.strip(), pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f'Unrecognized Parliament date: {value}')


def _service_dates(cells):
    value = ' '.join(cells[2].replace('\u00a0', ' ').split())
    if SLASH_DATE.fullmatch(value):
        start = _date(value, ('%d/%m/%Y',))
        end = _date(cells[3], ('%d/%m/%Y',)) if len(cells) > 3 and SLASH_DATE.fullmatch(cells[3]) else None
        return start, end
    match = DATE_RANGE.fullmatch(value)
    if match:
        return (_date(match[1], ('%d %B %Y', '%d %b %Y')),
                _date(match[2], ('%d %B %Y', '%d %b %Y')))
    if re.fullmatch(WRITTEN_DATE, value):
        return _date(value, ('%d %B %Y', '%d %b %Y')), None
    return None


def parse_index_page(raw):
    """Extract profile URLs and display names, including a short final page."""
    result = {}
    for row in ROW.findall(raw.decode('utf-8')):
        match = MEMBER.search(row)
        if not match:
            continue
        url = 'https://www3.parliament.nz' + unescape(match['url'])
        name = unescape(match['name']).strip()
        if url in result and result[url] != name:
            raise ValueError(f'Conflicting index name: {url}')
        result[url] = name
    if not result:
        raise ValueError('Empty Parliament member index page')
    return result


def parse_profile(raw, source):
    """Return explicit profile service rows; absent or malformed tenure stays unknown."""
    html = raw.decode('utf-8')
    title = TITLE.search(html)
    published = PUBLISHED.search(html)
    first = FIRST_ELECTED.search(html) or ENTERED.search(html)
    rows = []
    table_found = False
    unparsed_rows = 0
    for table in TABLE.findall(html):
        if 'Member for / List' not in ' '.join(_text(table).replace('\u00a0', ' ').split()):
            continue
        table_found = True
        for row in ROW_HTML.findall(table):
            cells = [_text(cell) for cell in CELL.findall(row)]
            if cells and cells[0].startswith('Member for'):
                continue
            dates = _service_dates(cells) if len(cells) >= 3 else None
            if dates is None:
                unparsed_rows += 1
                continue
            start, end = dates
            if end is not None and end < start:
                raise ValueError(f'Inverted tenure interval: {source["id"]}')
            rows.append({'serviceKind': 'list' if cells[0].casefold() == 'list' else 'electorate',
                         'electorateName': None if cells[0].casefold() == 'list' else cells[0],
                         'party': cells[1], 'startDate': start, 'endDate': end})
        break
    return {'sourceId': source['id'], 'sourceUrl': source['url'],
            'displayName': _text(title[1]).replace(' - New Zealand Parliament', '') if title else None,
            'publishedDate': _date(published[1], ('%d %b %Y', '%d %B %Y')) if published else None,
            'retrievedAt': source['retrievedAt'],
            'firstParliamentElectedDate': _date(first[1], ('%d %B %Y', '%d %b %Y')) if first else None,
            'serviceRows': rows,
            'unparsedServiceRows': unparsed_rows,
            'tenureEvidenceStatus': ('complete_dated_table' if table_found and rows and not unparsed_rows else
                                     'partial_dated_table' if rows else 'no_usable_dated_rows')}
