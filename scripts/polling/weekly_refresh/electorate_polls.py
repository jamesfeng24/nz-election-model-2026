"""Stage70 Part C: general-seat (non-Maori) 2026 electorate polls found by one bounded search, preserved with provenance.

Facts are transcribed from the preserved page bytes and each is checked against the page text below (`--check` re-verifies hashes
and phrases). Nothing here is modelled or used by any layer. Maori-seat polls belong to the Stage71 layer.
"""
import argparse
import html
import re
from .common import ROOT, rel, sha, write, read

RAW = ROOT / 'data/raw/polling/electorate-polls-2026'
OUT = ROOT / 'data/processed/polling/electorate-polls-2026'
RETRIEVED = {}
LICENCE = 'Publisher copyright; page bytes preserved unchanged for research provenance only; no text is republished.'
SOURCES = [
    ('newsroom-wellington-bays-2026-09-16.html', 'https://newsroom.co.nz/2026/09/16/early-poll-reveals-greens-and-labour-in-dead-heat-in-wellington-bays/', 'Newsroom'),
    ('spinoff-mt-albert-2026-09-30.html', 'https://thespinoff.co.nz/politics/30-09-2026/opportunity-knocked-qiulae-wong-trails-in-fourth-in-mt-albert-poll', 'The Spinoff'),
    ('nzherald-mt-albert-poll.html', 'https://www.nzherald.co.nz/nz/politics/election-2026-poll-shows-labour-barely-ahead-in-crucial-mt-albert-seat/26PQ3XERH5ABJNUWE4QKR2QEQI/', 'NZ Herald'),
    ('newsroom-mt-albert-2026-10-01.html', 'https://newsroom.co.nz/2026/10/01/mt-albert-and-the-unspoken-clash-of-the-campaign/', 'Newsroom (context only; not a poll source)'),
]
PHRASES = {
    'newsroom-wellington-bays-2026-09-16.html': ['sample size of 400 respondents', 'Renney and Genter on 29 percent', 'National’s Karunā Muthu on 15 percent',
                                                 'Act’s Nicole McKee and NZ First’s candidate Gerald Warner on 5 percent', 'Kayla Kingdon-Bebb on 3 percent',
                                                 '31 percent voted Green, 29 percent Labour, and 13 percent National', 'Taxpayers’ Union candidate debate'],
    'spinoff-mt-albert-2026-09-30.html': ['The Curia poll of 400 voters', 'The poll has White on 33% and Lee on 32%', 'Wong', '10% would have given their candidate vote',
                                          'Menéndez March is on 14%', 'NZ First’s Sheldon Eden-Whaitiri sits on 5% and Act’s Alex Price is on 3%',
                                          '6% said they were undecided', 'This result excludes voters who were unsure'],
    'nzherald-mt-albert-poll.html': ['Polling was carried out between September 21 and 28', 'poll’s 4.9% margin of error', 'National and Labour neck and neck at 32% in the party vote',
                                     'The Greens were on 19%, Opportunity and NZ First at 6% and Act on 3%'],
}


def text_of(path):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', path.read_text(encoding='utf8', errors='replace'), flags=re.S)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', t)).split())


def retrieved_of(name):
    for line in (RAW / 'fetch-log.tsv').read_text().splitlines():
        c = line.split('\t')
        if c[4] == name and c[1] == '200':
            return c[0]
    raise ValueError('No successful fetch logged for ' + name)


def verify():
    for name, phrases in PHRASES.items():
        t = text_of(RAW / name)
        missing = [p for p in phrases if p not in t]
        if missing:
            raise ValueError(f'{name}: phrases not in preserved bytes: {missing}')


