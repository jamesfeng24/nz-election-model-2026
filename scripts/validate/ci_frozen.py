"""Dependency-aware reuse of previously validated frozen pipelines; full validation is the default.

A pull request or main push may skip the expensive ``--check`` reconstruction of a registered frozen pipeline
only when the exact tree under validation is provably equivalent, for that pipeline, to a commit whose complete
Linux Verify run already passed *with that reconstruction executed*. Equivalence is established from Git, not
from generated manifests: no file in the pipeline's static import closure, referenced data paths, outputs or
environment files differs from the attested commit, no existing data file changed, no unreviewed consumer reads
the pipeline's runtime cache, no validation was removed from the workflow, and the runner matches the attested
runtime. Whenever any of that changes, the pipeline runs in full once.

Attestations never expire because newer unrelated runs exist. Each pipeline carries a durable **pin** in the
registry (commit, run id, evidence hash, scope fingerprint of the proved scope), checked first and Git-only; the
Actions API is consulted only when the pin is stale, and then the walk over successful reachable Verify runs is
per pipeline: it skips reuse-only runs and stops at the pinned run. Without a valid pin or API the answer is
full. A reuse-only run is never an attestation. Manual dispatch never reuses anything. Behavioural unit tests
are never skipped.
"""
import argparse
import ast
import hashlib
import importlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import urllib.request
from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = '.github/validation/frozen-pipelines.json'
WORKFLOW = '.github/workflows/ci.yml'
# Python environment files: any change forces full validation of every registered pipeline.
ENVIRONMENT = ('.python-version', 'pyproject.toml', 'requirements-boundaries.txt', 'requirements-external.lock',
               'requirements-polling.lock')
# Top-level directories that a bare string literal (no slash) in pipeline code may name as a whole-directory dependency.
SOURCE_DIRECTORIES = ('config', 'data', 'docs', 'scripts', 'src')
# CI selection machinery and policy files: they are not pipeline dependencies, so edits to them neither force a replay
# nor count as a pipeline change. They are guarded instead by the selector's own always-run unit tests and by
# ``workflow_errors`` (no attested validation may be removed or newly conditioned).
MACHINERY = ('.github/validation/', 'scripts/validate/ci_', 'AGENTS.md')
# Workflows that Verify never calls: the scheduled poll refresh (D120), the manual Full replay, whose commands
# are read from ci.yml, and the Publish workflow, which builds a release and pushes it. They cannot change what
# Verify executes, so adding or editing them is not a CI-configuration change; any other `.github/` path still is. The exemption lapses if ci.yml names the file (see
# ``non_verify_workflow``).
NON_VERIFY_WORKFLOWS = ('.github/workflows/poll-refresh.yml', '.github/workflows/full-replay.yml', '.github/workflows/publish.yml')
KNOWN = ('stage45', 'stage46', 'stage47', 'stage48', 'stage54', 'stage63')
EVENTS = ('pull_request', 'push')  # workflow_dispatch and anything unknown are always full
ATTESTING_EVENTS = ('pull_request', 'push', 'workflow_dispatch')  # a manual full dispatch of main is a valid reference
REGISTRY_VERSION = 4


def git(root, *args):
    return subprocess.check_output(('git',) + args, cwd=root, stderr=subprocess.DEVNULL)


def load_registry(root=ROOT):
    return json.loads((Path(root) / REGISTRY).read_text())


# ---------------------------------------------------------------- static dependency closure

def module_file(root, name):
    base = Path(root).joinpath(*name.split('.'))
    if base.with_suffix('.py').is_file():
        return base.with_suffix('.py')
    if (base / '__init__.py').is_file():
        return base / '__init__.py'
    return None


