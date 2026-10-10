"""Stage79 polls: load the transcription, verify it against the preserved bytes, attach the model reference.

The transcription (data/source-plans/seat-polls/polls.json) is checked against the preserved Wikipedia table text
for every share: each number must appear in the seat's section of the preserved page.
"""
import re
from html.parser import HTMLParser
from . import model
from .common import ROOT, POLLS, RAW, read, fold

SUBHEADINGS = {'partyvote', 'candidatevote', 'electoratevote'}
ALIASES = {'mtalbert': 'mountalbert', 'ohariu': 'ohariu'}


class Sections(HTMLParser):
    """Text of each h3/h4-headed section, keyed by folded heading."""

    def __init__(self):
        super().__init__()
        self.sections, self.key, self.heading, self.skip = {}, None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag in ('h2', 'h3', 'h4'):
            self.heading = ''
        if tag in ('style', 'sup', 'script'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('style', 'sup', 'script'):
            self.skip -= 1
        if tag in ('h2', 'h3', 'h4') and self.heading is not None:
            if fold(self.heading) not in SUBHEADINGS or self.key is None:
                self.key = fold(self.heading)
            self.sections.setdefault(self.key, '')
            self.heading = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.heading is not None:
            self.heading += data
        elif self.key is not None:
            self.sections[self.key] += ' ' + data


def page_sections(year):
    parser = Sections()
    parser.feed((ROOT / RAW / f'wikipedia-opinion-polling-{year}.html').read_text(encoding='utf8'))
    return parser.sections


def numbers(text):
    return {float(x) for x in re.findall(r'\d+(?:\.\d+)?', text)}


def polls():
    return read(POLLS)['polls']


def verify_transcription(rows):
    """Every transcribed share and the sample size must appear in the preserved section text for that seat."""
    cache, problems = {}, []
    for p in rows:
        sections = cache.setdefault(p['election'], page_sections(p['election']))
        key = fold(p['electorate'])
        key = ALIASES.get(key, key)
        text = sections.get(key)
        if text is None:
            problems.append(f"{p['id']}: no section for {p['electorate']}")
            continue
        seen = numbers(text)
        missing = [f'{k}={v}' for k, v in p['candidateVotePct'].items() if float(v) not in seen]
        if p['sampleSize'] is not None and float(p['sampleSize']) not in {float(x.replace(',', '')) for x in re.findall(r'\d[\d,]*', text)}:
            missing.append(f"n={p['sampleSize']}")
        if missing:
            problems.append(f"{p['id']}: not found in the preserved table: {', '.join(missing)}")
    if problems:
        raise ValueError('Seat-poll transcription differs from the preserved pages:\n' + '\n'.join(problems))


def derived(p, design):
    n = p['sampleSize'] if p['sampleSize'] is not None else design['pollError']['missingSampleSize']['assumed']
    shares = p['candidateVotePct']
    out = {'id': p['id'], 'election': p['election'], 'electorate': p['electorate'], 'pollster': p['pollster'],
           'sponsorGroup': p['sponsorGroup'], 'sampleSize': n, 'sampleSizeAssumed': p['sampleSize'] is None,
           'eligible': model.eligible(shares) and not p['excluded'], 'excluded': p['excluded'], 'hasNationalAndLabour': 'NAT' in shares and 'LAB' in shares}
    if out['hasNationalAndLabour']:
        out['value'] = model.poll_value(shares)
        out['samplingVariance'] = model.sampling_variance(shares, n)
    return out
