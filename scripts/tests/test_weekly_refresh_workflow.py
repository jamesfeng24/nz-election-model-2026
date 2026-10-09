"""Poll-refresh workflow: change guard, PR bodies, election-day stop and the shape of .github/workflows/poll-refresh.yml (stdlib only; no network)."""
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.polling.electorate_refresh import run as electorate
from scripts.polling.refresh_workflow import helper

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / '.github/workflows/poll-refresh.yml').read_text()
CODE = '\n'.join(l for l in WORKFLOW.splitlines() if not l.lstrip().startswith('#'))
DAY = '2026-10-14'


class ChangeGuardTests(unittest.TestCase):
    def test_published_run_may_only_add_its_own_paths(self):
        ok = ['?? data/raw/polling/weekly-refresh/2026-10-14/wikipedia.html', '?? data/processed/polling/weekly-refresh/2026-10-14/estimate.json',
              ' M data/processed/polling/weekly-refresh/index.json', '?? handoff.d/2026-10-14-poll-refresh.md']
        self.assertEqual(helper.check_changes(ok, DAY, 'published', 'none'), [])

    def test_earlier_runs_and_other_files_are_refused(self):
        for bad in (' M data/processed/polling/weekly-refresh/2026-10-07/estimate.json', ' M data/sources.json', '?? config/x.json',
                    ' M config/nowcast-2026.json', ' D data/processed/polling/weekly-refresh/index.json', '?? data/raw/polling/weekly-refresh/2026-10-07/x',
                    ' M data/processed/polling/electorate-live/2026-10-10/polls.json', '?? data/processed/polling/electorate-live/2026-10-14/polls.json'):
            self.assertEqual(helper.check_changes([bad], DAY, 'published', 'none'), [bad], bad)

    def test_index_may_not_be_added_as_new_file_or_the_fragment_modified(self):
        self.assertEqual(len(helper.check_changes(['?? data/processed/polling/weekly-refresh/index.json'], DAY, 'published', 'none')), 1)
        self.assertEqual(len(helper.check_changes([' M handoff.d/2026-10-14-poll-refresh.md'], DAY, 'published', 'none')), 1)

    def test_blocked_run_leaves_working_files_but_edits_nothing_tracked(self):
        self.assertEqual(helper.check_changes(['?? data/processed/polling/weekly-refresh/2026-10-14/dataset.npz', '?? data/raw/polling/weekly-refresh/2026-10-14/a'], DAY, 'blocked', 'none'), [])
        self.assertEqual(len(helper.check_changes([' M data/processed/polling/weekly-refresh/index.json'], DAY, 'blocked', 'none')), 1)

    def test_electorate_update_adds_its_own_dated_paths_and_may_create_its_first_index(self):
        ok = ['?? data/raw/polling/electorate-live/2026-10-14/a', '?? data/processed/polling/electorate-live/2026-10-14/polls.json',
              '?? data/processed/polling/electorate-live/index.json', '?? handoff.d/2026-10-14-electorate-poll-refresh.md']
        self.assertEqual(helper.check_changes(ok, DAY, 'none', 'updated'), [])
        self.assertEqual(helper.check_changes([' M data/processed/polling/electorate-live/index.json'], DAY, 'none', 'updated'), [])
        self.assertEqual(len(helper.check_changes(ok[:1], DAY, 'none', 'none')), 1)               # nothing may change when nothing was reported
        self.assertEqual(len(helper.check_changes([' M data/processed/polling/electorate-live/index.json'], DAY, 'none', 'blocked')), 1)
        self.assertEqual(len(helper.check_changes(['?? data/processed/polling/weekly-refresh/2026-10-14/panel.json'], DAY, 'none', 'updated')), 1)

    def test_paths_to_commit_never_include_working_files_of_a_blocked_run(self):
        paths = helper.paths_to_add(DAY, 'blocked', 'blocked')
        self.assertIn(f'data/processed/polling/weekly-refresh/{DAY}/blocked.json', paths)
        self.assertNotIn(f'data/processed/polling/weekly-refresh/{DAY}', paths)
        self.assertNotIn('data/processed/polling/electorate-live/index.json', paths)
        self.assertIn('data/processed/polling/electorate-live/index.json', helper.paths_to_add(DAY, 'none', 'updated'))