def imported_names(tree, parts, is_package):
    """Absolute (module, imported-name-or-None) pairs; relative imports are resolved."""
    package = parts if is_package else parts[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, None
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ''
            if node.level:
                base = '.'.join(package[:len(package) - node.level + 1] + ([node.module] if node.module else []))
            for alias in node.names:
                yield base, alias.name


def closure(root, entries):
    """Repository-local import closure, string-literal path dependencies, and dynamic-import errors."""
    root = Path(root)
    tops = {p.name for p in root.iterdir() if not p.name.startswith('.')} | {'.python-version'}
    modules, paths, errors, stack = {}, set(), [], list(entries)
    while stack:
        name = stack.pop()
        if name in modules:
            continue
        file = module_file(root, name)
        if file is None:
            continue
        modules[name] = file.relative_to(root).as_posix()
        parts = name.split('.')
        stack.extend('.'.join(parts[:i]) for i in range(1, len(parts)))
        tree = ast.parse(file.read_text(), filename=str(file))
        for module, imported in imported_names(tree, parts, file.name == '__init__.py'):
            stack.append(module)
            if imported:
                stack.append(module + '.' + imported)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                called = func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', '')
                if called in ('__import__', 'import_module', 'run_module', 'run_path'):
                    errors.append('dynamic import in ' + name)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.strip()
                if not value or ' ' in value or '\n' in value or len(value) > 200 or value.startswith('/'):
                    continue
                segments = [s for s in value.split('/') if s]
                if value in tops and '/' not in value:
                    # A bare name is a dependency when it is a top-level file, or a source directory a pipeline could read
                    # whole. Other top-level directories (the site's route folders such as `electorates/`) share their
                    # names with dictionary keys in pipeline code and are never read by a replay.
                    if value in SOURCE_DIRECTORIES or not (root / value).is_dir():
                        paths.add(value)
                elif len(segments) >= 2 and segments[0] in tops and segments[0] != '.cache':
                    if segments[0] == 'data' and len(segments) < 3:
                        continue
                    paths.add('/'.join(segments))
    return sorted(set(modules.values())), sorted(paths), errors


def under(path, prefix):
    prefix = prefix.rstrip('/')
    return path == prefix or path.startswith(prefix + '/')


# ---------------------------------------------------------------- evidence, runtime, changes

def pin_candidate(pipeline, root):
    """The pipeline's durable pinned full attestation: (candidate, error). Git-only, no API."""
    pin = pipeline.get('pin')
    if not pin:
        return None, 'no pinned attestation'
    path = Path(root) / pin['evidencePath']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != pin['evidenceSha256']:
        return None, 'pinned attestation evidence missing or changed'
    try:
        record = json.loads(path.read_text())
    except ValueError:
        return None, 'pinned attestation evidence unreadable'
    return {'commit': pin['commit'], 'source': 'pin', 'runId': pin['runId'], 'runUrl': pin.get('runUrl'),
            'createdAt': pin.get('createdAt'), 'fingerprint': pin.get('scopeFingerprint'), 'record': record}, None


def scope_fingerprint(root, pipeline, files, literals, rev='HEAD'):
    """SHA-256 over the git blob ids of everything a replay of this pipeline can read, at ``rev``.

    The scope is the static import closure, referenced literal paths, owned and output paths, extra
    dependencies and the Python environment files. It records what a pin proved; a pin is only used while the
    tree under validation has the same fingerprint.
    """
    paths = sorted(set(files) | set(ENVIRONMENT) | set(literals) | set(pipeline['outputPaths'])
                   | set(pipeline['ownedPaths']) | set(pipeline['extraDependencies']))
    return hashlib.sha256(git(root, 'ls-tree', '-r', '-z', rev, '--', *paths)).hexdigest()


def fetch_json(url, token):
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token, 'X-GitHub-Api-Version': '2022-11-28',
                                                   'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def is_ancestor(root, commit):
    try:
        git(root, 'merge-base', '--is-ancestor', commit, 'HEAD')
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def run_candidate(run, job):
    """A discovered attestation record shaped like a pin's evidence."""
    return {'commit': run['head_sha'], 'source': 'discovered-' + run['event'], 'runId': run.get('id'),
            'runUrl': run.get('html_url'), 'createdAt': run.get('created_at'), 'record': {
                'run': {key: run.get(key) for key in ('id', 'html_url', 'event', 'conclusion', 'head_sha', 'created_at')},
                'job': {key: job.get(key) for key in ('id', 'name', 'conclusion', 'steps')}}}


class Discovery:
    """Lazy, memoised, newest-first walk over successful reachable Verify runs (the Actions API).

    Used only when a pipeline's pin does not prove reuse. Runs whose head commit is not an ancestor of the tree
    under validation are skipped without a job request; every other run costs one job request, bounded by
    ``maxJobFetches`` and ``maxPages``. Any API, parse or network problem ends the walk and is remembered, so
    callers see "no candidate" with the reason and the answer stays full. Main push runs, pull-request runs and
    manual dispatches of main all count; a reuse-only run is skipped by ``newest_full`` because its python job did
    not execute every replaced command.
    """

    def __init__(self, registry, environ=None, fetch=fetch_json, root=ROOT, ancestor=is_ancestor):
        environ = os.environ if environ is None else environ
        self.config = registry.get('liveAttestation') or {}
        self.repository = environ.get('GITHUB_REPOSITORY')
        self.token = environ.get('GITHUB_TOKEN') or environ.get('GH_TOKEN')
        self.api = environ.get('GITHUB_API_URL', 'https://api.github.com') + '/repos/{}/actions/'.format(self.repository)
        self.fetch, self.root, self.ancestor = fetch, root, ancestor
        self.enabled = bool(self.config and self.repository and self.token)
        self.seen, self.done, self.error, self.bound, self.walker = [], not self.enabled, None, None, None

    def eligible(self, run):
        branch_ok = run.get('event') == 'pull_request' or run.get('head_branch') == self.config['branch']
        return run.get('event') in ATTESTING_EVENTS and run.get('conclusion', 'success') == 'success' and branch_ok

    def walk(self):
        per_page, jobs_fetched = self.config.get('perPage', 100), 0
        for page in range(1, self.config.get('maxPages', 10) + 1):
            runs = self.fetch(self.api + 'workflows/{}/runs?status=success&per_page={}&page={}'.format(
                self.config['workflow'], per_page, page), self.token)['workflow_runs']
            for run in runs:
                if not self.eligible(run) or not self.ancestor(self.root, run['head_sha']):
                    continue
                if jobs_fetched >= self.config.get('maxJobFetches', 120):
                    self.bound = 'job request bound ({}) reached'.format(self.config.get('maxJobFetches', 120))
                    return
                jobs_fetched += 1
                for job in self.fetch(self.api + 'runs/{}/jobs?per_page=100'.format(run['id']), self.token)['jobs']:
                    if job['name'] == self.config['job']:
                        yield run_candidate(run, job)
            if len(runs) < per_page:
                return
        self.bound = 'page bound ({}) reached'.format(self.config.get('maxPages', 10))

    def candidates(self):
        index = 0
        while True:
            if index < len(self.seen):
                index += 1
                yield self.seen[index - 1]
                continue
            if self.done:
                return
            self.walker = self.walker or self.walk()
            try:
                self.seen.append(next(self.walker))
            except StopIteration:
                self.done = True
            except (OSError, ValueError, KeyError, TypeError) as error:
                self.done, self.error = True, '{}: {}'.format(type(error).__name__, error)

    def newest_full(self, pipeline, stop=None):
        """(newest reachable run whose python job executed every replaced command, None) or (None, why not)."""
        if not self.enabled:
            return None, 'Actions API discovery unavailable (no token or repository)'
        for candidate in self.candidates():
            if stop and (candidate['runId'] == stop.get('runId')
                         or (stop.get('createdAt') and (candidate.get('createdAt') or '') <= stop['createdAt'])):
                return None, 'no full run newer than the pinned run among {} reachable runs examined'.format(len(self.seen))
            if not candidate_errors(candidate, pipeline['replacedCommands'])[0]:
                return candidate, None
        if self.error:
            return None, 'Actions API failed after {} reachable runs examined ({})'.format(len(self.seen), self.error)
        if self.bound:
            return None, 'no full run among {} reachable runs examined; {}'.format(len(self.seen), self.bound)
        return None, 'no reachable run executed every replaced command ({} examined)'.format(len(self.seen))


def candidate_errors(candidate, required):
    """(errors, successful step names) for one attested run record and one pipeline's replaced commands."""
    try:
        run, job = candidate['record']['run'], candidate['record']['job']
        steps = {step['name']: step['conclusion'] for step in job['steps']}
    except (KeyError, TypeError):
        return ['unreadable attestation evidence'], []
    errors = []
    if run.get('event') not in ATTESTING_EVENTS or run.get('conclusion') != 'success' \
            or run.get('head_sha') != candidate['commit']:
        errors.append('attested run is not a successful full run of the attested commit')
    if job.get('conclusion') != 'success' or job.get('name') != 'python':
        errors.append('attested python job did not succeed')
    for command in required:
        if steps.get('Run ' + command) != 'success':
            errors.append('attested run did not execute successfully: ' + command)
    return errors, [name for name, conclusion in steps.items() if conclusion == 'success']


def runtime_errors(expected, actual=None):
    if actual is None:
        actual = {'python': sys.version.split()[0], 'system': platform.system(), 'machine': platform.machine(),
                  'packages': {}}
        for package in expected['packages']:
            try:
                actual['packages'][package] = version(package)
            except PackageNotFoundError:
                actual['packages'][package] = None
        if actual['system'] == 'Linux':
            release = platform.freedesktop_os_release()
            actual.update(osId=release.get('ID'), osVersionId=release.get('VERSION_ID'))
    return ['unattested runtime: ' + key for key in expected if key != 'note' and actual.get(key) != expected[key]]


def changed_files(root, commit, ancestor=True):
    """(status, path) pairs between a commit and the tree under validation, or None if not provable."""
    try:
        git(root, 'cat-file', '-e', commit + '^{commit}')
        if git(root, 'status', '--porcelain', '--untracked-files=no').strip():
            return None
        if ancestor:
            git(root, 'merge-base', '--is-ancestor', commit, 'HEAD')
        raw = git(root, 'diff', '--name-status', '-z', '--no-renames', commit, 'HEAD').split(b'\0')
        return [(raw[i].decode(), raw[i + 1].decode()) for i in range(0, len(raw) - 1, 2)]
    except (subprocess.CalledProcessError, OSError, UnicodeDecodeError):
        return None


def workflow_errors(root, steps, registry):
    """Every command that passed in the attested run must still run, ungated except by a registered reuse gate.

    Compares against the attested run's recorded steps rather than against an older workflow file, so action
    bumps, extra steps and later stages never invalidate reuse, while removed, weakened or newly conditioned
    validation does.
    """
    try:
        lines = (Path(root) / WORKFLOW).read_text().splitlines()
    except OSError:
        return ['CI workflow unreadable']
    blocks, i = {}, 0
    while i < len(lines):
        match = re.match(r'^      - run: (.+?) *$', lines[i])
        i += 1
        if match:
            attributes = []
            while i < len(lines) and lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) > 6:
                attributes.append(lines[i].strip())
                i += 1
            blocks.setdefault(match.group(1), []).append(attributes)
    gates = {}
    for name, pipeline in registry['pipelines'].items():
        for command in pipeline['replacedCommands']:
            gates[command] = "if: steps.frozen.outputs.{} != 'integrity'".format(name)
    errors = []
    for step in steps:
        if not step.startswith('Run python3 '):
            continue
        command = step[len('Run '):]
        allowed = {gates.get(command)}
        if 'scripts.polling.candidate_integration.' in command:
            allowed.add("if: steps.stage39.outputs.mode != 'integrity'")
        present = blocks.get(command)
        if not present:
            errors.append('attested validation step removed from workflow: ' + command)
        elif any(a and (len(a) != 1 or a[0] not in allowed) for a in present):
            errors.append('attested validation step newly conditioned: ' + command)
    return errors


