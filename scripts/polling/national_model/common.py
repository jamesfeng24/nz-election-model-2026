"""Versioned Stage36 artifacts; no inference in deterministic readers."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
FOUNDATION=ROOT/'data/processed/polling/national-foundation'
OUT=ROOT/'data/processed/polling/national-backtest'
BASE='19be252b2a1e726e19ab90d9dd12afd39c7b38e5'
ORDER=['NAT','LAB','GRN','ACT','NZF','MRI','TOP','OTH']
COARSE=[p for p in ORDER if p!='TOP']


def encode(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def read(path):
    p=Path(path)
    raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
    return json.loads(raw)


def save(path,value,check=False):
    p=OUT/path;raw=encode(value)
    if p.suffix=='.gz':raw=gzip.compress(raw,mtime=0)
    if check:
        if p.read_bytes()!=raw:raise ValueError('Changed deterministic '+path)
    else:
        p.parent.mkdir(parents=True,exist_ok=True)
        tmp=p.with_name(p.name+'.tmp');tmp.write_bytes(raw);tmp.replace(p)


def schema(year):
    return [p for p in ORDER if p!='TOP' or year>=2017]


def coarsen(values,categories):
    d=dict(zip(categories,values));d['OTH']+=d.get('TOP',0)
    return [d[p] for p in COARSE]
