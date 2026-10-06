"""Dependency-aware reuse of previously validated frozen pipelines; full validation is the default.

A pull request or main push may skip the expensive ``--check`` reconstruction of a registered frozen pipeline
only when the exact tree under validation is provably equivalent, for that pipeline, to a main commit whose
complete Linux Verify run already passed *with that reconstruction executed*. Equivalence is established from
Git, not from generated manifests: no file in the pipeline's static import closure, referenced data paths,
outputs or environment files differs from the attested commit, no existing data file changed, no unreviewed
consumer reads the pipeline's runtime cache, no validation was removed from the workflow, and the runner
matches the attested runtime. Whenever any of that changes, the pipeline runs in full once; the successful
successful run (on its PR, or on main) then becomes the newest attestation (read from the Actions API; the pinned seed is the fallback), so a modified pipeline is replayed exactly once.
Manual dispatch never reuses anything. Behavioural unit tests are never skipped.
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
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = '.github/validation/frozen-pipelines.json'
WORKFLOW = '.github/workflows/ci.yml'
# Python environment files: any change forces full validation of every registered pipeline.
ENVIRONMENT = ('.python-version', 'pyproject.toml', 'requirements-boundaries.txt', 'requirements-external.lock',
               'requirements-polling.lock')
# CI selection machinery and policy files: they are not pipeline dependencies, so edits to them neither force a replay
# nor count as a pipeline change. They are guarded instead by the selector's own always-run unit tests and by
# ``workflow_errors`` (no attested validation may be removed or newly conditioned).
MACHINERY = ('.github/validation/', 'scripts/validate/ci_', 'AGENTS.md')
KNOWN = ('stage45', 'stage46', 'stage47', 'stage48', 'stage54')
EVENTS = ('pull_request', 'push')  # workflow_dispatch and anything unknown are always full


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

def seed_candidate(registry, root):
    """The pinned fallback attestation: (candidate, errors)."""
    attestation = registry['attestation']
    path = Path(root) / attestation['evidencePath']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != attestation['evidenceSha256']:
        return None, ['missing or changed seed attestation evidence']
    try:
        return {'commit': attestation['commit'], 'source': 'seed', 'record': json.loads(path.read_text())}, []
    except ValueError:
        return None, ['unreadable seed attestation evidence']


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


def live_candidates(registry, environ=None, fetch=fetch_json, root=ROOT, ancestor=is_ancestor):
    """Newest successful full-job records of reachable ci.yml runs, from the Actions API; [] on any failure.

    Both main push runs and pull-request runs count, so a modified pipeline that was fully validated on its PR is
    already the reference when the PR merges (a main push then reuses it instead of replaying a second time).
    A pull-request run attests its head commit; it must be an ancestor of the tree under validation, which holds
    for merge-commit merges and fails closed (no candidate) for squash merges.
    """
    environ = os.environ if environ is None else environ
    live, repository = registry.get('liveAttestation'), environ.get('GITHUB_REPOSITORY')
    token = environ.get('GITHUB_TOKEN') or environ.get('GH_TOKEN')
    if not (live and repository and token):
        return []
    api = environ.get('GITHUB_API_URL', 'https://api.github.com') + '/repos/' + repository + '/actions/'
    found = []
    try:
        runs = []
        for event in live['events']:
            query = 'workflows/{}/runs?event={}&status=success&per_page={}'.format(live['workflow'], event, live['maxRuns'])
            if event == 'push':
                query += '&branch=' + live['branch']
            runs.extend(fetch(api + query, token)['workflow_runs'])
        runs.sort(key=lambda run: run.get('created_at') or '', reverse=True)
        for run in runs:
            if len(found) >= live['maxRuns']:
                break
            if not ancestor(root, run['head_sha']):
                continue
            jobs = fetch(api + 'runs/{}/jobs?per_page=100'.format(run['id']), token)['jobs']
            for job in jobs:
                if job['name'] == live['job']:
                    found.append({'commit': run['head_sha'], 'source': 'live-' + run['event'], 'record': {
                        'run': {key: run.get(key) for key in ('id', 'html_url', 'event', 'conclusion', 'head_sha')},
                        'job': {key: job.get(key) for key in ('id', 'name', 'conclusion', 'steps')}}})
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return found


def candidate_errors(candidate, required):
    """(errors, successful step names) for one attested run record and one pipeline's replaced commands."""
    try:
        run, job = candidate['record']['run'], candidate['record']['job']
        steps = {step['name']: step['conclusion'] for step in job['steps']}
    except (KeyError, TypeError):
        return ['unreadable attestation evidence'], []
    errors = []
    if run.get('event') not in ('push', 'pull_request') or run.get('conclusion') != 'success' \
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

def select_pipeline(name, registry, event, root=ROOT, actual_runtime=None, candidates=None):
    """First candidate (newest first) that proves reuse wins; otherwise full with the newest candidate's reason."""
    if event not in EVENTS:
        return {'mode': 'full', 'reason': 'manual/unknown event always uses full validation'}
    if registry.get('version') != 3:
        return {'mode': 'full', 'reason': 'unsupported registry version'}
    if candidates is None:
        seed, errors = seed_candidate(registry, root)
        if seed is None:
            return {'mode': 'full', 'reason': '; '.join(errors)}
        candidates = [seed]
    runtime = runtime_errors(registry['runtime'], actual_runtime)
    if runtime:
        return {'mode': 'full', 'reason': '; '.join(runtime[:4])}
    first = None
    for candidate in candidates:
        result = select_against(name, registry, root, candidate)
        if result['mode'] == 'integrity':
            return result
        first = first or result
    return first or {'mode': 'full', 'reason': 'no attested full run available'}


def select_against(name, registry, root, candidate):
    pipeline = registry['pipelines'][name]
    commit = candidate['commit']

    def full(reason):
        return {'mode': 'full', 'reason': '{} [{} attestation {}]'.format(reason, candidate['source'], commit[:8])}
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
    return {'mode': 'integrity', 'reason': 'identical to the dependency scope of the {} full run on {} '
            '({} files in closure, {} changed paths outside it)'.format(candidate['source'], commit[:8], len(files), len(changes)),
            'closureFiles': len(files), 'changedPaths': len(changes), 'attestation': candidate}


def select(registry, event, root=ROOT, actual_runtime=None, force_full=False, live=None):
    if force_full:
        return {name: {'mode': 'full', 'reason': 'explicit full validation requested'} for name in registry['pipelines']}
    seed, errors = seed_candidate(registry, root)
    candidates = (live_candidates(registry, root=root) if live is None else live) + ([seed] if seed else [])
    result = {}
    for name in registry['pipelines']:
        try:
            result[name] = select_pipeline(name, registry, event, root, actual_runtime, candidates)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Force full validation of every pipeline')
    parser.add_argument('--event', default=os.environ.get('CI_EVENT_NAME', 'unknown'))
    parser.add_argument('--github-output')
    parser.add_argument('--result-file', help='Write (selection) or read (--check) the recorded selection')
    parser.add_argument('--check', action='store_true', help='Run the lightweight check for --pipeline')
    parser.add_argument('--pipeline')
    args = parser.parse_args()
    if args.check:
        print(name_line(args.pipeline, verify(args.pipeline, args.event, result_file=args.result_file)))
        return
    try:
        registry = load_registry()
        result = select(registry, args.event, force_full=args.full)
    except (OSError, ValueError, KeyError) as error:
        # An unreadable registry can only mean full validation of the known pipelines.
        result = {name: {'mode': 'full', 'reason': 'invalid registry: ' + str(error)} for name in KNOWN}
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