def build():
    verify()
    registry = {'schemaVersion': 1, 'note': 'Dated registry for the Stage70 general-seat electorate poll search; data/sources.json is frozen and not edited.',
                'sources': [{'dateOrElection': '2026 general election; electorate polls published 2026-09-16 to 2026-10-01', 'id': f'polling-electorate2026-{n}',
                             'licence': LICENCE, 'limitations': ['Secondary press report of a commissioned electorate poll; no primary Curia tables preserved.', who],
                             'organisation': who, 'processingScript': 'scripts/polling/weekly_refresh/electorate_polls.py', 'rawPath': rel(RAW / n), 'resource': n,
                             'retrievedAt': retrieved_of(n), 'schemaVersion': 1, 'sha256': sha(RAW / n), 'url': u} for n, u, who in SOURCES]}
    polls = {'schemaVersion': 1, 'status': 'preserved and listed only; not modelled, not used by any layer (a later stage)',
             'scope': 'general (non-Maori) electorates for the 2026 general election, found by one bounded web search on 2026-10-07',
             'polls': [
                 {'electorate': 'Wellington Bays', 'type': 'general', 'pollster': 'Curia', 'commissioner': "Taxpayers' Union", 'sampleSize': 400, 'fieldwork': None,
                  'fieldworkNote': 'not stated in the article; results revealed at a Taxpayers’ Union candidate debate on Tuesday 15 September 2026; reported 2026-09-16',
                  'candidateVotePct': {'Craig Renney (LAB)': 29, 'Julie Anne Genter (GRN)': 29, 'Karunā Muthu (NAT)': 15, 'Nicole McKee (ACT)': 5, 'Gerald Warner (NZF)': 5, 'Kayla Kingdon-Bebb (TOP)': 3},
                  'candidateVoteUndecidedTreatment': 'not stated; the six published shares sum to 86%',
                  'partyVotePct': {'GRN': 31, 'LAB': 29, 'NAT': 13}, 'partyVoteReported': 'three parties only',
                  'marginOfError': None,
                  'caveats': ['Newsroom: the survey is "to be taken with a pinch of salt"', 'results revealed at a pub debate; Newsroom notes the room may not be representative (this concerns the audience, not the sample method)',
                              'new electorate merging Rongotai and part of Wellington Central: no past result on the same boundaries', 'no primary Curia or Taxpayers’ Union release preserved (the Taxpayers’ Union page returned HTTP 403)'],
                  'sources': ['polling-electorate2026-newsroom-wellington-bays-2026-09-16.html']},
                 {'electorate': 'Mt Albert', 'type': 'general', 'pollster': 'Curia', 'commissioner': 'The Spinoff', 'sampleSize': 400, 'fieldwork': ['2026-09-21', '2026-09-28'],
                  'candidateVotePct': {'Helen White (LAB)': 33, 'Melissa Lee (NAT)': 32, 'Ricardo Menéndez March (GRN)': 14, 'Qiulae Wong (TOP)': 10, 'Sheldon Eden-Whaitiri (NZF)': 5, 'Alex Price (ACT)': 3},
                  'candidateVoteUndecidedTreatment': 'unsure voters excluded from the published shares; 6% of the total sample undecided',
                  'partyVotePct': {'NAT': 32, 'LAB': 32, 'GRN': 19, 'TOP': 6, 'NZF': 6, 'ACT': 3}, 'partyVoteReported': 'unsure voters excluded',
                  'marginOfError': 4.9, 'marginOfErrorNote': 'maximum, as reported by the NZ Herald',
                  'caveats': ['published by The Spinoff and the NZ Herald on 2026-09-30 and 2026-10-01, revealed at The Great Mt Albert Debate', 'first poll of the seat in 2026 (The Spinoff)',
                              'no primary Curia tables preserved', '2023 result for context: Labour won by 18 votes (NZ Herald)'],
                  'sources': ['polling-electorate2026-spinoff-mt-albert-2026-09-30.html', 'polling-electorate2026-nzherald-mt-albert-poll.html']}],
             'searchRecord': {'date': '2026-10-07', 'passes': 'one bounded pass of seven web searches (Taxpayers’ Union-Curia electorate polls, Freshwater, Talbot Mills, Horizon, Wikipedia electorate polling, Newsroom, The Spinoff, NZ Herald, named-seat queries)',
                              'found': 'two general-seat polls (above); no electorate-poll table on the Wikipedia opinion-polling page; no Freshwater, Talbot Mills or Horizon electorate polls surfaced (Q+A was not searched by name)',
                              'outsideScope': ['Te Tai Hauāuru, Te Tai Tonga and other Maori-seat polls (Curia for Whakaata Maori) belong to the Stage71 Maori layer; already preserved under data/raw/polling/current-2026-primary/'],
                              'notFound': ['Taxpayers’ Union-Curia monthly national poll pages were seen in results; any further TU-Curia electorate surveys beyond Wellington Bays were not found']}}
    return {'source-registry.json': registry, 'polls.json': polls}


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--check', action='store_true'); a = ap.parse_args()
    out = build()
    for n, v in out.items():
        if a.check:
            if read(OUT / n) != v:
                raise ValueError('Changed ' + n)
        else:
            write(OUT / n, v)
    print('ok' if a.check else 'written', {k: len(v.get('polls', v.get('sources'))) for k, v in out.items()})


if __name__ == '__main__':
    main()
