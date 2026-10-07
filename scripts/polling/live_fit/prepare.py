"""Stage62 input build: unchanged pinned upstream parsing of the preserved Wikipedia tables, pre-registered arms,
panel reconciliation and the input contract. Needs .venv-external; reads no 2026 result (none exists)."""
import argparse
import dataclasses
import sys
import tarfile
from datetime import date
from pathlib import Path
from .common import (ROOT, OUT, EXT, RAW38, WIKI2026, PANEL, UPSTREAM, LOCK, PIN, TARGET_YEAR, CUTOFF, WINDOWED_YEARS,
                     ARMS, CODES, read, save, sha, digest)

LAST_ELECTION = date(2023, 10, 14)
KEYS = ('NAT', 'LAB', 'GRN', 'ACT', 'NZF')
NAMES = {'National': 'NAT', 'Labour': 'LAB', 'Green': 'GRN', 'ACT': 'ACT', 'NZ First': 'NZF'}
NUMERICAL_CODE = ['scripts/polling/live_fit/common.py', 'scripts/polling/live_fit/prepare.py', 'scripts/polling/live_fit/inference.py']


def ensure_upstream():
    """Extract the pinned upstream archive on demand and verify every file against the Stage38 contract."""
    if not (UPSTREAM / 'src').exists():
        UPSTREAM.mkdir(parents=True, exist_ok=True)
        with tarfile.open(RAW38 / 'upstream.tar.gz') as tar:
            members = [m for m in tar.getmembers() if m.isfile()]
            for m in members:
                rel = Path(*Path(m.name).parts[1:])
                dest = UPSTREAM / rel; dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(tar.extractfile(m).read())
    contract = read(EXT / 'input-contract.json')
    for path, h in contract['upstreamSource'].items():
        if sha(UPSTREAM / path) != h:
            raise ValueError('Extracted upstream differs from pinned source ' + path)


def api():
    ensure_upstream()
    sys.path.insert(0, str(UPSTREAM / 'src'))
    from pollofpolls.config import Config
    from pollofpolls.data.wikipedia import parse_page_file
    from pollofpolls.prep.polls_table import build_polls_table
    from pollofpolls.data.results import election_results_from_polls, load_reference_results, verify_results
    from pollofpolls.prep.marshal import build_dataset
    return Config(UPSTREAM), parse_page_file, build_polls_table, election_results_from_polls, load_reference_results, verify_results, build_dataset


def key_of(shares, date_to):
    return (date_to.isoformat(),) + tuple(round(100 * shares[k], 1) if shares.get(k) is not None else None for k in KEYS)


def poll_key(p):
    return key_of({NAMES[k]: v for k, v in p.shares.items() if k in NAMES}, p.date_to)


def panel_records():
    return [r for r in read(PANEL)['records'] if r['cycle'] == TARGET_YEAR]


def panel_key(r):
    return key_of({k: v['share'] for k, v in r['estimates'].items() if k in KEYS}, date.fromisoformat(r['fieldworkEndBounds'][1]))


def parse_all(parse):
    polls = []
    for year in WINDOWED_YEARS:
        polls.extend(parse(RAW38 / f'{year}.html', year))
    polls.extend(parse(WIKI2026, TARGET_YEAR))
    return polls


def is_cycle_2026(p):
    return p.mid_date > LAST_ELECTION


def arm_polls(polls, arm):
    """Arm transformation on the parsed poll list (before the pinned table build); results always use all rows."""
    spec = ARMS[arm]
    out = []
    drop = set()
    if spec.get('drop_aggregator_only'):
        drop = {panel_key(r) for r in panel_records() if r.get('evidenceGrade') == 'aggregator_only'}
        if len(drop) != 2:
            raise ValueError('Expected exactly two aggregator_only 2026-cycle panel waves')
    for p in polls:
        if p.is_election_result:
            out.append(p); continue
        if is_cycle_2026(p):
            if spec.get('window') and p.date_to < date.fromisoformat(spec['window']):
                continue
            if drop and poll_key(p) in drop:
                continue
            if spec.get('merge_anacta') and 'anacta' in p.pollster_raw.lower():
                p = dataclasses.replace(p, pollster_raw='Talbot Mills')
        out.append(p)
    return out


