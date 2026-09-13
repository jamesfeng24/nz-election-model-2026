"""Offline registration of unchanged, format-checked planned boundary responses."""
import csv
import io
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def main():
    plan=json.loads((ROOT/'data/source-plans/boundary-2023-2026.json').read_text())
    registry_path=ROOT/'data/sources.json'
    registry=json.loads(registry_path.read_text())
    known={r['id']:r for r in registry['sources']}
    added=[]
    for entry in plan['resources']:
        path=ROOT/entry['rawPath']
        if not path.exists():continue
        raw=path.read_bytes()
        if entry['format']=='json':
            value=json.loads(raw)
            if 'error' in value:raise ValueError('API error: '+str(path))
        elif entry['format']=='csv':
            rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
            if not rows or 'MB2025_V2_00' not in rows[0]:
                raise ValueError('Unexpected population CSV schema: '+str(path))
        elif entry['format']=='pdf' and not raw.startswith(b'%PDF-'):
            raise ValueError('Not an official PDF response: '+str(path))
        digest=hashlib.sha256(raw).hexdigest()
        if entry['id'] in known:
            if known[entry['id']]['sha256']!=digest:raise ValueError('Existing source changed')
            continue
        registry['sources'].append({'schemaVersion':1,'id':entry['id'],'organisation':entry['organisation'],
            'url':entry['url'],'dateOrElection':'2020/2025 electorate boundaries for 2023/2026 elections',
            'resource':entry['role'],'retrievedAt':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),
            'rawPath':entry['rawPath'],'processingScript':None,
            'limitations':entry.get('limitations',['Stage 4 acquisition; geographic reconciliation pending. No population/vote-transfer inference from metadata.']),
            'sha256':digest,'licence':entry.get('licence','Representation Commission / Stats NZ attribution; specific reuse terms pending verification.')})
        added.append(entry['id'])
    registry_path.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Registered',len(added),'boundary sources:',', '.join(added))


if __name__=='__main__':main()
