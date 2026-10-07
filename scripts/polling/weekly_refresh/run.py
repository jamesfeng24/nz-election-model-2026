"""Stage70 weekly national poll refresh. One command:

    .venv-external/bin/python -m scripts.polling.weekly_refresh.run [--date YYYY-MM-DD]

capture -> new-row rules -> next dated panel -> source registry -> pinned dataset -> Stage62 fit with its gates -> dated estimate.
Refuses to publish (writes blocked.json, exits non-zero) on a blocker or a failed gate. Never edits an earlier run.
`--check` (stdlib + numpy) verifies every committed run; `--rebuild-check` (.venv-external) re-derives panel and dataset from the raw capture.
"""
import argparse
import json
import sys
from datetime import datetime, date
from zoneinfo import ZoneInfo
from pathlib import Path
from . import capture, delta
from .common import (ROOT, RAW, OUT, INDEX, FRAGMENTS, CAPTURE, WIKI_URL, TIMEZONE, ELECTION_DAY, BASE_PANEL, TARGET_YEAR,
                     read, write, sha, rel, load_index, previous_base)

EXIT_BLOCKED, EXIT_FIT = 2, 3
NUMERICAL_MODULES = [f'scripts/polling/weekly_refresh/{m}.py' for m in ('common', 'delta', 'dataset', 'fit', 'summarize')]
PROCESSING = 'scripts/polling/weekly_refresh/run.py'
LICENCE = 'Wikipedia text is CC BY-SA; bytes preserved unchanged for research provenance. Poll figures originate from the named pollsters.'


def nz_today():
    return datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()


def registry(run_date, rev, last_modified, retrieved):
    d = RAW / run_date
    srcs = []
    for name, role in ((CAPTURE, 'table'), (CAPTURE + '.headers', 'response headers'), ('fetch-log.tsv', 'fetch log')):
        srcs.append({'dateOrElection': f'2026 general election cycle; weekly refresh {run_date}', 'id': f'polling-weekly-{run_date}-{name}',
                     'licence': LICENCE, 'limitations': ['Aggregator transcription; fieldwork dates and sample sizes unverified against primary releases.',
                                                         f'Wikipedia revision {rev}, last modified {last_modified}; {role}'],
                     'organisation': 'Wikipedia (REST HTML, Opinion polling for the 2026 New Zealand general election)', 'processingScript': PROCESSING,
                     'rawPath': rel(d / name), 'resource': name, 'retrievedAt': retrieved, 'schemaVersion': 1, 'sha256': sha(d / name), 'url': WIKI_URL})
    return {'schemaVersion': 1, 'note': 'Dated registry for this weekly refresh; data/sources.json is frozen and not edited.', 'sources': srcs}


def blocked(run_dir, run_date, reason, review, code):
    write(run_dir / 'blocked.json', {'schemaVersion': 1, 'refreshDate': run_date, 'reason': reason, 'review': review,
                                     'note': 'No panel or estimate was published for this date. The raw capture is preserved.'})
    print('BLOCKED', reason, json.dumps(review['blockers'])[:2000], file=sys.stderr)
    return code


def manifest(run_dir):
    files = sorted(p for p in run_dir.rglob('*') if p.is_file() and p.name != 'manifest.json')
    return {'schemaVersion': 1, 'sha256': {str(p.relative_to(run_dir)): sha(p) for p in files}}


