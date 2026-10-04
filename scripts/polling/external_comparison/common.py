"""Separate Stage38 artifacts; no candidate or national fitting imports."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/processed/polling/external-comparison'
RAW = ROOT / 'data/raw/polling/stage38'
UPSTREAM = ROOT / '.cache/stage38/upstream'
PIN = 'ef76cf6562e1d028b4fff46d063f4b93945299de'
CASES = [(2017, '2017-07-29'), (2020, '2020-08-22'), (2023, '2023-08-19')]
CATEGORIES = ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'REST']
NAMES = {'National':'NAT', 'Labour':'LAB', 'Green':'GRN', 'ACT':'ACT', 'NZ First':'NZF'}


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    p = Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def save(path, value, check=False):
    p = OUT / path
    raw = encode(value)
    if p.suffix=='.gz':
        raw = bytearray(gzip.compress(raw, mtime=0)); raw[9]=255; raw=bytes(raw)
    if check:
        if p.read_bytes()!=raw: raise ValueError('Changed deterministic artifact '+str(path))
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp=p.with_name(p.name+'.tmp'); tmp.write_bytes(raw); tmp.replace(p)


def coarsen(values, categories):
    import numpy as np
    x=np.asarray(values, dtype=float)
    if x.shape[-1]!=len(categories) or len(set(categories))!=len(categories): raise ValueError('Invalid category schema')
    if not np.isfinite(x).all() or (x<0).any() or not np.allclose(x.sum(-1),1,atol=1e-10,rtol=0): raise ValueError('Invalid complete simplex')
    codes=[NAMES.get(c,c) for c in categories]
    if any(codes.count(k)!=1 for k in CATEGORIES[:-1]): raise ValueError('Missing/duplicate named category')
    out=np.stack([x[...,codes.index(k)] for k in CATEGORIES[:-1]]+[x[..., [i for i,k in enumerate(codes) if k not in CATEGORIES[:-1]]].sum(-1)], axis=-1)
    if not np.allclose(out.sum(-1),x.sum(-1),atol=1e-12,rtol=0): raise ValueError('Lost mass')
    return out


def validate_inputs():
    contract=read(OUT/'input-contract.json')
    for path,h in contract['sha256'].items():
        if sha(ROOT/path)!=h: raise ValueError('Changed consumed input '+path)
