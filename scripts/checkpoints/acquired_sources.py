"""Validate Stage 13 newly preserved identity sources and deduplication."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from scripts.checkpoints.identity_evidence_pass import ROOT


PLAN = Path('data/source-plans/stage13-identity-sources.json')
OLDER_PLANS = (Path('data/source-plans/candidate-persistence-sources.json'),
               Path('data/source-plans/freshman-incumbency-tenure-sources.json'),
               Path('data/source-plans/stage10-identity-sources.json'))


def canonical_url(url):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError('Invalid source URL')
    query = urlencode(sorted((key, value) for key, value in parse_qsl(parts.query)
                           if not key.lower().startswith(('utm_', 'fbclid', 'gclid'))))
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), query, ''))


def validate_sources(plan, older_plans, read_raw):
    """Reject excess, duplicate, inherited, changed or missing source evidence."""
    if plan.get('schemaVersion') != 1 or plan.get('stage') != 13:
        raise ValueError('Stage 13 source plan schema')
    sources = plan.get('sources')
    if not isinstance(sources, list) or len(sources) > 60:
        raise ValueError('Stage 13 source budget exceeded')
    old_urls = {canonical_url(record['url']) for older in older_plans for record in older['sources']}
    ids, urls, hashes, paths = set(), set(), set(), set()
    for record in sources:
        source_id, url, path, digest = (record.get(field) for field in
                                        ('id', 'url', 'rawPath', 'sha256'))
        canonical = canonical_url(url)
        parts = PurePosixPath(path).parts if isinstance(path, str) else ()
        if (not source_id or source_id in ids or canonical in urls or canonical in old_urls or
                path in paths or len(parts) < 4 or parts[:3] != ('data', 'raw', 'identity-stage13') or
                '..' in parts or
                digest in hashes):
            raise ValueError('Duplicate or inherited Stage 13 source')
        raw = read_raw(path)
        if sha256(raw).hexdigest() != digest:
            raise ValueError('Changed Stage 13 raw bytes')
        if not record.get('retrievedAt') or not record.get('limitations') or not record.get('resource'):
            raise ValueError('Incomplete Stage 13 source metadata')
        ids.add(source_id)
        urls.add(canonical)
        hashes.add(digest)
        paths.add(path)
    return len(sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    plan = json.loads((ROOT / PLAN).read_text())
    older = [json.loads((ROOT / path).read_text()) for path in OLDER_PLANS]
    count = validate_sources(plan, older, lambda path: (ROOT / path).read_bytes())
    print(f'Validated {count} new Stage 13 raw identity sources')


if __name__ == '__main__':
    main()
