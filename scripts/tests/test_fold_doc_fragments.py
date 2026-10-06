"""Handoff fragments fold deterministically into the shared handoff documents."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from scripts import fold_doc_fragments as fold

ROOT = Path(__file__).resolve().parents[2]
DOCS = ('CHANGELOG.md', 'PROJECT_STATE.md', 'DECISIONS.md', 'METHODOLOGY.md', 'DATA_SOURCES.md')

CHANGELOG = '# Changelog\n\n## Stage1 — old\n\n- old entry\n'
STATE = '# Stage1 — old checkpoint\n\nold state.\n\n---\n\n# Stage0 — older\n\nolder state.\n'
DECISIONS = '# Decision log\n\n## D001 — one\n\nbody 1\n\n## D003 — three\n\nbody 3\n'
METHODOLOGY = '# Methodology\n\n## Stage1 method\n\nm1\n'
SOURCES = '# Data sources\n\n## Stage1 sources\n\ns1\n'
ROADMAP = ('# Roadmap\n\n| Stage | Question | Status |\n|---|---|---|\n| Stage48 | balance | authorized |\n'
           '| Stage49 | MMP | authorized |\n\nNext free number: Stage58.\n')


def build(root, fragments=()):
    root = Path(root)
    (root / 'docs').mkdir()
    for name, text in (('CHANGELOG.md', CHANGELOG), ('PROJECT_STATE.md', STATE), ('DECISIONS.md', DECISIONS),
                       ('METHODOLOGY.md', METHODOLOGY), ('DATA_SOURCES.md', SOURCES),
                       (fold.ROADMAP, ROADMAP)):
        (root / name).write_text(text, encoding='utf-8')
    (root / 'handoff.d').mkdir()
    (root / 'handoff.d' / 'README.md').write_text('# readme, never folded\n', encoding='utf-8')
    for name, text in fragments:
        (root / 'handoff.d' / name).write_text(text, encoding='utf-8')
    return root


def section(name, body):
    return '<!-- fold: {} -->\n{}\n'.format(name, body)


FULL = ''.join([
    section('changelog', '## A — 2026-10-06\n\n- a'),
    section('state', '# A — 2026-10-06\n\nstate a.'),
    section('decisions', '## D002 — two\n\nbody 2\n\n## D004 — four\n\nbody 4'),
    section('methodology', '## A method\n\nma'),
    section('sources', '### A sources\n\nsa'),
    section('roadmap', '| Stage48 | balance | merged |\n| Stage50 | nominations | authorized |'),
])


class FoldFragmentTests(unittest.TestCase):
    def test_every_section_lands_in_its_document_in_the_right_place(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp, [('2026-10-06-a.md', FULL)])
            self.assertEqual(fold.fold(root), ['handoff.d/2026-10-06-a.md'])
            read = lambda name: (root / name).read_text()
            self.assertEqual(read('CHANGELOG.md'), CHANGELOG + '\n## A — 2026-10-06\n\n- a\n')
            self.assertEqual(read('PROJECT_STATE.md'), '# A — 2026-10-06\n\nstate a.\n\n---\n\n' + STATE)
            self.assertEqual(read('DECISIONS.md'),
                             '# Decision log\n\n## D001 — one\n\nbody 1\n\n## D002 — two\n\nbody 2\n\n'
                             '## D003 — three\n\nbody 3\n\n## D004 — four\n\nbody 4\n')
            self.assertEqual(read('METHODOLOGY.md'), METHODOLOGY + '\n## A method\n\nma\n')
            self.assertEqual(read('DATA_SOURCES.md'), SOURCES + '\n### A sources\n\nsa\n')
            roadmap = read(fold.ROADMAP)
            self.assertIn('| Stage48 | balance | merged |\n| Stage49 | MMP | authorized |\n| Stage50 | nominations | authorized |\n\nNext free', roadmap)
            self.assertNotIn('| Stage48 | balance | authorized |', roadmap)
            self.assertEqual(sorted(p.name for p in (root / 'handoff.d').iterdir()), ['README.md'])

    def test_several_fragments_apply_oldest_first_changelog_appended_state_newest_on_top(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp, [
                ('2026-10-07-b.md', section('changelog', '## B\n\n- b') + section('state', '# B\n\nstate b.')),
                ('2026-10-06-a.md', section('changelog', '## A\n\n- a') + section('state', '# A\n\nstate a.'))])
            fold.fold(root)
            self.assertEqual((root / 'CHANGELOG.md').read_text(), CHANGELOG + '\n## A\n\n- a\n\n## B\n\n- b\n')
            self.assertEqual((root / 'PROJECT_STATE.md').read_text(),
                             '# B\n\nstate b.\n\n---\n\n# A\n\nstate a.\n\n---\n\n' + STATE)

    def test_omitted_sections_leave_other_documents_untouched_and_no_fragments_is_a_no_op(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp, [('2026-10-06-a.md', section('changelog', '## A\n\n- a'))])
            fold.fold(root)
            for name, text in (('PROJECT_STATE.md', STATE), ('DECISIONS.md', DECISIONS), ('METHODOLOGY.md', METHODOLOGY)):
                self.assertEqual((root / name).read_text(), text)
            self.assertEqual(fold.fold(root), [])

    def test_check_changes_nothing(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp, [('2026-10-06-a.md', FULL)])
            self.assertEqual(fold.fold(root, check=True), ['handoff.d/2026-10-06-a.md'])
            self.assertEqual((root / 'CHANGELOG.md').read_text(), CHANGELOG)
            self.assertTrue((root / 'handoff.d' / '2026-10-06-a.md').exists())

    def test_invalid_fragments_fail_without_writing_or_deleting_anything(self):
        bad = {
            'bad name': ('notes.md', section('changelog', '## A')),
            'no sections': ('2026-10-06-b.md', 'just text\n'),
            'text before marker': ('2026-10-06-b.md', 'intro\n' + section('changelog', '## A')),
            'unknown section': ('2026-10-06-b.md', section('readme', '## A')),
            'duplicate section': ('2026-10-06-b.md', section('changelog', '## A') + section('changelog', '## B')),
            'empty section': ('2026-10-06-b.md', section('changelog', '  ')),
            'changelog without heading': ('2026-10-06-b.md', section('changelog', '- text')),
            'state with level-2 heading': ('2026-10-06-b.md', section('state', '## A')),
            'decision without D-number': ('2026-10-06-b.md', section('decisions', '## Two\n')),
            'duplicate decision number': ('2026-10-06-b.md', section('decisions', '## D003 — again\n\nx')),
            'already-folded changelog entry': ('2026-10-06-b.md', section('changelog', '## Stage1 — old\n\n- again')),
            'already-folded state entry': ('2026-10-06-b.md', section('state', '# Stage1 — old checkpoint\n\nagain')),
            'roadmap without table': ('2026-10-06-b.md', section('roadmap', '| Stage50 | only | two | extra | cells |')),
        }
        for label, (name, text) in bad.items():
            with self.subTest(label), TemporaryDirectory() as tmp:
                root = build(tmp, [('2026-10-06-ok.md', section('changelog', '## OK\n\n- ok'))])
                (root / 'handoff.d' / name).write_text(text, encoding='utf-8')
                with self.assertRaises(fold.FragmentError):
                    fold.fold(root)
                self.assertEqual((root / 'CHANGELOG.md').read_text(), CHANGELOG)
                self.assertTrue((root / 'handoff.d' / '2026-10-06-ok.md').exists())

    def test_command_line_reports_errors_with_a_nonzero_status(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp, [('2026-10-06-a.md', 'no marker\n')])
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(fold.main(['--check', '--root', str(root)]), 1)
                (root / 'handoff.d' / '2026-10-06-a.md').write_text(section('state', '# A\n\ns'), encoding='utf-8')
                self.assertEqual(fold.main(['--root', str(root)]), 0)

    def test_real_documents_accept_a_realistic_fragment(self):
        """Run against copies of the real shared documents, so the placement rules fit their actual structure."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'docs').mkdir()
            for name in DOCS + (fold.ROADMAP,):
                shutil.copy(ROOT / name, root / name)
            (root / 'handoff.d').mkdir()
            numbers = [int(m.group(1)) for m in fold.DECISION.finditer((root / 'DECISIONS.md').read_text())]
            new = max(numbers) + 5
            first_row = next(line for line in (root / fold.ROADMAP).read_text().splitlines() if line.startswith('| Stage48 |'))
            (root / 'handoff.d' / '2099-01-01-test.md').write_text(''.join([
                section('changelog', '## Test entry'), section('state', '# Test state'),
                section('decisions', '## D{:03d} — test decision\n\nbody'.format(new)),
                section('methodology', '## Test method'), section('sources', '## Test sources'),
                section('roadmap', first_row.replace('authorized', 'merged-test'))]), encoding='utf-8')
            fold.fold(root)
            self.assertTrue((root / 'PROJECT_STATE.md').read_text().startswith('# Test state\n\n---\n\n'))
            self.assertTrue((root / 'CHANGELOG.md').read_text().rstrip().endswith('## Test entry'))
            self.assertIn('## D{:03d} — test decision'.format(new), (root / 'DECISIONS.md').read_text())
            self.assertIn('merged-test', (root / fold.ROADMAP).read_text())

    def test_repository_fragments_are_valid(self):
        self.assertIsInstance(fold.fold(check=True), list)


if __name__ == '__main__':
    unittest.main()
