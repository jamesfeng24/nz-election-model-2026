"""Dependency-aware reuse of previously validated frozen pipelines; full validation is the default.

A pull request may skip the expensive ``--check`` reconstruction of a registered frozen pipeline only when
the exact tree under validation is provably equivalent, for that pipeline, to a commit whose complete
Linux Verify run already passed. Equivalence is established from Git, not from generated manifests:
no file in the pipeline's static import closure, referenced data paths, outputs, environment files or
CI selection machinery differs from the attested commit, no existing data file changed, no unreviewed
consumer reads the pipeline's runtime cache, and the runner matches the attested runtime.
Main pushes and manual dispatch never reuse anything. Behavioural unit tests are never skipped.
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
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = '.github/validation/frozen-pipelines.json'
WORKFLOW = '.github/workflows/ci.yml'
# Python environment files: any change forces full validation of every registered pipeline.
ENVIRONMENT = ('.python-version', 'pyproject.toml', 'requirements-boundaries.txt', 'requirements-external.lock',
               'requirements-polling.lock')
# CI selection machinery: reuse is decided by this code, so a pull request that changes it is never self-attesting.
# Judged on the pull request's own contribution (base..HEAD); earlier reviewed changes merged to main are not diffs.
MACHINERY = ('.github/validation/', 'scripts/validate/ci_', 'AGENTS.md')
KNOWN = ('stage45', 'stage46')


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

def evidence(attestation, root):
    """(errors, recorded step conclusions) of the pinned record of the attested full run."""
    path = Path(root) / attestation['evidencePath']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != attestation['evidenceSha256']:
        return ['missing or changed attestation evidence'], {}
    try:
        record = json.loads(path.read_text())
        run, steps = record['run'], {s['name']: s['conclusion'] for s in record['job']['steps']}
    except (ValueError, KeyError, TypeError):
        return ['unreadable attestation evidence'], {}
    errors = []
    if run.get('event') != 'push' or run.get('conclusion') != 'success' or run.get('head_sha') != attestation['commit']:
        errors.append('attested run is not a successful full push run of the attested commit')
    if record['job'].get('conclusion') != 'success' or record['job'].get('name') != 'python':
        errors.append('attested python job did not succeed')
    for command in attestation['requiredSteps']:
        if steps.get('Run ' + command) != 'success':
            errors.append('attested run lacks successful step: ' + command)
    return errors, steps


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
    owned = pipeline['ownedPaths']
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

def select_pipeline(name, registry, event, root=ROOT, actual_runtime=None, base=''):
    pipeline = registry['pipelines'][name]
    attestation = registry['attestations'][pipeline['attestation']]

    def full(reason):
        return {'mode': 'full', 'reason': reason}
    if event != 'pull_request':
        return full('main/manual/unknown event always uses full validation')
    if registry.get('version') != 2:
        return full('unsupported registry version')
    errors, steps = evidence(attestation, root)
    errors = errors + runtime_errors(attestation['runtime'], actual_runtime)
    if not errors:
        errors = workflow_errors(root, [n for n, c in steps.items() if c == 'success'], registry)
    if errors:
        return full('; '.join(errors[:4]))
    changes = changed_files(root, attestation['commit'])
    if changes is None:
        return full('attested commit unavailable, not an ancestor, or working tree dirty')
    contribution = changed_files(root, base, ancestor=False) if base else None
    if contribution is None:
        return full('pull request base unavailable')
    for status, path in contribution:
        if any(path.startswith(m) for m in MACHINERY):
            return full('this pull request changes CI selection machinery: ' + path)
    try:
        files, literals, dynamic = closure(root, pipeline['entryModules'])
    except (SyntaxError, OSError, ValueError) as error:
        return full('cannot analyse dependency closure: ' + str(error))
    if dynamic:
        return full('; '.join(dynamic[:3]))
    watched = set(files) | set(ENVIRONMENT)
    prefixes = set(literals) | set(pipeline['outputPaths']) | set(pipeline['ownedPaths']) | set(pipeline['extraDependencies'])
    for status, path in changes:
        if path == WORKFLOW:
            continue  # judged by workflow_errors above, against the steps that actually passed
        if any(path.startswith(m) for m in MACHINERY):
            continue  # reviewed on an earlier pull request; this one is judged above
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
    return {'mode': 'integrity', 'reason': 'identical to the dependency scope of attested full run on {} '
            '({} files in closure, {} changed paths outside it)'.format(attestation['commit'][:8], len(files), len(changes)),
            'closureFiles': len(files), 'changedPaths': len(changes)}


def select(registry, event, root=ROOT, actual_runtime=None, force_full=False, base=''):
    if force_full:
        return {name: {'mode': 'full', 'reason': 'explicit full validation requested'} for name in registry['pipelines']}
    result = {}
    for name in registry['pipelines']:
        try:
            result[name] = select_pipeline(name, registry, event, root, actual_runtime, base)
        except (KeyError, ValueError, TypeError, OSError) as error:
            result[name] = {'mode': 'full', 'reason': 'invalid selection inputs: ' + str(error)}
    return result


def verify(name, event='pull_request', root=ROOT, base=''):
    """Lightweight check for a pipeline whose full reconstruction was legitimately skipped."""
    registry = load_registry(root)
    result = select_pipeline(name, registry, event, root, base=base)
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
    parser.add_argument('--base', default=os.environ.get('CI_BASE_SHA', ''))
    parser.add_argument('--github-output')
    parser.add_argument('--check', action='store_true', help='Run the lightweight check for --pipeline')
    parser.add_argument('--pipeline')
    args = parser.parse_args()
    if args.check:
        print(name_line(args.pipeline, verify(args.pipeline, args.event, base=args.base)))
        return
    try:
        registry = load_registry()
        result = select(registry, args.event, force_full=args.full, base=args.base)
    except (OSError, ValueError, KeyError) as error:
        # An unreadable registry can only mean full validation of the known pipelines.
        result = {name: {'mode': 'full', 'reason': 'invalid registry: ' + str(error)} for name in KNOWN}
    print(json.dumps(result, sort_keys=True, indent=1))
    if args.github_output:
        with Path(args.github_output).open('a') as stream:
            for name, value in result.items():
                stream.write('{}={}\n'.format(name, value['mode']))


def name_line(name, result):
    return 'Frozen pipeline {} reused from attested full run: {}'.format(name, result['reason'])


if __name__ == '__main__':
    main()