def write_fragment(run_date, est):
    ld = est['lastData']; n = est['newPolls']
    line = ', '.join(f"{c} {ld[c]['mean']:.1f}" for c in ('NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'TOP', 'TPM') if c in ld)
    flags = len(est['review']['reviews'])
    text = (f'<!-- fold: changelog -->\n## Weekly poll refresh {run_date}\n\n- {len(n)} new national poll(s) added to the dated panel '
            f'`data/processed/polling/weekly-refresh/{run_date}/` from Wikipedia revision {est["capture"]["revision"]} and the Stage62 gauss fit rerun '
            f'(cutoff {run_date}, all gates met; nowcast input `lastDataSupport` only). Model state as of the week of {est["lastDataWeek"]}: {line}. {flags} item(s) flagged for human review. Internal only.\n')
    FRAGMENTS.mkdir(exist_ok=True)
    (FRAGMENTS / f'{run_date}-poll-refresh.md').write_text(text)


def run(run_date, skip_fit=False, use_existing=False):
    if date.fromisoformat(run_date) >= ELECTION_DAY:
        raise ValueError('The weekly refresh ends before election day (design: poll model horizon is 7 Nov 2026)')
    run_dir = OUT / run_date
    if run_dir.exists():
        raise FileExistsError('Run directory exists; earlier runs are never edited: ' + str(run_dir))
    if not use_existing:
        capture.fetch(run_date)
    cap = RAW / run_date / CAPTURE
    rev, last_modified = capture.revision(run_date)
    if rev is None:
        raise ValueError('Capture response has no revision id')
    retrieved = (RAW / run_date / 'fetch-log.tsv').read_text().splitlines()[-1].split('\t')[0]
    cap_sha = sha(cap); cap_rel = rel(cap)
    base_panel_path, base_est_path, base_label = previous_base()
    base = read(base_panel_path)
    wiki, unmapped = delta.wiki_rows(cap.read_text(encoding='utf-8'), f'weekly-refresh-{run_date}-wikipedia', cap_rel, cap_sha)
    added, blockers, reviews, infos = delta.evaluate(base['records'], wiki, unmapped, run_date)
    review = {'schemaVersion': 1, 'refreshDate': run_date, 'blockers': blockers, 'reviews': reviews, 'infos': infos}
    if not blockers and not added:
        import shutil
        shutil.rmtree(RAW / run_date)     # identical polls, nothing new to preserve or fit; the next run starts from the same base
        print('NO_NEW_POLLS', run_date, 'wikipedia revision', rev)
        return 0
    run_dir.mkdir(parents=True)
    if blockers:
        return blocked(run_dir, run_date, 'new-row rules', review, EXIT_BLOCKED)
    panel, changes = delta.next_panel(base_panel_path, added, run_date, cap_rel, cap_sha, rev)
    # Dataset (pinned upstream parse) and reconciliation against the new panel.
    from . import dataset
    ds, inv = dataset.build(cap, run_date, run_dir / 'dataset')
    pk = dataset.panel_keys(panel)
    if pk != inv['pollKeys2026']:
        review['blockers'].append({'kind': 'panel_wikipedia_key_mismatch', 'panelWaves': len(pk), 'wikipediaRows': len(inv['pollKeys2026']),
                                   'onlyPanel': [k for k in pk if k not in inv['pollKeys2026']], 'onlyWikipedia': [k for k in inv['pollKeys2026'] if k not in pk]})
        return blocked(run_dir, run_date, 'panel/upstream reconciliation', review, EXIT_BLOCKED)
    reg = registry(run_date, rev, last_modified, retrieved)
    write(run_dir / 'panel.json', panel); write(run_dir / 'changes.json', changes); write(run_dir / 'source-registry.json', reg)
    write(run_dir / 'inventory.json', inv); write(run_dir / 'review.json', review)
    contract = {'schemaVersion': 1, 'refreshDate': run_date, 'wikipediaRevision': rev,
                'base': {'panel': rel(base_panel_path), 'panelSha256': sha(base_panel_path), 'estimate': rel(base_est_path), 'estimateSha256': sha(base_est_path),
                         'previousRun': base_label},
                'sha256': {cap_rel: cap_sha, rel(RAW / run_date / (CAPTURE + '.headers')): sha(RAW / run_date / (CAPTURE + '.headers')),
                           'requirements-external.lock': sha(ROOT / 'requirements-external.lock'),
                           'data/processed/polling/live-fit-2026-10/input-contract.json': sha(ROOT / 'data/processed/polling/live-fit-2026-10/input-contract.json')},
                'datasetFiles': {f'dataset.{e}': sha(run_dir / f'dataset.{e}') for e in ('npz', 'json')}, 'datasetFingerprint': inv['fingerprint'],
                'codeSha256': {rel(p): sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))}}   # latest run's numerical modules are verified by --check
    write(run_dir / 'input-contract.json', contract)
    if skip_fit:
        print('SKIP_FIT: panel, inventory and dataset written; no estimate'); return 0
    from . import fit as fit_mod
    result = fit_mod.fit(run_dir, run_date, ds, sha(run_dir / 'input-contract.json'))
    if result['status'] != 'accepted':
        return blocked(run_dir, run_date, 'fit gates failed on both attempts; no estimate published', review, EXIT_FIT)
    return finish(run_dir, run_date, result, inv, review, changes, base_est_path, base_label, cap_rel, cap_sha, rev, last_modified)