def cache_consumers(root, pipeline):
    """Files outside the pipeline that read its runtime cache (a skipped reconstruction would starve them)."""
    root, found = Path(root), []
    owned = pipeline['ownedPaths'] + pipeline.get('reportPaths', [])
    readers = set(pipeline['cacheReaderModules'])
    reader_names = set(pipeline['cacheReaderNames'])
    for file in sorted((root / 'scripts').rglob('*.py')):
        relative = file.relative_to(root).as_posix()
        if relative.startswith('scripts/tests/') or any(under(relative, owned_path) for owned_path in owned):
            continue
        text = file.read_text()
        if pipeline['cacheDirectory'] in text and ast_has_string(text, pipeline['cacheDirectory']):
            found.append(relative)
            continue
        parts = relative[:-3].split('/')
        for module, imported in imported_names(ast.parse(text), parts, file.name == '__init__.py'):
            if module in readers and (imported is None or imported in reader_names or imported == '*'):
                found.append(relative)
                break
            if module + '.' + (imported or '') in readers:
                found.append(relative)
                break
    return [path for path in found if path not in pipeline.get('reviewedCacheConsumers', [])]


def ast_has_string(text, needle):
    return any(isinstance(node, ast.Constant) and isinstance(node.value, str) and needle in node.value
               for node in ast.walk(ast.parse(text)))


