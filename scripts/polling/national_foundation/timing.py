"""Availability and revision selection use dated evidence, never election outcomes."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NZ=ZoneInfo('Pacific/Auckland')


def timestamp(text):
    value=datetime.fromisoformat(text.replace('Z','+00:00'))
    if value.tzinfo is None:raise ValueError('Timezone required')
    return value.astimezone(timezone.utc)


def day_end(text):
    return datetime.fromisoformat(text+'T23:59:59.999999').replace(tzinfo=NZ)


def availability(r, lag_days=5):
    if r['publication']:
        return timestamp(r['publication']),r['publicationConfidence']
    # Latest possible field end + fixed lag, deliberately inferred.
    return day_end(r['fieldworkEndBounds'][1])+timedelta(days=lag_days),'inferred_fixed_lag'


def select(records, cutoff, lag_days=5, verified_only=False):
    limit=timestamp(cutoff)
    available=[]
    excluded=[]
    for r in records:
        when,quality=availability(r,lag_days)
        reason=None
        if r['status']!='usable_partial':reason=r['status']
        elif verified_only and quality!='verified':reason='unverified_publication'
        elif when>limit:reason='not_available_at_cutoff'
        elif day_end(r['fieldworkEndBounds'][1])>limit:reason='fieldwork_not_completed'
        if reason:excluded.append({'id':r['id'],'reason':reason});continue
        available.append((r,when,quality))
    # Do not count overlapping same-pollster samples twice; latest available wave wins.
    kept=[]
    for r,when,quality in sorted(available,key=lambda x:(x[1],x[0]['id']),reverse=True):
        overlap=any(x['pollster']==r['pollster'] and
            x['fieldworkStartBounds'][0]<=r['fieldworkEndBounds'][1] and
            r['fieldworkStartBounds'][0]<=x['fieldworkEndBounds'][1] for x in kept)
        if overlap:excluded.append({'id':r['id'],'reason':'overlapping_sample_conservative_latest'});continue
        kept.append(r)
    return sorted(kept,key=lambda r:r['id']),sorted(excluded,key=lambda r:(r['id'],r['reason']))


def select_revisions(revisions, cutoff):
    """Latest known revision available then; no use of future corrections."""
    by_wave={}
    for r in revisions:
        if timestamp(r['publication'])>timestamp(cutoff):continue
        key=r['waveId']
        if key not in by_wave or timestamp(r['publication'])>timestamp(by_wave[key]['publication']):by_wave[key]=r
    return [by_wave[k] for k in sorted(by_wave)]
