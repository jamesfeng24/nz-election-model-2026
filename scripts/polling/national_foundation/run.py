"""Reproduce Stage35 data/cutoff foundation only; no posterior fits or scores."""
import argparse
from collections import Counter
from datetime import date,timedelta
import hashlib
import json
from pathlib import Path
from .records import parse_bulk,deduplicate
from .wiki import parse_current
from .timing import select,day_end

ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/'data/raw/polling/stage35'
OUT=ROOT/'data/processed/polling/national-foundation'
BASE='9dedccd875dda04f78522e4caeb46a7f94ef0e66'
DATES={2014:'2014-09-20',2017:'2017-09-23',2020:'2020-10-17',2023:'2023-10-14',2026:'2026-11-07'}


def encode(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()


def save(name,value,check):
    raw=encode(value);p=OUT/name
    if check:
        if p.read_bytes()!=raw:raise ValueError('Changed deterministic '+name)
    else:p.write_bytes(raw)


def verify_sources():
    ledger=json.loads((RAW/'acquisition-ledger.json').read_text())
    if len(ledger['resources'])>60 or len({r['url'] for r in ledger['resources']})!=len(ledger['resources']):raise ValueError('Budget/duplicate resource')
    for r in ledger['resources']:
        if hashlib.sha256((ROOT/r['rawPath']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed resource '+r['id'])
    return ledger


def supplements(records):
    """Named occurrence verification with exact raw passage pinned separately."""
    for r in records:
        if r['pollsterCode']=='ROY' and r['fieldworkRaw']==['2020-08-01','2020-08-31']:
            r.update(publication='2020-09-01T23:59:59.999999+12:00',publicationConfidence='verified',
              publicationEvidence='polling35-rm2020.html; dated September01; conservative end-of-day',
              denominator='decided_inferred_from_total_and_nonresponse',nonresponseCombined=0.055,mode='landline_and_mobile',population='NZ electors')
            r['provenance'].append({'sourceId':'polling35-rm2020.html','role':'publication/sample/mode/nonresponse verification'})
        if r['pollsterCode']=='ROY' and r['fieldworkRaw']==['2023-08-00','2023-09-00']:
            r.update(fieldworkStartBounds=['2023-08-01','2023-08-01'],fieldworkEndBounds=['2023-08-31','2023-08-31'],
              publication='2023-09-05T23:59:59.999999+12:00',publicationConfidence='verified',
              publicationEvidence='polling35-rm2023.html; September05; PDF embargo; conservative end-of-day',
              denominator='decided_inferred_from_total_and_nonresponse',nonresponseCombined=0.05,mode='landline_and_mobile',population='NZ electors')
            r['provenance'].append({'sourceId':'polling35-rm2023.html','role':'publication and August fieldwork correction; raw label unchanged'})
            r['assumptionFlags'].append('original release coalition arithmetic differs from its individual party entries; use named entries')
        if r['pollsterCode']=='COL' and r['fieldworkRaw']==['2026-09-23','2026-09-27']:
            r.update(publication='2026-09-28T05:01:11.110+00:00',publicationConfidence='verified',
              publicationEvidence='polling35-verian2026.html; datePublished vs later publish_date',
              nonresponseCombined=0.13,denominator='decided_inferred_from_total_and_nonresponse',population='eligible NZ voters')
            r['provenance'].append({'sourceId':'polling35-verian2026.html','role':'original publication/sample/nonresponse'})
    return records


def semantic(obs):
    return (obs['status'],obs['share'],obs['bounds'])


def construct():
    bulk,nonpoll=parse_bulk((RAW/'nixinova-data.yml').read_text(),'polling35-nixinova-data.yml')
    wiki,wiki_audit=parse_current((RAW/'wiki2026.html').read_text(),'polling35-wiki2026.html')
    # Snapshot-specific current table supplements new waves only; disagreements retained.
    by_id={r['id']:r for r in bulk};cross=[]
    for r in wiki:
        if r['id'] not in by_id:bulk.append(r);continue
        old=by_id[r['id']]
        differences={p:[old['estimates'][p],r['estimates'][p]] for p in old['estimates'] if semantic(old['estimates'][p])!=semantic(r['estimates'][p])}
        cross.append({'id':r['id'],'comparison':'wiki2026_vs_bulk','differences':differences})
        if differences:
            old['status']='conflicting_reports';old['conflictingReports']=[r]
        old['provenance'].extend(r['provenance'])
    records,duplicates=deduplicate(bulk)
    records=supplements(records)
    return records,{'nonPollAndInvalidRows':nonpoll,'currentTableExcludedRows':wiki_audit,'duplicates':duplicates,'bulkCrossChecks':cross}


def coverage(records):
    rows=[]
    horizons=[]
    for year in DATES:
        group=[r for r in records if r['cycle']==year]
        rows.append({'election':year,'polls':len(group),'pollsters':dict(Counter(r['pollster'] for r in group)),
          'verifiedPublication':sum(r['publicationConfidence']=='verified' for r in group),
          'unknownSampleSize':sum(r['sampleSize'] is None for r in group),
          'unknownDay':sum(any(s.endswith('-00') for s in r['fieldworkRaw']) for r in group),
          'statuses':dict(Counter(r['status'] for r in group)),
          'latestPossibleFieldEnd':max((r['fieldworkEndBounds'][1] for r in group),default=None)})
        if year==2026:continue
        for h in (14,56):
            cutoff=day_end((date.fromisoformat(DATES[year])-timedelta(days=h)).isoformat()).isoformat()
            for lag in (5,10):
                admitted,ex=select([r for r in records if r['cycle']<=year],cutoff,lag)
                target=[r for r in admitted if r['cycle']==year]
                verified,_=select([r for r in records if r['cycle']<=year],cutoff,lag,True)
                horizons.append({'election':year,'horizonDays':h,'cutoff':cutoff,'lagDays':lag,
                 'allEarlierAvailableIds':[r['id'] for r in admitted], 'targetCycleIds':[r['id'] for r in target],
                 'verifiedOnlyIds':[r['id'] for r in verified], 'targetCycleCount':len(target),
                 'exclusions':ex,'informationSet':'retrospective bulk, verified dates plus explicitly inferred lag; not fully verified as-of'})
    return {'byElection':rows,'horizons':horizons,'current2026Status':'foundation through September27, not a nowcast or complete live feed'}


def preservation():
    # Frozen Git-blob inventory works in shallow CI checkouts without network/history.
    snapshot=json.loads((ROOT/'data/source-plans/stage35-prior-data-preservation.json').read_text())
    if snapshot['baseCommit']!=BASE:raise ValueError('Preservation base')
    for p,expected in snapshot['gitBlobSha1'].items():
        raw=(ROOT/p).read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=expected:raise ValueError('Changed earlier '+p)
    return len(snapshot['gitBlobSha1'])


def run(check=False):
    ledger=verify_sources();records,audit=construct()
    save('polls.json',{'schemaVersion':1,'records':records},check)
    save('audit.json',audit,check);save('coverage.json',coverage(records),check)
    consumed={r['rawPath']:r['sha256'] for r in ledger['resources']}
    for y in (2011,2014,2017,2020,2023):
        p=f'data/processed/elections/{y}.json';consumed[p]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    p='data/source-plans/stage35-prior-data-preservation.json'
    consumed[p]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    consumed['data/raw/polling/stage35/acquisition-ledger.json']=hashlib.sha256((RAW/'acquisition-ledger.json').read_bytes()).hexdigest()
    save('input-contract.json',{'schemaVersion':1,'consumedSha256':consumed,'baseCommit':BASE,
         'priorDataFilesPreserved':preservation(),'resourceCount':len(ledger['resources']),
         'generatorSha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'scripts/polling/national_foundation').glob('*.py'))}},check)
    print(len(records),'polls;',len(ledger['resources']),'resources;',preservation(),'prior data files unchanged')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
