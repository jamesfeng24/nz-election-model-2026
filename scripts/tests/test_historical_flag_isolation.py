"""D107: historical development flags (2014-2023, keyed by seat name) must never reach the live 2026 build.

Only the diagnostics that own them (Stage67, its predecessor and Stage83, which reads the Stage67 flags unchanged), and their own
tests, may import them or read their outputs.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OWNERS = {'exceptional_scale': 'data/processed/exceptional-scale', 'exceptional_balance_scale': 'data/processed/exceptional-balance-scale',
          'ordinary_minor_spread': 'data/processed/ordinary-minor-spread'}
STAGE83 = 'scripts/ordinary_minor_spread/'
# scripts/seat_polls/historical.py: the Stage79 scoring diagnostic reads the Stage67 flags for the historical multiplier class
# (development only); the live path never imports it (test_stage79_seat_polls.Isolation).
# scripts/top_candidate_offset/evidence.py (D132): descriptive third-party ratios outside flagged seats, a stand-in for two-tick
# campaigns; development evidence only, imported by nothing in the live path (test_d132_top_candidate_offset).
ALLOWED_FILES = {'scripts/tests/test_exceptional_scale.py', 'scripts/tests/test_stage67_exceptional_balance_scale.py',
                 'scripts/tests/test_stage83_ordinary_minor_spread.py', 'scripts/tests/test_historical_flag_isolation.py',
                 'scripts/seat_polls/historical.py', 'scripts/top_candidate_offset/evidence.py'}


def sources():
    for base, pattern in (('scripts', '*.py'), ('src', '*.ts'), ('src', '*.tsx')):
        for path in (ROOT / base).rglob(pattern):
            rel = path.relative_to(ROOT).as_posix()
            if '__pycache__' not in rel:
                yield rel, path.read_text(encoding='utf-8')


class HistoricalFlagIsolation(unittest.TestCase):
    def test_no_outside_module_reads_the_historical_flag_diagnostics(self):
        offenders = []
        for rel, text in sources():
            for package, output in OWNERS.items():
                if rel.startswith(f'scripts/{package}/') or rel.startswith(STAGE83) or rel in ALLOWED_FILES:
                    continue
                if re.search(rf'\bscripts[./]{package}\b', text) or output in text:
                    offenders.append(f'{rel} -> {package}')
        self.assertEqual(offenders, [], 'historical development flags must not be read outside their own diagnostics (D107)')

    def test_the_guard_sees_the_owners(self):
        found = {rel for rel, _ in sources() if any(rel.startswith(f'scripts/{p}/') for p in OWNERS)}
        self.assertTrue(any('exceptional_scale/' in r for r in found) and any('exceptional_balance_scale/' in r for r in found))


if __name__ == '__main__':
    unittest.main()
