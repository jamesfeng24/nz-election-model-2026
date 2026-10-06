"""Fold per-PR handoff fragments into CHANGELOG.md and PROJECT_STATE.md.

Parallel pull requests used to conflict on the top lines of both files. Each PR now writes
`changelog.d/<YYYY-MM-DD>-<slug>.md` (a `## ` entry) and `state.d/<YYYY-MM-DD>-<slug>.md` (a `# ` entry)
instead. This script moves them into the two files in the existing style and deletes them, so CHANGELOG.md
and PROJECT_STATE.md stay the single full record. Documentation only; it touches no data or statistics.

  python3 -m scripts.fold_doc_fragments --check   # validate fragments, change nothing
  python3 -m scripts.fold_doc_fragments           # fold and delete the fragments

CHANGELOG.md is append-ordered (oldest fragment first, appended at the end). PROJECT_STATE.md is
newest-first (newest fragment first, inserted above the existing top entry, separated by `---`).
Fragment order is the sorted file name, so the date prefix decides it.
"""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r'^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md$')
# directory -> (target file, required heading prefix, forbidden heading prefix)
KINDS = {'changelog.d': ('CHANGELOG.md', '## ', '###'), 'state.d': ('PROJECT_STATE.md', '# ', '##')}


class FragmentError(ValueError):
    pass


def read_fragments(root, directory):
    """Return [(name, text)] sorted by file name; raise FragmentError listing every problem."""
    target, required, forbidden = KINDS[directory]
    folder = root / directory
    problems, found = [], []
    for path in sorted(folder.glob('*')) if folder.is_dir() else []:
        if path.name == 'README.md':
            continue
        label = '{}/{}'.format(directory, path.name)
        if not NAME.match(path.name):
            problems.append('{}: name must match YYYY-MM-DD-<slug>.md'.format(label))
            continue
        try:
            text = path.read_text(encoding='utf-8').strip()
        except UnicodeDecodeError:
            problems.append('{}: not valid UTF-8'.format(label))
            continue
        heading = text.split('\n', 1)[0]
        if not text:
            problems.append('{}: empty'.format(label))
        elif not heading.startswith(required) or heading.startswith(forbidden):
            problems.append('{}: first line must be a "{}" heading'.format(label, required.strip()))
        else:
            found.append((path.name, text))
    if problems:
        raise FragmentError('; '.join(problems))
    return found


def plan(root=ROOT):
    """Compute new file contents without writing: {target: text}, plus the fragment paths to delete."""
    new, delete = {}, []
    for directory, (target, _, _) in KINDS.items():
        fragments = read_fragments(root, directory)
        if not fragments:
            continue
        current = (root / target).read_text(encoding='utf-8')
        lines = set(current.splitlines())
        for name, text in fragments:
            if text.split('\n', 1)[0] in lines:
                raise FragmentError('{}/{}: heading already present in {}'.format(directory, name, target))
        texts = [text for _, text in fragments]
        if directory == 'changelog.d':
            new[target] = current.rstrip('\n') + '\n\n' + '\n\n'.join(texts) + '\n'
        else:
            new[target] = '\n\n---\n\n'.join(reversed(texts)) + '\n\n---\n\n' + current.lstrip('\n')
        delete += [root / directory / name for name, _ in fragments]
    return new, delete


def fold(root=ROOT, check=False):
    new, delete = plan(root)
    if not check:
        for target, text in new.items():
            (root / target).write_text(text, encoding='utf-8')
        for path in delete:
            path.unlink()
    return sorted(p.relative_to(root).as_posix() for p in delete)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--check', action='store_true', help='validate fragments and report; change nothing')
    parser.add_argument('--root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        folded = fold(args.root, args.check)
    except FragmentError as error:
        print('fragment error: {}'.format(error), file=sys.stderr)
        return 1
    print('{} {} fragment(s){}'.format('would fold' if args.check else 'folded', len(folded),
                                       ''.join('\n  ' + name for name in folded)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
