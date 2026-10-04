"""Pin saved forecasts before held-out scoring; no inference or result access."""
import argparse
import hashlib
from .common import OUT,read,save


def validate_completion(cases,inventory):
    ids=[r['id'] for r in cases];expected={r['id'] for r in inventory}
    if len(ids)!=len(set(ids)) or set(ids)!=expected:raise ValueError('Incomplete or duplicate forecast frame')
    for row in cases:
        if row['status'] not in ('accepted','numerical_failure','data_abstention'):
            raise ValueError('Unfinished forecast '+row['id'])
        if row['status']=='numerical_failure' and len(row.get('attempts',[]))!=2:
            raise ValueError('Numerical failure before frozen retry '+row['id'])


def run(check=False):
    cases=read(OUT/'construction.json')['cases']
    validate_completion(cases,read(OUT/'inventory.json')['cases'])
    paths=['construction.json','benchmark.json']
    for case in cases:paths.extend(case.get('attempts',[]))
    value={'stage':36,'phase':'forecasts_saved_before_evaluation',
           'sha256':{p:hashlib.sha256((OUT/p).read_bytes()).hexdigest() for p in sorted(set(paths))}}
    save('forecast-contract.json',value,check)
    print(len(value['sha256']),'forecast/attempt artifacts pinned; no scores')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
