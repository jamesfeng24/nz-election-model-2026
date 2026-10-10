"""Publish workflow decisions: the run mode, what to release, the snapshot id and the release options (stdlib only; no network).

    python3 -m scripts.publish_workflow.plan mode --event E --publish-input B --auto-variable V --ref R
    python3 -m scripts.publish_workflow.plan release --existing-ids-from PATH --supersedes ID
    python3 -m scripts.publish_workflow.plan options --out PATH --snapshot-id ID --code-revision SHA --national-date D
    python3 -m scripts.publish_workflow.plan adoption ...   (text of the adoption pull request)
    python3 -m scripts.publish_workflow.plan gate-passed
    python3 -m scripts.publish_workflow.plan check-site

Each subcommand that decides something writes `key=value` lines to $GITHUB_OUTPUT when it is set (and prints them), so the workflow
holds no logic of its own. Nothing here touches the public repository; see `public.py` for that.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = 'config/nowcast-2026.json'
WEEKLY = 'data/processed/polling/weekly-refresh'
ELECTORATE = 'data/processed/polling/electorate-live'
GATE_REPORT = 'data/processed/nowcast-assembly/development-gate.json'
BOUNDARY_VERSION_ID = 'stats-nz-electorates-final-2025'
# Produced by the Stage84 site code (PR #108); the workflow refuses to run on a ref that lacks them.
SITE_FILES = ('scripts/site_evidence/build.py', 'scripts/site_incumbents/build.py', 'scripts/validate/check_site.mjs', 'src/app/pages.ts')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class Refused(Exception):
    """The run must stop and publish nothing."""


def read(path, root=ROOT):
    return json.loads((Path(root) / path).read_text(encoding='utf-8'))


def decide_mode(event, publish_input, auto_variable, ref):
    """('publish' | 'dry-run', reason). A dry run builds and checks everything and writes nothing outside the runner.

    Publishing needs an explicit go: a manual run with the publish box ticked, or a push to main while the repository variable PUBLISH_AUTO is
    exactly 'true' (James sets it after the first publish he has approved). Any other run, including every run before that, is a dry run.
    Publishing is possible from main only.
    """
    if event == 'workflow_dispatch':
        wants, why = str(publish_input).strip().lower() == 'true', 'the publish box was ' + ('ticked' if str(publish_input).strip().lower() == 'true' else 'not ticked')
    elif event == 'push':
        wants, why = str(auto_variable).strip() == 'true', 'PUBLISH_AUTO is ' + ('true' if str(auto_variable).strip() == 'true' else 'not set to true')
    else:
        wants, why = False, f'the {event or "unknown"} event never publishes'
    if wants and ref != 'refs/heads/main':
        raise Refused(f'Publishing is allowed from main only; this run is on {ref}. Run it from main, or untick the publish box for a dry run.')
    return ('publish' if wants else 'dry-run'), why


def latest_refresh(root=ROOT):
    """The newest weekly national run and Stage82 electorate-poll run, and the date of the newest of the two (the release date)."""
    national = [r['date'] for r in read(WEEKLY + '/index.json', root)['runs']]
    electorate_path = Path(root) / ELECTORATE / 'index.json'
    electorate = [r['date'] for r in read(ELECTORATE + '/index.json', root)['runs']] if electorate_path.exists() else []
    if not national:
        raise Refused('There is no published national refresh to release')
    nat, ele = max(national), (max(electorate) if electorate else None)
    return {'nationalDate': nat, 'electorateDate': ele, 'releaseDate': max(d for d in (nat, ele) if d)}


def snapshot_id(release_date, existing, supersedes=None):
    """(id, supersedes) of the next release, or (None, None) when this refresh is already published and no correction is asked for.

    One release per refresh date: `nowcast-<date>`. A correction (a supersedes id that is archived) takes the first free `-r<n>` id; the
    archive refuses an id it already holds, so ids are never reused.
    """
    if not DATE.match(release_date):
        raise Refused('Bad release date ' + release_date)
    existing = set(existing)
    if supersedes:
        if supersedes not in existing:
            raise Refused(f'Cannot supersede {supersedes}: it is not in the published archive')
    elif f'nowcast-{release_date}' in existing:
        return None, None
    n = 1
    while True:
        candidate = f'nowcast-{release_date}' + ('' if n == 1 else f'-r{n}')
        if candidate not in existing:
            return candidate, supersedes or None
        n += 1


def existing_ids(index_text):
    if not index_text:
        return []
    index = json.loads(index_text)
    return [e['snapshotId'] for e in index['snapshots']]


def election_guard(release_date, config):
    if release_date >= config['electionDate']:
        raise Refused(f"The refresh dated {release_date} is on or after election day ({config['electionDate']}); outputs are frozen at the last release")


LIMITATIONS = [
    'This shows how the parties would do if the election were held under current conditions; it is not a forecast of how opinion will change before election day.',
    'Ranges are central ranges across simulated elections under the current state of the polls; they are not margins of error.',
    'Electorates without a seat poll rest on the 2023 result on the 2026 boundaries and the national picture, and Māori electorates are shown as a range between two calibrations.',
]


def build_options(config, snapshot, national_date, code_revision, now=None):
    """The `release:publish` options file for the adopted configuration. `config` must already carry the adopted national input."""
    cutoff, state = config['national']['dataCutoff'], config['national']['modelStateAsOf']
    created = (now or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
    if created < cutoff:
        raise Refused(f'The data cutoff {cutoff} is after the creation time {created}')
    mmp = config['mmp']
    return {
        'snapshotId': snapshot, 'createdAt': created, 'dataCutoff': cutoff + 'T00:00:00+00:00', 'electionId': config['electionId'], 'electionDate': config['electionDate'],
        'boundaryVersionId': BOUNDARY_VERSION_ID, 'modelVersion': 'nz-nowcast-' + config['configVersion'], 'codeRevision': code_revision,
        'mmp': {'rulesVersion': mmp['rulesVersion'], 'rulesSourceIds': mmp['rulesSourceIds'], 'blocs': mmp['blocs'], 'hungParliament': mmp['hungParliament']},
        'nationalBasis': f'National polls to {cutoff} (weekly refresh of {national_date}); latent support in the week of {state}',
        'limitations': LIMITATIONS, 'probabilityMcseMax': config['release']['probabilityMcseMax'],
    }


def check_site_present(root=ROOT):
    missing = [p for p in SITE_FILES if not (Path(root) / p).is_file()]
    if missing:
        raise Refused('The public site code is not on this ref (missing ' + ', '.join(missing) + '). Merge the site pull request first.')


def gate_passed(root=ROOT):
    report = read(GATE_REPORT, root)
    failed = [c['check'] for c in report['checks'] if not c['passed']]
    if not report['publishable'] or failed:
        raise Refused('The development gate on the adopted configuration fails: ' + ', '.join(failed or ['not publishable']))


def adoption_fragment(snapshot, release_date, national_date, electorate_date, config_version, revision):
    """The handoff fragment of the adoption pull request (the shared documents are never edited directly)."""
    ele = f' and the {electorate_date} electorate-poll run' if electorate_date else ''
    return f"""<!-- fold: changelog -->
