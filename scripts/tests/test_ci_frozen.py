"""Frozen-pipeline reuse is conservative: every uncertainty in the proof forces full validation."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.validate import ci_frozen as frozen

ROOT = Path(__file__).resolve().parents[2]
COMMAND = 'python3 -m scripts.pipe.entry --check'
RUNTIME = {'python': '3.12.2', 'system': 'Linux', 'machine': 'x86_64', 'osId': 'ubuntu', 'osVersionId': '24.04',
           'packages': {'numpy': '2.2.6'}}
WORKFLOW = """name: Verify
jobs:
  python:
    steps:
      - uses: actions/checkout@v5
      - run: python3 -m unittest discover -s scripts/tests -v
      - run: python3 -m scripts.pipe.diagnosis --check
      - run: python3 -m scripts.pipe.entry --check
        if: steps.frozen.outputs.pipe != 'integrity'
      - name: Verify reused pipe
        if: steps.frozen.outputs.pipe == 'integrity'
        run: python3 -m scripts.validate.ci_frozen --check --pipeline pipe
      - run: python3 -m scripts.pipe.report --check
"""


def write(root, name, text):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def git(root, *args):
    return subprocess.check_output(('git', '-c', 'user.email=t@t', '-c', 'user.name=t') + args, cwd=root, text=True).strip()


def commit(root, message):
    git(root, 'add', '-A')
    git(root, 'commit', '-qm', message)
    return git(root, 'rev-parse', 'HEAD')


def registry_for(attested, evidence_sha):
    return {'version': 3, 'liveAttestation': {'workflow': 'ci.yml', 'branch': 'main', 'events': ['push', 'pull_request'], 'job': 'python', 'maxRuns': 3},
            'attestation': {'commit': attested, 'runs': [], 'evidencePath': '.github/validation/evidence/e.json',
                            'evidenceSha256': evidence_sha},
            'runtime': RUNTIME,
            'pipelines': {'pipe': {
                'entryModules': ['scripts.pipe.entry'], 'ownedPaths': ['scripts/pipe'],
                'outputPaths': ['data/processed/pipe'], 'extraDependencies': ['docs/spec.txt'],
                'cacheDirectory': '.cache/pipe', 'cacheReaderModules': ['scripts.pipe.entry'],
                'cacheReaderNames': ['arrays'], 'reviewedCacheConsumers': [], 'replacedCommands': [COMMAND],
                'integrityChecks': []}}}


class Repository:
    """A tiny repository: attested commit A, reviewed registry commit B (= pull request base), then changes."""

    def __init__(self, tmp):
        self.root = Path(tmp)
        git(self.root, 'init', '-q')
        write(self.root, 'scripts/__init__.py', '')
        write(self.root, 'scripts/pipe/__init__.py', '')
        write(self.root, 'scripts/pipe/entry.py',
              "from .helper import help\nfrom scripts.shared import tool\nPATH = 'data/processed/pipe/in.json'\n"
              "SPEC = 'docs/spec.txt'\nLOCK = 'requirements-boundaries.txt'\n\ndef arrays():\n    return 1\n")
        write(self.root, 'scripts/pipe/helper.py', 'def help():\n    return 1\n')
        write(self.root, 'scripts/shared.py', 'def tool():\n    return 1\n')
        write(self.root, 'scripts/other/__init__.py', '')
        write(self.root, 'scripts/other/unrelated.py', 'X = 1\n')
        write(self.root, 'scripts/tests/test_x.py', 'X = 1\n')
        write(self.root, 'data/processed/pipe/in.json', '{}\n')
        write(self.root, 'data/processed/other/x.json', '{}\n')
        write(self.root, 'docs/spec.txt', 'spec\n')
        write(self.root, 'docs/a.md', 'notes\n')
        write(self.root, 'requirements-boundaries.txt', 'numpy==2.2.6\n')
        write(self.root, '.python-version', '3.12.2\n')
        write(self.root, '.github/workflows/ci.yml', WORKFLOW)
        self.attested = commit(self.root, 'attested')
        record = {'run': {'event': 'push', 'conclusion': 'success', 'head_sha': self.attested},
                  'job': {'name': 'python', 'conclusion': 'success', 'steps': [
                      {'name': 'Run ' + COMMAND, 'conclusion': 'success'},
                      {'name': 'Run python3 -m scripts.pipe.diagnosis --check', 'conclusion': 'success'},
                      {'name': 'Run python3 -m unittest discover -s scripts/tests -v', 'conclusion': 'success'}]}}
        write(self.root, '.github/validation/evidence/e.json', json.dumps(record))
        self.sha = hashlib.sha256((self.root / '.github/validation/evidence/e.json').read_bytes()).hexdigest()
        self.registry = registry_for(self.attested, self.sha)
        write(self.root, '.github/validation/frozen-pipelines.json', json.dumps(self.registry))
        self.base = commit(self.root, 'registry (earlier reviewed pull request)')

    def select(self, event='pull_request', runtime=None, registry=None, candidates=None):
        return frozen.select_pipeline('pipe', registry or self.registry, event, self.root,
                                      RUNTIME if runtime is None else runtime, candidates)

    def live(self, commit_sha, skipped=False, event='push'):
        """A live attestation record shaped like the Actions API job record of a main push run."""
        steps = [{'name': 'Run ' + COMMAND, 'conclusion': 'skipped' if skipped else 'success'},
                 {'name': 'Run python3 -m scripts.pipe.diagnosis --check', 'conclusion': 'success'},
                 {'name': 'Run python3 -m unittest discover -s scripts/tests -v', 'conclusion': 'success'}]
        return {'commit': commit_sha, 'source': 'live-' + event, 'record': {
            'run': {'event': event, 'conclusion': 'success', 'head_sha': commit_sha},
            'job': {'name': 'python', 'conclusion': 'success', 'steps': steps}}}


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(self.tmp.name)

    def assertFull(self, result, text=''):
        self.assertEqual(result['mode'], 'full', result)
        self.assertIn(text, result['reason'])

    def test_unchanged_and_unrelated_changes_reuse_the_attested_run(self):
        self.assertEqual(self.repo.select()['mode'], 'integrity')
        write(self.repo.root, 'docs/a.md', 'edited\n')
        write(self.repo.root, 'scripts/tests/test_x.py', 'X = 2\n')
        write(self.repo.root, 'scripts/tests/test_new.py', 'X = 3\n')
        write(self.repo.root, 'scripts/other/unrelated.py', 'X = 2\n')
        write(self.repo.root, 'scripts/newstage/__init__.py', '')
        write(self.repo.root, 'scripts/newstage/run.py', 'import scripts.pipe.helper\n')
        write(self.repo.root, 'data/processed/newstage/out.json', '{}\n')
        write(self.repo.root, 'src/App.tsx', 'x\n')
        commit(self.repo.root, 'unrelated work and a new stage')
        self.assertEqual(self.repo.select()['mode'], 'integrity')

    def test_every_dependency_class_forces_full(self):
        cases = (('scripts/pipe/helper.py', 'def help():\n    return 2\n'),
                 ('scripts/shared.py', 'def tool():\n    return 2\n'),
                 ('scripts/pipe/new.py', 'X = 1\n'),
                 ('data/processed/pipe/in.json', '{"a": 1}\n'),
                 ('data/processed/pipe/added.json', '{}\n'),
                 ('data/processed/other/x.json', '{"a": 1}\n'),
                 ('docs/spec.txt', 'changed\n'),
                 ('requirements-boundaries.txt', 'numpy==9\n'),
                 ('.python-version', '3.13.0\n'),
                 ('.github/other.yml', 'x\n'))
        for name, text in cases:
            with self.subTest(name=name):
                git(self.repo.root, 'reset', '-q', '--hard', self.repo.base)
                write(self.repo.root, name, text)
                commit(self.repo.root, 'change ' + name)
                self.assertFull(self.repo.select())

    def test_deleted_existing_data_forces_full(self):
        git(self.repo.root, 'rm', '-q', 'data/processed/other/x.json')
        commit(self.repo.root, 'delete')
        self.assertFull(self.repo.select(), 'existing data file changed')

    def test_machinery_and_policy_edits_do_not_force_replay_but_cannot_remove_validation(self):
        write(self.repo.root, 'scripts/validate/ci_frozen.py', 'changed\n')
        write(self.repo.root, '.github/validation/frozen-pipelines.json', json.dumps(self.repo.registry))
        write(self.repo.root, 'AGENTS.md', 'rules\n')
        commit(self.repo.root, 'machinery and policy only')
        self.assertEqual(self.repo.select()['mode'], 'integrity')
        # ... but the same change set may not weaken the validation that the attested run executed.
        text = (self.repo.root / '.github/workflows/ci.yml').read_text()
        write(self.repo.root, '.github/workflows/ci.yml', text.replace('      - run: python3 -m scripts.pipe.diagnosis --check\n', ''))
        commit(self.repo.root, 'weaken')
        self.assertFull(self.repo.select(), 'removed from workflow')

    def test_non_pull_request_events_and_missing_history_are_full(self):
        for event in ('workflow_dispatch', 'schedule', 'unknown'):
            self.assertFull(self.repo.select(event), 'always uses full')
        self.assertEqual(self.repo.select('push')['mode'], 'integrity')
        registry = deepcopy(self.repo.registry)
        registry['attestation']['commit'] = '1' * 40
        self.assertFull(self.repo.select(registry=registry), 'attested run')
        self.assertIsNone(frozen.changed_files(self.repo.root, '1' * 40))

    def test_dirty_tree_and_unattested_runtime_are_full(self):
        write(self.repo.root, 'docs/a.md', 'dirty\n')
        self.assertFull(self.repo.select(), 'dirty')
        git(self.repo.root, 'checkout', '-q', '--', 'docs/a.md')
        for key, value in (('python', '3.12.3'), ('system', 'Darwin'), ('machine', 'arm64'), ('osVersionId', '26.04'),
                           ('packages', {'numpy': '2.3.0'})):
            with self.subTest(key=key):
                self.assertFull(self.repo.select(runtime={**RUNTIME, key: value}), 'unattested runtime: ' + key)

    def test_evidence_must_be_unchanged_successful_and_cover_required_steps(self):
        path = self.repo.root / '.github/validation/evidence/e.json'
        original = json.loads(path.read_text())
        for mutate in (lambda r: r['run'].update(event='schedule'), lambda r: r['run'].update(conclusion='failure'),
                       lambda r: r['run'].update(head_sha='2' * 40), lambda r: r['job'].update(conclusion='failure'),
                       lambda r: r['job']['steps'][0].update(conclusion='skipped'),
                       lambda r: r['job']['steps'].pop(0)):
            record = deepcopy(original)
            mutate(record)
            path.write_text(json.dumps(record))
            registry = deepcopy(self.repo.registry)
            registry['attestation']['evidenceSha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            commit(self.repo.root, 'tamper')
            self.assertFull(self.repo.select(registry=registry))
        self.assertFull(self.repo.select(), 'seed attestation evidence')

    def test_modification_runs_full_once_then_the_new_main_run_becomes_the_attestation(self):
        write(self.repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
        modified = commit(self.repo.root, 'modify frozen code')
        self.assertFull(self.repo.select(), 'dependency changed')  # the pull request/main run executes in full once
        write(self.repo.root, 'docs/a.md', 'later unrelated work\n')
        later = commit(self.repo.root, 'unrelated')
        live = self.repo.live(modified)
        self.assertEqual(self.repo.select(candidates=[live])['mode'], 'integrity')
        self.assertEqual(self.repo.select('push', candidates=[live])['mode'], 'integrity')
        write(self.repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 3\n')
        commit(self.repo.root, 'modified again')
        self.assertFull(self.repo.select(candidates=[live]), 'dependency changed')
        self.assertNotEqual(later, modified)

    def test_a_successful_pull_request_run_is_the_reference_for_its_own_merge(self):
        """Modified once on the PR; the merge's main push (a merge commit on top of that head) reuses it."""
        git(self.repo.root, 'checkout', '-q', '-b', 'pr')
        write(self.repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
        head = commit(self.repo.root, 'modify frozen code on the pull request')
        self.assertFull(self.repo.select(), 'dependency changed')  # the PR run replays once
        git(self.repo.root, 'checkout', '-q', '-')
        write(self.repo.root, 'docs/a.md', 'main moved on meanwhile\n')
        commit(self.repo.root, 'unrelated main commit')
        git(self.repo.root, 'merge', '--no-ff', '-qm', 'Merge pull request', 'pr')
        pr_run = self.repo.live(head, event='pull_request')
        self.assertEqual(self.repo.select('push', candidates=[pr_run])['mode'], 'integrity')  # no second replay
        self.assertFull(self.repo.select('push', candidates=[]), 'no attested')

    def test_live_attestations_must_have_executed_the_replaced_commands(self):
        head = git(self.repo.root, 'rev-parse', 'HEAD')
        for bad in (self.repo.live(head, skipped=True), self.repo.live(head, event='schedule')):
            self.assertFull(self.repo.select(candidates=[bad]), 'attested')
        self.assertEqual(self.repo.select(candidates=[self.repo.live(head)])['mode'], 'integrity')

    def test_newest_provable_candidate_wins_and_failures_fall_back_to_older_ones(self):
        seed, errors = frozen.seed_candidate(self.repo.registry, self.repo.root)
        self.assertEqual(errors, [])
        head = git(self.repo.root, 'rev-parse', 'HEAD')
        self.assertEqual(self.repo.select(candidates=[self.repo.live(head, skipped=True), seed])['mode'], 'integrity')
        self.assertFull(self.repo.select(candidates=[]), 'no attested')

    def test_dynamic_imports_cannot_be_analysed_and_force_full(self):
        write(self.repo.root, 'scripts/pipe/helper.py', 'import importlib\nimportlib.import_module("scripts.x")\n')
        commit(self.repo.root, 'dynamic')
        self.assertFull(self.repo.select())

    def test_reviewed_registry_with_unsupported_version_is_full(self):
        registry = deepcopy(self.repo.registry)
        registry['version'] = 1
        self.assertFull(self.repo.select(registry=registry), 'version')


class CacheConsumerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(self.tmp.name)

    def test_a_later_stage_reading_the_runtime_cache_blocks_reuse_until_reviewed(self):
        for name, text in (('scripts/later/a.py', 'from scripts.pipe.entry import arrays as control\n'),
                           ('scripts/later/b.py', "P = '.cache/pipe/x'\n"),
                           ('scripts/later/c.py', 'from scripts.pipe import entry\n')):
            with self.subTest(name=name):
                git(self.repo.root, 'reset', '-q', '--hard', self.repo.base)
                write(self.repo.root, 'scripts/later/__init__.py', '')
                write(self.repo.root, name, text)
                commit(self.repo.root, 'consumer')
                result = self.repo.select()
                self.assertEqual(result['mode'], 'full')
                self.assertIn('runtime cache', result['reason'])
                registry = deepcopy(self.repo.registry)
                registry['pipelines']['pipe']['reviewedCacheConsumers'] = [name]
                self.assertEqual(self.repo.select(registry=registry)['mode'], 'integrity')

    def test_importing_pure_functions_from_the_pipeline_is_not_a_cache_read(self):
        write(self.repo.root, 'scripts/later/__init__.py', '')
        write(self.repo.root, 'scripts/later/ok.py', 'from scripts.pipe.entry import SPEC\n')
        commit(self.repo.root, 'pure import')
        self.assertEqual(self.repo.select()['mode'], 'integrity')


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(self.tmp.name)

    def change(self, old, new):
        text = (self.repo.root / '.github/workflows/ci.yml').read_text()
        self.assertIn(old, text)
        write(self.repo.root, '.github/workflows/ci.yml', text.replace(old, new))
        commit(self.repo.root, 'workflow')
        return self.repo.select()

    def test_action_bumps_and_added_steps_keep_reuse(self):
        self.assertEqual(self.change('checkout@v5', 'checkout@v6')['mode'], 'integrity')
        result = self.change('      - run: python3 -m scripts.pipe.report --check\n',
                             '      - run: python3 -m scripts.pipe.report --check\n      - run: python3 -m scripts.later.new --check\n')
        self.assertEqual(result['mode'], 'integrity')

    def test_removed_or_newly_conditioned_validation_forces_full(self):
        for old, new in (('      - run: python3 -m scripts.pipe.diagnosis --check\n', ''),
                         ('      - run: python3 -m unittest discover -s scripts/tests -v\n', ''),
                         ('      - run: python3 -m scripts.pipe.diagnosis --check\n',
                          "      - run: python3 -m scripts.pipe.diagnosis --check\n        if: github.event_name == 'never'\n"),
                         ('      - run: python3 -m scripts.pipe.diagnosis --check\n',
                          '      - run: python3 -m scripts.pipe.diagnosis --check\n        continue-on-error: true\n'),
                         ("        if: steps.frozen.outputs.pipe != 'integrity'\n",
                          "        if: steps.frozen.outputs.other != 'integrity'\n")):
            with self.subTest(old=old):
                git(self.repo.root, 'reset', '-q', '--hard', self.repo.base)
                self.assertEqual(self.change(old, new)['mode'], 'full')


class SelectAndVerifyTests(unittest.TestCase):
    def test_force_full_and_registry_errors_never_reuse(self):
        registry = json.loads((ROOT / frozen.REGISTRY).read_text())
        for name, value in frozen.select(registry, 'pull_request', force_full=True).items():
            self.assertEqual(value['mode'], 'full')
        with TemporaryDirectory() as tmp:
            repo = Repository(tmp)
            broken = deepcopy(repo.registry)
            del broken['pipelines']['pipe']['entryModules']
            result = frozen.select(broken, 'pull_request', repo.root, RUNTIME)
            self.assertEqual(result['pipe']['mode'], 'full')
            self.assertIn('invalid selection inputs', result['pipe']['reason'])

    def test_verify_refuses_when_reuse_is_not_proven(self):
        with TemporaryDirectory() as tmp:
            repo = Repository(tmp)
            write(repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
            commit(repo.root, 'change')
            with patch.object(frozen, 'runtime_errors', return_value=[]):
                with self.assertRaises(ValueError):
                    frozen.verify('pipe', root=repo.root)

    def test_verify_runs_integrity_checks_when_reuse_is_proven(self):
        with TemporaryDirectory() as tmp:
            repo = Repository(tmp)
            registry = deepcopy(repo.registry)
            registry['pipelines']['pipe']['integrityChecks'] = ['scripts.validate.ci_frozen:load_registry']
            write(repo.root, '.github/validation/frozen-pipelines.json', json.dumps(registry))
            base = commit(repo.root, 'registry with integrity check')
            with patch.object(frozen, 'runtime_errors', return_value=[]), \
                    patch.object(frozen, 'load_registry', return_value=registry) as loaded:
                result = frozen.verify('pipe', root=repo.root)
            self.assertEqual(result['mode'], 'integrity')
            self.assertTrue(loaded.called)

    def test_command_line_writes_one_output_per_registered_pipeline(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch('sys.argv', ['ci_frozen', '--event', 'push', '--github-output', str(output)]), \
                    redirect_stdout(StringIO()):
                frozen.main()
            lines = sorted(output.read_text().split())
            self.assertEqual([line.split('=')[0] for line in lines], ['stage45', 'stage46'])
            # The mode depends on the runner and its Actions history, so only its form is fixed here.
            self.assertTrue(all(line.split('=')[1] in ('full', 'integrity') for line in lines))


class RealRegistryTests(unittest.TestCase):
    """The committed registry and workflow must stay mutually consistent."""

    def setUp(self):
        self.registry = json.loads((ROOT / frozen.REGISTRY).read_text())
        self.workflow = (ROOT / frozen.WORKFLOW).read_text()

    def test_replaced_commands_are_gated_and_the_replacement_step_exists(self):
        for name, pipeline in self.registry['pipelines'].items():
            for command in pipeline['replacedCommands']:
                self.assertIn('      - run: {}\n        if: steps.frozen.outputs.{} != \'integrity\'\n'.format(command, name),
                              self.workflow)
            self.assertIn("steps.frozen.outputs.{} == 'integrity'".format(name), self.workflow)
            self.assertIn('--check --pipeline {} '.format(name), self.workflow)
            self.assertIn('id: frozen\n        continue-on-error: true', self.workflow)

    def test_only_expensive_reconstruction_commands_are_replaced(self):
        replaced = {c for p in self.registry['pipelines'].values() for c in p['replacedCommands']}
        for command in replaced:
            self.assertTrue(any(part in command for part in ('construction', 'evaluation', 'verification', 'mean_audit')))
        for kept in ('diagnosis', 'estimation', 'numerics', 'report', 'manifest', 'reference', 'priors'):
            self.assertFalse(any(kept in command for command in replaced))
        self.assertIn('python3 -m unittest discover -s scripts/tests -v', self.workflow)

    def test_registered_closure_has_no_dynamic_imports_and_resolves_every_entry(self):
        for name, pipeline in self.registry['pipelines'].items():
            files, literals, errors = frozen.closure(ROOT, pipeline['entryModules'])
            self.assertEqual(errors, [], name)
            self.assertGreater(len(files), len(pipeline['entryModules']))
            for module in pipeline['entryModules']:
                self.assertIsNotNone(frozen.module_file(ROOT, module))
            self.assertIn('requirements-boundaries.txt', literals)

    def test_stage46_closure_includes_stage45_and_earlier_helpers(self):
        files, _, _ = frozen.closure(ROOT, self.registry['pipelines']['stage46']['entryModules'])
        self.assertIn('scripts/uncertainty_revision/construction.py', files)
        self.assertIn('scripts/uncertainty/construction.py', files)

    def test_seed_attestation_pins_a_full_push_run_that_executed_every_replaced_command(self):
        seed, errors = frozen.seed_candidate(self.registry, ROOT)
        self.assertEqual(errors, [])
        for name, pipeline in self.registry['pipelines'].items():
            errors, steps = frozen.candidate_errors(seed, pipeline['replacedCommands'])
            self.assertEqual(errors, [], name)
            self.assertEqual(frozen.workflow_errors(ROOT, steps, self.registry), [])
            self.assertNotIn('Verify previously validated Stage39 sealed integrity', steps)

    def test_live_candidates_are_read_from_the_api_for_push_and_pull_request_runs(self):
        calls = []

        def fetch(url, token):
            calls.append(url)
            if '/jobs' in url:
                return {'jobs': [{'id': 9, 'name': 'check', 'conclusion': 'success', 'steps': []},
                                 {'id': 8, 'name': 'python', 'conclusion': 'success', 'steps': [{'name': 'Run x', 'conclusion': 'success'}]}]}
            event = 'push' if 'event=push' in url else 'pull_request'
            return {'workflow_runs': [{'id': 1 if event == 'push' else 2, 'head_sha': ('a' if event == 'push' else 'b') * 40,
                                       'event': event, 'conclusion': 'success',
                                       'created_at': '2026-10-06T00:0{}:00Z'.format(1 if event == 'push' else 2)},
                                      {'id': 3, 'head_sha': 'c' * 40, 'event': event, 'created_at': '2026-10-05T00:00:00Z'}]}
        environ = {'GITHUB_REPOSITORY': 'o/r', 'GITHUB_TOKEN': 't'}
        reachable = lambda root, sha: sha != 'c' * 40  # unreachable (e.g. squash-merged or unrelated) heads are never attestations
        found = frozen.live_candidates(self.registry, environ, fetch, ROOT, reachable)
        self.assertEqual([(c['commit'][0], c['source']) for c in found], [('b', 'live-pull_request'), ('a', 'live-push')])
        self.assertEqual(found[0]['record']['job']['id'], 8)
        self.assertTrue(any('event=push' in c and 'branch=main' in c and 'status=success' in c for c in calls))
        self.assertTrue(any('event=pull_request' in c and 'branch=' not in c for c in calls))
        self.assertEqual(frozen.live_candidates(self.registry, {}, fetch), [])
        self.assertEqual(frozen.live_candidates(self.registry, environ, lambda *a: (_ for _ in ()).throw(OSError())), [])
        self.assertEqual(frozen.live_candidates(self.registry, environ, lambda *a: {}), [])

    def test_report_modules_outside_the_closure_are_not_dependencies(self):
        stage46 = self.registry['pipelines']['stage46']
        self.assertTrue(stage46['reportPaths'])
        for path in stage46['reportPaths']:
            self.assertNotIn(path, stage46['ownedPaths'])
            self.assertTrue((ROOT / path).is_file())
            files, _, _ = frozen.closure(ROOT, stage46['entryModules'])
            self.assertNotIn(path, files)

    def test_workflow_permissions_timeouts_and_event_wiring(self):
        self.assertIn('  contents: read\n  actions: read\n', self.workflow)
        self.assertIn('timeout-minutes: 150', self.workflow)
        self.assertIn('timeout-minutes: 20', self.workflow)
        self.assertIn('GITHUB_TOKEN: ${{ github.token }}', self.workflow)

    def test_current_cache_consumers_are_none(self):
        for pipeline in self.registry['pipelines'].values():
            self.assertEqual(frozen.cache_consumers(ROOT, pipeline), [])


class SourceRegistryFrozenTests(unittest.TestCase):
    def test_historical_contracts_pin_the_current_source_registry(self):
        pinned = json.loads((ROOT / 'data/processed/uncertainty-revision/preservation.json').read_text())
        actual = hashlib.sha256((ROOT / 'data/sources.json').read_bytes()).hexdigest()
        self.assertEqual(pinned['priorDataHashes']['data/sources.json'], actual,
                         'data/sources.json is pinned by historical preservation contracts; record new sources '
                         'in a standalone dated registry instead (docs/ci-validation.md)')


if __name__ == '__main__':
    unittest.main()
