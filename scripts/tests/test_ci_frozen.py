"""Frozen-pipeline reuse is conservative: every uncertainty in the proof forces full validation."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.validate import ci_frozen as frozen

ROOT = Path(__file__).resolve().parents[2]
COMMAND = 'python3 -m scripts.pipe.entry --check'
COMMAND2 = 'python3 -m scripts.pipe2.entry --check'
ENV = {'GITHUB_REPOSITORY': 'o/r', 'GITHUB_TOKEN': 't'}
NO_TOKEN = {'GITHUB_TOKEN': '', 'GH_TOKEN': ''}  # an empty token disables API discovery whatever the test environment
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
      - run: python3 -m scripts.pipe2.entry --check
        if: steps.frozen.outputs.pipe2 != 'integrity'
      - name: Verify reused pipe2
        if: steps.frozen.outputs.pipe2 == 'integrity'
        run: python3 -m scripts.validate.ci_frozen --check --pipeline pipe2
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


def pipeline_entry(name, **override):
    base = {'entryModules': ['scripts.{}.entry'.format(name)], 'ownedPaths': ['scripts/' + name],
            'outputPaths': ['data/processed/' + name], 'extraDependencies': [],
            'cacheDirectory': '.cache/' + name, 'cacheReaderModules': [], 'cacheReaderNames': [],
            'reviewedCacheConsumers': [], 'replacedCommands': ['python3 -m scripts.{}.entry --check'.format(name)],
            'integrityChecks': []}
    base.update(override)
    return base


def registry_for():
    """Two pipelines: ``pipe`` (stands for Stage45/46) and ``pipe2`` (Stage47: reads the pipe cache)."""
    return {'version': 4, 'liveAttestation': {'workflow': 'ci.yml', 'branch': 'main', 'events': ['push', 'pull_request', 'workflow_dispatch'],
                                              'job': 'python', 'perPage': 20, 'maxPages': 10, 'maxJobFetches': 120},
            'runtime': RUNTIME,
            'pipelines': {
                'pipe': pipeline_entry('pipe', extraDependencies=['docs/spec.txt'], cacheReaderModules=['scripts.pipe.entry'],
                                       cacheReaderNames=['arrays']),
                'pipe2': pipeline_entry('pipe2', cacheDependencies=['pipe'])}}


STANDARD_STEPS = ('python3 -m unittest discover -s scripts/tests -v', 'python3 -m scripts.pipe.diagnosis --check')


def job_steps(full=True, extra=()):
    """The python job's steps of a run that executed every replaced command (``full``) or reused both pipelines."""
    gated = 'success' if full else 'skipped'
    return [{'name': 'Run ' + c, 'conclusion': 'success'} for c in STANDARD_STEPS + tuple(extra)] + \
           [{'name': 'Run ' + c, 'conclusion': gated} for c in (COMMAND, COMMAND2)]


def run_record(run_id, sha, full=True, event='push', branch='main', created=None, conclusion='success'):
    return {'id': run_id, 'html_url': 'https://example.test/runs/{}'.format(run_id), 'event': event, 'head_branch': branch,
            'head_sha': sha, 'conclusion': conclusion, 'created_at': created or '2026-10-02T00:{:02d}:00Z'.format(run_id % 60),
            '_full': full}


class FakeApi:
    """The two Actions endpoints the selector reads, newest run first, with pagination and call accounting."""

    def __init__(self, runs, fail=None):
        self.runs, self.fail, self.list_calls, self.job_calls, self.calls = list(runs), fail, [], [], 0

    def __call__(self, url, token):
        self.calls += 1
        if self.fail:
            raise self.fail
        single = re.search(r'/runs/(\d+)$', url)
        if single:
            return next({k: v for k, v in r.items() if k != '_full'} for r in self.runs if r['id'] == int(single.group(1)))
        query = dict(part.split('=') for part in url.split('?', 1)[1].split('&')) if '?' in url else {}
        if '/jobs' in url:
            run_id = int(url.split('/runs/')[1].split('/')[0])
            self.job_calls.append(run_id)
            run = next(r for r in self.runs if r['id'] == run_id)
            return {'jobs': [{'id': 1, 'name': 'check', 'conclusion': 'success', 'steps': []},
                             {'id': 2, 'name': 'python', 'conclusion': 'success', 'steps': job_steps(run['_full'])}]}
        self.list_calls.append(int(query['page']))
        per_page, page = int(query['per_page']), int(query['page'])
        return {'workflow_runs': [{k: v for k, v in r.items() if k != '_full'} for r in self.runs[(page - 1) * per_page:page * per_page]]}