## Publish {snapshot} — {release_date}

- The Publish workflow adopted the {national_date} national refresh{ele} (configuration version {config_version}), ran the forecast and published `{snapshot}` to the public site. This pull request records that configuration in `config/nowcast-2026.json` and regenerates the development gate, the synthetic bank fixture and the Stage79 readout, so that main matches what was published. Code revision of the published forecast: `{revision}`. No model, data or frozen-pipeline change. Not needed for the next publish: each publish adopts the newest refresh itself.
"""


def adoption_pr(snapshot, release_date, national_date, electorate_date, config_version, revision, run_url):
    """(title, body) of the adoption pull request opened after a successful publish."""
    ele = f'electorate-poll run {electorate_date}' if electorate_date else 'no electorate-poll run'
    title = f'Polls: adopt the {release_date} refresh published as {snapshot}'
    body = f"""## Scope

Bookkeeping after a publish. The Publish workflow ({run_url}) adopted the {national_date} national refresh and the {ele}, published `{snapshot}`, and left main unchanged. This pull request puts the same adoption on main (`python3 -m scripts.polling.weekly_refresh.adopt --date {national_date}`, configuration version {config_version}) and regenerates the three files that follow the configuration: the development gate, the synthetic bank fixture and the Stage79 readout. Published code revision: `{revision}`.