def results_of(polls, cfg, scraped_fn, ref_fn, verify_fn):
    scraped = scraped_fn(polls)
    ref = ref_fn(UPSTREAM / 'data/reference/election_results.csv')
    issues = verify_fn(scraped, ref)
    if issues:
        raise ValueError('Bulk/reference result mismatch: ' + str(issues))
    return {y: {**scraped.get(y, {}), **ref.get(y, {})} for y in set(scraped) | set(ref)}, scraped, ref


def reconcile(polls, table, datasets):
    import polars as pl
    wiki = [p for p in polls if not p.is_election_result and is_cycle_2026(p)]
    wiki_keys = sorted(poll_key(p) for p in wiki)
    panel = panel_records()
    panel_keys = sorted(panel_key(r) for r in panel)
    only_panel = [k for k in panel_keys if k not in wiki_keys]
    only_wiki = [k for k in wiki_keys if k not in panel_keys]
    t26 = table.filter(pl.col('cycle') == TARGET_YEAR)
    ids = t26['poll_id'].unique(maintain_order=True).to_list()

    def one(pollster, field_end, **shares):
        sub = t26.filter((pl.col('pollster') == pollster) & (pl.col('date_to') == date.fromisoformat(field_end)))
        got = {r['party']: round(r['share'], 4) for r in sub.iter_rows(named=True)}
        return {'rows': sub['poll_id'].n_unique(), 'matches': all(abs(got.get(k, -1) - v) < 1e-9 for k, v in shares.items())}
    nov = one('Talbot Mills', '2024-11-10', **{'National': .34, 'Labour': .33, 'Green': .10, 'ACT': .10, 'NZ First': .07, 'Te Pāti Māori': .033})
    may = one('Talbot Mills', '2024-05-10', **{'National': .35, 'Labour': .32})
    april = one('Talbot Mills', '2026-04-16', **{'National': .29, 'Labour': .36})
    a = datasets['A']
    included = set(a['pollIds2026'])
    assertions = {'talbotMillsNov2024Present': nov['rows'] == 1 and nov['matches'],
                  'talbotMillsMay2024Present': may['rows'] == 1 and may['matches'],
                  'talbotMillsApril2026ExactlyOnce': april['rows'] == 1 and april['matches'],
                  'wikipediaAndPanelKeysIdentical': not only_panel and not only_wiki and len(panel_keys) == len(wiki_keys)}
    if not all(assertions.values()):
        raise ValueError('Stage59-correction assertions failed; an overlay must be frozen before any fit: ' + str(assertions))
    sponsored = sorted({(p.pollster_raw, p.date_text) for p in wiki if p.pollster_raw.startswith(('Labour–', 'National–'))})
    return {'panelWaves2026': len(panel), 'wikipediaRows2026': len(wiki), 'keysOnlyInPanel': only_panel, 'keysOnlyInWikipedia': only_wiki,
            'tablePolls2026': len(ids), 'excludedSponsoredReleases': [list(x) for x in sponsored],
            'excludedByMinPollsRule': sorted(set(ids) - included),
            'datasetPolls2026': len(included), 'assertions': assertions,
            'aggregatorOnlyPanelWaves': [list(panel_key(r)) for r in panel if r.get('evidenceGrade') == 'aggregator_only'],
            'panelSha256': sha(PANEL), 'panelBase': read(PANEL)['basePanelSha256'],
            'note': 'Panel waves 2026 cycle versus parsed Wikipedia rows (fieldwork end plus rounded NAT/LAB/GRN/ACT/NZF); the pinned pipeline then excludes sponsored releases and pollsters with fewer than min_polls eligible polls.'}


def dataset_row(ds, table, arm):
    import polars as pl
    c = ds.n_cycles - 1
    ids = [pid for pid, ci in zip(ds.poll_ids, ds.cycle_idx) if ci == c]
    info = {r['poll_id']: r for r in table.select('poll_id', 'pollster', 'date_text', 'sample_size', 'sample_reported', 'segment').unique(subset=['poll_id']).to_dicts()}
    return {'arm': arm, 'fingerprint': ds.fingerprint(), 'polls': ds.N, 'polls2026': len(ids), 'pollIds2026': ids,
            'pollInfo2026': [{'id': i, 'pollster': info[i]['pollster'], 'fieldwork': info[i]['date_text'], 'n': int(info[i]['sample_size']),
                              'nReported': bool(info[i]['sample_reported']), 'segment': int(info[i]['segment'])} for i in ids],
            'parties': ds.parties, 'codes': [CODES[p] for p in ds.parties], 'pollsters': ds.pollsters, 'houses': ds.houses,
            'cycles': ds.cycle_years, 'anchorYears': ds.election_years, 'weeks': ds.T, 'lastDataWeek': ds.weeks[ds.last_data_t].isoformat(),
            'targetWeek': ds.weeks[ds.target_t].isoformat(), 'lastDataIndex': int(ds.last_data_t), 'targetIndex': int(ds.target_t),
            'errorScale': ds.error_scale.tolist(), 'cutoff': ds.cutoff.isoformat()}


