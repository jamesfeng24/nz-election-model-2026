"""Import an explicit URL plan from normal browser downloads, without moving originals."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from scripts.ingest.historical_sources import ROOT, register


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, choices=(2008, 2011, 2014), required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--suffix', default='', help='Browser duplicate suffix before .csv, e.g. " (1)"')
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    plan = json.loads((ROOT / f'data/source-plans/historical-{args.year}.json').read_text())
    missing = []
    imported = 0
    for entry in plan['resources']:
        name = Path(entry['url']).name
        download = args.directory / entry.get('downloadFilename', Path(name).stem + args.suffix + '.csv')
        if not download.exists():
            missing.append(name)
            continue
        timestamp = datetime.fromtimestamp(download.stat().st_mtime, timezone.utc).isoformat()
        register(ROOT, args.year, entry['url'], download.read_bytes(), timestamp, 'normal browser download; timestamp from local download mtime')
        imported += 1
    print(f'{args.year}: imported/verified {imported}; missing {len(missing)}')
    if missing and not args.allow_partial:
        raise ValueError('Missing downloads: ' + ', '.join(missing))


if __name__ == '__main__':
    main()
