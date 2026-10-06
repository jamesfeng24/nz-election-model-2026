"""Fold per-PR handoff fragments into the shared handoff documents.

Parallel pull requests used to conflict on the top of CHANGELOG.md, PROJECT_STATE.md and the other shared
handoff documents, and each conflict cost a CI re-run. A PR now writes ONE fragment,
`handoff.d/YYYY-MM-DD-<slug>.md`, and never edits those documents. After a batch of PRs has merged, the
coordinator folds the pending fragments in one docs PR. Documentation only; it touches no data or statistics.

  python3 -m scripts.fold_doc_fragments --check   # validate fragments, change nothing
  python3 -m scripts.fold_doc_fragments           # fold into the shared documents, delete the fragments

Fragment format: sections introduced by a line `<!-- fold: NAME -->`, all optional, at least one:

  changelog    -> CHANGELOG.md             appended at the end; starts with a `## ` heading
  state        -> PROJECT_STATE.md         inserted at the top (newest first, `---` separated); starts with `# `
  decisions    -> DECISIONS.md             one or more `## DNNN — ...` entries, inserted in D-number order
  methodology  -> METHODOLOGY.md           appended at the end; starts with `## ` or `### `
  sources      -> DATA_SOURCES.md          appended at the end; starts with `## ` or `### `
  roadmap      -> docs/stage39-forecast-roadmap.md   table rows `| StageNN | question | status |`; a row whose
                  first cell matches an existing row replaces it, a new one is added after the table's last row

Fragments are applied in file-name order, so the date prefix decides it (oldest first). Omit a section instead of
writing "no change". Stage-specific documents are edited directly in the PR, not folded.
"""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = 'handoff.d'
NAME = re.compile(r'^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md$')
MARKER = re.compile(r'^<!-- fold: ([a-z]+) -->$')
DECISION = re.compile(r'^## D(\d{3,}) — ', re.M)
ROADMAP = 'docs/stage39-forecast-roadmap.md'
# section -> (target file, heading regex the first line must match)
SECTIONS = {
    'changelog': ('CHANGELOG.md', r'## \S'),
    'state': ('PROJECT_STATE.md', r'# \S'),
    'decisions': ('DECISIONS.md', r'## D\d{3,} — \S'),
    'methodology': ('METHODOLOGY.md', r'###? \S'),
    'sources': ('DATA_SOURCES.md', r'###? \S'),
    'roadmap': (ROADMAP, r'\| \S'),
}


class FragmentError(ValueError):
    pass


def parse(name, text):
    """Return {section: body} for one fragment; raise FragmentError on any malformed content."""
    label = '{}/{}'.format(DIRECTORY, name)
    sections, current = {}, None
    for line in text.splitlines():
        marker = MARKER.match(line)
        if marker:
            current = marker.group(1)
            if current not in SECTIONS:
                raise FragmentError('{}: unknown section "{}" (allowed: {})'.format(label, current, ', '.join(SECTIONS)))
            if current in sections:
                raise FragmentError('{}: section "{}" appears twice'.format(label, current))
            sections[current] = []
        elif current is None:
            if line.strip():
                raise FragmentError('{}: text before the first <!-- fold: NAME --> marker'.format(label))
        else:
            sections[current].append(line)
    if not sections:
        raise FragmentError('{}: no sections'.format(label))
    result = {}
    for section, lines in sections.items():
        body = '\n'.join(lines).strip()
        if not body:
            raise FragmentError('{}: section "{}" is empty (omit it instead)'.format(label, section))
        if not re.match(SECTIONS[section][1], body):
            raise FragmentError('{}: section "{}" must start with a heading/row matching {}'.format(
                label, section, SECTIONS[section][1]))
        if section == 'state' and re.match(r'##', body):
            raise FragmentError('{}: state entry must start with a single "# " heading'.format(label))
        result[section] = body
    return result


