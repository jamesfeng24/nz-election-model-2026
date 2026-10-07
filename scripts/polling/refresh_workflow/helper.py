"""Helpers for .github/workflows/poll-refresh.yml (stdlib only; no network, no inference, no statistical code).

  nz-date                          today's civil date in Pacific/Auckland
  active --date D                  exit 0 if the refresh may run on D (before election day), else 1
  check-changes --date D --outcome published|blocked   exit 1 if the working tree changes anything the refresh may not touch
  pr-body --date D --outcome published|blocked [--checks FILE] [--token-mode pat|builtin]   PR title (line 1) and body (rest) on stdout
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.polling.weekly_refresh.common import ELECTION_DAY, INDEX, OUT, RAW, ROOT, TIMEZONE

PARTIES = ('NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'TOP', 'TPM')


def rel(p):
    return str(Path(p).relative_to(ROOT))


def allowed(day, outcome):
    """Paths a refresh may add. published: the raw capture, the run directory, index.json (modified) and the fragment. blocked: the capture and the run directory (of which only the two reports are committed)."""
    raw, run = rel(RAW / day), rel(OUT / day)
    if outcome == 'published':
        return {'dirs': [raw + '/', run + '/'], 'files': {rel(INDEX): 'M', f'handoff.d/{day}-poll-refresh.md': 'A'}}
    # A blocked run leaves its working files (panel, dataset, fit) untracked in the run directory; only blocked.json and review.json are ever added.
    return {'dirs': [raw + '/', run + '/'], 'files': {}}


def check_changes(status_lines, day, outcome):
    """status_lines: `git status --porcelain=v1 -uall` lines. Returns the list of violations (empty when only allowed paths were added or, for index.json, modified)."""
    ok = allowed(day, outcome); bad = []
    for line in status_lines:
        if not line.strip():
            continue
        code, path = line[:2].strip(), line[3:]
        if code == '??':
            code = 'A'
        if path in ok['files']:
            if ok['files'][path] != code:
                bad.append(line)
        elif not (code == 'A' and any(path.startswith(d) for d in ok['dirs'])):
            bad.append(line)
    return bad


def read(p):
    return json.loads(Path(p).read_text())


def pp(x):
    return f'{x:.1f}'


def poll_table(polls):
    rows = ['| Pollster | Fieldwork | Sample | ' + ' | '.join(PARTIES[:5]) + ' | TOP | TPM |', '|---|---|---|' + '---|' * 7]
    for p in polls:
        s = p['shares']; fw = ' to '.join(dict.fromkeys(p['fieldworkRaw']))
        rows.append(f"| {p['commissioner']} | {fw} | {p.get('sampleSize') or 'blank'} | " + ' | '.join(str(s.get(c, 'n/a')) for c in ('NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'TOP', 'MRI')) + ' |')
    return '\n'.join(rows)


def flag_lines(review):
    lines = [f"- **{r['kind']}** ({r.get('pollster', 'all')}, {' to '.join(r.get('fieldwork', [])) or 'n/a'}): {r.get('detail', '')} {r.get('action', '')}".strip() for r in review['reviews']]
    return '\n'.join(lines) or '- None.'


def token_note(token_mode):
    if token_mode == 'pat':
        return 'This PR was opened with the repository secret `POLL_REFRESH_TOKEN`, so the Verify workflow starts on it automatically.'
    return ('**CI must be started manually.** This PR was opened with the built-in `GITHUB_TOKEN` (the repository secret `POLL_REFRESH_TOKEN` is not set), '
            'and GitHub does not start workflows for pull requests opened that way. Close and reopen the PR once from the GitHub web page to start Verify.')


def checks_block(checks):
    return checks.strip() if checks and checks.strip() else '- None run (see the workflow log).'


def published_body(day, token_mode, checks):
    d = OUT / day
    est, ch = read(d / 'estimate.json'), read(d / 'changes.json')
    ld, cmp_, conv, cap = est['lastData'], est['comparison'], est['convergence'], est['capture']
    means = ', '.join(f"{c} {pp(ld[c]['mean'])}" for c in PARTIES if c in ld)
    deltas = ', '.join(f"{c} {cmp_['deltaLastDataMeanPP'][c]:+.1f}" for c in PARTIES if c in cmp_['deltaLastDataMeanPP'])
    m = est['marginNatMinusLabLastData']
    gates = (f"max rank R-hat {conv['maxRhat']:.4f} (limit 1.01), min bulk ESS {conv['minBulkESS']:.0f} and tail ESS {conv['minTailESS']:.0f} (limit 400), "
             f"{conv['divergences']} divergences, {conv['treeDepthContacts']} tree-depth contacts, min BFMI {min(conv['energyBFMI']):.2f} (limit 0.3); "
             f"attempt {est['attempt']}, {est['runtimeSeconds']:.0f} s")
    review_state = 'Human review required (see the flags below).' if est['humanReviewRequired'] else 'No review flag.'
    infos = sorted({i['kind'] for i in est['review']['infos']})
    title = f'Polls: weekly national poll refresh {day}'
    body = f"""## Scope

