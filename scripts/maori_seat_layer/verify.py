"""Verify the curated poll transcriptions against the preserved source bytes (Wikipedia table rows; verbatim release text)."""
import re
from html import unescape
from html.parser import HTMLParser
from scripts.maori_seat_layer.common import ROOT, RAW, read, fold, HISTORICAL_POLLS, CURRENT_POLLS


class Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cell, self.row = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None and self.row is not None:
            self.row.append(unescape(''.join(self.cell)).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def number(text):
    m = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*%?\s*', re.sub(r'\[[^\]]*\]', '', text))
    return float(m.group(1)) if m else None


def table_rows(path):
    parser = Rows()
    parser.feed((ROOT / path).read_text(encoding='utf-8', errors='replace'))
    return [[c for c in row] for row in parser.rows]


def plain_text(path):
    text = (ROOT / path).read_text(encoding='utf-8', errors='replace')
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', text, flags=re.S)
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', text)))


def contiguous(row, values):
    nums = [n for n in (number(c) for c in row) if n is not None]  # blank, N/A and dash cells are skipped
    for start in range(len(nums) - len(values) + 1):
        if all(nums[start + k] is not None and abs(nums[start + k] - v) < 1e-9 for k, v in enumerate(values)):
            return True
    return False


def historical():
    """Every curated historical poll appears as an in-order run of numeric cells in a Reid or Curia row of its Wikipedia page."""
    errors, cache = [], {}
    for poll in read(HISTORICAL_POLLS)['polls']:
        page = RAW + '/' + poll['sourceIds'][0].replace('stage66-', '')
        rows = cache.setdefault(page, table_rows(page))
        values = [c['pollPercent'] for c in poll['candidates']]
        if not any(contiguous(r, values) and any(('Reid' in c or 'Curia' in c) for c in r) for r in rows):  # numeric cells in order
            errors.append('Not found in %s: %s %s' % (page, poll['id'], values))
        for source in poll['sourceIds'][1:]:
            text = plain_text(RAW + '/' + source.replace('stage66-', ''))
            for value in values + ([poll['undecidedPercent']] if poll['undecidedPercent'] is not None else []):
                shown = ('%g' % value)
                if not re.search(r'(?<![\d.])%s(?![\d.])' % re.escape(shown), text):
                    errors.append('Value %s not in %s for %s' % (shown, source, poll['id']))
    return errors


def current():
    """Each 2026 candidate share, sample size and fieldwork date is stated verbatim in a preserved release."""
    errors = []
    for poll in read(CURRENT_POLLS)['polls']:
        text = ' '.join(plain_text(f) for f in poll['sourceFiles'])
        for c in poll['candidates']:
            surname = fold(c['name'].split()[-1])
            pattern = r'%d%%' % c['pollPercent']
            ok = False
            for m in re.finditer(re.escape(pattern), text):
                window = fold(text[max(0, m.start() - 220):m.end() + 220])
                if surname in window:
                    ok = True
                    break
            if not ok:
                errors.append('2026 share not found: %s %s %d%%' % (poll['id'], c['name'], c['pollPercent']))
        if 'surveyed %d' % poll['sampleSize'] not in text:
            errors.append('Sample size not found: ' + poll['id'])
        for key in ('undecidedPercent', 'otherPercent'):
            if poll[key] is not None and not re.search(r'(?<!\d)%d%%?\s+(?:of voters |were )?(?:yet to decide|undecided|chose|“other|"other)|%d%%\s+of voters|%d%% were|%d%% (?:chose|undecided)|(?:undecided|other)[^.]{0,40}%d%%' % ((poll[key],) * 5), text):
                errors.append('%s %d%% not found for %s' % (key, poll[key], poll['id']))
    return errors


def main():
    errors = historical() + current()
    if errors:
        raise SystemExit('\n'.join(errors))
    print('Stage66 transcription verification ok')


if __name__ == '__main__':
    main()
