"""Independent checks on what is about to be published (stdlib only): the release archive and the built site tree.

    python3 -m scripts.publish_workflow.verify archive --new DIR [--previous DIR] (--snapshot-id ID --cutoff YYYY-MM-DD [--supersedes ID] | --no-new)
    python3 -m scripts.publish_workflow.verify tree --site DIR
    python3 -m scripts.publish_workflow.verify frozen --tree DIR

These re-read the files rather than trusting the TypeScript publisher, so a bug there cannot reach the public repository unnoticed. The archive
is append-only: every earlier index entry must be unchanged and its file must still match its recorded hash. Each forecast that can be opened has
one frozen copy of the whole site at `archive/<data cutoff date>/`, which a later publish must never change.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SYNTHETIC_PREFIX = 'synthetic-'
PAGES_FILE = 'src/app/pages.ts'
DATED = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def openable(entries):
    """The entries that have a frozen site copy: not withdrawn and not replaced by a correction (the Archive page links exactly these)."""
    replaced = {e['supersedes'] for e in entries if e.get('supersedes')}
    return [e for e in entries if e['status'] != 'withdrawn' and e['snapshotId'] not in replaced]


def check_archive(new_dir, previous_dir, snapshot_id, cutoff, supersedes=None):
    """Errors (empty when the archive in `new_dir` is exactly `previous_dir` plus one valid model release; with `snapshot_id` None, exactly `previous_dir`)."""
    new_dir = Path(new_dir)
    errors = []
    if not (new_dir / 'index.json').is_file():
        return ['The archive has no index.json']
    entries = load(new_dir / 'index.json')['snapshots']
    previous = load(Path(previous_dir) / 'index.json')['snapshots'] if previous_dir and (Path(previous_dir) / 'index.json').is_file() else []
    if entries[:len(previous)] != previous:
        errors.append('Earlier archive entries changed or were removed (the archive is append-only)')
    added = entries[len(previous):]
    if [e['snapshotId'] for e in added] != ([snapshot_id] if snapshot_id else []):
        errors.append(f"Expected {'exactly one new entry, ' + snapshot_id if snapshot_id else 'no new entry'}; found {[e['snapshotId'] for e in added]}")
    days = [e['dataCutoff'][:10] for e in openable(entries)]
    if len(days) != len(set(days)):
        errors.append('Two current forecasts share a data cutoff date (their frozen site folders would collide): ' + ', '.join(sorted({d for d in days if days.count(d) > 1})))
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
    if snapshot_id and len(added) == 1 and added[0]['snapshotId'] == snapshot_id and (new_dir / added[0]['path']).is_file():
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


def check_frozen(tree_dir):
    """Errors for an assembled public tree: every openable forecast has its frozen copy, and no frozen folder is orphaned or half-written."""
    tree = Path(tree_dir)
    index_path = tree / 'forecasts' / 'index.json'
    if not index_path.is_file():
        return ['The tree has no forecasts/index.json']
    wanted = {e['dataCutoff'][:10] for e in openable(load(index_path)['snapshots'])}
    archive = tree / 'archive'
    present = {p.name for p in archive.iterdir() if p.is_dir()} if archive.is_dir() else set()
    errors = []
    for day in sorted(wanted - present):
        errors.append(f'No frozen site copy at archive/{day}/ for a current forecast')
    for day in sorted(present - wanted):
        errors.append(f'archive/{day}/ belongs to no current forecast')
    for day in sorted(wanted & present):
        for required in ('index.html', 'forecast/index.html', 'forecasts/index.json'):
            if not (archive / day / required).is_file():
                errors.append(f'archive/{day}/ is incomplete: missing {required}')
    for name in sorted(present):
        if not DATED.match(name):
            errors.append(f'archive/{name}/ is not a dated folder')
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    a_ = sub.add_parser('archive')
    a_.add_argument('--new', required=True); a_.add_argument('--previous'); a_.add_argument('--snapshot-id', default='')
    a_.add_argument('--cutoff', default=''); a_.add_argument('--supersedes', default=''); a_.add_argument('--no-new', action='store_true')
    t = sub.add_parser('tree'); t.add_argument('--site', required=True)
    f = sub.add_parser('frozen'); f.add_argument('--tree', required=True)
    a = ap.parse_args(argv)
    if a.command == 'archive':
        if a.no_new == bool(a.snapshot_id):
            ap.error('give --snapshot-id and --cutoff for a release, or --no-new for a site-only run')
        errors = check_archive(a.new, a.previous, a.snapshot_id or None, a.cutoff, a.supersedes or None)
    elif a.command == 'frozen':
        errors = check_frozen(a.tree)
    else:
        errors = check_tree(a.site, site_pages())
    for error in errors:
        print('::error::' + error, file=sys.stderr)
    print('ok' if not errors else f'{len(errors)} problem(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