# ---------------------------------------------------------------- selection

def describe(candidate):
    run = ' run {}'.format(candidate['runId']) if candidate.get('runId') else ''
    return '{} attestation {}{}'.format(candidate['source'], candidate['commit'][:8], run)


def chosen(candidate):
    return {key: candidate.get(key) for key in ('source', 'commit', 'runId', 'runUrl')}


def select_pipeline(name, registry, event, root=ROOT, actual_runtime=None, candidates=None, discovery=None):
    """Pick the attestation that proves reuse of one pipeline, or full with every reason it was rejected.

    1. The pipeline's durable pin, Git-only: no API call, no dependence on how recent the attested run is.
    2. Only if the pin does not prove reuse: the newest reachable Verify run (API, paginated, reuse-only runs
       skipped, stopping at the pinned run) whose python job executed every replaced command.
    ``candidates`` (an explicit newest-first list) bypasses both and is used to re-prove a recorded selection.
    """
    if event not in EVENTS:
        return {'mode': 'full', 'reason': 'manual/unknown event always uses full validation'}
    if registry.get('version') != REGISTRY_VERSION:
        return {'mode': 'full', 'reason': 'unsupported registry version'}
    runtime = runtime_errors(registry['runtime'], actual_runtime)
    if runtime:
        return {'mode': 'full', 'reason': '; '.join(runtime[:4])}
    pipeline = registry['pipelines'][name]
    if candidates is not None:
        reasons = []
        for candidate in candidates:
            result = select_against(name, registry, root, candidate)
            if result['mode'] == 'integrity':
                return result
            reasons.append(result['reason'])
        return {'mode': 'full', 'reason': ' | '.join(reasons[:2]) or 'no attested full run available'}
    reasons = []
    pin, why = pin_candidate(pipeline, root)
    if pin:
        result = select_against(name, registry, root, pin)
        if result['mode'] == 'integrity':
            return result
        reasons.append(result['reason'])
    else:
        reasons.append(why)
    discovery = discovery or Discovery(registry, root=root)
    found, note = discovery.newest_full(pipeline, pin)
    if found is None:
        reasons.append(note)
        return {'mode': 'full', 'reason': ' | '.join(reasons)}
    result = select_against(name, registry, root, found)
    if result['mode'] == 'integrity':
        result['reason'] += ' [pin not used: {}]'.format(reasons[0])
        return result
    reasons.append(result['reason'])
    return {'mode': 'full', 'reason': ' | '.join(reasons)}


