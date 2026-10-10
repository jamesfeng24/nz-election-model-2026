"""Stage82: header-driven reader for the "Electorate polling" tables of the Wikipedia opinion-polling page (stdlib only).

Each poll is two rows: a "Party Vote" row and an "Electorate vote" row; the date, pollster and sample cells are merged (rowspan) across the
pair, so the electorate row is shorter than the header in the raw HTML. The reader first expands every merged cell into a rectangular grid, then
reads each cell under its header column, so a number can never land under the wrong party. Anything unexpected raises Block (the run stops for a
human); nothing is guessed. Only the electorate-vote shares are used downstream; the party-vote row is read and validated, then stored unused."""
import re
from datetime import date
from html.parser import HTMLParser

SECTION = 'Electorate polling'
KINDS = {'general electorates': 'general', 'māori electorates': 'maori'}
# Published party column labels -> stored key. Labels outside this set stop the run (a new party or a changed layout needs a human).
PARTY_COLUMNS = {'NAT': 'NAT', 'LAB': 'LAB', 'GRN': 'GRN', 'ACT': 'ACT', 'NZF': 'NZF', 'TPM': 'TPM', 'OPP': 'TOP', 'TOP': 'TOP', 'IND': 'IND', 'Others': 'OTH', 'OTH': 'OTH'}
MONTHS = {m: i + 1 for i, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'))}
ROUNDING = 0.5            # each published share is rounded, so a row of k shares may total up to 100 + k * 0.5
MISSING = re.compile(r'[-‒–—−]?\s*(N/?A)?', re.I)    # "-", "—", blank and the hidden "N/a" accessibility text
NUMBER = re.compile(r'(~|≈)?\s*(\d+(?:\.\d+)?)\s*%?')


class Block(ValueError):
    """The page is not in the shape this reader understands; the refresh refuses to publish."""

    def __init__(self, kind, **detail):
        super().__init__(kind + ' ' + str(detail))
        self.kind, self.detail = kind, detail


class _Tables(HTMLParser):
    """Headings and tables in page order; table cells with text, spans and the footnote anchors they carry."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items, self.table, self.row, self.cell, self.head, self.skip, self.depth = [], None, None, None, None, 0, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if re.fullmatch(r'h[1-6]', tag) and self.table is None:
            self.head = [int(tag[1]), '']
        elif tag == 'table':
            self.depth += 1
            if self.depth == 1:
                self.table = []
        elif self.table is not None and self.depth == 1:
            if tag == 'tr':
                self.row = []; self.table.append(self.row)
            elif tag in ('td', 'th') and self.row is not None:
                self.cell = {'t': '', 'rs': int(a.get('rowspan', 1) or 1), 'cs': int(a.get('colspan', 1) or 1), 'refs': []}
            elif tag in ('sup', 'style', 'script') and self.cell is not None:
                self.skip += 1
            elif tag == 'a' and self.cell is not None and '#cite_note-' in (a.get('href') or ''):
                self.cell['refs'].append(a['href'].split('#cite_note-')[-1])

    def handle_endtag(self, tag):
        if self.head is not None and tag == 'h%d' % self.head[0]:
            self.items.append(('h', self.head[0], re.sub(r'\s+', ' ', self.head[1]).strip())); self.head = None
        elif tag == 'table':
            if self.depth == 1 and self.table is not None:
                self.items.append(('t', self.table)); self.table = None
            self.depth = max(0, self.depth - 1)
        elif self.table is not None and self.depth == 1:
            if tag in ('td', 'th') and self.cell is not None:
                self.row.append(self.cell); self.cell = None
            elif tag in ('sup', 'style', 'script') and self.skip:
                self.skip -= 1

    def handle_data(self, data):
        if self.head is not None:
            self.head[1] += data
        elif self.cell is not None and not self.skip:
            self.cell['t'] += data


def expand(rows):
    """Rectangular grid from rows with rowspan/colspan: [[(text, refs)]]. Every row must end up the same width."""
    grid, carry = [], {}
    for r in rows:
        out, col, it = [], 0, iter(r)
        while True:
            if col in carry:
                left, cell = carry[col]
                out.append(cell)
                if left > 1:
                    carry[col] = (left - 1, cell)
                else:
                    del carry[col]
                col += 1
                continue
            c = next(it, None)
            if c is None:
                break
            cell = (re.sub(r'\s+', ' ', c['t']).strip(), tuple(c['refs']))
            for _ in range(c['cs']):
                out.append(cell)
                if c['rs'] > 1:
                    carry[col] = (c['rs'] - 1, cell)
                col += 1
        grid.append(out)
    return grid


def cell_number(text):
    """(value, flag): flag is None for a plain number, 'approx' for "~30"; blank and dashes are missing (None), never zero."""
    t = text.replace('−', '-').strip()
    if MISSING.fullmatch(t):
        return None, None
    m = NUMBER.fullmatch(t)
    if not m:
        raise Block('unreadable_cell', text=text)
    return float(m.group(2)), ('approx' if m.group(1) else None)


def parse_fieldwork(text, today_year=2026):
    """"22–29 Jul 2026", "21 Sep – 1 Oct 2026" or "17 Jul 2026" -> (start, end) as ISO dates; anything else blocks."""
    t = re.sub(r'\s+', ' ', text.replace('–', '-').replace('—', '-')).strip()
    m = re.fullmatch(r'(\d{1,2})(?: ([A-Za-z]{3,9}))? ?- ?(\d{1,2}) ([A-Za-z]{3,9}) (\d{4})', t)
    if m:
        d1, m1, d2, m2, y = m.groups()
        a, b = _date(d1, m1 or m2, y), _date(d2, m2, y)
    else:
        m = re.fullmatch(r'(\d{1,2}) ([A-Za-z]{3,9}) (\d{4})', t)
        if not m:
            raise Block('unreadable_fieldwork', text=text)
        a = b = _date(*m.groups())
    if a > b:
        raise Block('fieldwork_reversed', text=text)
    return a.isoformat(), b.isoformat()


def _date(d, month, y):
    mon = MONTHS.get(month[:3].lower())
    if mon is None:
        raise Block('unreadable_fieldwork', text=f'{d} {month} {y}')
    try:
        return date(int(y), mon, int(d))
    except ValueError:
        raise Block('unreadable_fieldwork', text=f'{d} {month} {y}')


def parse_sample(text):
    t = text.replace(',', '').strip()
    if MISSING.fullmatch(t):
        return None
    if not re.fullmatch(r'\d{2,5}', t):
        raise Block('unreadable_sample', text=text)
    return int(t)


def shares(row, parties, labels):
    out, flags = {}, {}
    for key, label, cell in zip(parties, labels, row):
        v, flag = cell_number(cell[0])
        if v is None:
            continue
        if key in out:
            raise Block('duplicate_party_column', party=key)
        out[key] = v
        if flag:
            flags[key] = flag
    return out, flags


def references(html):
    """Footnote number -> first external URL of its reference text (None if absent)."""
    urls = {}
    for m in re.finditer(r'<li[^>]*id="cite_note-([^"]+)"[^>]*>(.*?)</li>', html, re.S):
        link = re.search(r'<a[^>]*href="(https?://[^"]+)"', m.group(2))
        urls[m.group(1)] = link.group(1) if link else None
    return urls


def parse_page(html):
    """Every electorate poll on the page: [{kind, seatName, fieldwork, pollster, sampleSize, electorate, partyVote, flags, refs}].
    Raises Block on any structure it does not understand, including a missing section."""
    p = _Tables(); p.feed(html)
    level = None; kind = seat = None; polls = []; seen_tables = 0
    urls = references(html)
    for item in p.items:
        if item[0] == 'h':
            _, lvl, text = item
            if level is None:
                if text == SECTION:
                    level = lvl
                continue
            if lvl <= level:
                break
            low = text.lower()
            if lvl == level + 1:
                if low not in KINDS:
                    raise Block('unknown_subsection', heading=text)
                kind, seat = KINDS[low], None
            else:
                seat = text
            continue
        if level is None:
            continue
        if kind is None or seat is None:
            raise Block('table_without_seat', seat=seat, sectionKind=kind)
        seen_tables += 1
        polls.extend(_table(item[1], kind, seat, urls))
    if level is None:
        raise Block('electorate_section_missing')
    if not polls:
        raise Block('electorate_section_empty')
    return polls


def _table(rows, kind, seat, urls):
    grid = expand(rows)
    if not grid or len({len(r) for r in grid}) != 1:
        raise Block('ragged_table', seat=seat, widths=sorted({len(r) for r in grid}))
    head = [c[0] for c in grid[0]]
    if head[:4] != ['Date', 'Polling organisation', 'Sample size', ''] or head[-1] != 'Lead' or len(head) < 6:
        raise Block('unexpected_header', seat=seat, header=head)
    labels = head[4:-1]
    unknown = [x for x in labels if x not in PARTY_COLUMNS]
    if unknown:
        raise Block('unknown_party_column', seat=seat, columns=unknown)
    parties = [PARTY_COLUMNS[x] for x in labels]
    if len(set(parties)) != len(parties):
        raise Block('duplicate_party_column', seat=seat, columns=labels)
    body = grid[1:]
    if not body or len(body) % 2:
        raise Block('rows_not_in_pairs', seat=seat, rows=len(body))
    out = []
    for a, b in zip(body[0::2], body[1::2]):
        if a[3][0].lower() != 'party vote' or b[3][0].lower() != 'electorate vote':
            raise Block('row_pair_labels', seat=seat, labels=[a[3][0], b[3][0]])
        if a[:3] != b[:3]:
            raise Block('row_pair_not_merged', seat=seat, date=a[0][0])
        start, end = parse_fieldwork(a[0][0])
        ev, ev_flags = shares(b[4:-1], parties, labels)
        pv, pv_flags = shares(a[4:-1], parties, labels)
        for name, d in (('electorate', ev), ('party', pv)):
            if not d and name == 'electorate':
                raise Block('empty_electorate_row', seat=seat, date=a[0][0])
            if sum(d.values()) > 100 + ROUNDING * len(d):
                raise Block('shares_exceed_100', seat=seat, date=a[0][0], row=name, total=round(sum(d.values()), 1))
        out.append({'kind': kind, 'seatName': seat, 'fieldwork': {'raw': a[0][0], 'start': start, 'end': end}, 'pollster': a[1][0],
                    'sampleSize': parse_sample(a[2][0]), 'electorate': ev, 'partyVote': pv,
                    'flags': {'electorate': ev_flags, 'partyVote': pv_flags},
                    'references': [{'note': n, 'url': urls.get(n)} for n in a[1][1] + a[0][1] + a[2][1]]})
    return out
