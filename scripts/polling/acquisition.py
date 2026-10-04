"""Offline registration of shell-fetched resources; no network in Python."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/polling/stage35'


def register(name, url, purpose, status, version=None):
    path = RAW / 'acquisition-ledger.json'
    ledger = json.loads(path.read_text())
    now = datetime.now(timezone.utc).isoformat()
    ledger['attempts'].append(dict(url=url, purpose=purpose, retrievedAt=now,
                                   status=status, rawPath=str((RAW/name).relative_to(ROOT))))
    if status == 'success' and url not in {r['url'] for r in ledger['resources']}:
        if len(ledger['resources']) >= ledger['resourceLimit']:
            raise ValueError('Resource cap')
        raw = (RAW / name).read_bytes()
        ledger['resources'].append(dict(id='polling35-'+name, url=url, purpose=purpose,
            retrievedAt=now, repositoryVersion=version, rawPath=str((RAW/name).relative_to(ROOT)),
            sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for k in ('name', 'url', 'purpose', 'status'):
        p.add_argument(k)
    p.add_argument('--version')
    a = p.parse_args()
    register(a.name, a.url, a.purpose, a.status, a.version)
