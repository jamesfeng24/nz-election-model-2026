"""The manual Full replay workflow runs exactly the Verify commands, split into parallel groups."""
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.validate import ci_full_replay as replay

ROOT = Path(__file__).resolve().parents[2]
FULL_WORKFLOW = ROOT / '.github/workflows/full-replay.yml'


def synthetic_root(directory, runs):
    path = Path(directory) / replay.WORKFLOW
    path.parent.mkdir(parents=True)
    body = ''.join('      - run: {}\n'.format(command) for command in runs)
    path.write_text('jobs:\n  check:\n    steps:\n      - run: npm ci\n  python:\n    steps:\n'
                    '      - run: python3 -m pip install -r requirements-boundaries.txt\n'
                    '      - name: Verify reused Stage45 frozen pipeline\n'
                    '        if: steps.frozen.outputs.stage45 == \'integrity\'\n'
                    '        run: python3 -m scripts.validate.ci_frozen --check --pipeline stage45\n' + body +
                    '  later:\n    steps:\n      - run: python3 -m scripts.not_in_python_job --check\n')
    return Path(directory)


class PartitionTests(unittest.TestCase):
    def test_every_verify_command_runs_in_exactly_one_group(self):
        self.assertEqual(replay.check(), [])
        merged = [c for items in replay.partition().values() for c in items]
        self.assertEqual(sorted(merged), sorted(replay.commands()))
        self.assertGreater(len(merged), 140)  # guards against a parser that silently finds nothing

    def test_reuse_steps_and_other_jobs_are_not_commands(self):
        commands = replay.commands()
        self.assertFalse([c for c in commands if 'ci_frozen' in c or 'ci_stage39' in c or 'pip install' in c])
        self.assertIn('python3 -m unittest discover -s scripts/tests -v', commands)

    def test_every_replaced_command_of_a_registered_pipeline_has_its_own_group(self):
        registry = json.loads((ROOT / '.github/validation/frozen-pipelines.json').read_text())
        for name, pipeline in registry['pipelines'].items():
            for command in pipeline['replacedCommands']:
                with self.subTest(pipeline=name, command=command):
                    self.assertNotEqual(replay.group_of(command), replay.BASE)
        for command in ('python3 -m scripts.polling.candidate_integration.construction --check',):
            self.assertEqual(replay.group_of(command), 'stage39')

    def test_stage47_shares_a_group_with_the_stage45_and_stage46_caches_it_reads(self):
        groups = {replay.group_of('python3 -m scripts.{}.construction --check'.format(m))
                  for m in ('uncertainty_revision', 'uncertainty_tails', 'uncertainty_expectation')}
        self.assertEqual(groups, {'stage45-47'})
        items = replay.partition()['stage45-47']
        order = [i for i, c in enumerate(items) if c.endswith('construction --check')]
        self.assertEqual([items[i].split('.')[1] for i in order],
                         ['uncertainty_revision', 'uncertainty_tails', 'uncertainty_expectation'])

    def test_an_unregistered_new_command_falls_into_base_and_a_lost_one_is_reported(self):
        with TemporaryDirectory() as directory:
            root = synthetic_root(directory, ['python3 -m scripts.new_stage.run --check',
                                             'python3 -m scripts.balance_scale.fit --check'])
            parts = replay.partition(root)
            self.assertEqual(parts['base'], ['python3 -m scripts.new_stage.run --check'])
            self.assertEqual(parts['stage48'], ['python3 -m scripts.balance_scale.fit --check'])
            self.assertIn('group stage39 has no commands', replay.check(root))


class WorkflowTests(unittest.TestCase):
    def test_workflow_groups_and_timeouts_match_the_script(self):
        text = FULL_WORKFLOW.read_text()
        groups = re.findall(r'^          - group: (\S+)$', text, re.M)
        timeouts = re.findall(r'^            timeout: (\d+)$', text, re.M)
        self.assertEqual(sorted(groups), sorted((replay.BASE,) + tuple(replay.GROUPS)))
        self.assertEqual(len(timeouts), len(groups))
        self.assertTrue(all(0 < int(t) <= 360 for t in timeouts))  # GitHub's own job limit is 6 hours
        self.assertIn('--group ${{ matrix.group }}', text)

    def test_workflow_is_manual_only_and_not_named_by_verify(self):
        text = FULL_WORKFLOW.read_text()
        self.assertEqual(re.findall(r'^on:\n((?:  .+\n)+)', text, re.M), ['  workflow_dispatch:\n'])
        self.assertNotIn('pull_request', text.split('jobs:')[0].replace('# ', ''))
        self.assertNotIn('full-replay.yml', (ROOT / replay.WORKFLOW).read_text())
        self.assertIn('needs: [check, python]', text)

    def test_every_group_is_visible_in_the_aggregate_job(self):
        text = FULL_WORKFLOW.read_text()
        self.assertIn('if: always()', text)
        self.assertIn('"success success"', text)


class RunnerTests(unittest.TestCase):
    def test_runs_in_order_and_stops_at_the_first_failure(self):
        with TemporaryDirectory() as directory:
            marker = Path(directory) / 'order.txt'
            commands = ['python3 -c "open(r\'{}\', \'a\').write(\'1\')"'.format(marker),
                        'python3 -c "import sys; sys.exit(3)"',
                        'python3 -c "open(r\'{}\', \'a\').write(\'2\')"'.format(marker)]
            root = synthetic_root(directory, commands)
            with patch('builtins.print'):
                self.assertEqual(replay.run(replay.BASE, root), 3)
            self.assertEqual(marker.read_text(), '1')

    def test_unknown_group_is_an_error(self):
        with self.assertRaises(SystemExit):
            replay.run('nope')


if __name__ == '__main__':
    unittest.main()
