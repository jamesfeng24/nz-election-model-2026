"""Stage52 primary-source capture ledger and verification audit for the 2026-cycle national polls.

Offline only. Raw bytes are fetched by shell (curl, honest User-Agent, no challenge bypass) into
data/raw/polling/current-2026-primary together with response headers and fetch-log.tsv. This module
registers them with checksums, checks that every fact it reports occurs in the preserved bytes, and writes a
dated Stage40-style registry. It fits nothing and changes no Stage35 or earlier Stage52 file.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/polling/current-2026-primary'
OUT = ROOT / 'data/processed/polling/current-cycle-acquisition'
LICENCE = ('Publisher/pollster page preserved unchanged for research provenance only; copyright remains with the '
           'publisher (Wikipedia text CC BY-SA). Not redistributed in application results.')

# file -> (kind, publisher/pollster, subject)
FILES = {
    'wikipedia-opinion-polling-2026.html': ('aggregator table', 'Wikipedia REST HTML, revision 1378752122', '2026 NZ opinion-polling table (all polls)'),
    'rnz-reid-2026-10-06.html': ('national poll release', 'RNZ', 'RNZ-Reid Research, published 2026-10-06'),
    'rnz-reid-2026-07-09.html': ('national poll release', 'RNZ', 'RNZ-Reid Research, 2-9 Jul 2026'),
    'rnz-reid-2026-08-21.html': ('national poll release', 'RNZ', 'RNZ-Reid Research, 14-21 Aug 2026'),
    '1news-verian-2026-09-28.html': ('national poll release', '1News', '1News-Verian, 23-27 Sep 2026'),
    'scribd-verian-2026-06.html': ('national poll report (publisher upload)', 'Scribd, uploaded by 1News', '1News-Verian report, 13-17 Jun 2026'),
    'scribd-verian-2026-08.html': ('national poll report (publisher upload)', 'Scribd, uploaded by 1News', '1News-Verian report, 8-11 Aug 2026'),
    'roymorgan-10271-june-2026.html': ('national poll release', 'Roy Morgan', 'Roy Morgan, 25 May-21 Jun 2026'),
    'roymorgan-10281-july-2026.html': ('national poll release', 'Roy Morgan', 'Roy Morgan, 29 Jun-26 Jul 2026'),
    'roymorgan-10321-august-2026.html': ('national poll release', 'Roy Morgan', 'Roy Morgan, 27 Jul-23 Aug 2026'),
    'freshwater-post-2026-06.html': ('pollster landing page', 'Freshwater Strategy', 'The Post-Freshwater Strategy June 2026 landing page'),
    'freshwater-data-tables-post-2026-06.xlsx': ('pollster data tables', 'Freshwater Strategy', 'The Post-Freshwater Strategy, 5-11 Jun 2026 data tables'),
    'freshwater-post-2026-09-15.html': ('pollster landing page', 'Freshwater Strategy', 'The Post-Freshwater Strategy September 2026 landing page'),
    'freshwater-data-tables-post-2026-09.xlsx': ('pollster data tables', 'Freshwater Strategy', 'The Post-Freshwater Strategy, 4-11 Sep 2026 data tables'),
    'talbot-stuff-2026-06.html': ('national poll release (JS shell, metadata only)', 'Stuff', 'Talbot Mills-Anacta, June 2026; article text not in bytes'),
    'talbot-herald-2026-06.html': ('national poll release', 'NZ Herald', 'Talbot Mills-Anacta, 1-10 Jun 2026'),
    'talbot-herald-2026-07.html': ('national poll release', 'NZ Herald', 'Talbot Mills, 10-19 Jul 2026'),
    'talbot-herald-2026-08.html': ('national poll release', 'NZ Herald', 'Talbot Mills, 1-11 Aug 2026'),
    'anacta-herald-2026-09.html': ('national poll release', 'NZ Herald', 'Anacta (formerly Talbot Mills), 4-10 Sep 2026'),
    'talbot-herald-2024-11.html': ('national poll release', 'NZ Herald', 'Talbot Mills, 1-10 Nov 2024 (missing from Stage35 panel)'),
    'curia-tu-2026-06.html': ('pollster blog post', 'Curia Market Research', 'Taxpayers\' Union-Curia June 2026 post (links to blocked taxpayers.org.nz)'),
    'curia-tu-2026-08.html': ('pollster blog post', 'Curia Market Research', 'Taxpayers\' Union-Curia August 2026 post (links to blocked taxpayers.org.nz)'),
    'curia-tu-2026-09.html': ('pollster blog post', 'Curia Market Research', 'Taxpayers\' Union-Curia September 2026 post (links to blocked taxpayers.org.nz)'),
    'curia-political-poll-tag.html': ('pollster index', 'Curia Market Research', 'Curia political poll archive index'),
    'curia-whakaata-maori-poll-2026-09.html': ('Maori roll poll pointer', 'Curia Market Research', 'Curia post for the Whakaata Maori Maori-roll poll (18 Sep)'),
    'curia-te-tai-tonga-2026-09-29.html': ('Maori electorate poll pointer', 'Curia Market Research', 'Curia post for the Te Tai Tonga poll (29 Sep)'),
    'maori-teaonews-maori-roll-2026-09-17.html': ('Maori roll poll release', 'Te Ao Maori News (Whakaata Maori)', 'Whakaata Maori-Curia Maori-roll poll, n=1,000 (not a seat poll)'),
    'maori-teaonews-te-tai-tonga-2026-09-29.html': ('Maori electorate poll release', 'Te Ao Maori News (Whakaata Maori)', 'Whakaata Maori-Curia Te Tai Tonga'),
    'maori-rnz-te-tai-tonga.html': ('Maori electorate poll release (mirror)', 'RNZ', 'Whakaata Maori-Curia Te Tai Tonga (RNZ mirror)'),
    'maori-teaonews-te-tai-hauauru-2026-09-30.html': ('Maori electorate poll release', 'Te Ao Maori News (Whakaata Maori)', 'Whakaata Maori-Curia Te Tai Hauauru'),
    'maori-teaonews-hauraki-waikato-2026-10-06.html': ('Maori electorate poll release', 'Te Ao Maori News (Whakaata Maori)', 'Whakaata Maori-Curia Hauraki-Waikato'),
    'maori-teaonews-hauraki-waikato-kingitanga-2026-10-06.html': ('Maori electorate poll release', 'Te Ao Maori News (Whakaata Maori)', 'Hauraki-Waikato Kingitanga question from the same poll'),
    'maori-hauraki-waikato-herald.html': ('Maori electorate poll release (mirror)', 'NZ Herald', 'Whakaata Maori-Curia Hauraki-Waikato (Herald mirror)'),
    'maori-newsroom-seat-poll-2026-09-29.html': ('Maori seat context', 'Newsroom', 'Analysis of the seven Maori seats after the Te Tai Tonga poll'),
    'index-teaonews-whakatau-2026-tag.html': ('series index (JS-rendered, no listing in bytes)', 'Te Ao Maori News', 'Whakatau 2026 tag page'),
    'index-teaonews-poll-tag.html': ('series index (JS-rendered, no listing in bytes)', 'Te Ao Maori News', 'Poll tag page'),
    'index-teaonews-whakatau.html': ('series index (JS-rendered, no listing in bytes)', 'Te Ao Maori News', 'Whakatau landing page'),
}

# 200 responses discarded because the bytes were a JavaScript application shell with no article text
DISCARDED_SHELLS = {
    'talbot-post-2024-05.html': 'The Post: Talbot Mills 1-10 May 2024 article; identical 7,271-byte JS shell, no article text',
    'talbot-post-2026-07.html': 'The Post: Talbot Mills 10-19 Jul 2026 article; identical 7,271-byte JS shell, no article text',
    'post-freshwater-2026-09-11.html': 'The Post: Freshwater 4-11 Sep 2026 article; identical 7,271-byte JS shell, no article text',
}

# (id, file, facts, needles that must occur verbatim in the normalised text of the file)
CHECKS = [
    ('rnz-reid-2026-10-06', 'rnz-reid-2026-10-06.html',
     dict(pollster='RNZ-Reid Research', fieldwork='2026-09-24 to 2026-10-01', n=1000, mode='online quota sample', published='2026-10-06 06:27 NZDT',
          shares=dict(NAT=25.9, LAB=30.8, GRN=14.8, ACT=9.0, NZF=10.6, TPM=2.0, TOP=5.5)),
     ['surveyed 1000 eligible voters online between 24 September and 1 October 2026', '6 October 2026, 6:27am',
      'National has plunged below 26 percent', 'New Zealand First has fallen 1.3 points to 10.6 percent', 'Opportunity has edged up 0.2 points to 5.5 percent']),
    ('rnz-reid-2026-07-09', 'rnz-reid-2026-07-09.html',
     dict(pollster='RNZ-Reid Research', fieldwork='2026-07-02 to 2026-07-09', n=1000, mode='online'),
     ['online interviews between 2-9 July 2026', 'This poll of 1000 people']),
    ('rnz-reid-2026-08-21', 'rnz-reid-2026-08-21.html',
     dict(pollster='RNZ-Reid Research', fieldwork='2026-08-14 to 2026-08-21', n=1000, mode='online'),
     ['online interviews between 14-21 August 2026', 'This poll of 1000 people']),
    ('verian-2026-09', '1news-verian-2026-09-28.html',
     dict(pollster='1News-Verian', fieldwork='2026-09-23 to 2026-09-27', n=1004, mode='503 mobile phone, 501 online panel'),
     ['Between September 23 and September 27 2026, 1004 eligible voters were polled by mobile phone (503) and online using online panels (501)']),
    ('verian-2026-06', 'scribd-verian-2026-06.html',
     dict(pollster='1News-Verian', fieldwork='2026-06-13 to 2026-06-17', n=1001, mode='501 mobile phone, 500 online panel', released='2026-06-22'),
     ['Interviewing took place from Saturday 13 to Wednesday 17 June 2026', 'n = 1,001 eligible voters, including n=501 polled via mobile phone and n=500 polled online']),
    ('verian-2026-08', 'scribd-verian-2026-08.html',
     dict(pollster='1News-Verian', fieldwork='2026-08-08 to 2026-08-11', n=847),
     ['conducted from August 8-11, 2026, surveyed 847 eligible New Zealand voters']),
    ('roymorgan-2026-06', 'roymorgan-10271-june-2026.html',
     dict(pollster='Roy Morgan', fieldwork='2026-05-25 to 2026-06-21', n=891, mode='telephone'),
     ['cross-section of 891 electors from May 25 – June 21, 2026']),
    ('roymorgan-2026-07', 'roymorgan-10281-july-2026.html',
     dict(pollster='Roy Morgan', fieldwork='2026-06-29 to 2026-07-26', n=881, mode='telephone'),
     ['cross-section of 881 electors from June 29 – July 26, 2026']),
    ('roymorgan-2026-08', 'roymorgan-10321-august-2026.html',
     dict(pollster='Roy Morgan', fieldwork='2026-07-27 to 2026-08-23', n=858, mode='telephone'),
     ['cross-section of 858 electors from July 27 – August 23, 2026']),
    ('freshwater-2026-06', 'freshwater-data-tables-post-2026-06.xlsx',
     dict(pollster='The Post-Freshwater Strategy', fieldwork='2026-06-05 to 2026-06-11', n=1038),
     ['5-11 June 2026', 'n=1038 New Zealand adults aged 18+']),
    ('freshwater-2026-09', 'freshwater-data-tables-post-2026-09.xlsx',
     dict(pollster='The Post-Freshwater Strategy', fieldwork='2026-09-04 to 2026-09-11', n=1011, effectiveSampleSize=703),
     ['4-11 September 2026', 'base n = 1011', 'effective sample size = 703 (70%)']),
    ('talbot-2026-06', 'talbot-herald-2026-06.html',
     dict(pollster='Talbot Mills (for Anacta Consulting)', fieldwork='2026-06-01 to 2026-06-10', n=None, nNote='not stated in article; margin of error 3.1% reported; Wikipedia lists 1021 (Stuff, not recoverable)',
          shares=dict(GRN=13, NZF=12, LAB=34, NAT=29, ACT=6)),
     ['June 1-10 and has a margin of error of 3.1%', 'Green Party on 13%', 'Labour fell 2 points to 34%']),
    ('talbot-2026-07', 'talbot-herald-2026-07.html',
     dict(pollster='Talbot Mills', fieldwork='2026-07-10 to 2026-07-19', n=None, nNote='not stated in article; margin of error 3.1% reported', shares=dict(LAB=33, NAT=31, NZF=12, GRN=9, ACT=7, TPM=3, TOP=4.7)),
     ['conducted between July 10 and 19, had a margin of error of 3.1%', 'Labour on 33%, down one point']),
    ('talbot-2026-08', 'talbot-herald-2026-08.html',
     dict(pollster='Talbot Mills', fieldwork='2026-08-01 to 2026-08-11', n=None, nNote='not stated in article; margin of error 3.1% reported'),
     ['The polling period was August 1-11 and has a margin of error of 3.1%']),
    ('anacta-2026-09', 'anacta-herald-2026-09.html',
     dict(pollster='Anacta (formerly Talbot Mills)', fieldwork='2026-09-04 to 2026-09-10', n=1701, marginOfError='2.4%'),
     ['The polling period was from 4 to 10 September. The poll’s sample was 1701', 'Anacta was known as Talbot Mills until its recent rebranding']),
    ('talbot-2024-11', 'talbot-herald-2024-11.html',
     dict(pollster='Talbot Mills', fieldwork='2024-11-01 to 2024-11-10', n=None, nNote='not stated; margin of error 3.1% reported', corporateClient='yes (also polls for Labour)',
          shares=dict(NAT=34, LAB=33, GRN=10, ACT=10, NZF=7, TPM=3.3)),
     ['National on 34% and Labour one point behind on 33%', 'unusually long period of November 1-10 (with a margin of error of 3.1%)']),
    ('maori-roll-2026-09', 'maori-teaonews-maori-roll-2026-09-17.html',
     dict(pollster='Whakaata Maori-Curia', scope='Maori voters on both rolls, not a seat poll', n=1000, nPhone=500, nOnline=500),
     ['surveyed 1,000 Māori voters on both the general and Māori rolls, including 500 by phone and 500 through an online panel']),
    ('maori-te-tai-tonga', 'maori-teaonews-te-tai-tonga-2026-09-29.html',
     dict(seat='Te Tai Tonga', pollster='Whakaata Maori-Curia (Whakatau 2026)', fieldwork='2026-09-14 to 2026-09-24', n=500, nPhone=420, nOnline=80, marginOfError='4.5%',
          pageDate='2026-09-28 (Te Ao Maori News header); Newsroom says Tuesday 2026-09-29; Curia post 2026-09-29',
          candidateVote=dict(Ramsden_LAB=30, Murch_TPM=17, TeMorenga_GRN=16, Ferris_IND=15), partyVote=dict(LAB=28, GRN=14, TPM=11, NZF=6, NAT=6, TOP=4, undecided=10)),
     ['conducted from September 14 to September 24 by Curia Market Research', 'surveyed 500 Māori voters aged 18 and older in Te Tai Tonga, including 420 by phone and 80 through an online panel',
      'Labour’s Mananui Ramsden with 30%', 'Lisa Marie Murch with 17%', 'Lisa Te Morenga with 16%', 'at 15% support']),
    ('maori-te-tai-hauauru', 'maori-teaonews-te-tai-hauauru-2026-09-30.html',
     dict(seat='Te Tai Hauauru', pollster='Whakaata Maori-Curia (Whakatau 2026)', fieldwork='2026-09-14 to 2026-09-24', n=500, nPhone=420, nOnline=80, marginOfError='4.5%',
          pageDate='Tuesday 2026-09-29 (Te Ao Maori News header)',
          candidateVote=dict(NgarewaPacker_TPM=38, Katene_LAB=27, Raukawa_NAT=10, undecided=18, other=6)),
     ['Ngarewa-Packer led the Whakaata Māori-Curia poll at 38%', 'Te Pūoho Katene at 27%', 'Coral Raukawa at 10%',
      'Curia Market Research conducted the survey from September 14 to September 24',
      'surveyed 500 Māori voters aged 18 and older in Te Tai Hauāuru, including 420 by phone and 80 through an online panel']),
    ('maori-hauraki-waikato', 'maori-teaonews-hauraki-waikato-2026-10-06.html',
     dict(seat='Hauraki-Waikato', pollster='Whakaata Maori-Curia (Whakatau 2026)', fieldwork='2026-09-21 to 2026-10-01', n=500, nPhone=420, nOnline=80, marginOfError='4.5%',
          pageDate='2026-10-06', candidateVote=dict(MaipiClarke_TPM=45, Kiriona_LAB=26, undecided=17, other=13),
          partyVote=dict(TPM=22, LAB=21, GRN=16, undecided=15, NZF=7, NAT=5)),
     ['conducted by Curia Market Research from September 21 to October 1', 'surveyed 500 Māori voters aged 18 and older enrolled in Hauraki-Waikato, including 420 by phone and 80 through an online panel']),
    ('maori-hauraki-waikato-herald', 'maori-hauraki-waikato-herald.html',
     dict(seat='Hauraki-Waikato', note='NZ Herald mirror of the same poll'),
     ['Maipi-Clarke was in the lead on 45% to Kiriona’s 26%', 'conducted between September 21 and October 1']),
    ('newsroom-seat-context', 'maori-newsroom-seat-poll-2026-09-29.html',
     dict(note='Newsroom: "These seats are almost impossible to poll reliably"; names no commissioning for further seat polls'),
     ['These seats are almost impossible to poll reliably']),
]

WIKIPEDIA_ROW_PREFIXES = ['24 Sep - 1 Oct 2026 RNZ—Reid Research 1,000 25.9 30.8 14.8 9 10.6 2 5.5',
                          '1–10 Nov 2024 Talbot Mills 34 33 10 10 7 3.3',
                          '1–10 May 2024 Talbot Mills 35 32']

# What could not be recovered, with the route tried (all one bounded pass; none bypasses a access control)
UNRESOLVED = [
    dict(item='Taxpayers\' Union-Curia, Jun/Jul/Aug/Sep 2026 (n=1000)', reason='taxpayers.org.nz answers every request with a Cloudflare managed challenge (HTTP 403, cf-mitigated: challenge); not bypassed. Curia posts only link to those pages and hold no figures; Wikipedia lists the results. The Sep 2026 Wikipedia URL carries a stray trailing "?" that Curia\'s own link lacks.',
         needed='A browser-saved copy of each of the four taxpayers.org.nz poll pages or the Curia PDF/results; dates 4-8 Jun, 1-5 Jul, 1-4 Aug, 1-3 Sep 2026.'),
    dict(item='Talbot Mills 1-10 May 2024 (Wikipedia NAT 35, LAB 32 only)', reason='The Post article is a JS shell (discarded), web.archive.org is denied by the egress policy, and the Herald stories searched were other months or years. The poll is not recovered; Wikipedia remains the only evidence and its blank-sample row stays excluded from the panel.',
         needed='A saved copy of https://www.thepost.co.nz/politics/350282502/are-tax-cuts-boost-economy-needs or the Talbot Mills release.'),
    dict(item='Talbot Mills 2026 sample sizes (Jun 1-10, Jul 10-19, Aug 1-11)', reason='NZ Herald articles give fieldwork and a 3.1% margin of error but no n; the June Stuff page and July Post page are JS shells. Wikipedia lists n=1021 for June and blank for July and August.',
         needed='Talbot Mills/Anacta release or The Post/Stuff article text.'),
    dict(item='The Post-Freshwater Strategy articles (Jun, Sep 2026)', reason='The Post pages are JS shells. The pollster\'s own data tables (xlsx) were captured instead and carry fieldwork dates and sample sizes, so no further capture is needed for the panel.', needed='None for the panel.'),
    dict(item='1News-Verian June and August reports', reason='Only the publisher-uploaded Scribd copies exist; no verian.com or 1news.co.nz report was found. The June 1news.co.nz article URL tried returned 404.', needed='Optional: Verian PDFs if James has them.'),
    dict(item='Maori electorate polls for Waiariki, Ikaroa-Rawhiti, Tamaki Makaurau, Te Tai Tokerau', reason='Whakatau 2026 tag, poll tag and landing pages are JS-rendered and list no articles in the fetched bytes; two search passes and the Curia blog index show only Te Tai Tonga, Te Tai Hauauru and Hauraki-Waikato. No source announces commissioning for the other four.',
         needed='Re-check Te Ao Maori News/Curia blog before the 7 Nov 2026 election; capture each seat poll when published.'),
]

LIVE_FIT_INPUT = dict(
    suggestion='James suggested using only the most recent 2026 polls (a recent window) for the live fit.',
    status='Recorded as an input to the later live-fit stage; no data dropped or filtered here, and no fit run.',
    consideration='The frozen national design uses older polls to centre house effects across the pollster roster, to start the trend at the 2023 result and to scale shared polling bias. A recent-window run is plausible as a sensitivity (for example since mid-2025 with the start reset) but departs from the validated design and thins sparse pollsters (Anacta now has one poll under that name; Talbot Mills history carries its earlier name).',
    namingNote='Anacta Consulting is the rebranded Talbot Mills (NZ Herald, 2026-09-10 poll article); the June 2026 article names it "Talbot Mills poll for Anacta". A later stage must decide whether these are one house-effect group.',
)

MAORI_COVERAGE = dict(
    publishedSeatPolls=['Te Tai Tonga', 'Te Tai Hauauru', 'Hauraki-Waikato'],
    seatsWithoutPublishedPoll=['Waiariki', 'Ikaroa-Rawhiti', 'Tamaki Makaurau', 'Te Tai Tokerau'],
    allSevenPolledConfirmed=False,
    commissioner='Whakaata Maori, fieldwork by Curia Market Research, n=500 per seat (420 phone, 80 online), margin of error 4.5%, under the Whakatau 2026 series',
    pace='Three seat polls published 28 Sep-6 Oct 2026 (about one every 4 days), with the election on 7 Nov 2026 (Te Ao Maori News); consistent with, but not a statement of, coverage of all seven.',
    verdict='No fetched source states that all seven seats will be polled or announces further seat polls. Not confirmed; the fallback baseline stays deferred until a seat is shown to be unpolled.',
)

PROTOCOL_NOTES = [
    'Wider environment network: Wikipedia, RNZ, 1News, Roy Morgan, NZ Herald, Stuff, Te Ao Maori News, Newsroom, Curia and Freshwater answered over the pre-configured proxy; taxpayers.org.nz (Cloudflare challenge) and web.archive.org (policy denial) did not. No challenge, paywall or access control was bypassed.',
    'curl with User-Agent "nz-election-model-research/1.0" and -L; body and response headers kept only on HTTP 200; every attempt, including 429/403/404, is in fetch-log.tsv. The Wikipedia REST endpoint rate-limited twice (HTTP 429) before the third attempt succeeded.',
    'Three HTTP-200 bodies were identical 7,271-byte JavaScript shells from thepost.co.nz and were deleted rather than preserved as data; they are listed in discardedShells.',
    'Unlogged discovery that produced leads only, never data: three WebSearch queries, one web.archive.org availability JSON (snapshot exists, bytes denied) and five NZ Herald Talbot Mills articles searched for the May 2024 poll (other months or years; not preserved).',
    'No raw file from the earlier Stage52 GitHub-snapshot capture (data/raw/polling/current-2026) or any Stage35 file was altered; data/sources.json is untouched.',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n').encode()


def norm(text):
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def text_of(path):
    path = Path(path)
    if path.suffix == '.xlsx':
        strings = re.findall(r'<t[^>]*>([^<]*)</t>', zipfile.ZipFile(path).read('xl/sharedStrings.xml').decode())
        return norm(' '.join(strings))
    raw = path.read_text(encoding='utf-8')
    raw = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', raw, flags=re.S)
    return norm(re.sub(r'<[^>]+>', ' ', raw))


def fetch_rows():
    return [line.split('\t') for line in (RAW / 'fetch-log.tsv').read_text().splitlines() if line]


def build_ledger():
    rows = fetch_rows()
    names = {r[5] for r in rows}
    ok = {r[5]: r for r in rows if r[1] == '200'}
    resources, attempts, shells = [], [], []
    for name in sorted(set(ok) & set(FILES)):
        ts, code, final, size, url, _ = ok[name]
        body = RAW / name
        if len(body.read_bytes()) != int(size):
            raise ValueError('Size differs from fetch log for ' + name)
        kind, publisher, subject = FILES[name]
        resources.append(dict(id='polling-current2026primary-' + name, url=url, finalUrl=final, kind=kind, publisher=publisher, subject=subject,
                              retrievedAt=ts, httpStatus=200, rawPath=str(body.relative_to(ROOT)), sha256=sha(body), bytes=int(size),
                              headersPath=str((RAW / (name + '.headers')).relative_to(ROOT)), headersSha256=sha(RAW / (name + '.headers')),
                              licence=LICENCE, processingScript='scripts/polling/primary_capture.py'))
    if set(FILES) != {r['rawPath'].rsplit('/', 1)[1] for r in resources}:
        raise ValueError('FILES and fetch-log disagree')
    for ts, code, final, size, url, name in rows:
        if code == '200' and name in FILES:
            status = 'success'
        elif code == '200' and name in DISCARDED_SHELLS:
            status = 'discarded-js-shell'
        else:
            status = 'failed'
        attempts.append(dict(url=url, retrievedAt=ts, httpStatus=int(code) if code.isdigit() else None, status=status, name=name))
    for name, reason in sorted(DISCARDED_SHELLS.items()):
        if name not in names:
            raise ValueError('Discarded shell missing from fetch log: ' + name)
        shells.append(dict(name=name, reason=reason, present=(RAW / name).exists()))
    return dict(schemaVersion=1, scope='2026-cycle national party-vote poll primary capture (acquisition only; no fit)',
                resources=resources, attempts=attempts, discardedShells=shells, protocolNotes=PROTOCOL_NOTES)


def wikipedia_rows():
    raw = (RAW / 'wikipedia-opinion-polling-2026.html').read_text(encoding='utf-8')
    return [norm(re.sub(r'<[^>]+>', ' ', r)) for r in re.findall(r'<tr.*?</tr>', raw, flags=re.S)]


def audit():
    verified = []
    for cid, name, facts, needles in CHECKS:
        text = text_of(RAW / name)
        missing = [n for n in needles if norm(n) not in text]
        if missing:
            raise ValueError(f'{cid}: not found in {name}: {missing}')
        verified.append(dict(id=cid, file=name, facts=facts, evidencePhrases=needles))
    rows = wikipedia_rows()
    found = {p: any(r.startswith(p) for r in rows) for p in WIKIPEDIA_ROW_PREFIXES}
    if not all(found.values()):
        raise ValueError('Wikipedia rows not found: ' + str([p for p, f in found.items() if not f]))
    raw = (RAW / 'wikipedia-opinion-polling-2026.html').read_text(encoding='utf-8')
    revision = re.search(r'/revision/(\d+)"', raw) and re.search(r'/revision/(\d+)"', raw).group(1)
    etag = re.search(r'etag: W/"(\d+)/', (RAW / 'wikipedia-opinion-polling-2026.html.headers').read_text())
    return dict(
        schemaVersion=1,
        note='Every fact below was checked as verbatim text in the preserved raw bytes (evidencePhrases). None of this is modelled, averaged or added to the Stage35 panel.',
        wikipedia=dict(file='wikipedia-opinion-polling-2026.html', etagRevision=etag.group(1) if etag else None, pageRevision=revision,
                       tableRowsParsed=len(rows), rowPrefixesFound=found),
        confirmed=[
            dict(finding='RNZ-Reid Research poll published 2026-10-06: fieldwork 24 Sep-1 Oct 2026 (labo49 was right; danylmc 4-11 Sep was wrong), n=1000 online quota sample.', evidence='rnz-reid-2026-10-06'),
            dict(finding='Wikipedia (revision above) lists the same row, so the newer 3 Oct Stage35 Wikipedia snapshot is superseded by this capture for that poll only.', evidence='wikipedia'),
            dict(finding='Talbot Mills 1-10 Nov 2024 recovered from a publisher page: NAT 34, LAB 33, GRN 10, ACT 10, NZF 7, TPM 3.3; no n published.', evidence='talbot-2024-11'),
            dict(finding='Fieldwork dates and sample sizes for every Roy Morgan, RNZ-Reid, Verian, Freshwater, Anacta poll since 1 Jun 2026 are confirmed from publisher or pollster bytes and match Wikipedia.', evidence='see verified'),
            dict(finding='Anacta Consulting is the rebranded Talbot Mills (Herald, 2026-09-10 article).', evidence='anacta-2026-09'),
        ],
        verified=verified,
        unresolved=UNRESOLVED,
        maoriCoverage=MAORI_COVERAGE,
        liveFitInput=LIVE_FIT_INPUT)


def build_registry(ledger=None):
    """Dated Stage40-style registry (data/sources.json schema); data/sources.json itself is never touched."""
    ledger = ledger or build_ledger()
    sources = [dict(id=r['id'], organisation=r['publisher'], url=r['url'], dateOrElection='2026 general election cycle; captured ' + r['retrievedAt'][:10],
                    resource=Path(r['rawPath']).name, retrievedAt=r['retrievedAt'], rawPath=r['rawPath'], processingScript=r['processingScript'],
                    limitations=[r['kind'] + ': ' + r['subject'] + '. Fact extraction is checked in primary-capture-audit.json; the bytes are not a parsed dataset.'],
                    sha256=r['sha256'], licence=r['licence'], schemaVersion=1) for r in ledger['resources']]
    return dict(schemaVersion=1, sources=sources)


def verify_ledger():
    ledger = json.loads((RAW / 'acquisition-ledger.json').read_text())
    for r in ledger['resources']:
        if sha(ROOT / r['rawPath']) != r['sha256'] or sha(ROOT / r['headersPath']) != r['headersSha256']:
            raise ValueError('Changed resource ' + r['id'])
    if (RAW / 'acquisition-ledger.json').read_bytes() != encode(build_ledger()):
        raise ValueError('Ledger differs from deterministic rebuild')
    return ledger


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true', help='verify committed outputs byte-for-byte')
    a = ap.parse_args()
    ledger = build_ledger()
    outputs = {RAW / 'acquisition-ledger.json': encode(ledger),
               OUT / 'primary-capture-audit.json': encode(audit()),
               OUT / 'source-registry-primary.json': encode(build_registry(ledger))}
    for path, data in outputs.items():
        if a.check:
            if path.read_bytes() != data:
                raise ValueError('Changed deterministic output ' + path.name)
        else:
            path.write_bytes(data)
    print('ok' if a.check else 'written')


if __name__ == '__main__':
    main()