def non_verify_workflow(root, path):
    """True for a registered scheduled workflow that the Verify workflow does not reference."""
    if path not in NON_VERIFY_WORKFLOWS:
        return False
    try:
        return Path(path).name not in (Path(root) / WORKFLOW).read_text()
    except OSError:
        return False


def select_against(name, registry, root, candidate):
    pipeline = registry['pipelines'][name]
    commit = candidate['commit']

    def full(reason):
        return {'mode': 'full', 'reason': '{}: {}'.format(describe(candidate), reason)}
    errors, steps = candidate_errors(candidate, pipeline['replacedCommands'])
    if not errors:
        errors = workflow_errors(root, steps, registry)
    if errors:
        return full('; '.join(errors[:4]))
    changes = changed_files(root, commit)
    if changes is None:
        return full('attested commit unavailable, not an ancestor, or working tree dirty')
    try:
        files, literals, dynamic = closure(root, pipeline['entryModules'])
    except (SyntaxError, OSError, ValueError) as error:
        return full('cannot analyse dependency closure: ' + str(error))
    if dynamic:
        return full('; '.join(dynamic[:3]))
    if not files:
        return full('pipeline entry modules not present')
    watched = set(files) | set(ENVIRONMENT)
    prefixes = set(literals) | set(pipeline['outputPaths']) | set(pipeline['ownedPaths']) | set(pipeline['extraDependencies'])
    for status, path in changes:
        if path == WORKFLOW:
            continue  # judged by workflow_errors above, against the steps that actually passed
        if any(path.startswith(m) for m in MACHINERY):
            continue  # not a pipeline dependency; guarded by always-run selector tests and workflow_errors
        if non_verify_workflow(root, path):
            continue  # scheduled workflow outside Verify; cannot change what Verify runs
        if path in watched:
            return full('dependency changed: ' + path)
        if any(under(path, prefix) for prefix in prefixes):
            return full('referenced path changed: ' + path)
        if path.startswith('data/') and status != 'A' and not path.endswith('.md'):
            return full('existing data file changed: ' + path)
        if path.startswith('.github/'):
            return full('CI configuration changed: ' + path)
    consumers = cache_consumers(root, pipeline)
    if consumers:
        return full('unreviewed reader of this pipeline runtime cache: ' + ', '.join(consumers[:3]))
    if candidate.get('fingerprint') and scope_fingerprint(root, pipeline, files, literals) != candidate['fingerprint']:
        return full('scope fingerprint differs from the one the pin recorded')
    return {'mode': 'integrity', 'reason': 'reusing the {}: dependency scope unchanged since that full run '
            '({} files in closure, {} changed paths outside it)'.format(describe(candidate), len(files), len(changes)),
            'closureFiles': len(files), 'changedPaths': len(changes), 'attestation': candidate, 'chosen': chosen(candidate)}