Automated weekly refresh of the national poll input, run by the `Poll refresh` GitHub Actions workflow with `python -m scripts.polling.weekly_refresh.run --date {day}` (Stage70; `docs/stage70-weekly-poll-refresh.md`). It captures the pinned Wikipedia table, appends new polls to a new dated panel, reruns the unchanged Stage62 fit and writes a dated estimate. It never edits an earlier run, `data/sources.json`, the nowcast configuration or the shared handoff documents, and it does not merge. Adoption into `config/nowcast-2026.json` is a separate reviewed step (`python3 -m scripts.polling.weekly_refresh.adopt --date {day}`).

## Changes and limits

New polls ({len(ch['added'])}), from Wikipedia revision {cap['revision']} (last modified {cap['lastModified']}):

{poll_table(ch['added'])}

All enter the panel as `aggregator_only`; primary-release verification is pending and was not done by the workflow.

Model state as of the week of {est['lastDataWeek']}, polls to {day} (means in percentage points): {means}. Change against {cmp_['previous']}: {deltas} (Monte Carlo noise floor about {cmp_['noiseFloorPP']} pp; review threshold 1 pp for NAT or LAB). NAT minus LAB {m['mean']:+.1f} pp (90% {m['q05']:+.1f} to {m['q95']:+.1f}). This is the latest-state nowcast input only: no probability, seat, bloc or government output, and no horizon or spread calibration.

{review_state}

Review flags:
{flag_lines(est['review'])}

Info items on the new rows: {', '.join(infos) or 'none'}. Dataset: {est['pollsAll']} polls, {est['polls2026']} in the current cycle.

## Local validation

Fit gates: {gates}.

Checks run by the workflow after the refresh:
{checks_block(checks)}

## CI and boundaries

{token_note(token_mode)} Only the raw capture, the dated run directory, `index.json` and one handoff fragment are added (the workflow refuses to open the PR if anything else changed). Not merged by the workflow; reviewed and merged by the project coordinator or James.

## Final published head and hosted validation

Pending: Verify on this PR's head commit. Merge only when it is green on that exact commit.

Next: review the flags and the new rows, merge, then adopt the run into the nowcast configuration in a separate PR.
"""
    return title, body


def blocked_body(day, token_mode, checks):
    d = OUT / day
    b = read(d / 'blocked.json'); rv = read(d / 'review.json')
    reason = b['reason']
    blockers = '\n'.join(f"- **{x['kind']}**: {json.dumps({k: v for k, v in x.items() if k != 'kind'}, ensure_ascii=False)}" for x in rv['blockers']) or '- None recorded (the fit gates failed on both attempts; see the workflow log).'
    title = f'Polls: weekly refresh {day} blocked ({reason})'
    body = f"""## Scope

The `Poll refresh` GitHub Actions workflow ran `python -m scripts.polling.weekly_refresh.run --date {day}` and the refresh **refused to publish**: {reason}. No panel, estimate, index entry or fragment was written. This PR preserves the raw capture (`data/raw/polling/weekly-refresh/{day}/`) and the run's `blocked.json` and `review.json` so a human can decide: extend the adapter, accept a revised row, or rerun. Nothing is adopted and nothing is merged by the workflow.

## Changes and limits

Blockers:
{blockers}

Review flags recorded before the block:
{flag_lines(rv)}

## Local validation

{checks_block(checks)}

## CI and boundaries

{token_note(token_mode)} Merging this PR only preserves the capture and the reports; if the capture should not be kept, close it instead (a later run starts from the same base).

## Final published head and hosted validation

Pending: Verify on this PR's head commit.

Next: a human reads `blocked.json`, decides, and either fixes the rule or adapter in a separate PR or reruns the workflow (`workflow_dispatch`) after closing this one.
"""
    return title, body


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['nz-date', 'active', 'check-changes', 'pr-body'])
    ap.add_argument('--date'); ap.add_argument('--outcome', choices=['published', 'blocked'])
    ap.add_argument('--checks'); ap.add_argument('--token-mode', choices=['pat', 'builtin'], default='builtin')
    a = ap.parse_args(argv)
    if a.command == 'nz-date':
        print(datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()); return 0
    if a.command == 'active':
        return 0 if datetime.fromisoformat(a.date).date() < ELECTION_DAY else 1
    if a.command == 'check-changes':
        out = subprocess.run(['git', 'status', '--porcelain=v1', '-uall'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
        bad = check_changes(out, a.date, a.outcome)
        for line in bad:
            print('UNEXPECTED CHANGE:', line, file=sys.stderr)
        return 1 if bad else 0
    checks = Path(a.checks).read_text() if a.checks and Path(a.checks).exists() else ''
    title, body = (published_body if a.outcome == 'published' else blocked_body)(a.date, a.token_mode, checks)
    print(title); print(body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