def finish(run_dir, run_date, result, inv, review, changes, base_est_path, base_label, cap_rel, cap_sha, rev, last_modified):
    from . import summarize
    attempt = result['attempt']
    est = summarize.summarize(run_dir / f'fit/attempt{attempt}.npz', result, inv)
    prev = summarize.previous_summary(base_est_path)
    cmp_, shift_flags = summarize.compare(est, prev, base_label or 'Stage62 arm A (2026-10-06 cutoff)')
    review['reviews'].extend(shift_flags)
    if inv['lastDataWeek'] > run_date:
        review['blockers'].append({'kind': 'model_state_after_cutoff', 'lastDataWeek': inv['lastDataWeek']})
        return blocked(run_dir, run_date, 'model state dated after the cutoff', review, EXIT_FIT)
    fit_rel = f'data/processed/polling/weekly-refresh/{run_date}/fit/attempt{attempt}'
    est.update({'schemaVersion': 1, 'refreshDate': run_date, 'cutoff': run_date, 'targetType': 'nowcast',
                'modelStateAsOf': inv['lastDataWeek'], 'dataCutoff': run_date,
                'modelStateLabel': f"latent state as of the week of {inv['lastDataWeek']}, polls to {run_date}",
                'nowcastInput': {'source': fit_rel + '.npz', 'record': fit_rel + '.json', 'stateKey': 'lastDataSupport', 'forbiddenStateKeys': ['electionDay'],
                                 'modelStateAsOf': inv['lastDataWeek'], 'dataCutoff': run_date, 'draws': est['draws'],
                                 'note': 'The values config/nowcast-2026.json national.source, modelStateAsOf and dataCutoff take when this refresh is adopted (scripts/polling/weekly_refresh/adopt.py).'},
                'status': 'internal; not a probability or seat output',
                'model': 'pinned external gauss (Stage38), Stage62 settings, unchanged', 'attempt': attempt,
                'capture': {'rawPath': cap_rel, 'sha256': cap_sha, 'revision': rev, 'lastModified': last_modified},
                'dataset': inv['fingerprint'], 'polls2026': inv['polls2026'], 'pollsAll': inv['polls'], 'lastDataWeek': inv['lastDataWeek'],
                'targetWeek': inv['targetWeek'], 'newPolls': changes['added'], 'comparison': cmp_, 'review': review,
                'humanReviewRequired': bool(review['reviews']), 'runtimeSeconds': result['runtimeSeconds']})
    from scripts.polling.live_fit.summarize import scan
    scan({k: v for k, v in est.items() if k != 'review'})   # the review block's `blockers` key trips the substring scan for 'bloc'; it holds no estimates
    write(run_dir / 'review.json', review)
    write(run_dir / 'estimate.json', est)
    write(run_dir / 'manifest.json', manifest(run_dir))
    idx = load_index()
    idx['runs'].append({'date': run_date, 'wikipediaRevision': rev, 'panelSha256': sha(run_dir / 'panel.json'), 'estimateSha256': sha(run_dir / 'estimate.json'),
                        'manifestSha256': sha(run_dir / 'manifest.json'), 'humanReviewRequired': est['humanReviewRequired']})
    write(INDEX, idx)
    write_fragment(run_date, est)
    ld = est['lastData']
    print('PUBLISHED', run_date, {c: round(ld[c]['mean'], 2) for c in ld}, 'review flags', len(review['reviews']))
    return 0


