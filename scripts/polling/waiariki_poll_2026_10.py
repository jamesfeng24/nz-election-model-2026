"""Waiariki 2026 Whakatau poll (Whakaata Maori-Curia, published 2026-10-07): preserved page bytes, a dated registry and a transcription.

Recorded only. Nothing here is read by the Stage66 seat layer, Stage71, Stage78 or the assembly: the curated
`data/source-plans/maori-seat-layer/polls-2026.json` that those pipelines pin is unchanged, so Waiariki stays an unpolled seat
(fallback) until a separate, authorized update adopts this record. `--check` re-verifies the bytes and every transcribed phrase.
"""
import argparse
import html
import re
from scripts.polling.weekly_refresh.common import ROOT, rel, sha, write, read

RAW = ROOT / 'data/raw/polling/maori-seat-polls-2026-10'
OUT = ROOT / 'data/processed/polling/maori-seat-polls-2026-10'
NAME = 'spinoff-waiariki-2026-10-07.html'
URL = 'https://thespinoff.co.nz/atea/07-10-2026/rawiri-waititi-is-miles-ahead-in-waiariki-but-the-party-vote-is-a-three-way-scrap'
LICENCE = 'Publisher copyright; page bytes preserved unchanged for research provenance only; no text is republished.'
PHRASES = ['This story was originally published by Te Ao Māori News', 'Waititi is on 42%', 'Green’s Tania Waikato on 16%', 'Labour’s Toni Boynton on 14%',
           'Opportunity Party’s Pāpā Wharewera on 3%', 'A further 18% were undecided, while 6% chose “other”', 'Curia Market Research conducted it from September 21 to October 1',
           'The poll surveyed 500 Māori voters aged 18 and older enrolled in Waiariki, including 420 by phone and 80 through an online panel',
           'plus or minus 4.5% at the 95% confidence level', 'Waititi charging ahead to 52%', 'Labour Party leads a tight contest with 24%',
           'Te Pāti Māori is following closely behind on 23% and the Green Party on 22%', 'sits at 0% for the party vote', 'A further 14 % of voters remain unsure on the party vote']


def text_of(path):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', path.read_text(encoding='utf8', errors='replace'), flags=re.S)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', t)).split())


def retrieved():
    for line in (RAW / 'fetch-log.tsv').read_text().splitlines():
        c = line.split('\t')
        if c[4] == NAME and c[1] == '200':
            return c[0], int(c[3])
    raise ValueError('No successful fetch logged for ' + NAME)


def build():
    text = text_of(RAW / NAME)
    missing = [p for p in PHRASES if p not in text]
    if missing:
        raise ValueError('Phrases not in the preserved bytes: %s' % missing)
    when, size = retrieved()
    if size != (RAW / NAME).stat().st_size:
        raise ValueError('Logged size differs from the preserved bytes')
    registry = {'schemaVersion': 1, 'note': 'Dated registry for the Waiariki poll of 2026-10-07; data/sources.json is frozen and not edited.',
                'sources': [{'dateOrElection': '2026 general election; Waiariki poll published 2026-10-07', 'id': 'polling-maori2026-' + NAME, 'licence': LICENCE,
                             'limitations': ['Secondary republication by The Spinoff of a Te Ao Māori News story; the original Te Ao Māori News page and Curia tables were not found and are not preserved.',
                                             'Party-vote base is not stated (14% unsure is reported separately).'],
                             'organisation': 'The Spinoff (from Te Ao Māori News / Whakaata Māori; fieldwork Curia Market Research)', 'processingScript': 'scripts/polling/waiariki_poll_2026_10.py',
                             'rawPath': rel(RAW / NAME), 'resource': NAME, 'retrievedAt': when, 'schemaVersion': 1, 'sha256': sha(RAW / NAME), 'url': URL}]}
    candidates = [{'name': 'Rawiri Waititi', 'party': 'MP', 'pollPercent': 42}, {'name': 'Tania Waikato', 'party': 'GRN', 'pollPercent': 16},
                  {'name': 'Toni Boynton', 'party': 'LAB', 'pollPercent': 14}, {'name': 'Pāpā Wharewera', 'party': 'TOP', 'pollPercent': 3}]
    poll = {'id': '2026-waiariki', 'seat': 'Waiariki', 'pollster': 'Whakaata Māori–Curia (Whakatau 2026)', 'published': '2026-10-07', 'fieldworkStart': '2026-09-21',
            'fieldworkEnd': '2026-10-01', 'sampleSize': 500, 'mode': '420 phone, 80 online panel', 'marginOfErrorPercent': 4.5, 'candidates': candidates,
            'undecidedPercent': 18, 'otherPercent': 6,
            'partyVotePercent': {'LAB': 24, 'MP': 23, 'GRN': 22, 'TOP': 0, 'undecided': 14},
            'candidateVoteExcludingUndecided': {'Rawiri Waititi': 52},
            'notes': 'Candidate shares are shares of all respondents; the four named shares sum to 75% with 18% undecided and 6% other. Party-vote figures are recorded for the '
                     'national-layer reconciliation and are not used in a seat forecast; their base is not stated.',
            'sourceFiles': [rel(RAW / NAME)]}
    polls = {'schemaVersion': 1, 'status': 'recorded only; not in data/source-plans/maori-seat-layer/polls-2026.json and not read by any layer (Waiariki stays an unpolled seat until a separate update adopts it)',
             'scope': 'Waiariki (Maori electorate), 2026 general election', 'polls': [poll],
             'adoptionNote': 'The record has the Stage66 current-poll shape (candidates with pollPercent, id, seat, fieldworkEnd). Adopting it would change a pinned input of Stage66, Stage71 and Stage78 '
                             'and so needs regenerated, re-checked artifacts; James (2026-10-09) preferred not to update each time one electorate poll appears.'}
    return {'source-registry.json': registry, 'polls.json': polls}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out = build()
    for n, v in out.items():
        if a.check:
            if read(OUT / n) != v:
                raise ValueError('Changed ' + n)
        else:
            write(OUT / n, v)
    print('ok' if a.check else 'written')


if __name__ == '__main__':
    main()
