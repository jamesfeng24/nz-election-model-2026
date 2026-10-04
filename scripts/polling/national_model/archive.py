"""Pin saved forecasts before held-out scoring; no inference or result access."""
import argparse
import hashlib
from .common import OUT,read,save


def run(check=False):
    paths=['construction.json','benchmark.json']
    for case in read(OUT/'construction.json')['cases']:paths.extend(case.get('attempts',[]))
    value={'stage':36,'phase':'forecasts_saved_before_evaluation',
           'sha256':{p:hashlib.sha256((OUT/p).read_bytes()).hexdigest() for p in sorted(set(paths))}}
    save('forecast-contract.json',value,check)
    print(len(value['sha256']),'forecast/attempt artifacts pinned; no scores')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
