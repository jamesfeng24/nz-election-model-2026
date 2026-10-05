"""Conservative Stage39-only PR selection; full validation is the default."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = '.github/validation/stage39.json'


def load_registry(root=ROOT):
    return json.loads((root / REGISTRY).read_text())


def fingerprint_errors(registry, root=ROOT):
    """Validate prior successful evidence and every reviewed dependency byte."""
    errors = []
    evidence = registry['attestation']
    path = root / evidence['evidencePath']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != evidence['evidenceSha256']:
        errors.append('missing or changed prior Linux evidence')
    else:
        text = path.read_text()
        if any(marker not in text for marker in evidence['requiredLogMarkers']):
            errors.append('prior Linux evidence lacks required completion markers')
    if registry['version'] != 1 or registry['pipeline'] != 'stage39' or not registry['dependencies']:
        errors.append('unsupported or incomplete reviewed registry')
    for name, expected in registry['dependencies'].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append('changed dependency: ' + name)
    return errors


def runtime_errors(registry):
    """Different inference runtime/platform has no automatic prior attestation."""
    expected = registry['attestation']['runtime']
    actual = {'python': sys.version.split()[0], 'system': platform.system(), 'machine': platform.machine()}
    if actual['system'] == 'Linux':
        release = platform.freedesktop_os_release()
        actual.update(osId=release.get('ID'), osVersionId=release.get('VERSION_ID'))
    return ['unattested runtime: ' + key for key, value in expected.items() if actual.get(key) != value]


def select(changed, event, registry, errors=(), history_available=True):
    """Unknown inputs or changed protection force the original full commands."""
    if event != 'pull_request':
        return {'mode': 'full', 'reason': 'main/manual/unknown event uses full validation'}
    if not history_available:
        return {'mode': 'full', 'reason': 'comparison history unavailable'}
    if errors:
        return {'mode': 'full', 'reason': '; '.join(errors[:5])}
    for path in changed:
        if path in registry['dependencies']:
            return {'mode': 'full', 'reason': 'Stage39 dependency changed: ' + path}
        if path.startswith(('.github/', 'scripts/tests/', 'scripts/validate/ci')) or path == 'AGENTS.md':
            return {'mode': 'full', 'reason': 'CI, test or checkpoint policy changed: ' + path}
        editorial = path in registry['reviewedEditorialFiles'] or (path.startswith('docs/') and path.endswith('.md'))
        unrelated = any(path.startswith(prefix) for prefix in registry['reviewedUnaffectedPrefixes'])
        if not editorial and not unrelated:
            return {'mode': 'full', 'reason': 'unreviewed dependency scope: ' + path}
    return {'mode': 'integrity', 'reason': 'validated Stage39 dependency closure unchanged; behavioural tests remain full'}


def changed_paths(base, root=ROOT):
    """Missing commits/shallow history fail closed; no network or checkout edits."""
    if not base:
        return [], False
    try:
        subprocess.run(['git', 'cat-file', '-e', base + '^{commit}'], cwd=root, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        merge_base = subprocess.check_output(['git', 'merge-base', base, 'HEAD'], cwd=root, text=True).strip()
        if not merge_base:
            return [], False
        raw = subprocess.check_output(['git', 'diff', '--name-only', '-z', merge_base, 'HEAD'], cwd=root)
        return [p.decode('utf-8') for p in raw.split(b'\0') if p], True
    except (subprocess.CalledProcessError, UnicodeDecodeError, OSError):
        return [], False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Force original full validation')
    parser.add_argument('--base', default='')
    parser.add_argument('--event', default='unknown')
    parser.add_argument('--github-output')
    args = parser.parse_args()
    try:
        registry = load_registry()
        paths, available = changed_paths(args.base)
        result = ({'mode': 'full', 'reason': 'explicit full validation requested'} if args.full else
                  select(paths, args.event, registry, fingerprint_errors(registry) + runtime_errors(registry), available))
    except (OSError, KeyError, ValueError, TypeError) as error:
        result = {'mode': 'full', 'reason': 'invalid selection inputs: ' + str(error)}
    print(json.dumps(result, sort_keys=True))
    if args.github_output:
        with Path(args.github_output).open('a') as stream:
            stream.write('mode=' + result['mode'] + '\n')


if __name__ == '__main__':
    main()