def resume(run_date):
    """Finish a run whose fit was accepted but whose summary step was interrupted. Never refits; verifies the fit belongs to this run."""
    run_dir = OUT / run_date
    if (run_dir / 'estimate.json').exists() or not (run_dir / 'input-contract.json').exists():
        raise ValueError('Nothing to resume for ' + run_date)
    result = None
    for attempt in (1, 2):
        p = run_dir / f'fit/attempt{attempt}.json'
        if p.exists() and read(p)['status'] == 'accepted':
            result = read(p); break
    if result is None:
        raise ValueError('No accepted fit to resume from')
    contract = read(run_dir / 'input-contract.json'); inv = read(run_dir / 'inventory.json')
    if result['signature']['inputContract'] != sha(run_dir / 'input-contract.json') or result['signature']['dataset'] != inv['fingerprint']:
        raise ValueError('The fit does not belong to this run')
    rev, last_modified = capture.revision(run_date)
    cap = RAW / run_date / CAPTURE
    return finish(run_dir, run_date, result, inv, read(run_dir / 'review.json'), read(run_dir / 'changes.json'), ROOT / contract['base']['estimate'],
                  contract['base']['previousRun'], rel(cap), sha(cap), rev, last_modified)


def check():
    """Stdlib + numpy. Verifies every committed run; never infers."""
    import numpy as np
    from . import summarize
    idx = load_index(); prev_panel = BASE_PANEL; seen = []
    for n, entry in enumerate(idx['runs']):
        d = OUT / entry['date']
        if json.loads((d / 'manifest.json').read_bytes()) != manifest(d):
            raise ValueError('Manifest mismatch ' + entry['date'])
        for key, f in (('panelSha256', 'panel.json'), ('estimateSha256', 'estimate.json'), ('manifestSha256', 'manifest.json')):
            if sha(d / f) != entry[key]:
                raise ValueError(f'Index hash mismatch {entry["date"]} {f}')
        contract = read(d / 'input-contract.json')
        for p, h in contract['sha256'].items():
            if sha(ROOT / p) != h:
                raise ValueError('Changed raw input ' + p)
        if n == len(idx['runs']) - 1:     # code may evolve between weekly runs; the latest run must still match the code that made it
            for mod in NUMERICAL_MODULES:
                if sha(ROOT / mod) != contract['codeSha256'][mod]:
                    raise ValueError('Numerical module changed since the latest run: ' + mod)
        if sha(ROOT / contract['base']['panel']) != contract['base']['panelSha256'] or contract['base']['panel'] != rel(prev_panel):
            raise ValueError('Broken panel chain at ' + entry['date'])
        if sha(ROOT / contract['base']['estimate']) != contract['base']['estimateSha256']:
            raise ValueError('Changed base estimate at ' + entry['date'])
        for r in read(d / 'source-registry.json')['sources']:
            if sha(ROOT / r['rawPath']) != r['sha256']:
                raise ValueError('Changed registered source ' + r['rawPath'])
        panel = read(d / 'panel.json'); base = read(prev_panel)
        if panel['basePanelSha256'] != sha(prev_panel):
            raise ValueError('Panel base hash')
        ids_base = {r['id'] for r in base['records']}; ids = [r['id'] for r in panel['records']]
        added = [r['id'] for r in panel['records'] if r['id'] not in ids_base]
        if len(set(ids)) != len(ids) or not ids_base <= set(ids) or sorted(a['id'] for a in read(d / 'changes.json')['added']) != sorted(added):
            raise ValueError('Panel is not previous panel plus the recorded additions ' + entry['date'])
        if read(d / 'review.json')['blockers']:
            raise ValueError('Published run carries blockers')
        est = read(d / 'estimate.json')
        fit_dir = d / 'fit'; rec = read(fit_dir / f'attempt{est["attempt"]}.json')
        if rec['status'] != 'accepted' or sha(fit_dir / f'attempt{est["attempt"]}-diagnostics.json.gz') != rec['diagnosticsSha256'] or sha(fit_dir / f'attempt{est["attempt"]}.npz') != rec['npzSha256']:
            raise ValueError('Fit record/hash ' + entry['date'])
        inv = read(d / 'inventory.json')
        with np.load(fit_dir / f'attempt{est["attempt"]}.npz', allow_pickle=False) as a:
            if 'electionDay' in a.files:
                raise ValueError('Election-week draws saved in a nowcast archive ' + entry['date'])
            x = a['lastDataSupport']
            if list(x.shape) != rec['savedDrawChainShape'] or not np.isfinite(x).all() or (x < 0).any() or not np.allclose(x.sum(-1), 1, atol=1e-10, rtol=0):
                raise ValueError('Invalid draws ' + entry['date'])
            if not np.allclose(x.mean((0, 1)), rec['expectedLastData'], atol=1e-12, rtol=0):
                raise ValueError('Wrong last-data mean ' + entry['date'])
            if int(a['extra__diverging'].sum()) != rec['diagnostics']['divergences']:
                raise ValueError('Divergences ' + entry['date'])
        again = summarize.summarize(fit_dir / f'attempt{est["attempt"]}.npz', rec, inv)
        for k, v in again.items():
            if not summarize.close(v, est[k]):
                raise ValueError(f'Estimate not reproduced from draws: {entry["date"]} {k}')
        if not rec['diagnostics']['passed']:
            raise ValueError('Gates not met')
        prev_panel = d / 'panel.json'; seen.append(entry['date'])
    return seen


