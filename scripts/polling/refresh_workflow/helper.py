"""Helpers for .github/workflows/poll-refresh.yml (stdlib only; no network, no inference, no statistical code).

  nz-date                          today's civil date in Pacific/Auckland
  active --date D                  exit 0 if the refresh may run on D (before election day), else 1
  paths --date D --national N --electorate E          the paths to commit, one per line
  check-changes --date D --national N --electorate E  exit 1 if the working tree changes anything the refresh may not touch
  pr-body --date D --national N --electorate E [--checks FILE] [--token-mode pat|builtin]   PR title (line 1) and body (rest) on stdout
N is none|published|blocked (national refresh); E is none|updated|blocked (electorate polls).
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.polling.electorate_refresh import run as electorate
from scripts.polling.weekly_refresh.common import ELECTION_DAY, INDEX, OUT, RAW, ROOT, TIMEZONE

PARTIES = ('NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'TOP', 'TPM')


def rel(p):
    return str(Path(p).relative_to(ROOT))


def allowed(day, national, electorate_outcome):
    """Paths a refresh may add. dirs: anything new below them; files: path -> allowed git status codes.
    A blocked run leaves its working files (panel, dataset, fit) untracked in the run directory; only its reports are committed."""
    dirs, files = [], {}
    if national in ('published', 'blocked'):
        dirs += [rel(RAW / day) + '/', rel(OUT / day) + '/']
    if national == 'published':
        files[rel(INDEX)] = {'M'}
        files[f'handoff.d/{day}-poll-refresh.md'] = {'A'}
    if electorate_outcome in ('updated', 'blocked'):
        dirs += [rel(electorate.RAW / day) + '/', rel(electorate.OUT / day) + '/']
    if electorate_outcome == 'updated':
        files[rel(electorate.INDEX)] = {'M', 'A'}      # 'A' only on the first ever update
        files[f'handoff.d/{day}-electorate-poll-refresh.md'] = {'A'}
    return {'dirs': dirs, 'files': files}


def paths_to_add(day, national, electorate_outcome):
    out = []
    if national == 'published':
        out += [rel(RAW / day), rel(OUT / day), rel(INDEX), f'handoff.d/{day}-poll-refresh.md']
    elif national == 'blocked':
        out += [rel(RAW / day), rel(OUT / day / 'blocked.json'), rel(OUT / day / 'review.json')]
    if electorate_outcome == 'updated':
        out += [rel(electorate.RAW / day), rel(electorate.OUT / day), rel(electorate.INDEX), f'handoff.d/{day}-electorate-poll-refresh.md']
    elif electorate_outcome == 'blocked':
        out += [rel(electorate.RAW / day), rel(electorate.OUT / day / 'blocked.json'), rel(electorate.OUT / day / 'review.json')]
    return out


def check_changes(status_lines, day, national, electorate_outcome):
    """status_lines: `git status --porcelain=v1 -uall` lines. Returns the violations: anything but additions below the allowed directories and the listed files."""
    ok = allowed(day, national, electorate_outcome); bad = []
    for line in status_lines:
        if not line.strip():
            continue
        code, path = line[:2].strip(), line[3:]
        if code == '??':
            code = 'A'
        if path in ok['files']:
            if code not in ok['files'][path]:
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
    lines = [f"- **{r['kind']}** ({r.get('pollster', 'all')}, {' to '.join(r.get('fieldwork', [])) if isinstance(r.get('fieldwork'), list) else r.get('fieldwork', 'n/a')}): {r.get('detail', '')} {r.get('action', '')}".strip() for r in review['reviews']]
    return '\n'.join(lines) or '- None.'


def token_note(token_mode):
    if token_mode == 'pat':
        return 'This PR was opened with the repository secret `POLL_REFRESH_TOKEN`, so the Verify workflow starts on it automatically.'
    return ('**CI must be started manually.** This PR was opened with the built-in `GITHUB_TOKEN` (the repository secret `POLL_REFRESH_TOKEN` is not set), '
            'and GitHub does not start workflows for pull requests opened that way. Close and reopen the PR once from the GitHub web page to start Verify.')


def checks_block(checks):
    return checks.strip() if checks and checks.strip() else '- None run (see the workflow log).'


def electorate_table(polls):
    rows = ['| Seat | Pollster | Fieldwork | Sample | Electorate vote (%) |', '|---|---|---|---|---|']
    for r in polls:
        shares = ', '.join(f"{k} {v:g}{'~' if k in r['electorateVoteFlags'] else ''}" for k, v in sorted(r['electorateVotePct'].items(), key=lambda kv: -kv[1]))
        rows.append(f"| {r['seat']} | {r['pollster']} | {r['fieldwork']['raw']} | {r['sampleSize'] or 'blank'} | {shares} |")
    return '\n'.join(rows)


def electorate_updated_section(day):
    d = electorate.OUT / day
    ch, rv = read(d / 'changes.json'), read(d / 'review.json')
    idx = [e for e in read(electorate.INDEX)['runs'] if e['date'] == day][0]
    return f"""### Electorate polls ({len(ch['added'])} new, {idx['pollCount']} held)

