"""Verify immutable source-record dependencies without pinning registry additions."""

import hashlib
from pathlib import PurePosixPath


def validated_supporting_sources(snapshot, registry, read_raw):
    """Return required URL evidence after exact record and raw-byte checks.

    The stage contract pins the snapshot bytes. New unrelated registry entries
    are allowed; removing or changing a pinned record, or changing its raw file,
    fails before any model record is built.
    """
    pinned = snapshot.get('requiredSourceRecords')
    live = registry.get('sources')
    if snapshot.get('schemaVersion') != 1 or registry.get('schemaVersion') != 1:
        raise ValueError('Source registry schema')
    if not isinstance(pinned, list) or len(pinned) != 42 or not isinstance(live, list):
        raise ValueError('Supporting candidate source inventory')
    live_by_id = {}
    live_urls = {}
    for record in live:
        source_id, url = record.get('id'), record.get('url')
        if not source_id or not url or source_id in live_by_id:
            raise ValueError('Duplicate or malformed current source record')
        live_by_id[source_id] = record
        live_urls[url] = live_urls.get(url, 0) + 1
    required = {}
    paths = set()
    for record in pinned:
        source_id, url, path = (record.get(field) for field in ('id', 'url', 'rawPath'))
        parts = PurePosixPath(path).parts if isinstance(path, str) else ()
        if (not source_id or not url or url in required or path in paths or
                len(parts) < 3 or parts[:2] != ('data', 'raw') or '..' in parts):
            raise ValueError('Malformed pinned source record')
        if live_by_id.get(source_id) != record or live_urls.get(url) != 1:
            raise ValueError(f'Changed or deleted required source record: {source_id}')
        raw = read_raw(path)
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError(f'Changed required raw source: {source_id}')
        required[url] = {'record': record, 'raw': raw}
        paths.add(path)
    return required
