"""Stage70 dataset: the pinned upstream parse of the preserved tables, exactly as Stage62 arm A, with the new capture and cutoff.
Needs .venv-external. Reuses Stage62 helpers unchanged; nothing in live_fit is edited."""
from datetime import date
import polars as pl
from scripts.polling.live_fit import prepare as P
from scripts.polling.live_fit.common import WINDOWED_YEARS, RAW38
from .common import TARGET_YEAR, RAW


def parse_polls(parse, capture_path):
    polls = []
    for year in WINDOWED_YEARS:
        polls.extend(parse(RAW38 / f'{year}.html', year))
    polls.extend(parse(capture_path, TARGET_YEAR))
    return polls


def build(capture_path, run_date, out_prefix=None):
    cfg, parse, build_table, scraped_fn, ref_fn, verify_fn, build_dataset = P.api()
    polls = parse_polls(parse, capture_path)
    results, scraped, ref = P.results_of(polls, cfg, scraped_fn, ref_fn, verify_fn)
    if TARGET_YEAR in results:
        raise ValueError('A 2026 result must not exist')
    permitted = {y: v for y, v in results.items() if y < TARGET_YEAR}
    cutoff = date.fromisoformat(run_date)
    table = build_table(polls, cfg)
    ds = build_dataset(table, permitted, cfg, TARGET_YEAR, cutoff, lagged=False)
    fake = build_dataset(table, {**permitted, TARGET_YEAR: {'National': .99}}, cfg, TARGET_YEAR, cutoff, lagged=False)
    if fake.fingerprint() != ds.fingerprint():
        raise ValueError('Held-out result dependence')
    if table.filter(pl.col('date_to') > cutoff).height:
        raise ValueError('Poll after the cutoff present in the table')
    if out_prefix is not None:
        out_prefix.parent.mkdir(parents=True, exist_ok=True); ds.save(out_prefix)
    wiki = [p for p in polls if not p.is_election_result and P.is_cycle_2026(p)]
    row = P.dataset_row(ds, table, 'A')
    t26 = table.filter(pl.col('cycle') == TARGET_YEAR)
    ids = t26['poll_id'].unique(maintain_order=True).to_list()
    row['wikipediaRows2026'] = len(wiki)
    row['tablePolls2026'] = len(ids)
    row['excludedByPinnedRules'] = sorted(set(ids) - set(row['pollIds2026']))
    row['pollKeys2026'] = sorted([list(P.poll_key(p)) for p in wiki])
    row['resultsAudit'] = {'scrapedYears': sorted(scraped), 'referenceYears': sorted(ref), 'issues': []}
    return ds, row


def panel_keys(panel):
    return sorted([list(P.key_of({k: v['share'] for k, v in r['estimates'].items() if k in P.KEYS}, date.fromisoformat(r['fieldworkEndBounds'][1])))
                   for r in panel['records'] if r['cycle'] == TARGET_YEAR])