def select(registry, event, root=ROOT, actual_runtime=None, force_full=False, discovery=None):
    if force_full:
        return {name: {'mode': 'full', 'reason': 'explicit full validation requested'} for name in registry['pipelines']}
    discovery = discovery or Discovery(registry, root=root)  # lazy: no request unless a pin fails to prove reuse
    result = {}
    for name in registry['pipelines']:
        try:
            result[name] = select_pipeline(name, registry, event, root, actual_runtime, discovery=discovery)
        except (KeyError, ValueError, TypeError, OSError) as error:
            result[name] = {'mode': 'full', 'reason': 'invalid selection inputs: ' + str(error)}
    return couple_cache_dependencies(registry, result)


def couple_cache_dependencies(registry, result):
    """A pipeline that runs in full and reads another pipeline's runtime cache needs that pipeline's full replay too.

    Registry `cacheDependencies` names those pipelines; a dependency reused as `integrity` would leave its
    uncommitted cache absent for the consumer's full commands.
    """
    changed = True
    while changed:  # iterate to a fixed point so a dependency's own cacheDependencies are coupled too
        changed = False
        for name, pipeline in registry['pipelines'].items():
            if result[name]['mode'] == 'full':
                for dependency in pipeline.get('cacheDependencies', []):
                    if result[dependency]['mode'] != 'full':
                        result[dependency] = {'mode': 'full', 'reason': '{} runs in full and reads the {} runtime cache'.format(name, dependency)}
                        changed = True
    return result


