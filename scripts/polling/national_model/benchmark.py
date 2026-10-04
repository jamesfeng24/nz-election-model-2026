"""Frozen transparent national average; no model or probability fitting."""
from datetime import date
import numpy as np
from scripts.polling.national_foundation.timing import select
from .common import COARSE,FOUNDATION,read
from .transforms import project_box


def poll_vector(record):
    points=[];lower=[];upper=[]
    for p in COARSE[:-1]:
        o=record['estimates'].get(p)
        if o is None or o['status'] not in ('rounded','rounded_zero'):raise ValueError('missing_or_threshold_core')
        factor=1.
        if record['denominator']=='all_respondents':
            if record.get('nonresponseCombined') is None:raise ValueError('all_respondent_denominator_unresolved')
            factor=1-record['nonresponseCombined']
        points.append(o['share']/factor);lower.append(o['bounds'][0]/factor);upper.append(min(1,o['bounds'][1]/factor))
    projected=project_box(points,lower,upper)
    return np.r_[projected,1-sum(projected)]


def benchmark(case,polls=None):
    polls=read(FOUNDATION/'polls.json')['records'] if polls is None else polls
    selected,_=select(polls,case['cutoff'],10 if case['branch']=='publication_lag10' else 5,case['branch']=='verified_only')
    admitted=[];excluded=[];cutoff=date.fromisoformat(case['cutoff'][:10])
    for r in selected:
        if r['cycle']!=case['year']:continue
        age=(cutoff-date.fromisoformat(r['fieldworkEndBounds'][1])).days
        if not 0<=age<=180:excluded.append({'id':r['id'],'reason':'outside_benchmark_window'});continue
        try:v=poll_vector(r)
        except ValueError as e:excluded.append({'id':r['id'],'reason':str(e)});continue
        admitted.append({'id':r['id'],'pollster':r['pollsterCode'],'ageDays':age,
                         'weight':2**(-age/30)*np.sqrt(min(r['sampleSize'] or 750,1500)/1000),'shares':v.tolist()})
    if not admitted:return {'status':'abstain','reason':'no_complete_recent_poll','excluded':excluded}
    means=[];weights=[];groups=[]
    for pollster in sorted({r['pollster'] for r in admitted}):
        rows=[r for r in admitted if r['pollster']==pollster];w=np.array([r['weight'] for r in rows])
        mean=np.average([r['shares'] for r in rows],axis=0,weights=w);weight=2**(-min(r['ageDays'] for r in rows)/30)
        means.append(mean);weights.append(weight);groups.append({'pollster':pollster,'shares':mean.tolist(),'weight':weight})
    v=np.average(means,axis=0,weights=weights)
    return {'status':'constructed','categories':COARSE,'shares':v.tolist(),'polls':admitted,'pollsterMeans':groups,'excluded':excluded,
            'informationSet':case['informationSet'],'probabilityDistribution':None}
