"""Verify every earlier tracked data artifact against the merged stage base."""
from hashlib import sha1, sha256

from .common import ROOT, DEST, encode, read


def verify_prior_data():
    contract = read(str((DEST / 'prior-data-contract.json').relative_to(ROOT)))
    base = contract['baseCommit']
    records, changed = contract['records'], []
    if len(records) != len({r['path'] for r in records}):
        raise ValueError('Duplicate prior data path')
    for row in records:
        path, expected = row['path'], row['gitBlob']
        file = ROOT / path
        raw = file.read_bytes() if file.is_file() else b''
        actual = sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if not file.is_file() or actual != expected:
            changed.append(path)
    if changed:
        raise ValueError(f'Changed earlier data artifacts: {changed}')
    return {'baseCommit': base, 'protectedFileCount': len(records),
            'protectedPathBlobSha256': sha256(encode(records)).hexdigest(),
            'changedEarlierFiles': [], 'scope': 'all_preexisting_tracked_data_including_raw_identity_geography_numerical_and_selection_outputs'}
