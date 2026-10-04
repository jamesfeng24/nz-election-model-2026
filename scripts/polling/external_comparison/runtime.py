"""Explicit source/environment guard before resumed internal inference calls."""
import importlib.metadata
import os
from pathlib import Path
import sys
from .common import ROOT,OUT,UPSTREAM,read,sha,validate_inputs


def validate_files():
    validate_inputs();contract=read(OUT/'input-contract.json')
    for path,h in contract['upstreamSource'].items():
        if sha(UPSTREAM/path)!=h:raise ValueError('Extracted upstream differs from pinned source '+path)
    for path,h in contract['runnerCode'].items():
        if sha(ROOT/path)!=h:raise ValueError('Frozen numerical runner changed '+path)
    override=os.environ.get('POLLOFPOLLS_ROOT')
    if override and Path(override).resolve()!=UPSTREAM.resolve():raise ValueError('Unexpected upstream configuration-root override')


def validate_runtime():
    validate_files();env=read(OUT/'environment.json')
    actual={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    if actual!=env['packages'] or sys.version!=env['python']:raise ValueError('Changed isolated runtime')


def validate_cached_record(record,year,attempt):
    """Batch skips must compare full signatures, not just accepted status."""
    sys.path.insert(0,str(UPSTREAM/'src'))
    from pollofpolls.prep.marshal import Dataset
    from .inference import signature,PRIMARY,RETRY
    ds=Dataset.load(OUT/f'datasets/{year}')
    expected=signature(ds,PRIMARY if attempt==1 else RETRY)
    if record['signature']!=expected:raise ValueError('Incompatible completed cache signature')
    if record.get('npzSha256') and sha(OUT/f'fits/{year}/attempt{attempt}.npz')!=record['npzSha256']:raise ValueError('Changed cached joint forecast archive')
