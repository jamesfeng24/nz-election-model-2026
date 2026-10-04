"""Unchanged pinned upstream preparation, with earlier-only result adapter."""
import argparse
from datetime import date
import sys
import numpy as np
from .common import ROOT,OUT,RAW,UPSTREAM,CASES,PIN,save,read,sha


def upstream_api():
    sys.path.insert(0,str(UPSTREAM/'src'))
    from pollofpolls.config import Config
    from pollofpolls.data.wikipedia import parse_page_file
    from pollofpolls.prep.polls_table import build_polls_table
    from pollofpolls.data.results import election_results_from_polls,load_reference_results,verify_results
    from pollofpolls.prep.marshal import build_dataset
    return Config(UPSTREAM),parse_page_file,build_polls_table,election_results_from_polls,load_reference_results,verify_results,build_dataset


def source_table():
    cfg,parse,build,results_of,load_ref,verify,_=upstream_api()
    polls=[]
    for year in (2014,2017,2020,2023): polls.extend(parse(RAW/f'{year}.html',year))
    table=build(polls,cfg);scraped=results_of(polls);ref=load_ref(UPSTREAM/'data/reference/election_results.csv')
    issues=verify(scraped,ref)
    if issues:raise ValueError('Bulk/reference result mismatch: '+str(issues))
    results={y:{**scraped.get(y,{}),**ref.get(y,{})} for y in set(scraped)|set(ref)}
    return cfg,table,results


def earlier_dataset(table,results,cfg,year,cutoff):
    from pollofpolls.prep.marshal import build_dataset
    # Drop target/later result values altogether rather than trusting downstream filtering.
    permitted={y:v for y,v in results.items() if y<year}
    return build_dataset(table,permitted,cfg,year,date.fromisoformat(cutoff),lagged=True)


def check_counterfactuals(table,results,cfg,year,cutoff,ds):
    import polars as pl
    changed={**results,year:{k:.9 for k in results.get(year,{})},2026:{'National':.99}}
    if earlier_dataset(table,changed,cfg,year,cutoff).fingerprint()!=ds.fingerprint():raise ValueError('Held-out result dependence')
    modified=table.with_columns(pl.when(pl.col('available')>date.fromisoformat(cutoff)).then(pl.lit(.999)).otherwise(pl.col('share')).alias('share'))
    if earlier_dataset(modified,results,cfg,year,cutoff).fingerprint()!=ds.fingerprint():raise ValueError('Post-cutoff poll dependence')
    # Future-only publication revision changes excluded information but never brings a poll into cutoff.
    modified=table.with_columns(pl.when(pl.col('available')>date.fromisoformat(cutoff)).then(pl.col('available')+pl.duration(days=100)).otherwise(pl.col('available')).alias('available'))
    if earlier_dataset(modified,results,cfg,year,cutoff).fingerprint()!=ds.fingerprint():raise ValueError('Future-only revision dependence')


def run(check=False):
    cfg,table,results=source_table();rows=[]
    if not check:
        table.write_parquet(OUT/'prepared-polls.parquet');save('prepared-results-audit-only.json',{str(k):v for k,v in results.items()})
    for year,cutoff in CASES:
        ds=earlier_dataset(table,results,cfg,year,cutoff);check_counterfactuals(table,results,cfg,year,cutoff,ds)
        selected=table.filter(__import__('polars').col('poll_id').is_in(ds.poll_ids))
        availability=[{'id':r['poll_id'],'fieldEnd':r['date_to'].isoformat(),'available':r['available'].isoformat(),'midpoint':r['mid_date'].isoformat(),'n':r['sample_size'],'sampleReported':r['sample_reported'],'pollster':r['pollster'],'segment':r['segment'],'cycle':r['cycle']} for r in selected.select('poll_id','date_to','available','mid_date','sample_size','sample_reported','pollster','segment','cycle').unique(maintain_order=True).sort('poll_id').to_dicts()]
        row={'year':year,'cutoff':cutoff,'fingerprint':ds.fingerprint(),'parties':ds.parties,'pollCount':ds.N,'weeks':ds.T,'resultAnchors':[cfg.anchor_election]+ds.election_years,'cycles':ds.cycle_years,'lastDataWeek':ds.weeks[ds.last_data_t].isoformat(),'electionWeek':ds.weeks[ds.target_t].isoformat(),'errorScale':ds.error_scale.tolist(),'polls':availability,'counterfactualsPassed':True,'meanPointPlacement':'fieldwork midpoint, Sunday week','cutoffSemantics':'date_to plus pollster fixed lag <= cutoff date; no historical timestamp verified','informationSet':'retrospective reconstructed pinned upstream parser/config; not exact archived input fingerprint'}
        prefix=OUT/f'datasets/{year}'
        if check:
            from pollofpolls.prep.marshal import Dataset
            if Dataset.load(prefix).fingerprint()!=ds.fingerprint():raise ValueError('Dataset changed')
        else:
            prefix.parent.mkdir(parents=True,exist_ok=True);ds.save(prefix)
        rows.append(row)
    save('inventory.json',{'pin':PIN,'cases':rows,'sourceRows':table.height,'sourceWaves':table['poll_id'].n_unique(),'directHeldOutOutcomesConsumed':False,'fixedRetrospectiveCalibration':'minor_party_factor2.5/8percent threshold comments reference2011–2023 errors; unchanged','noSpreadCalibrationOrEnsemble':True},check)
    print([(r['year'],r['pollCount'],r['parties']) for r in rows])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