def read_fragments(root):
    folder = root / DIRECTORY
    found, problems = [], []
    for path in sorted(folder.glob('*')) if folder.is_dir() else []:
        if path.name == 'README.md':
            continue
        try:
            if not NAME.match(path.name):
                raise FragmentError('{}/{}: name must match YYYY-MM-DD-<slug>.md'.format(DIRECTORY, path.name))
            found.append((path.name, parse(path.name, path.read_text(encoding='utf-8'))))
        except UnicodeDecodeError:
            problems.append('{}/{}: not valid UTF-8'.format(DIRECTORY, path.name))
        except FragmentError as error:
            problems.append(str(error))
    if problems:
        raise FragmentError('; '.join(problems))
    return found


def append(current, body):
    return current.rstrip('\n') + '\n\n' + body + '\n'


def prepend(current, body):
    return body + '\n\n---\n\n' + current.lstrip('\n')


def insert_decisions(current, body, label):
    """Insert each `## DNNN` entry before the first existing entry with a larger number (else at the end)."""
    starts = [m.start() for m in DECISION.finditer(body)]
    if not starts or starts[0] != 0:
        raise FragmentError('{}: decisions must consist of "## DNNN — ..." entries'.format(label))
    entries = [body[a:b].strip() for a, b in zip(starts, starts[1:] + [len(body)])]
    for entry in entries:
        number = int(DECISION.match(entry).group(1))
        existing = [(int(m.group(1)), m.start()) for m in DECISION.finditer(current)]
        if any(n == number for n, _ in existing):
            raise FragmentError('{}: D{:03d} already exists in DECISIONS.md'.format(label, number))
        later = [pos for n, pos in existing if n > number]
        current = current[:later[0]] + entry + '\n\n' + current[later[0]:] if later else append(current, entry)
    return current


def apply_roadmap_rows(current, body, label):
    lines = current.split('\n')
    for row in body.splitlines():
        row = row.strip()
        if not row:
            continue
        cells = [c.strip() for c in row.strip('|').split('|')]
        if not row.startswith('|') or len(cells) < 2:
            raise FragmentError('{}: roadmap lines must be table rows'.format(label))
        key = '| {} |'.format(cells[0])
        rows = [i for i, line in enumerate(lines) if line.startswith(key)]
        if rows:
            lines[rows[0]] = row
            continue
        # a new row goes after the last row of the table that has the same number of cells
        table = [i for i, line in enumerate(lines) if line.startswith('|') and not set(line) <= set('|- ')
                 and len([c for c in line.strip().strip('|').split('|')]) == len(cells)]
        if not table:
            raise FragmentError('{}: no roadmap table with {} columns to add "{}" to'.format(label, len(cells), cells[0]))
        lines.insert(table[-1] + 1, row)
    return '\n'.join(lines)


def plan(root=ROOT):
    """Compute new file contents without writing: ({target: text}, [fragment paths])."""
    fragments = read_fragments(root)
    texts = {}

    def text_of(target):
        if target not in texts:
            texts[target] = (root / target).read_text(encoding='utf-8')
        return texts[target]

    for name, sections in fragments:
        label = '{}/{}'.format(DIRECTORY, name)
        for section, body in sections.items():
            target = SECTIONS[section][0]
            current = text_of(target)
            if section == 'decisions':
                texts[target] = insert_decisions(current, body, label)
            elif section == 'roadmap':
                texts[target] = apply_roadmap_rows(current, body, label)
            else:
                # state/changelog/methodology/sources: refuse to fold an entry twice
                first = body.split('\n', 1)[0]
                if first in set(current.splitlines()):
                    raise FragmentError('{}: heading "{}" is already present in {}'.format(label, first, target))
                texts[target] = prepend(current, body) if section == 'state' else append(current, body)
    return texts, [root / DIRECTORY / name for name, _ in fragments]


def fold(root=ROOT, check=False):
    texts, delete = plan(root)
    if not check:
        for target, text in texts.items():
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
