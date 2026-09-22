"""Reconstruct an unchanged large official archive from verified Git byte segments."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def archive_bytes(manifest, root=ROOT):
    pieces, offset = [], 0
    for part in manifest['parts']:
        path = (root / part['rawPath']).resolve()
        if not path.is_relative_to((root / 'data/raw').resolve()):
            raise ValueError('Unsafe archive segment path')
        raw = path.read_bytes()
        if part['offset'] != offset or len(raw) != part['bytes']:
            raise ValueError('Archive segment order/length mismatch')
        if hashlib.sha256(raw).hexdigest() != part['sha256']:
            raise ValueError('Archive segment checksum mismatch')
        pieces.append(raw)
        offset += len(raw)
    raw = b''.join(pieces)
    if offset != manifest['originalBytes'] or hashlib.sha256(raw).hexdigest() != manifest['originalSha256']:
        raise ValueError('Original archive checksum/length mismatch')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raw = archive_bytes(json.loads(args.manifest.read_bytes()))
    if args.output.exists():
        if args.output.read_bytes() != raw:
            raise ValueError('Refusing to replace a different existing file')
    else:
        with args.output.open('xb') as stream:
            stream.write(raw)
    print('Original archive reconstructed and verified:', hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':
    main()