class Repository:
    """A tiny repository: attested commit A, reviewed registry commit B (= pull request base), then changes."""

    def __init__(self, tmp):
        self.root = Path(tmp)
        git(self.root, 'init', '-q')
        write(self.root, 'scripts/__init__.py', '')
        write(self.root, 'scripts/pipe/__init__.py', '')
        write(self.root, 'scripts/pipe/entry.py',
              "from .helper import help\nfrom scripts.shared import tool\nPATH = 'data/processed/pipe/in.json'\n"
              "SPEC = 'docs/spec.txt'\nLOCK = 'requirements-boundaries.txt'\nKEY = 'electorates'\n\ndef arrays():\n    return 1\n")
        write(self.root, 'scripts/pipe/helper.py', 'def help():\n    return 1\n')
        write(self.root, 'scripts/pipe2/__init__.py', '')
        write(self.root, 'scripts/pipe2/entry.py', "from .helper import help2\nPATH = 'data/processed/pipe2/in.json'\n")
        write(self.root, 'scripts/pipe2/helper.py', 'def help2():\n    return 1\n')
        write(self.root, 'scripts/shared.py', 'def tool():\n    return 1\n')
        write(self.root, 'scripts/other/__init__.py', '')
        write(self.root, 'scripts/other/unrelated.py', 'X = 1\n')
        write(self.root, 'scripts/tests/test_x.py', 'X = 1\n')
        write(self.root, 'data/processed/pipe/in.json', '{}\n')
        write(self.root, 'data/processed/pipe2/in.json', '{}\n')
        write(self.root, 'data/processed/other/x.json', '{}\n')
        write(self.root, 'docs/spec.txt', 'spec\n')
        write(self.root, 'docs/a.md', 'notes\n')
        write(self.root, 'requirements-boundaries.txt', 'numpy==2.2.6\n')
        write(self.root, '.python-version', '3.12.2\n')
        write(self.root, '.github/workflows/ci.yml', WORKFLOW)
        self.attested = commit(self.root, 'attested')
        self.registry = registry_for()
        record = {'run': {'id': 1, 'html_url': 'https://example.test/runs/1', 'event': 'push', 'conclusion': 'success',
                          'head_sha': self.attested, 'created_at': '2026-10-01T00:00:00Z'},
                  'job': {'name': 'python', 'conclusion': 'success', 'steps': job_steps()}}
        write(self.root, '.github/validation/evidence/e.json', json.dumps(record))
        self.sha = hashlib.sha256((self.root / '.github/validation/evidence/e.json').read_bytes()).hexdigest()
        for name, pipeline in self.registry['pipelines'].items():
            files, literals, _ = frozen.closure(self.root, pipeline['entryModules'])
            pipeline['pin'] = {'commit': self.attested, 'runId': 1, 'runUrl': 'https://example.test/runs/1',
                               'createdAt': '2026-10-01T00:00:00Z', 'evidencePath': '.github/validation/evidence/e.json',
                               'evidenceSha256': self.sha, 'scopeFingerprint': frozen.scope_fingerprint(self.root, pipeline, files, literals)}
        write(self.root, '.github/validation/frozen-pipelines.json', json.dumps(self.registry))
        self.base = commit(self.root, 'registry (earlier reviewed pull request)')

    def without_pins(self, *names):
        registry = deepcopy(self.registry)
        for name in names or registry['pipelines']:
            del registry['pipelines'][name]['pin']
        return registry

    def discovery(self, api=None, registry=None):
        """API discovery over a fake API, or disabled (no token) when no API is given."""
        registry = registry or self.registry
        if api is None:
            return frozen.Discovery(registry, {}, root=self.root)
        return frozen.Discovery(registry, ENV, api, self.root, lambda root, sha: frozen.is_ancestor(root, sha))

    def select(self, event='pull_request', runtime=None, registry=None, candidates=None, discovery=None):
        registry = registry or self.registry
        return frozen.select_pipeline('pipe', registry, event, self.root, RUNTIME if runtime is None else runtime,
                                      candidates, discovery or self.discovery(registry=registry))

    def select_all(self, event='pull_request', registry=None, discovery=None):
        registry = registry or self.registry
        return frozen.select(registry, event, self.root, RUNTIME, discovery=discovery or self.discovery(registry=registry))

    def head(self):
        return git(self.root, 'rev-parse', 'HEAD')

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

    def test_a_new_top_level_directory_named_like_a_dictionary_key_is_not_a_dependency(self):
        """The site's route folders (`electorates/`, ...) share names with keys in pipeline code; adding them is no replay."""
        write(self.repo.root, 'electorates/index.html', '<!doctype html>\n')
        commit(self.repo.root, 'site route folder')
        self.assertEqual(self.repo.select()['mode'], 'integrity')
        files, literals, _ = frozen.closure(self.repo.root, ['scripts.pipe.entry'])
        self.assertNotIn('electorates', literals)
        self.assertIn('requirements-boundaries.txt', literals)
        write(self.repo.root, 'electorates/index.html', '<!doctype html><title>changed</title>\n')
        commit(self.repo.root, 'site route edited')
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

    def test_scheduled_workflow_outside_verify_does_not_force_replay(self):
        write(self.repo.root, '.github/workflows/poll-refresh.yml', 'name: Poll refresh\n')
        commit(self.repo.root, 'scheduled workflow')
        self.assertEqual(self.repo.select()['mode'], 'integrity')
        write(self.repo.root, '.github/workflows/full-replay.yml', 'name: Full replay\n')
        commit(self.repo.root, 'manual full replay workflow')
        self.assertEqual(self.repo.select()['mode'], 'integrity')
        # Any other workflow file still forces full.
        write(self.repo.root, '.github/workflows/other.yml', 'name: Other\n')
        commit(self.repo.root, 'another workflow')
        self.assertFull(self.repo.select(), 'CI configuration changed')
        # So does the exempt file once Verify names it.
        git(self.repo.root, 'reset', '-q', '--hard', self.repo.base)
        text = (self.repo.root / '.github/workflows/ci.yml').read_text()
        write(self.repo.root, '.github/workflows/ci.yml', text + '# calls poll-refresh.yml\n')
        write(self.repo.root, '.github/workflows/poll-refresh.yml', 'name: Poll refresh\n')
        commit(self.repo.root, 'verify names the scheduled workflow')
        self.assertFull(self.repo.select(), 'CI configuration changed')

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

    def test_handoff_fragments_and_their_fold_script_are_documentation_not_dependencies(self):
        write(self.repo.root, 'handoff.d/2026-10-06-x.md', '<!-- fold: changelog -->\n## X\n')
        write(self.repo.root, 'CHANGELOG.md', 'folded\n')
        write(self.repo.root, 'scripts/fold_doc_fragments.py', 'new\n')
        commit(self.repo.root, 'fragments')
        self.assertEqual(self.repo.select()['mode'], 'integrity')

    def test_non_pull_request_events_and_missing_history_are_full(self):
        for event in ('workflow_dispatch', 'schedule', 'unknown'):
            self.assertFull(self.repo.select(event), 'always uses full')
        self.assertEqual(self.repo.select('push')['mode'], 'integrity')
        registry = deepcopy(self.repo.registry)
        registry['pipelines']['pipe']['pin']['commit'] = '1' * 40
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
                       lambda r: next(x for x in r['job']['steps'] if x['name'] == 'Run ' + COMMAND).update(conclusion='skipped'),
                       lambda r: r['job']['steps'].remove(next(x for x in r['job']['steps'] if x['name'] == 'Run ' + COMMAND))):
            record = deepcopy(original)
            mutate(record)
            path.write_text(json.dumps(record))
            registry = deepcopy(self.repo.registry)
            registry['pipelines']['pipe']['pin']['evidenceSha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            commit(self.repo.root, 'tamper')
            self.assertFull(self.repo.select(registry=registry))
        self.assertFull(self.repo.select(), 'pinned attestation evidence missing or changed')

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
        pin, why = frozen.pin_candidate(self.repo.registry['pipelines']['pipe'], self.repo.root)
        self.assertIsNone(why)
        head = git(self.repo.root, 'rev-parse', 'HEAD')
        self.assertEqual(self.repo.select(candidates=[self.repo.live(head, skipped=True), pin])['mode'], 'integrity')
        self.assertFull(self.repo.select(candidates=[]), 'no attested')

    def test_dynamic_imports_cannot_be_analysed_and_force_full(self):
        write(self.repo.root, 'scripts/pipe/helper.py', 'import importlib\nimportlib.import_module("scripts.x")\n')
        commit(self.repo.root, 'dynamic')
        self.assertFull(self.repo.select())

    def test_reviewed_registry_with_unsupported_version_is_full(self):
        registry = deepcopy(self.repo.registry)
        registry['version'] = 1
        self.assertFull(self.repo.select(registry=registry), 'version')


class AttestationDurabilityTests(unittest.TestCase):
    """A genuine full attestation must not expire because newer unrelated runs exist."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(self.tmp.name)

    def later(self, text='later unrelated work\n'):
        write(self.repo.root, 'docs/a.md', text)
        return commit(self.repo.root, 'unrelated ' + text.strip())

    def reuse_only_runs(self, count, sha):
        return [run_record(100 + i, sha, full=False, event='push' if i % 2 else 'pull_request',
                           branch='main' if i % 2 else 'feature-{}'.format(i), created='2026-10-03T00:{:02d}:00Z'.format(i)) for i in range(count)][::-1]

    def test_one_full_attestation_followed_by_fifty_five_reuse_only_runs_still_selects_integrity(self):
        head = self.later()
        full = run_record(2, self.repo.attested, created='2026-10-02T00:00:00Z')
        runs = self.reuse_only_runs(55, head) + [full]
        # (a) the pin proves it from Git alone: the API is never touched, however many runs have happened since.
        api = FakeApi(runs, fail=AssertionError('the API must not be used while the pin proves reuse'))
        result = self.repo.select(discovery=self.repo.discovery(api))
        self.assertEqual(result['mode'], 'integrity', result)
        self.assertEqual((result['chosen']['source'], result['chosen']['runId']), ('pin', 1))
        self.assertEqual(api.calls, 0)
        # (b) with no pin, paginated discovery walks past every reuse-only run to the genuine full run.
        registry = self.repo.without_pins()
        api = FakeApi(runs)
        result = self.repo.select(registry=registry, discovery=self.repo.discovery(api, registry))
        self.assertEqual(result['mode'], 'integrity', result)
        self.assertEqual((result['chosen']['source'], result['chosen']['runId']), ('discovered-push', 2))
        self.assertEqual(len(api.job_calls), 56)
        self.assertEqual(api.list_calls, [1, 2, 3])  # 20 runs per page
        self.assertIn('discovered-push attestation', result['reason'])
        self.assertIn('run 2', result['reason'])

    def test_a_reuse_only_run_is_never_an_attestation(self):
        head = self.later()
        registry = self.repo.without_pins()
        api = FakeApi(self.reuse_only_runs(5, head))
        result = self.repo.select(registry=registry, discovery=self.repo.discovery(api, registry))
        self.assertEqual(result['mode'], 'full')
        self.assertIn('no reachable run executed every replaced command (5 examined)', result['reason'])

    def test_the_newest_applicable_full_run_wins_when_several_exist(self):
        self.later('b\n')
        newer = self.later('c\n')
        runs = [run_record(5, newer, full=False), run_record(3, newer, created='2026-10-02T09:00:00Z'),
                run_record(2, self.repo.attested, created='2026-10-02T01:00:00Z')]
        registry = self.repo.without_pins()
        api = FakeApi(runs)
        result = self.repo.select(registry=registry, discovery=self.repo.discovery(api, registry))
        self.assertEqual(result['mode'], 'integrity', result)
        self.assertEqual(result['chosen']['runId'], 3)
        self.assertEqual(api.job_calls, [5, 3])  # the older full run is never even requested

    def test_a_newer_full_run_beats_a_stale_pin_and_the_log_says_why(self):
        write(self.repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
        changed = commit(self.repo.root, 'modify frozen code')
        stale = self.repo.select()  # the pull request that modifies the pipeline replays it once
        self.assertEqual(stale['mode'], 'full', stale)
        self.assertIn('dependency changed', stale['reason'])
        runs = [run_record(8, changed, event='pull_request', branch='pr', created='2026-10-04T00:00:00Z')]
        result = self.repo.select(discovery=self.repo.discovery(FakeApi(runs)))
        self.assertEqual(result['mode'], 'integrity', result)
        self.assertEqual(result['chosen']['runId'], 8)
        self.assertIn('pin not used', result['reason'])
        self.assertIn('dependency changed: scripts/pipe/helper.py', result['reason'])

    def test_a_relevant_dependency_change_selects_full_even_with_the_attested_run_in_the_api(self):
        for path, text in (('scripts/pipe/helper.py', 'def help():\n    return 2\n'), ('scripts/shared.py', 'def tool():\n    return 9\n'),
                           ('data/processed/pipe/in.json', '{"a": 1}\n'), ('docs/spec.txt', 'changed\n')):
            with self.subTest(path=path):
                git(self.repo.root, 'reset', '-q', '--hard', self.repo.base)
                write(self.repo.root, path, text)
                head = commit(self.repo.root, 'change ' + path)
                runs = [run_record(5, head, full=False), run_record(2, self.repo.attested)]
                result = self.repo.select(discovery=self.repo.discovery(FakeApi(runs)))
                self.assertEqual(result['mode'], 'full', result)
                self.assertIn('changed: ' + path, result['reason'])

    def test_unchanged_pipe2_selects_integrity_without_forcing_pipe_full(self):
        self.later()
        result = self.repo.select_all()
        self.assertEqual({n: r['mode'] for n, r in result.items()}, {'pipe': 'integrity', 'pipe2': 'integrity'})
        self.assertEqual({r['chosen']['source'] for r in result.values()}, {'pin'})
        # pipe2 is unchanged even though pipe changed: the dependency runs the other way round, so no coupling.
        write(self.repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
        commit(self.repo.root, 'modify the cache-producing pipeline only')
        result = self.repo.select_all()
        self.assertEqual({n: r['mode'] for n, r in result.items()}, {'pipe': 'full', 'pipe2': 'integrity'})

    def test_pipe2_running_full_still_forces_the_pipelines_whose_cache_it_reads_full(self):
        write(self.repo.root, 'scripts/pipe2/helper.py', 'def help2():\n    return 2\n')
        commit(self.repo.root, 'modify the cache-reading pipeline')
        result = self.repo.select_all()
        self.assertEqual({n: r['mode'] for n, r in result.items()}, {'pipe': 'full', 'pipe2': 'full'})
        self.assertIn('pipe2 runs in full and reads the pipe runtime cache', result['pipe']['reason'])

    def test_losing_the_attestation_is_what_used_to_cascade_and_a_pin_prevents_it(self):
        head = self.later()
        runs = self.reuse_only_runs(55, head)  # the recency window that used to hold only reuse-only runs
        unpinned = self.repo.without_pins('pipe2')
        result = self.repo.select_all(registry=unpinned, discovery=self.repo.discovery(FakeApi(runs), unpinned))
        self.assertEqual({n: r['mode'] for n, r in result.items()}, {'pipe': 'full', 'pipe2': 'full'})
        self.assertIn('no pinned attestation', result['pipe2']['reason'])
        pinned = self.repo.select_all(discovery=self.repo.discovery(FakeApi(runs, fail=AssertionError('no API call'))))
        self.assertEqual({n: r['mode'] for n, r in pinned.items()}, {'pipe': 'integrity', 'pipe2': 'integrity'})

    def test_api_failure_falls_back_to_the_valid_pin(self):
        self.later()
        for failure in (OSError('network down'), ValueError('bad json'), KeyError('workflow_runs')):
            with self.subTest(failure=type(failure).__name__):
                api = FakeApi([], fail=failure)
                result = self.repo.select(discovery=self.repo.discovery(api))
                self.assertEqual(result['mode'], 'integrity', result)
                self.assertEqual(result['chosen']['source'], 'pin')
                self.assertEqual(api.calls, 0)

    def test_a_stale_pin_and_an_api_failure_select_full(self):
        write(self.repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
        commit(self.repo.root, 'modify frozen code')
        for failure in (OSError('network down'), ValueError('bad json'), KeyError('workflow_runs')):
            with self.subTest(failure=type(failure).__name__):
                result = self.repo.select(discovery=self.repo.discovery(FakeApi([], fail=failure)))
                self.assertEqual(result['mode'], 'full', result)
                self.assertIn('dependency changed', result['reason'])
                self.assertIn('Actions API failed', result['reason'])
        for malformed in ({}, {'workflow_runs': [{'id': 1}]}):
            api = lambda url, token, malformed=malformed: malformed
            result = self.repo.select(discovery=self.repo.discovery(api))
            self.assertEqual(result['mode'], 'full', result)
        self.assertIn('unavailable (no token or repository)', self.repo.select()['reason'])

    def test_discovery_is_bounded_and_fails_closed(self):
        head = self.later()
        registry = self.repo.without_pins()
        runs = self.reuse_only_runs(60, head)
        registry['liveAttestation']['maxJobFetches'] = 5
        api = FakeApi(runs)
        result = self.repo.select(registry=registry, discovery=self.repo.discovery(api, registry))
        self.assertEqual((result['mode'], len(api.job_calls)), ('full', 5))
        self.assertIn('job request bound (5) reached', result['reason'])
        registry['liveAttestation'].update(maxJobFetches=500, maxPages=1)
        api = FakeApi(runs)
        result = self.repo.select(registry=registry, discovery=self.repo.discovery(api, registry))
        self.assertEqual((result['mode'], api.list_calls), ('full', [1]))
        self.assertIn('page bound (1) reached', result['reason'])

    def test_unreachable_runs_cost_no_job_request(self):
        head = self.later()
        registry = self.repo.without_pins()
        stray = [run_record(200 + i, '9' * 40, event='pull_request', branch='gone') for i in range(30)]
        api = FakeApi(stray + [run_record(2, head), run_record(1, self.repo.attested)])
        result = self.repo.select(registry=registry, discovery=self.repo.discovery(api, registry))
        self.assertEqual(result['mode'], 'integrity', result)
        self.assertEqual(api.job_calls, [2])

    def test_a_manual_full_dispatch_of_main_attests_but_other_branches_do_not(self):
        head = self.later()
        registry = self.repo.without_pins()
        feature = run_record(7, head, event='workflow_dispatch', branch='feature')
        result = self.repo.select(registry=registry, discovery=self.repo.discovery(FakeApi([feature]), registry))
        self.assertEqual(result['mode'], 'full', result)
        main = run_record(6, head, event='workflow_dispatch', branch='main')
        api = FakeApi([feature, main])
        result = self.repo.select(registry=registry, discovery=self.repo.discovery(api, registry))
        self.assertEqual((result['mode'], result['chosen']['source'], result['chosen']['runId']), ('integrity', 'discovered-workflow_dispatch', 6))
        self.assertEqual(api.job_calls, [6])

    def test_discovery_stops_at_the_pinned_run(self):
        write(self.repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
        head = commit(self.repo.root, 'modify frozen code')
        pinned_run = run_record(1, self.repo.attested, created='2026-10-01T00:00:00Z')
        older = run_record(0, self.repo.attested, created='2026-09-30T00:00:00Z')
        api = FakeApi(self.reuse_only_runs(30, head) + [pinned_run, older])
        result = self.repo.select(discovery=self.repo.discovery(api))
        self.assertEqual(result['mode'], 'full', result)
        self.assertEqual(len(api.job_calls), 31)  # 30 reuse-only runs and the pinned run itself; nothing older
        self.assertNotIn(0, api.job_calls)
        self.assertIn('no full run newer than the pinned run', result['reason'])

    def test_a_pin_whose_scope_fingerprint_does_not_match_is_not_used(self):
        registry = deepcopy(self.repo.registry)
        registry['pipelines']['pipe']['pin']['scopeFingerprint'] = '0' * 64
        result = self.repo.select(registry=registry)
        self.assertEqual(result['mode'], 'full', result)
        self.assertIn('scope fingerprint differs', result['reason'])

    def test_the_selection_names_the_attestation_and_every_reason_for_full(self):
        self.later()
        result = self.repo.select()
        self.assertEqual(result['chosen'], {'source': 'pin', 'commit': self.repo.attested, 'runId': 1, 'runUrl': 'https://example.test/runs/1'})
        self.assertIn('pin attestation {} run 1'.format(self.repo.attested[:8]), result['reason'])
        write(self.repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
        commit(self.repo.root, 'modify')
        reason = self.repo.select()['reason']
        self.assertIn('pin attestation {} run 1: dependency changed: scripts/pipe/helper.py'.format(self.repo.attested[:8]), reason)
        self.assertIn(' | ', reason)  # the pin's reason, then why discovery could not help


class RecordPinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(self.tmp.name)
        write(self.repo.root, 'docs/a.md', 'later\n')
        self.head = commit(self.repo.root, 'later unrelated work')

    def test_recording_a_full_run_pins_every_pipeline_it_executed_and_selection_then_reuses_it(self):
        api = FakeApi([run_record(2, self.repo.attested, event='pull_request', branch='pr'), run_record(3, self.head, full=False)])
        registry, report = frozen.record_pin(2, self.repo.without_pins(), self.repo.root, environ=ENV, fetch=api)
        self.assertEqual(len(report), 2)
        for name in ('pipe', 'pipe2'):
            pin = registry['pipelines'][name]['pin']
            self.assertEqual((pin['commit'], pin['runId']), (self.repo.attested, 2))
            self.assertEqual(pin['evidencePath'], '.github/validation/evidence/frozen-run-2.json')
            evidence = (self.repo.root / pin['evidencePath']).read_bytes()
            self.assertEqual(hashlib.sha256(evidence).hexdigest(), pin['evidenceSha256'])
            # the fingerprint taken in a worktree at the pinned commit equals the one computed directly there
            self.assertEqual(pin['scopeFingerprint'], self.repo.registry['pipelines'][name]['pin']['scopeFingerprint'])
        self.assertEqual([(x['name'], x['conclusion']) for x in json.loads(evidence)['job']['steps']],
                         [(x['name'], x['conclusion']) for x in job_steps()])
        result = self.repo.select(registry=registry)
        self.assertEqual((result['mode'], result['chosen']['runId']), ('integrity', 2))
        self.assertFalse((self.repo.root / '.git/worktrees').exists() and list((self.repo.root / '.git/worktrees').iterdir()))

    def test_recording_refuses_runs_that_did_not_execute_the_pipeline_or_are_unreachable(self):
        api = FakeApi([run_record(3, self.head, full=False), run_record(4, '9' * 40)])
        registry, report = frozen.record_pin(3, self.repo.without_pins(), self.repo.root, environ=ENV, fetch=api)
        self.assertEqual(registry, self.repo.without_pins())
        self.assertTrue(all('not pinned (attested run did not execute successfully' in line for line in report), report)
        self.assertFalse((self.repo.root / '.github/validation/evidence/frozen-run-3.json').exists())
        with self.assertRaises(ValueError):
            frozen.record_pin(4, self.repo.without_pins(), self.repo.root, environ=ENV, fetch=api)


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
            result = frozen.select(broken, 'pull_request', repo.root, RUNTIME, discovery=repo.discovery())
            self.assertEqual(result['pipe']['mode'], 'full')
            self.assertIn('invalid selection inputs', result['pipe']['reason'])

    def test_verify_refuses_when_reuse_is_not_proven(self):
        with TemporaryDirectory() as tmp:
            repo = Repository(tmp)
            write(repo.root, 'scripts/pipe/helper.py', 'def help():\n    return 2\n')
            commit(repo.root, 'change')
            with patch.object(frozen, 'runtime_errors', return_value=[]), patch.dict(os.environ, NO_TOKEN):
                with self.assertRaises(ValueError):
                    frozen.verify('pipe', root=repo.root)

    def test_verify_runs_integrity_checks_when_reuse_is_proven(self):
        with TemporaryDirectory() as tmp:
            repo = Repository(tmp)
            registry = deepcopy(repo.registry)
            registry['pipelines']['pipe']['integrityChecks'] = ['scripts.validate.ci_frozen:load_registry']
            write(repo.root, '.github/validation/frozen-pipelines.json', json.dumps(registry))
            base = commit(repo.root, 'registry with integrity check')
            with patch.object(frozen, 'runtime_errors', return_value=[]), patch.dict(os.environ, NO_TOKEN), \
                    patch.object(frozen, 'load_registry', return_value=registry) as loaded:
                result = frozen.verify('pipe', root=repo.root)
            self.assertEqual(result['mode'], 'integrity')
            self.assertTrue(loaded.called)

    def test_command_line_writes_one_output_per_registered_pipeline(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            printed = StringIO()
            with patch('sys.argv', ['ci_frozen', '--event', 'push', '--github-output', str(output)]), \
                    patch.dict(os.environ, NO_TOKEN), redirect_stdout(printed):
                frozen.main()
            # one human-readable line per pipeline: its mode and the attestation chosen or every reason for full
            for name in ('stage45', 'stage46', 'stage47', 'stage48', 'stage54', 'stage63'):
                self.assertRegex(printed.getvalue(), r'(?m)^{}: (full|integrity) - .+'.format(name))
            lines = sorted(output.read_text().split())
            self.assertEqual([line.split('=')[0] for line in lines], ['stage45', 'stage46', 'stage47', 'stage48', 'stage54', 'stage63'])
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
            self.assertTrue(any(part in command for part in ('construction', 'evaluation', 'verification', 'mean_audit', 'audits', 'attribution')))
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

    def test_every_registered_pipeline_has_a_pin_that_proves_its_own_full_run(self):
        """Each pin's evidence shows its pipeline's replaced commands executed successfully in one full run."""
        for name, pipeline in self.registry['pipelines'].items():
            pin, why = frozen.pin_candidate(pipeline, ROOT)
            self.assertIsNone(why, name)
            self.assertEqual(pin['record']['run']['id'], pin['runId'], name)
            self.assertEqual(pin['record']['run']['head_sha'], pin['commit'], name)
            self.assertRegex(pin['fingerprint'], '^[0-9a-f]{64}$', name)
            errors, steps = frozen.candidate_errors(pin, pipeline['replacedCommands'])
            self.assertEqual(errors, [], name)
            self.assertEqual(frozen.workflow_errors(ROOT, steps, self.registry), [], name)
            self.assertNotIn('Verify previously validated Stage39 sealed integrity', steps)
            durations = {step['name']: step for step in pin['record']['job']['steps']}
            for command in pipeline['replacedCommands']:
                self.assertEqual(durations['Run ' + command]['conclusion'], 'success', command)
            try:
                subprocess.check_output(['git', 'cat-file', '-e', pin['commit'] + '^{commit}'], cwd=ROOT, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                continue  # shallow checkout: the pin commit is simply not present, which fails closed at selection time

    def test_pins_cover_every_registered_pipeline_and_cache_dependencies_are_pinned_consistently(self):
        for name, pipeline in self.registry['pipelines'].items():
            self.assertIn('pin', pipeline, name)
            for dependency in pipeline.get('cacheDependencies', []):
                self.assertIn(dependency, self.registry['pipelines'])
        self.assertEqual(self.registry['version'], frozen.REGISTRY_VERSION)
        self.assertNotIn('maxRuns', self.registry['liveAttestation'])  # recency windows are not how reuse is decided

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
        self.assertIn('timeout-minutes: 180', self.workflow)
        self.assertIn('timeout-minutes: 20', self.workflow)
        self.assertIn('GITHUB_TOKEN: ${{ github.token }}', self.workflow)

    def test_stage47_declares_the_caches_it_reads_and_couples_the_dependencies(self):
        stage47 = self.registry['pipelines']['stage47']
        self.assertEqual(stage47['cacheDependencies'], ['stage45', 'stage46'])
        for name in stage47['cacheDependencies']:
            for consumer in self.registry['pipelines'][name]['reviewedCacheConsumers']:
                self.assertTrue(consumer.startswith('scripts/uncertainty_expectation/'), consumer)
                self.assertTrue((ROOT / consumer).is_file())

    def test_a_full_pipeline_forces_its_cache_dependencies_full_but_not_the_reverse(self):
        registry = {'pipelines': {'a': {'cacheDependencies': ['b']}, 'b': {}, 'c': {}}}
        reused = {'mode': 'integrity', 'reason': 'x'}
        full = {'mode': 'full', 'reason': 'y'}
        coupled = frozen.couple_cache_dependencies(registry, {'a': dict(full), 'b': dict(reused), 'c': dict(reused)})
        self.assertEqual([coupled[n]['mode'] for n in 'abc'], ['full', 'full', 'integrity'])
        self.assertIn('a runs in full', coupled['b']['reason'])
        coupled = frozen.couple_cache_dependencies(registry, {'a': dict(reused), 'b': dict(full), 'c': dict(reused)})
        self.assertEqual([coupled[n]['mode'] for n in 'abc'], ['integrity', 'full', 'integrity'])

    def test_cache_dependencies_couple_transitively_whatever_the_registry_order(self):
        registry = {'pipelines': {'c': {}, 'b': {'cacheDependencies': ['c']}, 'a': {'cacheDependencies': ['b']}, 'd': {}}}
        reused = {'mode': 'integrity', 'reason': 'x'}
        coupled = frozen.couple_cache_dependencies(registry, {
            'a': {'mode': 'full', 'reason': 'y'}, 'b': dict(reused), 'c': dict(reused), 'd': dict(reused)})
        self.assertEqual([coupled[n]['mode'] for n in 'abcd'], ['full', 'full', 'full', 'integrity'])
        self.assertIn('b runs in full', coupled['c']['reason'])

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
