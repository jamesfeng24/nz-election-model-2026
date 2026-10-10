"""Independent checks on what is about to be published (stdlib only): the release archive and the built site tree.

    python3 -m scripts.publish_workflow.verify archive --new DIR [--previous DIR] --snapshot-id ID --cutoff YYYY-MM-DD [--supersedes ID]
    python3 -m scripts.publish_workflow.verify tree --site DIR

These re-read the files rather than trusting the TypeScript publisher, so a bug there cannot reach the public repository unnoticed. The archive
is append-only: every earlier index entry must be unchanged and its file must still match its recorded hash.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SYNTHETIC_PREFIX = 'synthetic-'
PAGES_FILE = 'src/app/pages.ts'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def check_archive(new_dir, previous_dir, snapshot_id, cutoff, supersedes=None):
    """Errors (empty when the archive in `new_dir` is exactly `previous_dir` plus one valid model release)."""
    new_dir = Path(new_dir)
    errors = []
    if not (new_dir / 'index.json').is_file():
        return ['The archive has no index.json']
    entries = load(new_dir / 'index.json')['snapshots']
    previous = load(Path(previous_dir) / 'index.json')['snapshots'] if previous_dir and (Path(previous_dir) / 'index.json').is_file() else []
    if entries[:len(previous)] != previous:
        errors.append('Earlier archive entries changed or were removed (the archive is append-only)')
    added = entries[len(previous):]
    if [e['snapshotId'] for e in added] != [snapshot_id]:
        errors.append(f"Expected exactly one new entry, {snapshot_id}; found {[e['snapshotId'] for e in added]}")
    for entry in entries:
        file = new_dir / entry['path']
        if entry['path'] != f"{entry['snapshotId']}/snapshot.json":
            errors.append(f"{entry['snapshotId']}: unexpected path {entry['path']}")
        elif not file.is_file():
            errors.append(f"{entry['snapshotId']}: snapshot file is missing")
        elif sha256(file) != entry['sha256']:
            errors.append(f"{entry['snapshotId']}: snapshot file does not match its recorded hash")
        if entry['snapshotId'].startswith(SYNTHETIC_PREFIX) or entry['provenanceKind'] != 'model':
            errors.append(f"{entry['snapshotId']}: only model releases may be archived (provenance {entry['provenanceKind']})")
    on_disk = {p.name for p in new_dir.iterdir() if p.is_dir()}
    listed = {e['snapshotId'] for e in entries}
    if on_disk != listed:
        errors.append(f'Archive directories {sorted(on_disk ^ listed)} are not exactly the indexed snapshots (a stray or missing release)')
    stray = [p.name for p in new_dir.iterdir() if p.is_file() and p.name != 'index.json']
    if stray:
        errors.append('Unexpected files in the archive root: ' + ', '.join(sorted(stray)))
    if len(added) == 1 and added[0]['snapshotId'] == snapshot_id and (new_dir / added[0]['path']).is_file():
        entry, snapshot = added[0], load(new_dir / added[0]['path'])
        if entry['status'] != 'published' or entry['supersedes'] != (supersedes or None):
            errors.append(f"New entry must be published and supersede {supersedes or 'nothing'}; it is {entry['status']} / {entry['supersedes']}")
        if snapshot.get('snapshotId') != snapshot_id or snapshot.get('schemaVersion') != 2 or snapshot.get('targetType') != 'nowcast':
            errors.append('The new snapshot is not a schema v2 nowcast with the expected id')
        if snapshot.get('provenance', {}).get('kind') != 'model':
            errors.append('The new snapshot does not have model provenance')
        if not str(snapshot.get('dataCutoff', '')).startswith(cutoff):
            errors.append(f"The new snapshot's data cutoff {snapshot.get('dataCutoff')} is not {cutoff}")
    return errors


def site_pages(root='.'):
    text = (Path(root) / PAGES_FILE).read_text(encoding='utf-8')
    return re.findall(r"path:\s*'([a-z0-9-]+)'", text)


def check_tree(site_dir, pages):
    """Errors for a built site folder: every page present, an archive, and nothing a public tree must not carry."""
    site = Path(site_dir)
    errors = []
    for required in ['index.html', '404.html', 'forecasts/index.json'] + [f'{p}/index.html' for p in pages]:
        if not (site / required).is_file():
            errors.append('Missing ' + required)
    for path in site.rglob('*'):
        rel = path.relative_to(site).as_posix()
        if path.is_file() and (path.suffix == '.map' or path.name.lower().startswith('readme') or path.name in ('.env', '.DS_Store')):
            errors.append('Must not be published: ' + rel)
        if path.name == '.git' or rel.startswith(('public/', '.release-build/', 'rehearsal')) or 'synthetic' in path.name.lower():
            errors.append('Must not be published: ' + rel)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    a_ = sub.add_parser('archive')
    a_.add_argument('--new', required=True); a_.add_argument('--previous'); a_.add_argument('--snapshot-id', required=True)
    a_.add_argument('--cutoff', required=True); a_.add_argument('--supersedes', default='')
    t = sub.add_parser('tree'); t.add_argument('--site', required=True)
    a = ap.parse_args(argv)
    if a.command == 'archive':
        errors = check_archive(a.new, a.previous, a.snapshot_id, a.cutoff, a.supersedes or None)
    else:
        errors = check_tree(a.site, site_pages())
    for error in errors:
        print('::error::' + error, file=sys.stderr)
    print('ok' if not errors else f'{len(errors)} problem(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