class BodyTests(unittest.TestCase):
    ELECTORATE_DAY = electorate.load_index()['runs'][0]['date']

    def test_published_body_of_the_committed_first_run(self):
        title, body = helper.pr_text('2026-10-07', 'published', 'none', 'builtin', '- `check`: ok')
        self.assertEqual(title, 'Polls: weekly national poll refresh 2026-10-07')
        for section in ('## Scope', '## Changes and limits', '## Local validation', '## CI and boundaries', '## Final published head and hosted validation'):
            self.assertIn(section, body)
        for text in ('1 News–Verian', 'Roy Morgan', 'NAT 27.9', 'Review flags:', 'max rank R-hat', '- `check`: ok', 'CI must be started manually', 'Not merged by the workflow'):
            self.assertIn(text, body)
        pat = helper.pr_text('2026-10-07', 'published', 'none', 'pat', '')[1]
        self.assertNotIn('CI must be started manually', pat)
        self.assertIn('POLL_REFRESH_TOKEN', pat)

    def test_electorate_only_update_body_lists_the_polls_and_says_nothing_reads_them(self):
        title, body = helper.pr_text(self.ELECTORATE_DAY, 'none', 'updated', 'pat', '- `c`: ok')
        self.assertEqual(title, f'Polls: electorate poll update {self.ELECTORATE_DAY}')
        for text in ('Mt Albert', 'Wellington Bays', 'Te Tai Tonga', 'NAT 30~', 'IND 18', 'data change only, with no refit', 'aggregator_only', 'sponsored_source'):
            self.assertIn(text, body)
        self.assertNotIn('Fit gates', body)

    def test_titles_by_outcome(self):
        self.assertEqual(helper.title_of(DAY, 'published', 'updated'), f'Polls: weekly national poll refresh {DAY} and electorate polls')
        self.assertEqual(helper.title_of(DAY, 'none', 'updated'), f'Polls: electorate poll update {DAY}')

    def test_blocked_bodies_name_every_blocker(self):
        review = {'blockers': [{'kind': 'revised_row', 'id': 'nz-poll-1', 'pollster': 'COL'}, {'kind': 'unmapped_row', 'detail': 'New Pollster'}], 'reviews': [], 'infos': []}
        with tempfile.TemporaryDirectory() as national, tempfile.TemporaryDirectory() as seats:
            for root, reason in ((national, 'new-row rules'), (seats, 'electorate-poll rules')):
                (Path(root) / DAY).mkdir()
                (Path(root) / DAY / 'blocked.json').write_text(json.dumps({'reason': reason, 'review': review}))
                (Path(root) / DAY / 'review.json').write_text(json.dumps(review))
            with mock.patch.object(helper, 'OUT', Path(national)), mock.patch.object(electorate, 'OUT', Path(seats)):
                title, body = helper.pr_text(DAY, 'blocked', 'blocked', 'builtin', '')
        self.assertEqual(title, f'Polls: weekly refresh {DAY} blocked (new-row rules, electorate-poll rules)')
        self.assertIn('revised_row', body); self.assertIn('unmapped_row', body); self.assertIn('refused to publish', body)
        self.assertIn('Electorate polls blocked', body)


class ScheduleTests(unittest.TestCase):
    def test_election_day_stops_the_refresh(self):
        self.assertEqual(helper.main(['active', '--date', '2026-11-05']), 0)
        self.assertEqual(helper.main(['active', '--date', '2026-11-07']), 1)


class WorkflowShapeTests(unittest.TestCase):
    def test_triggers_are_schedule_and_dispatch_only(self):
        on = WORKFLOW.split('\njobs:')[0]
        self.assertRegex(on, r"cron: '55 17 \* \* 3'")      # Wednesday 17:55 UTC = Thursday 06:55 NZDT (UTC+13)
        self.assertIn('workflow_dispatch:', on)
        self.assertNotRegex(on, r'(?m)^\s+(pull_request|push|pull_request_target):')

    def test_never_merges_or_pushes_to_main(self):
        self.assertNotRegex(CODE, r'gh pr merge|pulls/\S+/merge|--force|push[^\n]*\bmain\b|auto-merge')
        self.assertIn('git push -u origin "$branch"', WORKFLOW)
        self.assertIn('routine/poll-refresh-', WORKFLOW)

    def test_runs_the_runbook_command_in_the_pinned_environment(self):
        self.assertIn('-r requirements-external.lock', WORKFLOW)
        self.assertIn('-m scripts.polling.weekly_refresh.run --date', WORKFLOW)
        self.assertIn('-m scripts.polling.electorate_refresh.run --date', CODE)
        self.assertIn('--use-existing-capture', CODE)
        for check in ('weekly_refresh.run --check', 'unittest scripts.tests.test_weekly_refresh', 'electorate_refresh.run --check', 'unittest scripts.tests.test_electorate_refresh', 'fold_doc_fragments --check'):
            self.assertIn(check, WORKFLOW)
        self.assertRegex(WORKFLOW, r'timeout-minutes: \d+')

    def test_token_falls_back_to_the_built_in_token(self):
        self.assertIn('secrets.POLL_REFRESH_TOKEN || github.token', WORKFLOW)
        self.assertEqual(set(re.findall(r'secrets\.(\w+)', WORKFLOW)), {'POLL_REFRESH_TOKEN'})