def run(check=False):
    cfg, parse, build, scraped_fn, ref_fn, verify_fn, build_dataset = api()
    polls = parse_all(parse)
    results, scraped, ref = results_of(polls, cfg, scraped_fn, ref_fn, verify_fn)
    if TARGET_YEAR in results:
        raise ValueError('A 2026 result must not exist')
    permitted = {y: v for y, v in results.items() if y < TARGET_YEAR}
    cutoff = date.fromisoformat(CUTOFF)
    rows = {}; tables = {}
    for arm in ('A', 'B1', 'B2', 'E', 'T'):
        table = build(arm_polls(polls, arm), cfg); tables[arm] = table
        ds = build_dataset(table, permitted, cfg, TARGET_YEAR, cutoff, lagged=False)
        if arm == 'A':
            # information-set counterfactuals: a fake 2026 result and any post-cutoff poll cannot change the dataset
            fake = build_dataset(table, {**permitted, TARGET_YEAR: {'National': .99}}, cfg, TARGET_YEAR, cutoff, lagged=False)
            if fake.fingerprint() != ds.fingerprint():
                raise ValueError('Held-out result dependence')
            import polars as pl
            if table.filter(pl.col('date_to') > cutoff).height:
                raise ValueError('Poll after the cutoff present in the table')
        prefix = OUT / 'datasets' / arm
        if check:
            from pollofpolls.prep.marshal import Dataset
            if Dataset.load(prefix).fingerprint() != ds.fingerprint():
                raise ValueError('Dataset changed ' + arm)
        else:
            prefix.parent.mkdir(parents=True, exist_ok=True); ds.save(prefix)
        rows[arm] = dataset_row(ds, tables[arm], arm)
    rec = reconcile(polls, tables['A'], rows)
    save('reconciliation.json', rec, check)
    save('inventory.json', {'pin': PIN, 'cutoff': CUTOFF, 'lagged': False, 'targetYear': TARGET_YEAR, 'arms': rows,
                            'resultsAudit': {'scrapedYears': sorted(scraped), 'referenceYears': sorted(ref), 'issues': []},
                            'informationSet': 'preserved Wikipedia tables parsed by the pinned upstream code; poll fieldwork dates as listed; every poll on the page treated as published by the cutoff'}, check)
    contract = {'attribution': 'upstream pollofpolls (GPL-3.0-or-later) retained in data/raw/polling/stage38; this stage reads it, unchanged',
                'pin': PIN, 'cutoff': CUTOFF,
                'sha256': {**{f'data/raw/polling/stage38/{y}.html': sha(RAW38 / f'{y}.html') for y in WINDOWED_YEARS},
                           'data/raw/polling/stage38/upstream.tar.gz': sha(RAW38 / 'upstream.tar.gz'),
                           'data/raw/polling/current-2026-primary/wikipedia-opinion-polling-2026.html': sha(WIKI2026),
                           'data/processed/polling/panel-update-2026-10/panel.json': sha(PANEL),
                           'data/processed/polling/external-comparison/input-contract.json': sha(EXT / 'input-contract.json'),
                           'requirements-external.lock': sha(LOCK)},
                'numericalCode': {p: sha(ROOT / p) for p in NUMERICAL_CODE},
                'datasets': {f'datasets/{a}.{e}': sha(OUT / 'datasets' / f'{a}.{e}') for a in rows for e in ('npz', 'json')},
                'stage38Dataset2017': {e: sha(EXT / f'datasets/2017.{e}') for e in ('npz', 'json')}}
    save('input-contract.json', contract, check)
    print({a: (r['polls'], r['polls2026'], r['fingerprint'][:12]) for a, r in rows.items()}, rec['assertions'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); run(p.parse_args().check)