def verify(name, event='pull_request', root=ROOT, result_file=None):
    """Lightweight check for a pipeline whose full reconstruction was legitimately skipped.

    Re-proves the selection against the very attestation the selector recorded (no network), then runs the
    pipeline's own consumed-input and prior-artifact verification and parses every committed output.
    """
    registry = load_registry(root)
    candidates = None
    if result_file:
        recorded = json.loads(Path(result_file).read_text())[name]
        candidates = [recorded['attestation']] if recorded['mode'] == 'integrity' else []
    result = select_pipeline(name, registry, event, root, candidates=candidates)
    if result['mode'] != 'integrity':
        raise ValueError('{} is not reusable ({}); the full commands must run'.format(name, result['reason']))
    for target in registry['pipelines'][name]['integrityChecks']:
        module, function = target.split(':')
        getattr(importlib.import_module(module), function)()
    for output in registry['pipelines'][name]['outputPaths']:
        folder = Path(root) / output
        for file in sorted(folder.rglob('*.json')) if folder.is_dir() else []:
            json.loads(file.read_text())
    return result


REPOSITORY = 'jamesfeng24/nz-election-model-2026'
EVIDENCE_DIRECTORY = '.github/validation/evidence'


def record_pin(run_id, registry, root=ROOT, names=None, environ=None, fetch=fetch_json):
    """Pin one successful Verify run as the durable attestation of every pipeline it fully validated.

    Reads the run and its python job from the Actions API, writes the evidence file (the run, the job and every
    step with its conclusion and timestamps), fingerprints each pipeline's scope **at the run's own commit** in a
    temporary worktree and returns ``(updated registry, report lines)``. A pipeline is pinned only if the run is a
    successful push, pull-request or manual run whose head is an ancestor of HEAD and whose python job executed
    every one of its replaced commands successfully; any other pipeline is left unchanged and reported. Nothing
    here is needed for correctness (discovery finds the newest full run on its own); a pin only makes reuse
    independent of the API and of how many runs have happened since.
    """
    environ = os.environ if environ is None else environ
    token = environ.get('GITHUB_TOKEN') or environ.get('GH_TOKEN') or ''
    api = '{}/repos/{}/actions/'.format(environ.get('GITHUB_API_URL', 'https://api.github.com'),
                                         environ.get('GITHUB_REPOSITORY', REPOSITORY))
    run = fetch(api + 'runs/{}'.format(run_id), token)
    jobs = [job for job in fetch(api + 'runs/{}/jobs?per_page=100&filter=latest'.format(run_id), token)['jobs']
            if job['name'] == registry['liveAttestation']['job']]
    if len(jobs) != 1:
        raise ValueError('run {} has no unique {} job'.format(run_id, registry['liveAttestation']['job']))
    candidate = run_candidate(run, jobs[0])
    if not is_ancestor(root, candidate['commit']):
        raise ValueError('run {} head {} is not an ancestor of HEAD'.format(run_id, candidate['commit']))
    evidence = {'description': 'Subset of the GitHub Actions API records of the successful Verify run {} (head {}): the run, '
                'its python job and every step with its conclusion and timestamps. The live API records are the source of '
                'truth; this copy pins the step conclusions the reuse registry relies on.'.format(run_id, candidate['commit']),
                'run': candidate['record']['run'],
                'job': {**candidate['record']['job'], 'completed_at': jobs[0].get('completed_at'), 'started_at': jobs[0].get('started_at'),
                        'steps': [{key: step.get(key) for key in ('name', 'conclusion', 'started_at', 'completed_at')}
                                  for step in jobs[0]['steps']]},
                'source': 'recorded by scripts.validate.ci_frozen --record-pin'}
    candidate['record'] = {'run': evidence['run'], 'job': evidence['job']}
    text = json.dumps(evidence, indent=1, sort_keys=True) + '\n'
    relative = '{}/frozen-run-{}.json'.format(EVIDENCE_DIRECTORY, run_id)
    registry, report, wrote = deepcopy(registry), [], False
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / 'tree'
        git(root, 'worktree', 'add', '--detach', str(tree), candidate['commit'])
        try:
            for name, pipeline in registry['pipelines'].items():
                if names and name not in names:
                    continue
                errors, _ = candidate_errors(candidate, pipeline['replacedCommands'])
                if errors:
                    report.append('{}: not pinned ({})'.format(name, '; '.join(errors[:2])))
                    continue
                files, literals, dynamic = closure(tree, pipeline['entryModules'])
                if dynamic or not files:
                    report.append('{}: not pinned (scope not analysable at the run commit)'.format(name))
                    continue
                if not wrote:
                    (Path(root) / relative).parent.mkdir(parents=True, exist_ok=True)
                    (Path(root) / relative).write_text(text)
                    wrote = True
                pipeline['pin'] = {'commit': candidate['commit'], 'runId': run['id'], 'runUrl': run.get('html_url'),
                                   'createdAt': run.get('created_at'), 'evidencePath': relative,
                                   'evidenceSha256': hashlib.sha256(text.encode()).hexdigest(),
                                   'scopeFingerprint': scope_fingerprint(tree, pipeline, files, literals)}
                report.append('{}: pinned to {}'.format(name, describe(candidate)))
        finally:
            git(root, 'worktree', 'remove', '--force', str(tree))
    return registry, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Force full validation of every pipeline')
    parser.add_argument('--event', default=os.environ.get('CI_EVENT_NAME', 'unknown'))
    parser.add_argument('--github-output')
    parser.add_argument('--result-file', help='Write (selection) or read (--check) the recorded selection')
    parser.add_argument('--check', action='store_true', help='Run the lightweight check for --pipeline')
    parser.add_argument('--pipeline')
    parser.add_argument('--fingerprint', action='store_true', help='Print the current scope fingerprint of --pipeline')
    parser.add_argument('--record-pin', metavar='RUN_ID', help='Pin a successful Verify run as the attestation (maintenance; needs a token)')
    args = parser.parse_args()
    if args.check:
        print(name_line(args.pipeline, verify(args.pipeline, args.event, result_file=args.result_file)))
        return
    if args.fingerprint:
        pipeline = load_registry()['pipelines'][args.pipeline]
        files, literals, _ = closure(ROOT, pipeline['entryModules'])
        print(scope_fingerprint(ROOT, pipeline, files, literals))
        return
    if args.record_pin:
        registry, report = record_pin(args.record_pin, load_registry(), names=[args.pipeline] if args.pipeline else None)
        (ROOT / REGISTRY).write_text(json.dumps(registry, indent=1) + '\n')
        print('\n'.join(report))
        return
    try:
        registry = load_registry()
        result = select(registry, args.event, force_full=args.full)
    except (OSError, ValueError, KeyError) as error:
        # An unreadable registry can only mean full validation of the known pipelines.
        result = {name: {'mode': 'full', 'reason': 'invalid registry: ' + str(error)} for name in KNOWN}
    for name, item in result.items():
        print('{}: {} - {}'.format(name, item['mode'], item['reason']))
    summary = {name: {key: value for key, value in item.items() if key != 'attestation'} for name, item in result.items()}
    print(json.dumps(summary, sort_keys=True, indent=1))
    if args.result_file:
        Path(args.result_file).write_text(json.dumps(result, sort_keys=True))
    if args.github_output:
        with Path(args.github_output).open('a') as stream:
            for name, value in result.items():
                stream.write('{}={}\n'.format(name, value['mode']))


def name_line(name, result):
    return 'Frozen pipeline {} reused from attested full run: {}'.format(name, result['reason'])


if __name__ == '__main__':
    main()