From Wikipedia revision {idx['wikipediaRevision']}, written to `data/processed/polling/electorate-live/{day}/polls.json` (cumulative; earlier dates are never edited). Only the electorate-vote shares are kept for use; the party-vote rows are stored but unused. `~` marks a published approximate value. All rows are `aggregator_only` and unverified. Nothing reads this file yet: it is a data change only, with no refit and no change to any estimate.

{electorate_table(ch['added'])}

Electorate review flags:
{flag_lines(rv)}
"""


def electorate_blocked_section(day):
    d = electorate.OUT / day
    rv = read(d / 'review.json')
    blockers = '\n'.join(f"- **{x['kind']}**: {json.dumps({k: v for k, v in x.items() if k != 'kind'}, ensure_ascii=False)}" for x in rv['blockers']) or '- None recorded.'
    return f"""### Electorate polls blocked

The electorate step refused to publish and wrote only `blocked.json` and `review.json` under `data/processed/polling/electorate-live/{day}/` plus a copy of the capture. Blockers:
{blockers}
"""


def blocked_reasons(day, national, electorate_outcome):
    r = []
    if national == 'blocked':
        r.append(read(OUT / day / 'blocked.json')['reason'])
    if electorate_outcome == 'blocked':
        r.append(read(electorate.OUT / day / 'blocked.json')['reason'])
    return ', '.join(r)


def national_body(day):
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
    text = f"""### National polls ({len(ch['added'])} new)

From Wikipedia revision {cap['revision']} (last modified {cap['lastModified']}):

{poll_table(ch['added'])}

All enter the panel as `aggregator_only`; primary-release verification is pending and was not done by the workflow.

Model state as of the week of {est['lastDataWeek']}, polls to {day} (means in percentage points): {means}. Change against {cmp_['previous']}: {deltas} (Monte Carlo noise floor about {cmp_['noiseFloorPP']} pp; review threshold 1 pp for NAT or LAB). NAT minus LAB {m['mean']:+.1f} pp (90% {m['q05']:+.1f} to {m['q95']:+.1f}). This is the latest-state nowcast input only: no probability, seat, bloc or government output, and no horizon or spread calibration.

{review_state}

Review flags:
{flag_lines(est['review'])}

Info items on the new rows: {', '.join(infos) or 'none'}. Dataset: {est['pollsAll']} polls, {est['polls2026']} in the current cycle.
"""
    return text, gates


def national_blocked_section(day):
    rv = read(OUT / day / 'review.json')
    blockers = '\n'.join(f"- **{x['kind']}**: {json.dumps({k: v for k, v in x.items() if k != 'kind'}, ensure_ascii=False)}" for x in rv['blockers']) or '- None recorded (the fit gates failed on both attempts; see the workflow log).'
    return f"""### National refresh blocked: {read(OUT / day / 'blocked.json')['reason']}

The national refresh refused to publish: no panel, estimate, index entry or fragment was written. `data/raw/polling/weekly-refresh/{day}/`, `blocked.json` and `review.json` are preserved so a human can decide: extend the adapter, accept a revised row, or rerun. Blockers:
{blockers}

