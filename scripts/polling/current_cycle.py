"""Current-cycle (2026) national poll acquisition ledger and gap audit.

Offline only. Raw bytes are fetched by shell (curl) into data/raw/polling/current-2026;
this module registers them with checksums, and compares the preserved snapshots with the
frozen Stage35 national panel. It fits nothing and changes no Stage35 file.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/polling/current-2026'
OUT = ROOT / 'data/processed/polling/current-cycle-acquisition'
PANEL = ROOT / 'data/processed/polling/national-foundation/polls.json'
AUDIT = ROOT / 'data/processed/polling/national-foundation/audit.json'
RESOURCE_CAP = 20
PARTIES = ('NAT', 'LAB', 'GRN', 'ACT', 'NZF')

LABO49 = ('labo49/nzpolls', 'da33cf52497f394509caec147f13265667e2679e')
DANYLMC = ('danylmc/nz-polls', '25c58bc937d52d27f5fd60197347b1c088831ebb')
NO_LICENCE = ('Repository has no LICENSE file; bytes preserved unchanged for research provenance only. '
              'Underlying poll figures originate from Wikipedia (CC BY-SA) and the named pollsters.')

# raw file -> (repository, path in repository, purpose)
RESOURCES = {
    'labo49-polls.json': (LABO49, 'data/polls.json',
                          'Parsed Wikipedia 2026 poll table incl. per-poll source URL; automated daily refresh'),
    'labo49-meta.json': (LABO49, 'data/meta.json', 'Scrape timestamp for labo49-polls.json'),
    'labo49-newPolls.json': (LABO49, 'data/newPolls.json', 'Rows first seen on the last labo49 refresh'),
    'labo49-fetch-polls.ts': (LABO49, 'scripts/fetch-polls.ts', 'Scraper provenance (reference only, not run)'),
    'labo49-wikiPollScraper.ts': (LABO49, 'lib/wikiPollScraper.ts', 'Table parser provenance (reference only, not run)'),
    'labo49-README.md': (LABO49, 'README.md', 'Repository description'),
    'danylmc-2026_polling.json': (DANYLMC, 'data/2026_polling.json',
                                  'Independently scraped Wikipedia 2026 poll table with fieldwork start/end'),
    'danylmc-scraper.py': (DANYLMC, 'scraper.py', 'Scraper provenance (reference only, not run)'),
    'danylmc-README.md': (DANYLMC, 'README.md', 'Repository description'),
}

# Routes that returned no usable raw bytes; recorded as leads, never as data.
LEADS = [
    {'kind': 'national poll', 'url': 'https://www.rnz.co.nz/news/politics_election-2026/1749693/rnz-reid-research-poll-national-crashes-greens-surge-opportunity-kingmaker',
     'note': 'RNZ-Reid Research national poll published 2026-10-06; labo49 snapshot lists fieldwork 24 Sep-1 Oct 2026, n=1000, NAT 25.9 LAB 30.8 GRN 14.8 ACT 9 NZF 10.6 TPM 2 TOP 5.5. '
             'Primary page not retrievable here; method, exact fieldwork dates and publication time remain unverified.'},
    {'kind': 'national poll', 'url': 'https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_New_Zealand_general_election',
     'note': 'Canonical aggregator table. Direct fetch denied; Stage35 holds the 2026-10-03 snapshot and the two GitHub snapshots here are parsed copies refreshed 2026-10-05/06.'},
    {'kind': 'Maori roll poll', 'url': 'https://www.teaonews.co.nz/2026/09/17/whakaata-maori-poll-labour-leads-party-vote-as-te-pati-maori-dominates-maori-roll/',
     'note': 'Whakaata Maori poll by Curia, published 2026-09-17; summary-reported fieldwork 29 Aug-10 Sep, n=1000 Maori voters (500 phone/500 online), Maori and general rolls overall, not individual seats. Mirror: https://thespinoff.co.nz/atea/17-09-2026/whakaata-maori-poll-labour-leads-party-vote-as-te-pati-maori-dominates-maori-roll. Unverified summary.'},
    {'kind': 'Maori electorate poll', 'seat': 'Te Tai Tonga', 'url': 'https://www.teaonews.co.nz/2026/09/29/whakaata-maori-curia-poll-shows-takuta-ferris-trailing-in-te-tai-tonga/',
     'note': 'Whakaata Maori-Curia, published 2026-09-29; summary-reported fieldwork 14-24 Sep, n=500 Maori voters 18+ (420 phone/80 online), +/-4.5%. Candidate vote: Ramsden (LAB) 30, Murch (TPM) 17, Te Morenga (GRN) 16, Ferris (IND) 15. Also party vote. Mirrors: RNZ 1647755, NZ Herald 7GVSRBESHZDKRPHO5VHNPJB3SM. Unverified summary.'},
    {'kind': 'Maori electorate poll', 'seat': 'Te Tai Hauāuru', 'url': 'https://www.teaonews.co.nz/2026/09/30/debbie-ngarewa-packer-leads-te-tai-hauauru-poll/',
     'note': 'Whakaata Maori-Curia as part of its "Whakatau 2026" election series, published 2026-09-30; summary-reported fieldwork 14-24 Sep, n=500 (420 phone/80 online), +/-4.5%. Candidate vote: Ngarewa-Packer (TPM) 38, Katene (LAB) 27, Raukawa 10, undecided 18. Party vote shown Labour 30, Greens 22, TPM 18. Mirrors: RNZ 1656179, NZ Herald XCKALCEWXBBSDB43Z55QMSM4JE. Unverified summary.'},
    {'kind': 'Maori electorate poll', 'seat': 'Hauraki-Waikato', 'url': 'https://www.nzherald.co.nz/nz/politics/election-2026-hana-rawhiti-maipi-clarke-well-ahead-in-hauraki-waikato-poll/CETAZEFVJBHM3N2AVG2MLVM6EA/',
     'note': 'NZ Herald headline only (Maipi-Clarke well ahead); page blocked to the reading tool by robots.txt and by egress policy; commissioner, dates, n and figures unknown.'},
    {'kind': 'Maori electorate polls (context)', 'url': 'https://newsroom.co.nz/2026/09/29/maori-seat-poll-electorates-hang-in-balance-as-willie-jackson-tackles-vote-splitting/',
     'note': 'Newsroom headline "Maori seat poll: electorates hang in balance" (blocked by robots.txt for the reading tool).'},
    {'kind': 'strategy context', 'url': 'https://waateanews.com/2026/10/05/all-in-the-maori-seats-te-pati-maori-unveils-one-person-party-list/',
     'note': 'Waatea News 2026-10-05: Te Pati Maori one-person party list (Lance Norman), electorate vote to TPM and party vote to Labour or the Greens. Also Newsroom 2026-08-28 "one-tick trick" and NZ Herald (Willie Jackson) coverage of the strategy; not retrieved.'},
]

MAORI_COVERAGE = dict(
    teTapatiMaoriOneTickStrategy='Confirmed by multiple 2026 reports (Waatea 2026-10-05, Newsroom, NZ Herald): electorate vote to TPM, party vote to Labour or the Greens, one-person party list.',
    publishedElectoratePolls='At least 3 of 7 seats have a published poll as of 2026-10-06: Te Tai Tonga, Te Tai Hauāuru (Whakaata Maori-Curia, fieldwork reported 14-24 Sep, n=500 each) and Hauraki-Waikato (headline only).',
    allSevenPolledConfirmed=False,
    verdict='Not confirmed: no readable source states that all seven seats will be polled or announces commissioning for the other four (Waiariki, Ikaroa-Rawhiti, Tamaki Makaurau, Te Tai Tokerau). The pattern, a Whakaata Maori "Whakatau 2026" Curia series released seat by seat, is consistent with James\'s expectation.',
)

PROTOCOL_NOTES = [
    'Outbound HTTPS in this environment allows GitHub raw/git only; every news, Wikipedia, pollster and Electoral Commission host answered the proxy CONNECT with 403 (reachability-probe.tsv).',
    'Two WebSearch discovery queries (GitHub datasets; Maori electorate polls) and three WebFetch reads were used for discovery only. WebFetch returns model-summarised text, is not raw bytes, was observed stale/inconsistent for the Wikipedia table, and is never a data source here.',
    'No fresh Wikipedia, pollster or news bytes were captured. Existing Stage35 raw files (Wikipedia 2026-10-03, Nixinova bulk at 781f9eec) remain the preserved primary-aggregator evidence.',
    'Upstream HEADs checked with git ls-remote on 2026-10-06 are unchanged from Stage35 pins: ariedotcodotnz/nz-poll-of-polls ef76cf65, Nixinova/NZPolls 781f9eec, ellisp/nz-election-forecast 7aa741e7.',
    'danylmc/nz-polls and labo49/nzpolls are new relative to Stage35; they are derivative scrapes of Wikipedia, not independent measurements, and add no independent poll evidence.',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n').encode()


def tsv(name):
    return [line.split('\t') for line in (RAW / name).read_text().splitlines() if line]


def build_ledger():
    fetched = {row[3]: row for row in tsv('fetch-log.tsv')}
    if set(fetched) != set(RESOURCES):
        raise ValueError('fetch-log.tsv and RESOURCES disagree')
    resources, attempts = [], []
    for name, ((repo, commit), path, purpose) in sorted(RESOURCES.items()):
        ts, code, url, _ = fetched[name]
        if code != '200' or url != f'https://raw.githubusercontent.com/{repo}/{commit}/{path}':
            raise ValueError('Unexpected fetch record for ' + name)
        raw = (RAW / name).read_bytes()
        rel = str((RAW / name).relative_to(ROOT))
        resources.append(dict(id='polling-current2026-' + name, url=url, repository=repo, commit=commit,
                              purpose=purpose, retrievedAt=ts, rawPath=rel, sha256=hashlib.sha256(raw).hexdigest(),
                              bytes=len(raw), licence=NO_LICENCE, processingScript='scripts/polling/current_cycle.py'))
        attempts.append(dict(url=url, retrievedAt=ts, status='success', httpStatus=200, rawPath=rel))
    for ts, code, url in tsv('reachability-probe.tsv'):
        attempts.append(dict(url=url, retrievedAt=ts, status='blocked', httpStatus=None,
                             detail='curl exit with no HTTP status (proxy CONNECT 403 policy denial)', rawPath=None))
    if len(resources) > RESOURCE_CAP or len({r['url'] for r in resources}) != len(resources):
        raise ValueError('Budget/duplicate resource')
    return dict(schemaVersion=1, scope='2026-cycle national party-vote poll acquisition (acquisition only; no fit)',
                resourceCap=RESOURCE_CAP, resources=resources, attempts=attempts, leads=LEADS,
                maoriCoverage=MAORI_COVERAGE,
                protocolNotes=PROTOCOL_NOTES,
                stoppingReason='Only GitHub-hosted derivative snapshots were reachable; primary pollster/news/Wikipedia routes are denied by egress policy. '
                               'Further searching cannot produce raw bytes from this environment.')


def build_registry(ledger=None):
    """Stage40-style dated registry (data/sources.json schema); data/sources.json itself is never touched."""
    ledger = ledger or build_ledger()
    sources = [dict(id=r['id'], organisation=r['repository'] + ' (GitHub; derivative scrape of Wikipedia 2026 opinion-polling table)',
                    url=r['url'], dateOrElection='2026 general election cycle; snapshot ' + r['retrievedAt'][:10],
                    resource=Path(r['rawPath']).name, retrievedAt=r['retrievedAt'], rawPath=r['rawPath'],
                    processingScript=r['processingScript'],
                    limitations=['Derivative aggregator copy, not an original pollster release; fieldwork/publication metadata unverified.', r['purpose']],
                    sha256=r['sha256'], licence=r['licence'], schemaVersion=1) for r in ledger['resources']]
    return dict(schemaVersion=1, sources=sources)


def verify_ledger():
    ledger = json.loads((RAW / 'acquisition-ledger.json').read_text())
    for r in ledger['resources']:
        if sha(ROOT / r['rawPath']) != r['sha256']:
            raise ValueError('Changed resource ' + r['id'])
    if ledger != build_ledger():
        raise ValueError('Ledger differs from deterministic rebuild')
    return ledger


def _round(m, k):
    return round(m[k], 1) if m.get(k) is not None else None


def keys_labo49(rows):
    return [(r['date'],) + tuple(_round(r['results'], k) for k in PARTIES) for r in rows]


def keys_danylmc(rows):
    names = dict(zip(PARTIES, ('National', 'Labour', 'Green', 'ACT', 'NZ First')))
    return [(r['fieldwork_end'],) + tuple(_round(r['parties'], names[k]) for k in PARTIES) for r in rows]


def keys_panel(records):
    out = []
    for r in records:
        e = {k: v['share'] * 100 for k, v in r['estimates'].items() if v.get('share') is not None}
        out.append((r['fieldworkEndBounds'][1],) + tuple(_round(e, k) for k in PARTIES))
    return out


def audit():
    lab_all = json.loads((RAW / 'labo49-polls.json').read_text())
    dan_all = json.loads((RAW / 'danylmc-2026_polling.json').read_text())
    lab = [r for r in lab_all if 'election result' not in r['pollster']]
    dan = [r for r in dan_all['polls'] if 'election result' not in r['pollster']]
    panel = [r for r in json.loads(PANEL.read_text())['records'] if r['cycle'] == 2026]
    cl, cd, cp = Counter(keys_labo49(lab)), Counter(keys_danylmc(dan)), Counter(keys_panel(panel))

    lab_only = sorted((k, n - cp.get(k, 0)) for k, n in cl.items() if n > cp.get(k, 0))
    by_key = {k: r for r, k in zip(lab, keys_labo49(lab))}
    dan_by_key = {k: r for r, k in zip(dan, keys_danylmc(dan))}
    unmatched_lab = [dict(key=list(k), missingCopies=n, pollster=by_key[k]['pollster'], fieldwork=by_key[k]['dateLabel'],
                          sampleSize=by_key[k]['sampleSize'], sourceUrl=by_key[k]['sourceUrl'],
                          firstSeenInLabo49=by_key[k]['firstSeenAt']) for k, n in lab_only]
    # same shares reported with a different fieldwork end in the two snapshots
    shares = lambda k: k[1:]
    lab_vs_dan = []
    for k in sorted(set(cl) - set(cd)):
        for k2 in sorted(set(cd) - set(cl)):
            if shares(k) == shares(k2):
                lab_vs_dan.append(dict(sharesNATLABGRNACTNZF=list(shares(k)), labo49End=k[0], danylmcEnd=k2[0],
                                       labo49Label=by_key[k]['dateLabel'], danylmcFieldwork=[dan_by_key[k2]['fieldwork_start'], dan_by_key[k2]['fieldwork_end']],
                                       pollster=by_key[k]['pollster']))
    panel_dups = sorted((k, n) for k, n in cp.items() if n > 1)
    excluded = json.loads(AUDIT.read_text())['currentTableExcludedRows']
    blank_n = [dict(row=x['row'], fieldwork=x['raw'][0], pollster=x['raw'][1], sampleCell=x['raw'][2])
               for x in excluded if str(x['reason']).startswith('invalid literal for int()')]
    return dict(
        schemaVersion=1,
        note='Comparison only. Keys are (fieldwork end, NAT, LAB, GRN, ACT, NZF) rounded to 0.1pp; None = party not reported. No Stage35 file is changed; panel decisions stay with a later authorised stage.',
        snapshots=dict(labo49=dict(commit=LABO49[1], rows=len(lab), scrapedAt=json.loads((RAW / 'labo49-meta.json').read_text())['fetchedAt'],
                                   latestFieldworkEnd=max(r['date'] for r in lab), pollsters=dict(sorted(Counter(r['pollster'] for r in lab).items()))),
                       danylmc=dict(commit=DANYLMC[1], rows=len(dan), scrapedAt=dan_all['scraped_at'],
                                    latestFieldworkEnd=max(r['fieldwork_end'] for r in dan))),
        stage35Panel=dict(cycle2026Waves=len(panel), distinctKeys=len(cp), latestFieldworkEnd=max(k[0] for k in cp)),
        panelMissingFromLabo49=sorted(k for k in cp if k not in cl),
        labo49RowsNotInStage35Panel=unmatched_lab,
        danylmcRowsNotInStage35Panel=sorted([list(k), n - cp.get(k, 0)] for k, n in cd.items() if n > cp.get(k, 0)),
        labo49VersusDanylmcDateConflicts=lab_vs_dan,
        stage35PanelWavesWithIdenticalEndAndShares=[dict(key=list(k), copies=n) for k, n in panel_dups],
        stage35WikipediaParserRowsDroppedForBlankOrNonIntegerSample=blank_n,
        interpretation=[
            'All 119 distinct Stage35 2026-cycle keys are present in both snapshots with identical shares: no value conflict.',
            'Rows absent from the Stage35 panel: the RNZ-Reid Research poll published 2026-10-06 (after the 2026-10-03 Stage35 snapshot), and two Talbot Mills rows (1-10 May 2024, 1-10 Nov 2024) that exist only in the Wikipedia table and were dropped by the Stage35 Wikipedia parser for a blank sample-size cell.',
            'The two snapshots disagree on the fieldwork of the RNZ-Reid Research row (labo49 24 Sep-1 Oct; danylmc 4-11 Sep with identical shares). A 6 Oct 2026 NZCity report quotes the RNZ article as comparing with the August poll, consistent with a late-September/October poll; the primary page is unreachable so the dates stay unverified.',
            'Stage35 holds both a Nixinova row with a day-00 fieldwork start and a Wikipedia row for the same Talbot Mills 16 Apr 2026 result; same-pollster overlap is screened at cutoff by the frozen design, so no change is made here.',
        ])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true', help='verify committed outputs byte-for-byte')
    a = ap.parse_args()
    ledger = build_ledger()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.check:
        verify_ledger()
    else:
        (RAW / 'acquisition-ledger.json').write_bytes(encode(ledger))
    gap = encode(audit())
    registry = encode(build_registry(ledger))
    if a.check:
        if (OUT / 'source-registry.json').read_bytes() != registry:
            raise ValueError('Changed deterministic source-registry.json')
        if (OUT / 'gap-audit.json').read_bytes() != gap:
            raise ValueError('Changed deterministic gap-audit.json')
        if (RAW / 'acquisition-ledger.json').read_bytes() != encode(ledger):
            raise ValueError('Changed deterministic acquisition-ledger.json')
    else:
        (OUT / 'gap-audit.json').write_bytes(gap)
        (OUT / 'source-registry.json').write_bytes(registry)
    print('ok' if a.check else 'written')


if __name__ == '__main__':
    main()
