"""Published observations, not fabricated respondent counts or probabilities."""
import calendar
import hashlib
import re
from datetime import date
from decimal import Decimal

PARTIES = ('NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'MRI', 'TOP')
POLLSTERS = {'COL':'Verian lineage','REI':'Reid Research','ROY':'Roy Morgan',
 'CUR':'Curia','TBM':'Talbot Mills/UMR','DGI':'DigiPoll','IPS':'Ipsos',
 'BAU':'Bauer','DYN':'Dynata','ESS':'Essential','GUA':'Essential',
 'FWS':'Freshwater Strategy','HOR':'Horizon','YGV':'YouGov','ANA':'Anacta'}


def date_bounds(text):
    """Retain unknown-day intervals; never replace day00 with a midpoint."""
    y, m, d = map(int, text.split('-'))
    if d:
        value = date(y, m, d).isoformat()
        return [value, value]
    return [date(y, m, 1).isoformat(), date(y, m, calendar.monthrange(y, m)[1]).isoformat()]


def observation(raw):
    text = str(raw).strip().strip('"\'').replace('%', '')
    if text in ('~', '', '–', '—', '-', 'N/A'):
        return {'published':text, 'status':'not_reported', 'share':None, 'bounds':None}
    if text.startswith('<'):
        upper = Decimal(text[1:])/100
        if not 0 < upper <= 1:
            raise ValueError('Threshold range')
        return {'published':text, 'status':'threshold', 'share':None, 'bounds':[0, float(upper)], 'upperExclusive':True}
    value = Decimal(text)
    if not value.is_finite() or not 0 <= value <= 100:
        raise ValueError('Published percentage')
    unit = Decimal(1).scaleb(value.as_tuple().exponent)/100
    p = value/100
    return {'published':text, 'status':'rounded_zero' if p == 0 else 'rounded',
            'share':float(p), 'roundingUnit':float(unit),
            'bounds':[float(max(Decimal(0),p-unit/2)),float(min(Decimal(1),p+unit/2))]}


def record(cycle, fields, provenance):
    dates = fields['date']
    if len(dates) not in (1,2) or fields['org'] not in POLLSTERS:
        raise ValueError('Date/pollster schema')
    start, end = date_bounds(dates[0]), date_bounds(dates[-1])
    if start[0] > end[1]:
        raise ValueError('Reversed fieldwork')
    group = '|'.join((fields['org'], dates[0], dates[-1]))
    key = hashlib.sha256(group.encode()).hexdigest()[:20]
    estimates = {p:observation(fields.get(p,'~')) for p in PARTIES}
    minor = {p:observation(v) for p,v in fields.items() if p not in (*PARTIES,'date','org','n','OTH')}
    bounds = [x['bounds'] for x in (*estimates.values(),*minor.values()) if x['bounds']]
    if sum(x[0] for x in bounds) > 1+1e-12:
        status='incompatible_published_lower_sum'
    else:
        status='usable_partial'
    n = fields.get('n')
    if n in (None,'~','–'):n=None
    else:
        n=int(str(n).replace(',',''))
        if n<=0:raise ValueError('Sample size')
    return {'id':'nz-poll-'+key,'waveId':'inferred-'+key,'waveIdStatus':'inferred_pollster_and_dates',
      'cycle':cycle,'pollsterCode':fields['org'],'pollster':POLLSTERS[fields['org']],
      'commissioner':None,'fieldworkRaw':dates,'fieldworkStartBounds':start,'fieldworkEndBounds':end,
      'publication':None,'publicationConfidence':'unresolved','publicationEvidence':None,
      'sampleSize':n,'effectiveSampleSize':None,'population':None,'mode':None,
      'denominator':'unknown','undecided':None,'refused':None,'nonresponseCombined':None,
      'estimates':estimates,'additionalPublishedCategories':minor,
      'publishedOther':observation(fields.get('OTH','~')),'status':status,
      'provenance':[provenance],'revisionStatus':'no_revision_history_preserved',
      'overlapStatus':'unknown; same-pollster overlapping fieldwork screened at cutoff',
      'assumptionFlags':['aggregator transcription','denominator_decided_assumption_required',
                         'fieldwork_dates_may_be_release_dates_in_upstream_table'],
      'methodSegment':'Reid-after-2017-assumed' if fields['org']=='REI' and start[0]>='2017-01-01' else 'unverified-base'}


def deduplicate(records):
    by_id = {}
    audit = []
    for r in records:
        prior=by_id.get(r['id'])
        if prior is None:
            by_id[r['id']]=r
            continue
        fields=('estimates','additionalPublishedCategories','sampleSize','publishedOther')
        if all(prior[k]==r[k] for k in fields):
            prior['provenance'].extend(r['provenance'])
            audit.append({'id':r['id'],'state':'duplicate_report_collapsed'})
        else:
            prior['status']='conflicting_reports'
            prior.setdefault('conflictingReports',[]).append(r)
            audit.append({'id':r['id'],'state':'conflict_not_resolved'})
    return sorted(by_id.values(),key=lambda r:r['id']),audit


def parse_bulk(text, source_id):
    """Read this pinned source's finite inline-map dialect; fail on layout drift."""
    cycle=None
    records=[]
    results=[]
    for number,line in enumerate(text.splitlines(),1):
        heading=re.fullmatch(r"'(\d{4})':",line.strip())
        if heading:
            cycle=int(heading[1]);continue
        if not line.startswith('- {'):continue
        fields=dict(re.findall(r'(\w+):\s*(\[[^\]]+\]|[^,}]+)',line.split('}',1)[0]))
        fields['date']=[x.strip() for x in fields['date'].strip('[]').split(',')]
        if 'org' not in fields:
            results.append({'cycle':cycle,'line':number,'role':'evaluation_or_earlier_anchor_only'})
            continue
        try:
            records.append(record(cycle,fields,{'sourceId':source_id,'line':number,'sourceType':'aggregator'}))
        except ValueError as exc:
            results.append({'cycle':cycle,'line':number,'role':'parse_error','reason':str(exc),'raw':line})
    return records,results