def rebuild_check():
    """Re-derive added rows, panel and dataset fingerprint from the raw capture of every committed run (.venv-external)."""
    from . import dataset
    prev_panel = BASE_PANEL
    for entry in load_index()['runs']:
        d = OUT / entry['date']; cap = RAW / entry['date'] / CAPTURE
        rev, _ = capture.revision(entry['date'])
        wiki, unmapped = delta.wiki_rows(cap.read_text(encoding='utf-8'), f'weekly-refresh-{entry["date"]}-wikipedia', rel(cap), sha(cap))
        added, blockers, _, _ = delta.evaluate(read(prev_panel)['records'], wiki, unmapped, entry['date'])
        panel, changes = delta.next_panel(prev_panel, added, entry['date'], rel(cap), sha(cap), rev)
        if blockers or panel != read(d / 'panel.json') or changes != read(d / 'changes.json'):
            raise ValueError('Panel not reproduced ' + entry['date'])
        ds, inv = dataset.build(cap, entry['date'])
        if ds.fingerprint() != read(d / 'inventory.json')['fingerprint'] or inv != read(d / 'inventory.json'):
            raise ValueError('Dataset not reproduced ' + entry['date'])
        prev_panel = d / 'panel.json'
    return [e['date'] for e in load_index()['runs']]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--date', default=None, help='run date (NZ civil date), default today in Pacific/Auckland; also the poll cutoff')
    ap.add_argument('--use-existing-capture', action='store_true', help='reuse data/raw/polling/weekly-refresh/<date>/ already on disk (offline rebuild)')
    ap.add_argument('--skip-fit', action='store_true'); ap.add_argument('--resume', action='store_true', help='finish a run whose fit was accepted but whose summary step was interrupted')
    ap.add_argument('--check', action='store_true'); ap.add_argument('--rebuild-check', action='store_true')
    a = ap.parse_args()
    if a.check:
        print('ok', check()); return 0
    if a.rebuild_check:
        print('ok', rebuild_check()); return 0
    if a.resume:
        return resume(a.date or nz_today())
    return run(a.date or nz_today(), a.skip_fit, a.use_existing_capture)


if __name__ == '__main__':
    sys.exit(main())
