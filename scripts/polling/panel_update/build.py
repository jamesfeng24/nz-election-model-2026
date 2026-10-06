"""Stage59: derived 2026-cycle national poll panel (Stage35 panel + three additions - one duplicate).

Offline only; stdlib only. Reads the frozen Stage35 panel and preserved raw bytes, writes a NEW dated panel under
data/processed/polling/panel-update-2026-10/. It changes no Stage35, Stage52 or other earlier file (their
consumers pin the old bytes by hash), fits nothing and averages nothing.

Changes relative to the Stage35 panel (496 waves):
  + RNZ-Reid Research 24 Sep-1 Oct 2026 (published 6 Oct; Stage35 stops at fieldwork end 27 Sep).
  + Talbot Mills 1-10 Nov 2024 (blank-sample row dropped by the Stage35 Wikipedia parser; primary Herald bytes).
  + Talbot Mills 1-10 May 2024 (same parser gap; NAT 35, LAB 32 only; aggregator evidence only).
  - Talbot Mills 16 Apr 2026 duplicate (the Wikipedia-only single-date copy of the Nixinova row).
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re

from scripts.polling.national_foundation.records import record, deduplicate
from scripts.polling.national_foundation.wiki import Tables, clean, dates, pollster

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/processed/polling/panel-update-2026-10'
BASE_PANEL = ROOT / 'data/processed/polling/national-foundation/polls.json'
STAGE35_WIKI = ROOT / 'data/raw/polling/stage35/wiki2026.html'
PRIMARY = ROOT / 'data/raw/polling/current-2026-primary'
LEDGER = PRIMARY / 'acquisition-ledger.json'
CAPTURE_AUDIT = ROOT / 'data/processed/polling/current-cycle-acquisition/primary-capture-audit.json'
LABO49 = ROOT / 'data/raw/polling/current-2026/labo49-polls.json'
DANYLMC = ROOT / 'data/raw/polling/current-2026/danylmc-2026_polling.json'

RNZ_FILE = 'rnz-reid-2026-10-06.html'
HERALD_FILE = 'talbot-herald-2024-11.html'
PARTIES = ('NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'MRI', 'TOP')

# The two Talbot Mills rows the Stage35 Wikipedia adapter dropped (blank sample cell), and the duplicate pair.
GAP_FIELDWORK = {('TBM', '2024-05-01', '2024-05-10'), ('TBM', '2024-11-01', '2024-11-10')}
DUPLICATE_KEPT = 'nz-poll-342c0ad79dbdb93739cf'      # Nixinova row, fieldwork ['2026-04-00', '2026-04-16']
DUPLICATE_DROPPED = 'nz-poll-76482a3c446b7d615157'   # Wikipedia row, single date 2026-04-16

RNZ_PHRASES = ['National Party has fallen 3.2 percentage points since August, registering just 25.9 percent',
               'falling 1.4 points to 30.8 percent', 'jumping 4.6 points to 14.8 percent',
               'New Zealand First has fallen 1.3 points to 10.6 percent', 'ACT has climbed 1.3 points to 9 percent',
               'Te Pāti Māori has dropped one point to 2 percent', 'Opportunity has edged up 0.2 points to 5.5 percent',
               'Reid Research surveyed 1000 eligible voters online between 24 September and 1 October 2026',
               'using quota sampling', 'maximum margin of error of +/- 3.1 percentage points',
               'excluded the 3 percent who were undecided or did not know and the 2.6 percent who said they would not vote',
               '6 October 2026, 6:27am']
HERALD_PHRASES = ['A corporate poll from Talbot Mills', 'has National on 34% and Labour one point behind on 33%',
                  'the Greens and Act on 10% each, followed by NZ First on 7% and Te Pāti Māori on 3.3%',
                  'taken over an unusually long period of November 1-10 (with a margin of error of 3.1%)']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n').encode()


def text_of(path):
    t = Path(path).read_text(encoding='utf8', errors='replace')
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', t, flags=re.S)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', t)).split())


def ledger_entry(name):
    for r in json.loads(LEDGER.read_text())['resources']:
        if r['rawPath'].endswith('/' + name):
            if sha(ROOT / r['rawPath']) != r['sha256']:
                raise ValueError('Changed raw file ' + name)
            return r
    raise ValueError('Not ledgered ' + name)


def require_phrases(name, phrases):
    text = text_of(PRIMARY / name)
    missing = [p for p in phrases if p not in text]
    if missing:
        raise ValueError(f'{name}: phrases not in preserved bytes: {missing}')


def primary_provenance(name, role):
    e = ledger_entry(name)
    return {'sourceId': e['id'], 'rawPath': e['rawPath'], 'sha256': e['sha256'], 'url': e['url'], 'role': role,
            'sourceType': 'primary_publisher_page'}


def wikipedia_rows():
    """Every poll row of the pinned Stage35 Wikipedia table, including rows with a blank sample cell.

    Same table walk and field parsing as the Stage35 adapter; the only difference is that an empty or '1,000+'
    sample cell becomes 'unknown' instead of rejecting the row. Event rows and the 2023 result row are skipped.
    """
    parser = Tables()
    parser.feed(STAGE35_WIKI.read_text())
    tables = [t for t in parser.tables if t and t[0][:3] == ['Date[a]', 'Polling organisation', 'Sample size'] and 'NAT' in t[0]]
    if len(tables) != 1:
        raise ValueError('Party table layout')
    header = tables[0][0]
    rows = []
    for number, row in enumerate(tables[0][1:], 2):
        if len(row) != len(header):
            continue
        try:
            fs = {'date': dates(row[0]), 'org': pollster(row[1])}
        except ValueError:
            continue
        n = clean(row[2])
        fs['n'] = '~' if n in ('', '1,000+') else n
        for k, v in zip(header[3:-1], row[3:-1]):
            fs[{'TPM': 'MRI', 'OPP': 'TOP', 'Others': 'OTH'}.get(k, k)] = clean(v)
        prov = {'sourceId': 'polling35-wiki2026.html', 'row': number, 'sourceType': 'aggregator'}
        r = record(2026, fs, prov)
        r['commissioner'] = row[1]
        rows.append(r)
    return rows


def with_update(r, grade, note, extra_provenance):
    r = json.loads(json.dumps(r))
    r['provenance'].extend(extra_provenance)
    r['evidenceGrade'] = grade
    r['panelUpdateNote'] = note
    return r


def build_rnz(audit_fact):
    """RNZ-Reid 24 Sep-1 Oct 2026 from the preserved RNZ article; Others 0.7 only from the Wikipedia capture."""
    require_phrases(RNZ_FILE, RNZ_PHRASES)
    f = audit_fact['facts']
    s = f['shares']
    wiki = text_of(PRIMARY / 'wikipedia-opinion-polling-2026.html')
    wiki_row = re.search(r'24 Sep - 1 Oct 2026 RNZ—Reid Research 1,000 25\.9 30\.8 14\.8 9 10\.6 2 5\.5 0\.7 4\.9', wiki)
    if not wiki_row:
        raise ValueError('Wikipedia capture row for RNZ-Reid 24 Sep-1 Oct not found')
    fields = {'date': ['2026-09-24', '2026-10-01'], 'org': 'REI', 'n': '1000',
              'NAT': '25.9', 'LAB': '30.8', 'GRN': '14.8', 'ACT': '9', 'NZF': '10.6', 'MRI': '2', 'TOP': '5.5', 'OTH': '0.7'}
    if {k: float(fields[k]) for k in ('NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'TOP')} != \
            {k: s[k] for k in ('NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'TOP')} or float(fields['MRI']) != s['TPM']:
        raise ValueError('RNZ shares differ from the verified capture audit')
    r = record(2026, fields, primary_provenance(RNZ_FILE, 'primary release: fieldwork, sample, mode, publication, party shares'))
    r['provenance'].append({'sourceId': 'polling-current2026primary-wikipedia-opinion-polling-2026.html',
                            'rawPath': 'data/raw/polling/current-2026-primary/wikipedia-opinion-polling-2026.html',
                            'sha256': sha(PRIMARY / 'wikipedia-opinion-polling-2026.html'),
                            'role': 'Others 0.7 only (not in the RNZ article text)', 'sourceType': 'aggregator'})
    r.update(commissioner='RNZ–Reid Research', publication='2026-10-06T06:27:00+13:00', publicationConfidence='verified',
             publicationEvidence=f'{RNZ_FILE}; "6 October 2026, 6:27am" (NZDT)', mode='online_quota_sample',
             population='eligible NZ voters', denominator='decided_stated_by_publisher', undecided=0.03)
    r['assumptionFlags'] = ['published party-vote figures exclude 3% undecided/do not know and 2.6% who would not vote (RNZ)',
                            'maximum margin of error +/-3.1 points (95%); quota sample weighted by age, gender, geography',
                            'Others 0.7 from the Wikipedia capture only']
    return with_update(r, 'primary_verified', 'Added: published after the Stage35 snapshot (latest fieldwork end 2026-09-27).', [])


def build_gap_rows(base_ids, wiki_rows):
    gap = {}
    for r in wiki_rows:
        if r['id'] in base_ids:
            continue
        gap[(r['pollsterCode'], r['fieldworkRaw'][0], r['fieldworkRaw'][-1])] = r
    if set(gap) != GAP_FIELDWORK:
        raise ValueError(f'Unexpected parser-gap rows: {sorted(gap)}')
    nov = gap[('TBM', '2024-11-01', '2024-11-10')]
    may = gap[('TBM', '2024-05-01', '2024-05-10')]
    require_phrases(HERALD_FILE, HERALD_PHRASES)
    herald = primary_provenance(HERALD_FILE, 'primary article: fieldwork 1-10 Nov, NAT 34, LAB 33, GRN 10, ACT 10, NZF 7, TPM 3.3, margin 3.1%')
    for k, v in (('NAT', 34), ('LAB', 33), ('GRN', 10), ('ACT', 10), ('NZF', 7), ('MRI', 3.3)):
        if nov['estimates'][k]['share'] != v / 100:
            raise ValueError('Wikipedia Nov 2024 row disagrees with the Herald article: ' + k)
    nov = with_update(nov, 'primary_verified', 'Added: dropped by the Stage35 Wikipedia adapter (blank sample cell); Wikipedia row agrees with the Herald article.', [herald])
    nov['assumptionFlags'].append('Talbot Mills corporate poll; sample size not published (margin of error 3.1%)')
    for k, v in (('NAT', 35), ('LAB', 32)):
        if may['estimates'][k]['share'] != v / 100:
            raise ValueError('Unexpected May 2024 shares')
    if any(may['estimates'][k]['status'] != 'not_reported' for k in ('GRN', 'ACT', 'NZF', 'MRI', 'TOP')):
        raise ValueError('May 2024 row should report only NAT and LAB')
    may = with_update(may, 'aggregator_only',
                      'Added: dropped by the Stage35 Wikipedia adapter (blank sample cell). Only NAT 35 and LAB 32 are published; '
                      'no primary article could be recovered (The Post page is a JavaScript shell; web.archive.org denied).',
                      [{'sourceId': 'labo49/nzpolls@da33cf52 data/polls.json', 'sha256': sha(LABO49), 'rawPath': str(LABO49.relative_to(ROOT)),
                        'role': 'derivative Wikipedia scrape; cites https://www.thepost.co.nz/politics/350282502/are-tax-cuts-boost-economy-needs (not retrievable)',
                        'sourceType': 'aggregator'}])
    may['assumptionFlags'].append('only two party shares published; unreported parties are missing, not zero')
    return [nov, may]


def collapse_duplicate(records):
    by_id = {r['id']: r for r in records}
    kept, dropped = by_id[DUPLICATE_KEPT], by_id[DUPLICATE_DROPPED]
    def semantic(o):  # missing-marker spelling ('~' vs an en dash) is not a substantive difference (Stage35)
        return (o['status'], o['share'], o['bounds'])
    same = (all(semantic(kept['estimates'][p]) == semantic(dropped['estimates'][p]) for p in kept['estimates'])
            and semantic(kept['publishedOther']) == semantic(dropped['publishedOther'])
            and kept['additionalPublishedCategories'] == dropped['additionalPublishedCategories']
            and all(kept[k] == dropped[k] for k in ('sampleSize', 'pollsterCode', 'cycle')))
    if not same:
        raise ValueError('April 2026 pair is not a duplicate')
    new_kept = with_update(kept, 'aggregator_only',
                           'Kept as the single Talbot Mills April 2026 wave; the Wikipedia single-date copy (16 Apr) was collapsed into it.',
                           dropped['provenance'])
    new_kept['assumptionFlags'].append('fieldwork start day not published; 16 Apr is the date the poll was first reported, so the end bound is an upper bound')
    out = [new_kept if r['id'] == DUPLICATE_KEPT else r for r in records if r['id'] != DUPLICATE_DROPPED]
    return out, {'kept': DUPLICATE_KEPT, 'dropped': DUPLICATE_DROPPED}


def snapshot_rows(path, key):
    d = json.loads(Path(path).read_text())
    rows = d if isinstance(d, list) else d['polls'] if 'polls' in d else d
    if key == 'labo49':
        return [{'end': r['date'], 'label': r['dateLabel'], 'pollster': r['pollster'], 'n': r['sampleSize'],
                 'shares': {k: v for k, v in r['results'].items() if k in ('NAT', 'LAB', 'GRN', 'ACT', 'NZF')}} for r in rows]
    names = {'National': 'NAT', 'Labour': 'LAB', 'Green': 'GRN', 'ACT': 'ACT', 'NZ First': 'NZF'}
    return [{'end': r['fieldwork_end'], 'label': f"{r['fieldwork_start']}..{r['fieldwork_end']}", 'pollster': r['pollster'], 'n': r['sample_size'],
             'shares': {names[k]: v for k, v in r['parties'].items() if k in names}} for r in rows]


def match_snapshot(rows, panel):
    """Snapshot rows that name Talbot Mills/Anacta and have no panel wave with the same shares and a fieldwork window containing the end date."""
    talbot = [r for r in rows if re.search('Talbot|Anacta', r['pollster']) and r['end'] >= '2023-10-15']
    unmatched, hits = [], {}
    for r in talbot:
        found = [p['id'] for p in panel if p['pollsterCode'] in ('TBM', 'ANA')
                 and p['fieldworkStartBounds'][0] <= r['end'] <= p['fieldworkEndBounds'][1]
                 and all(p['estimates'][k]['share'] is not None and abs(p['estimates'][k]['share'] * 100 - v) < 1e-9 for k, v in r['shares'].items())
                 and (r['n'] is None or p['sampleSize'] in (None, r['n']))]
        if not found:
            unmatched.append({'label': r['label'], 'pollster': r['pollster'], 'shares': r['shares']})
        for i in found:
            hits.setdefault(i, []).append(r['label'])
    return {'talbotMillsRows': len(talbot), 'unmatched': unmatched,
            'panelWavesMatchedByMoreThanOneSnapshotRow': {k: v for k, v in hits.items() if len(v) > 1}}


def build():
    base_bytes = BASE_PANEL.read_bytes()
    base = json.loads(base_bytes)['records']
    base_ids = {r['id'] for r in base}
    capture = json.loads(CAPTURE_AUDIT.read_text())
    fact = next(v for v in capture['verified'] if v['id'] == 'rnz-reid-2026-10-06')
    gap = build_gap_rows(base_ids, wikipedia_rows())
    rnz = build_rnz(fact)
    records, dup = collapse_duplicate(base)
    additions = [rnz] + gap
    records, audit_dups = deduplicate(records + additions)
    if audit_dups:
        raise ValueError('Addition collides with an existing wave: ' + json.dumps(audit_dups))
    ids = [r['id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate ids')
    panel = {'schemaVersion': 1, 'basePanel': 'data/processed/polling/national-foundation/polls.json',
             'basePanelSha256': hashlib.sha256(base_bytes).hexdigest(), 'records': records}
    by_cycle = {}
    for r in records:
        by_cycle[r['cycle']] = by_cycle.get(r['cycle'], 0) + 1
    base_cycle = {}
    for r in base:
        base_cycle[r['cycle']] = base_cycle.get(r['cycle'], 0) + 1
    labo, dan = snapshot_rows(LABO49, 'labo49'), snapshot_rows(DANYLMC, 'danylmc')
    rnz_snap = {'labo49': [r['label'] for r in labo if r['shares'].get('NAT') == 25.9 and r['shares'].get('LAB') == 30.8],
                'danylmc': [r['label'] for r in dan if r['shares'].get('NAT') == 25.9 and r['shares'].get('LAB') == 30.8]}
    changes = {
        'schemaVersion': 1,
        'added': [{'id': r['id'], 'pollsterCode': r['pollsterCode'], 'fieldworkRaw': r['fieldworkRaw'], 'evidenceGrade': r['evidenceGrade'],
                   'sampleSize': r['sampleSize'], 'shares': {k: v['published'] for k, v in r['estimates'].items() if v['status'] != 'not_reported'},
                   'provenance': [p['sourceId'] for p in r['provenance']]} for r in additions],
        'removed': [{'id': DUPLICATE_DROPPED, 'collapsedInto': DUPLICATE_KEPT, 'identicalFields': ['party estimates (status, share, bounds)', 'sampleSize', 'pollsterCode', 'cycle'],
                     'whyThisOneWasDropped': 'The kept Nixinova row preserves that the fieldwork start day is unknown (start day 00, interval); the Wikipedia copy states the single day 16 Apr, which is the date the poll was first reported, not a published fieldwork date, and would silently turn an end bound into a fieldwork day.'}],
        'baseWaves': len(base), 'updatedWaves': len(records), 'wavesByCycleBase': {str(k): v for k, v in sorted(base_cycle.items())},
        'wavesByCycleUpdated': {str(k): v for k, v in sorted(by_cycle.items())},
        'unchangedBaseWaves': len(base) - 2,
        'rnzReidAcrossStage52Snapshots': {'panelFieldwork': ['2026-09-24', '2026-10-01'], 'snapshotLabels': rnz_snap,
             'note': 'labo49 (24 Sep-1 Oct) agrees with the RNZ article; danylmc dates the same shares 4-11 Sep, which the RNZ article contradicts. Both are derivative Wikipedia scrapes.'},
        'stage52TalbotMillsCheck': {'labo49': match_snapshot(labo, records), 'danylmc': match_snapshot(dan, records)},
        'stage52TalbotMillsCheckAgainstStage35Panel': {'labo49': match_snapshot(labo, base), 'danylmc': match_snapshot(dan, base)},
        'notes': ['Stage35 polls.json is unchanged; Stage36-Stage48 consumers still pin its bytes.',
                  'evidenceGrade is present only on the waves this update added or changed.',
                  'Labour-commissioned Talbot Mills rows (30 Apr and 22-28 Nov 2024) share pollster code TBM with the corporate rows in the Stage35 panel; unchanged here.'],
    }
    consumed = {str(p.relative_to(ROOT)): sha(p) for p in (BASE_PANEL, STAGE35_WIKI, LEDGER, CAPTURE_AUDIT, LABO49, DANYLMC,
                                                          PRIMARY / RNZ_FILE, PRIMARY / HERALD_FILE, PRIMARY / 'wikipedia-opinion-polling-2026.html')}
    contract = {'schemaVersion': 1, 'consumedSha256': consumed,
                'generatorSha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))}}
    return {'panel.json': panel, 'changes.json': changes, 'input-contract.json': contract}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true', help='verify committed outputs byte-for-byte')
    a = ap.parse_args()
    outputs = build()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in outputs.items():
        data = encode(value)
        if a.check:
            if (OUT / name).read_bytes() != data:
                raise ValueError('Changed deterministic output ' + name)
        else:
            (OUT / name).write_bytes(data)
    print('ok' if a.check else 'written', len(outputs['panel.json']['records']), 'waves')


if __name__ == '__main__':
    main()
