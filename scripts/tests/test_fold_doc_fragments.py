"""Handoff fragments fold deterministically into CHANGELOG.md and PROJECT_STATE.md."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import fold_doc_fragments as fold

CHANGELOG = '# Changelog\n\n## Stage1 — old\n\n- old entry\n'
STATE = '# Stage1 — old checkpoint\n\nold state.\n\n---\n\n# Stage0 — older\n\nolder state.\n'


def build(root, changelog=(), state=()):
    root = Path(root)
    (root / 'CHANGELOG.md').write_text(CHANGELOG, encoding='utf-8')
    (root / 'PROJECT_STATE.md').write_text(STATE, encoding='utf-8')
    for directory, files in (('changelog.d', changelog), ('state.d', state)):
        (root / directory).mkdir()
        (root / directory / 'README.md').write_text('# readme, never folded\n', encoding='utf-8')
        for name, text in files:
            (root / directory / name).write_text(text, encoding='utf-8')
    return root


class FoldFragmentTests(unittest.TestCase):
    def test_changelog_appends_oldest_first_and_state_prepends_newest_first(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp,
                         changelog=[('2026-10-07-b.md', '## B — 2026-10-07\n\n- b\n'), ('2026-10-06-a.md', '## A — 2026-10-06\n\n- a\n')],
                         state=[('2026-10-06-a.md', '# A — 2026-10-06\n\nstate a.\n'), ('2026-10-07-b.md', '# B — 2026-10-07\n\nstate b.\n')])
            folded = fold.fold(root)
            self.assertEqual(len(folded), 4)
            self.assertEqual((root / 'CHANGELOG.md').read_text(),
                             CHANGELOG + '\n## A — 2026-10-06\n\n- a\n\n## B — 2026-10-07\n\n- b\n')
            self.assertEqual((root / 'PROJECT_STATE.md').read_text(),
                             '# B — 2026-10-07\n\nstate b.\n\n---\n\n# A — 2026-10-06\n\nstate a.\n\n---\n\n' + STATE)
            self.assertEqual(sorted(p.name for p in (root / 'changelog.d').iterdir()), ['README.md'])
            self.assertEqual(sorted(p.name for p in (root / 'state.d').iterdir()), ['README.md'])

    def test_folding_is_idempotent_and_ignores_empty_directories(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp)
            self.assertEqual(fold.fold(root), [])
            self.assertEqual((root / 'CHANGELOG.md').read_text(), CHANGELOG)
            self.assertEqual((root / 'PROJECT_STATE.md').read_text(), STATE)

    def test_one_kind_alone_leaves_the_other_file_untouched(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp, changelog=[('2026-10-06-a.md', '## A\n\n- a\n')])
            fold.fold(root)
            self.assertEqual((root / 'PROJECT_STATE.md').read_text(), STATE)
            self.assertTrue((root / 'CHANGELOG.md').read_text().endswith('\n## A\n\n- a\n'))

    def test_check_changes_nothing(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp, changelog=[('2026-10-06-a.md', '## A\n\n- a\n')], state=[('2026-10-06-a.md', '# A\n\ns\n')])
            self.assertEqual(len(fold.fold(root, check=True)), 2)
            self.assertEqual((root / 'CHANGELOG.md').read_text(), CHANGELOG)
            self.assertTrue((root / 'changelog.d' / '2026-10-06-a.md').exists())

    def test_invalid_fragments_fail_without_writing_anything(self):
        bad = {
            'bad name': ('changelog.d', 'notes.md', '## A\n'),
            'empty': ('changelog.d', '2026-10-06-a.md', '  \n'),
            'wrong heading level in changelog': ('changelog.d', '2026-10-06-a.md', '# A\n'),
            'wrong heading level in state': ('state.d', '2026-10-06-a.md', '## A\n'),
            'no heading': ('state.d', '2026-10-06-a.md', 'text only\n'),
            'already folded': ('changelog.d', '2026-10-06-a.md', '## Stage1 — old\n\n- again\n'),
        }
        for label, (directory, name, text) in bad.items():
            with self.subTest(label), TemporaryDirectory() as tmp:
                root = build(tmp, changelog=[('2026-10-06-ok.md', '## OK\n\n- ok\n')])
                (root / directory / name).write_text(text, encoding='utf-8')
                with self.assertRaises(fold.FragmentError):
                    fold.fold(root)
                self.assertEqual((root / 'CHANGELOG.md').read_text(), CHANGELOG)
                self.assertTrue((root / 'changelog.d' / '2026-10-06-ok.md').exists())

    def test_command_line_reports_errors_with_a_nonzero_status(self):
        with TemporaryDirectory() as tmp:
            root = build(tmp, state=[('2026-10-06-a.md', 'no heading\n')])
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(fold.main(['--check', '--root', str(root)]), 1)
                (root / 'state.d' / '2026-10-06-a.md').write_text('# A\n\ns\n', encoding='utf-8')
                self.assertEqual(fold.main(['--root', str(root)]), 0)

    def test_repository_fragments_are_valid(self):
        self.assertIsInstance(fold.fold(check=True), list)


if __name__ == '__main__':
    unittest.main()