Review flags recorded before the block:
{flag_lines(rv)}
"""


def title_of(day, national, electorate_outcome):
    if 'blocked' in (national, electorate_outcome):
        return f'Polls: weekly refresh {day} blocked ({blocked_reasons(day, national, electorate_outcome)})'
    if national == 'published':
        return f'Polls: weekly national poll refresh {day}' + (' and electorate polls' if electorate_outcome == 'updated' else '')
    return f'Polls: electorate poll update {day}'


def pr_text(day, national, electorate_outcome, token_mode, checks):
    changes, gates = [], None
    if national == 'published':
        text, gates = national_body(day); changes.append(text)
    elif national == 'blocked':
        changes.append(national_blocked_section(day))
    if electorate_outcome == 'updated':
        changes.append(electorate_updated_section(day))
    elif electorate_outcome == 'blocked':
        changes.append(electorate_blocked_section(day))
    what = []
    if national in ('published', 'blocked'):
        what.append(f'`python -m scripts.polling.weekly_refresh.run --date {day}` (Stage70; `docs/stage70-weekly-poll-refresh.md`): it captures the pinned Wikipedia table, appends new national polls to a new dated panel, reruns the unchanged Stage62 fit and writes a dated estimate')
    if electorate_outcome in ('updated', 'blocked'):
        what.append(f'`python -m scripts.polling.electorate_refresh.run --date {day}` (Stage82): it reads the electorate tables of the same capture and appends new electorate polls to a dated live-inputs file')
    adopt = f" Adoption of a national run into `config/nowcast-2026.json` is a separate reviewed step (`python3 -m scripts.polling.weekly_refresh.adopt --date {day}`)." if national == 'published' else ''
    verdict = 'Human decision needed: at least one step refused to publish.' if 'blocked' in (national, electorate_outcome) else 'Next: review the flags and the new rows, then merge.'
    local = f"Fit gates: {gates}.\n\n" if gates else ''
    body = f"""## Scope

Automated weekly refresh, run by the `Poll refresh` GitHub Actions workflow with {' and '.join(what)}. It never edits an earlier run, `data/sources.json`, the nowcast configuration or the shared handoff documents, and it does not merge.{adopt}

## Changes and limits

{chr(10).join(changes)}
## Local validation

{local}Checks run by the workflow after the refresh:
{checks_block(checks)}

## CI and boundaries

{token_note(token_mode)} Only the paths listed for this run are added (the workflow refuses to open the PR if anything else changed). Not merged by the workflow; reviewed and merged by the project coordinator or James.

## Final published head and hosted validation

Pending: Verify on this PR's head commit. Merge only when it is green on that exact commit.

{verdict}
"""
    return title_of(day, national, electorate_outcome), body


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['nz-date', 'active', 'paths', 'check-changes', 'pr-body'])
    ap.add_argument('--date'); ap.add_argument('--national', choices=['none', 'published', 'blocked'], default='none')
    ap.add_argument('--electorate', choices=['none', 'updated', 'blocked'], default='none')
    ap.add_argument('--checks'); ap.add_argument('--token-mode', choices=['pat', 'builtin'], default='builtin')
    a = ap.parse_args(argv)
    if a.command == 'nz-date':
        print(datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()); return 0
    if a.command == 'active':
        return 0 if datetime.fromisoformat(a.date).date() < ELECTION_DAY else 1
    if a.command == 'paths':
        print('\n'.join(paths_to_add(a.date, a.national, a.electorate))); return 0
    if a.command == 'check-changes':
        out = subprocess.run(['git', 'status', '--porcelain=v1', '-uall'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
        bad = check_changes(out, a.date, a.national, a.electorate)
        for line in bad:
            print('UNEXPECTED CHANGE:', line, file=sys.stderr)
        return 1 if bad else 0
    checks = Path(a.checks).read_text() if a.checks and Path(a.checks).exists() else ''
    title, body = pr_text(a.date, a.national, a.electorate, a.token_mode, checks)
    print(title); print(body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