## Changes and limits

`config/nowcast-2026.json` (national source, dates, electorate-poll run and configuration version), `data/processed/nowcast-assembly/development-gate.json`, `data/fixtures/synthetic/nowcast-draw-bank.json`, `data/processed/seat-polls/readout-2026.json` and one handoff fragment. The Stage77 rehearsal report is not regenerated (about 30 minutes) and may be stale. Nothing else changes. Merging is optional for the next publish, which adopts the newest refresh again, but keeps main's configuration equal to what is published.

## Decisions recorded

Handoff fragment `handoff.d/{release_date}-publish-{snapshot}.md` (changelog). No new decision, methodology or source entry.

## Local validation

Run by the workflow before opening this pull request: `nowcast_config.validate --require-complete`, `nowcast_assembly.run --check`, `nowcast_assembly.fixture --check`, `seat_polls.readout --check`, `fold_doc_fragments --check` (the pull request is opened only if all pass).

## CI and boundaries

Opened by the workflow with a personal token so that CI runs. Not merged by the workflow.

## Final published head and hosted validation

Pending the Verify run on this head.
"""
    return title, body


def emit(pairs):
    for key, value in pairs.items():
        line = f'{key}={"" if value is None else value}'
        print(line)
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
                out.write(line + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    m = sub.add_parser('mode')
    m.add_argument('--event', default=''); m.add_argument('--publish-input', default=''); m.add_argument('--auto-variable', default=''); m.add_argument('--ref', default='')
    r = sub.add_parser('release')
    r.add_argument('--existing-ids-from', help='the archive index.json of the public site; absent in a dry run'); r.add_argument('--supersedes', default='')
    o = sub.add_parser('options')
    o.add_argument('--out', required=True); o.add_argument('--snapshot-id', required=True); o.add_argument('--code-revision', required=True); o.add_argument('--national-date', required=True)
    f = sub.add_parser('adoption')
    for name in ('snapshot-id', 'release-date', 'national-date', 'config-version', 'revision', 'run-url', 'fragment-out', 'title-out', 'body-out'):
        f.add_argument('--' + name, required=True)
    f.add_argument('--electorate-date', default='')
    sub.add_parser('gate-passed'); sub.add_parser('check-site')
    a = ap.parse_args(argv)
    try:
        if a.command == 'mode':
            mode, why = decide_mode(a.event, a.publish_input, a.auto_variable, a.ref)
            print(f'Mode: {mode} ({why})')
            emit({'mode': mode})
        elif a.command == 'release':
            config = read(CONFIG)
            found = latest_refresh()
            election_guard(found['releaseDate'], config)
            text = Path(a.existing_ids_from).read_text(encoding='utf-8') if a.existing_ids_from and Path(a.existing_ids_from).exists() else ''
            new_id, superseded = snapshot_id(found['releaseDate'], existing_ids(text), a.supersedes.strip() or None)
            if new_id is None:
                print(f"Nothing to publish: nowcast-{found['releaseDate']} is already in the archive. Run again with a supersedes id to publish a correction.")
            emit({'national_date': found['nationalDate'], 'electorate_date': found['electorateDate'], 'release_date': found['releaseDate'],
                  'snapshot_id': new_id, 'supersedes': superseded, 'skip': 'true' if new_id is None else 'false'})
        elif a.command == 'options':
            options = build_options(read(CONFIG), a.snapshot_id, a.national_date, a.code_revision)
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(options, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            print('Options written to', a.out)
        elif a.command == 'adoption':
            ele = a.electorate_date or None
            Path(a.fragment_out).write_text(adoption_fragment(a.snapshot_id, a.release_date, a.national_date, ele, a.config_version, a.revision), encoding='utf-8')
            title, body = adoption_pr(a.snapshot_id, a.release_date, a.national_date, ele, a.config_version, a.revision, a.run_url)
            Path(a.title_out).write_text(title, encoding='utf-8'); Path(a.body_out).write_text(body, encoding='utf-8')
            print('Adoption text written')
        elif a.command == 'gate-passed':
            gate_passed(); print('Development gate on the adopted configuration passes')
        elif a.command == 'check-site':
            check_site_present(); print('Site code present')
    except Refused as error:
        print('::error::' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
