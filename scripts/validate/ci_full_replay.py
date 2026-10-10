"""Partition the Verify `python` job's commands into groups that the manual Full replay workflow runs in parallel.

`.github/workflows/ci.yml` stays the single list of validation commands. This module reads that list, assigns every
command to exactly one group (first matching prefix, otherwise ``base``) and runs one group in workflow order. It
ignores `if:` gates, so a group always executes the complete replay of its pipelines (the manual full dispatch
behaviour), and it skips the named reuse steps (`Verify reused ...`, `Verify previously validated ...`) because
those are not commands that reconstruct anything. Order inside a group is the order in ci.yml, which matters for
Stage45, 46 and 47: Stage47 reads the sealed Stage45 and Stage46 banks that those constructions write to the
runtime cache of the same job, so the three share one group.

    python3 -m scripts.validate.ci_full_replay --list
    python3 -m scripts.validate.ci_full_replay --check          # partition covers every command exactly once
    python3 -m scripts.validate.ci_full_replay --group stage54  # run it (what the workflow does)

`live` is the Verify job of that name (the live 2026 chain); `tests` is the full unittest discovery plus source
validation, which touch no runtime cache and so can run apart from the historical checks.
"""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = '.github/workflows/ci.yml'
JOB = 'python'
LIVE_JOB = 'live'  # Verify already runs it as its own parallel job; here it is the group of the same name
BASE = 'base'
# Command prefixes per group, in matching order, matched against the command after `python3 ` with a leading `-m `
# removed. Everything unmatched in the `python` job is `base`.
GROUPS = {
    'tests': ('unittest', 'scripts/validate/source_files.py'),
    'stage39': ('scripts.polling.candidate_integration.',),
    'stage45-47': ('scripts.uncertainty_revision.', 'scripts.uncertainty_tails.',
                   'scripts.diagnostics.uncertainty_tails_', 'scripts.uncertainty_expectation.'),
    'stage48': ('scripts.balance_scale.',),
    'stage54': ('scripts.composed_precision.',),
    'stage63': ('scripts.layer_replication.',),
}
LIVE = 'live'


def job_commands(lines, job):
    """Plain `- run: python3 ...` commands of one job, in order; named steps (reuse gates) and pip setup excluded."""
    start = next(i for i, line in enumerate(lines) if line == '  {}:'.format(job))
    found = []
    for line in lines[start + 1:]:
        if re.match(r'^  \S', line):
            break  # next job
        match = re.match(r'^      - run: (python3 .+?) *$', line)
        if match and not match.group(1).startswith('python3 -m pip '):  # environment setup, not validation
            found.append(match.group(1))
    return found


def entries(root=ROOT):
    """(group, command) for every validation command of the Verify `live` and `python` jobs, in workflow order."""
    lines = (Path(root) / WORKFLOW).read_text().splitlines()
    return ([(LIVE, command) for command in job_commands(lines, LIVE_JOB)] +
            [(group_of(command), command) for command in job_commands(lines, JOB)])


def commands(root=ROOT):
    return [command for _, command in entries(root)]


def group_of(command):
    """Group of a `python` job command."""
    rest = command[len('python3 '):]
    target = rest[len('-m '):] if rest.startswith('-m ') else rest
    for name, prefixes in GROUPS.items():
        if any(target.startswith(prefix) for prefix in prefixes):
            return name
    return BASE


def partition(root=ROOT):
    result = {name: [] for name in (BASE,) + tuple(GROUPS) + (LIVE,)}
    for group, command in entries(root):
        result[group].append(command)
    return result


def check(root=ROOT):
    """Return problems: a command lost, duplicated or an empty group (an empty group would pass vacuously)."""
    everything = commands(root)
    parts = partition(root)
    errors = ['group {} has no commands'.format(name) for name, items in parts.items() if not items]
    merged = [command for items in parts.values() for command in items]
    if sorted(merged) != sorted(everything):
        errors.append('partition does not cover every ci.yml command exactly once')
    if not everything:
        errors.append('no commands found in the {} job'.format(JOB))
    return errors


def run(group, root=ROOT):
    parts = partition(root)
    if group not in parts:
        raise SystemExit('unknown group {!r}; choose from {}'.format(group, ', '.join(parts)))
    rows = []
    status = 0
    for command in parts[group]:
        print('::group::{}'.format(command), flush=True)
        started = time.monotonic()
        code = subprocess.call(shlex.split(command), cwd=str(root))
        seconds = time.monotonic() - started
        print('::endgroup::', flush=True)
        rows.append((command, 'ok' if code == 0 else 'FAILED ({})'.format(code), seconds))
        print('{}  {}  {:.0f}s'.format(rows[-1][1], command, seconds), flush=True)
        if code:
            status = code  # like consecutive workflow steps: stop at the first failure
            break
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as stream:
            stream.write('### Group `{}`: {} of {} commands run\n\n| command | result | seconds |\n|---|---|---|\n'.format(
                group, len(rows), len(parts[group])))
            for command, result, seconds in rows:
                stream.write('| `{}` | {} | {:.0f} |\n'.format(command, result, seconds))
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--list', action='store_true', help='print each group and its commands')
    action.add_argument('--check', action='store_true', help='fail unless the partition covers ci.yml exactly')
    action.add_argument('--group', help='run one group in workflow order')
    args = parser.parse_args(argv)
    if args.list:
        for name, items in partition().items():
            print('{} ({})'.format(name, len(items)))
            for command in items:
                print('  ' + command)
        return 0
    if args.check:
        errors = check()
        for error in errors:
            print('ERROR: ' + error)
        if not errors:
            print('partition ok: {}'.format(', '.join('{} {}'.format(n, len(i)) for n, i in partition().items())))
        return 1 if errors else 0
    return run(args.group)


if __name__ == '__main__':
    sys.exit(main())
