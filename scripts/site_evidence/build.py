"""Stage84 public-site evidence: the polls the forecast rests on, and the national model's weekly trend.

Reads the preserved weekly-refresh outputs (panel, estimate, dataset) and the electorate-poll run the configuration pins
(`seatPolls.electorateRun`, the run the forecast itself reads), and writes one deterministic JSON file that the release publisher
embeds in the forecast snapshot (`--evidence`). Nothing is fitted and no number is invented: poll figures are copied as published,
missing values stay null, and a seat poll names its source page from the poll's own reference. Whether the forecast used a poll is
decided by the forecast's own readers (`scripts.seat_polls.live.combine` for general seats, the latest poll by fieldwork end for Maori
seats), so the site cannot list a poll the model did not read or hide one it did.

    python3 -m scripts.site_evidence.build --refresh data/processed/polling/weekly-refresh/2026-10-07
    python3 -m scripts.site_evidence.build --refresh data/processed/polling/weekly-refresh/2026-10-07 --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / 'data' / 'processed' / 'site-evidence'
SCHEMA_VERSION = 1
ELECTION_2023 = '2023-10-15'

# Panel category codes to export party ids (config/nowcast-2026.json and the draw-bank directory).
PARTY_IDS = {'NAT': 'nationalparty', 'LAB': 'labourparty', 'GRN': 'greenparty', 'ACT': 'actnewzealand', 'NZF': 'newzealandfirstparty',
             'TPM': 'tepatimaori', 'MRI': 'tepatimaori', 'TOP': 'opportunity', 'OTH': 'other'}
POLL_ORDER = ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'MRI', 'TOP']
# Used only for a poll the Wikipedia table no longer carries (a collapsed duplicate); every other poll keeps the table's own label.
POLLSTER_NAMES = {'Verian lineage': 'Verian', 'Talbot Mills/UMR': 'Talbot Mills'}
WIKIPEDIA_TITLE = 'Opinion_polling_for_the_2026_New_Zealand_general_election'
CONFIG = 'config/nowcast-2026.json'
TARGET_FRAME = 'data/processed/forecast-readiness/snapshots/2026-10-05/target-frame.json'
# Poll column codes -> ballot-group keys of the official candidate roster; IND is an independent (no group), OTH is not a candidate.
POLL_GROUPS = {'NAT': 'nationalparty', 'LAB': 'labourparty', 'GRN': 'greenparty', 'ACT': 'actnewzealand', 'NZF': 'newzealandfirstparty',
               'TOP': 'opportunity', 'TPM': 'tepatimaori', 'IND': None}
POLL_LABELS = {'NAT': 'National', 'LAB': 'Labour', 'GRN': 'Greens', 'ACT': 'ACT', 'NZF': 'NZ First', 'TOP': 'TOP', 'TPM': 'Te Pāti Māori',
               'IND': 'Independent', 'OTH': 'Other'}
OUTLETS = {'nzherald.co.nz': 'NZ Herald', 'thepost.co.nz': 'The Post', 'taxpayers.org.nz': "Taxpayers' Union", 'rnz.co.nz': 'RNZ',
           'thespinoff.co.nz': 'The Spinoff', 'teaonews.co.nz': 'Te Ao News', 'newsroom.co.nz': 'Newsroom', 'stuff.co.nz': 'Stuff'}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def number(value) -> float | None:
    return None if value is None else float(value)


FAMILY = {'Verian lineage': 'Verian', 'Talbot Mills/UMR': 'Talbot Mills'}


def valid_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def midpoint(start: str, end: str) -> str:
    """The fieldwork midpoint the model's dataset uses; a start with no stated day falls back to the end date."""
    a, b = valid_date(start), valid_date(end)
    assert b is not None, f'fieldwork end {end!r} is not a date'
    return (a + (b - a) / 2).isoformat() if a is not None else b.isoformat()


def used_flags(panel: dict, dataset: dict) -> dict[str, bool]:
    """Which 2026-cycle panel records are in the model's dataset, matched by pollster family and fieldwork midpoint."""
    left = Counter((pid.split('|')[0], pid.split('|')[1]) for pid, mid in zip(dataset['poll_ids'], dataset['mid_dates']) if mid >= ELECTION_2023)
    flags = {}
    for r in panel['records']:
        if r['cycle'] != 2026:
            continue
        key = (FAMILY.get(r['pollster'], r['pollster']), midpoint(r['fieldworkRaw'][0], r['fieldworkRaw'][-1]))
        flags[r['id']] = left[key] > 0
        if flags[r['id']]:
            left[key] -= 1
    assert sum(left.values()) == 0, f'dataset polls with no panel record: {dict(+left)}'
    return flags


def wikipedia_labels(capture: dict) -> dict[str, str]:
    """Panel record id to the poll's name as the Wikipedia table prints it (for example "Taxpayers' Union–Curia"), from the preserved capture."""
    from scripts.polling.weekly_refresh.delta import wiki_rows
    path = ROOT / capture['rawPath']
    assert sha256(path) == capture['sha256'], 'the preserved Wikipedia capture does not match the fit\'s recorded hash'
    rows, unmapped = wiki_rows(path.read_text(encoding='utf-8'), 'site-evidence', capture['rawPath'], capture['sha256'])
    assert not unmapped, 'unmapped Wikipedia rows'
    return {r['id']: r['commissioner'].strip() for r in rows}


def national_polls(panel: dict, used: dict[str, bool], labels: dict[str, str]) -> list[dict]:
    out = []
    for r in panel['records']:
        if r['cycle'] != 2026:
            continue
        start, end = r['fieldworkRaw'][0], r['fieldworkRaw'][-1]
        start = start if valid_date(start) and start != end else None
        shares = []
        for code in POLL_ORDER:
            est = r['estimates'][code]
            reported = est['status'] != 'not_reported' and est.get('share') is not None
            shares.append({'partyId': PARTY_IDS[code], 'percent': round(100 * est['share'], 3) if reported else None,
                           'approximate': str(est.get('published', '')).startswith('~')})
        other = r.get('publishedOther') or {}
        shares.append({'partyId': 'other', 'percent': round(100 * other['share'], 3) if other.get('share') is not None else None,
                       'approximate': str(other.get('published', '')).startswith('~') and other.get('share') is not None})
        out.append({'id': r['id'], 'pollster': labels.get(r['id']) or POLLSTER_NAMES.get(r['pollster'], r['pollster']), 'commissioner': None,
                    'fieldworkStart': start, 'fieldworkEnd': end, 'sampleSize': r.get('sampleSize'),
                    'shares': shares, 'publisherUrl': None, 'usedInModel': used[r['id']],
                    'note': None if used[r['id']] else "Listed by Wikipedia but not in the model's data set"})
    out.sort(key=lambda p: (p['fieldworkEnd'], p['id']), reverse=True)
    return out


def trend(estimate: dict, dataset: dict) -> dict:
    path = estimate['pathWeekly']
    n = len(path['meanPP'])
    start = dataset['last_data_t'] - n + 1
    weeks = dataset['weeks'][start:start + n]
    assert len(weeks) == n and weeks[-1] == estimate['lastDataWeek'], 'path weeks do not end at the last data week'
    codes = estimate['codes']
    parties = []
    for i, code in enumerate(codes):
        parties.append({'partyId': PARTY_IDS[code], 'mean': [row[i] for row in path['meanPP']],
                        'lower90': [row[i] for row in path['q05PP']], 'upper90': [row[i] for row in path['q95PP']]})
    return {'basis': "The national model's weekly estimate of true support, from the 2023 election result to the week of the last poll data. "
                     'It is built from the polls and is not an average of them. The band is the 90% range.',
            'weeks': weeks, 'parties': parties}


def outlet(url: str) -> str:
    host = re.sub(r'^www\.', '', re.match(r'https?://([^/]+)', url).group(1))
    return OUTLETS.get(host, host)


def roster(config: dict) -> dict[str, list[dict]]:
    """{target electorate id: active official candidates (displayed name, ballot-group key)}, from the configured nominations file."""
    out: dict[str, list[dict]] = {}
    for r in load(ROOT / config['candidate']['features'])['candidateRecords']:
        if r['active']:
            out.setdefault(r['targetElectorateId'], []).append({'name': r['displayedName'], 'group': r['ballotGroupKey']})
    return out


def poll_results(poll: dict, people: list[dict]) -> list[dict]:
    """Each poll share, named by the one active official candidate of the seat on that party's ballot line (an independent line only when
    the seat has exactly one independent). A share that names no single candidate keeps the party's own name, so nothing is guessed."""
    flags = poll['electorateVoteFlags']
    results = []
    for code, percent in sorted(poll['electorateVotePct'].items(), key=lambda kv: (-kv[1], kv[0])):
        group = POLL_GROUPS.get(code)
        found = [p for p in people if p['group'] == group] if code in POLL_GROUPS else []
        results.append({'name': found[0]['name'] if len(found) == 1 else POLL_LABELS.get(code, code),
                        'party': code if code != 'OTH' else None, 'percent': percent, **({'approximate': True} if flags.get(code) == 'approx' else {})})
    return results


def seat_polls(as_of: str) -> tuple[list[dict], dict[str, str]]:
    """Every seat poll of the pinned electorate-poll run, general and Maori, with whether and why the forecast used it, and the run's hash.

    General seats: `seat_polls.live.combine` is the forecast's own reader and decides use (eligibility, the data cutoff, merging within a
    source); Maori seats: the latest poll by fieldwork end up to the data cutoff is the layer's one input and earlier ones are superseded."""
    from scripts.maori_seat_layer import live as maori_live
    from scripts.polling import electorate_live
    from scripts.seat_polls import live as general_live
    from scripts.seat_polls.common import fold

    config = load(ROOT / CONFIG)
    run, sha = electorate_live.pinned(config)
    assert run, 'the configuration pins no electorate-poll run, so there is no seat poll evidence to list'
    polls = electorate_live.polls(run, sha)
    people = roster(config)
    seat_ids = general_live.seat_ids()
    maori_ids = {fold(r['canonicalName']): r['targetElectorateId'] for r in load(ROOT / TARGET_FRAME)['records'] if r['scope'] == 'maori'}
    _, detail = general_live.combine(as_of, rows=general_live.live_rows(run, sha))
    general_status = {rec['pollId']: rec for seat in detail.values() for rec in seat}
    latest: dict[str, tuple] = {}
    for poll in polls:
        if poll['type'] == 'maori' and poll['fieldwork']['end'] <= as_of:
            key = (poll['fieldwork']['end'], poll['id'])
            if poll['seat'] not in latest or key > latest[poll['seat']]:
                latest[poll['seat']] = key
    out = []
    for poll in polls:
        seat = poll['seat']
        if poll['type'] == 'maori':
            target = maori_ids[fold(maori_live.seat_name(seat))]
            if poll['fieldwork']['end'] > as_of:
                used, reason = False, 'fieldwork ended after the data cutoff'
            elif latest[seat] == (poll['fieldwork']['end'], poll['id']):
                used, reason = True, None
            else:
                used, reason = False, 'superseded by a newer poll for the seat'
        else:
            target = seat_ids[fold(seat)]
            record = general_status[poll['id']]
            used, reason = record['status'] == 'used', record['reason']
        out.append({'electorateName': seat, 'pollster': poll['pollster'], 'commissioner': None,
                    'fieldworkStart': poll['fieldwork']['start'], 'fieldworkEnd': poll['fieldwork']['end'], 'published': None,
                    'sampleSize': poll['sampleSize'], 'marginOfError': None, 'results': poll_results(poll, people[target]),
                    'usedInModel': used, 'note': None if used else reason[0].upper() + reason[1:],
                    'sources': [{'label': outlet(url), 'url': url} for url in poll['references']]})
    out.sort(key=lambda p: (p['electorateName'], p['fieldworkEnd'], p['pollster']))
    return out, {f'{electorate_live.LIVE}/{run}/polls.json': sha}


def forecast_cutoff(national_cutoff: str) -> str:
    """The date the forecast is as of: the configuration's (it can be later than the national cutoff after an electorate-only refresh) when the
    configuration adopts this national refresh, else the refresh's own cutoff."""
    from scripts.polling import electorate_live

    config = load(ROOT / CONFIG)
    return electorate_live.forecast_cutoff(config) if config['national']['dataCutoff'] == national_cutoff else national_cutoff


def build(refresh_dir: Path) -> dict:
    panel, estimate, dataset = (load(refresh_dir / f) for f in ('panel.json', 'estimate.json', 'dataset.json'))
    capture = estimate['capture']
    inputs = {rel(refresh_dir / f): sha256(refresh_dir / f) for f in ('panel.json', 'estimate.json', 'dataset.json')}
    used = used_flags(panel, dataset)
    polls = national_polls(panel, used, wikipedia_labels(capture))
    cutoff = forecast_cutoff(estimate['dataCutoff'])
    seat, seat_inputs = seat_polls(cutoff)
    inputs.update(seat_inputs)
    inputs[capture['rawPath']] = capture['sha256']
    assert sum(p['usedInModel'] for p in polls) == estimate['polls2026'], 'the polls marked used are not the polls the fit used'
    return {
        'schemaVersion': SCHEMA_VERSION, 'refreshDate': panel['refreshDate'], 'dataCutoff': cutoff,
        'modelStateAsOf': estimate['modelStateAsOf'],
        'source': {'label': 'Wikipedia, Opinion polling for the 2026 New Zealand general election (volunteer-edited aggregator; text CC BY-SA)',
                   'url': f"https://en.wikipedia.org/w/index.php?title={WIKIPEDIA_TITLE}&oldid={capture['revision']}",
                   'revision': str(capture['revision']), 'retrieved': capture['lastModified']},
        'nationalPolls': polls, 'trend': trend(estimate, dataset), 'seatPolls': seat, 'inputs': inputs,
    }


def render(evidence: dict) -> str:
    return json.dumps(evidence, ensure_ascii=False, indent=1, sort_keys=True) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--refresh', required=True, help='a weekly-refresh directory, for example data/processed/polling/weekly-refresh/2026-10-07')
    parser.add_argument('--check', action='store_true', help='re-derive and compare with the saved file instead of writing')
    args = parser.parse_args(argv)
    refresh = (ROOT / args.refresh).resolve()
    evidence = build(refresh)
    target = OUT_DIR / evidence['refreshDate'] / 'evidence.json'
    text = render(evidence)
    if args.check:
        if not target.exists() or target.read_text(encoding='utf-8') != text:
            print(f'MISMATCH: {rel(target)} is missing or differs from a fresh derivation', file=sys.stderr)
            return 1
        print(f'ok: {rel(target)} reproduced ({len(evidence["nationalPolls"])} national polls, {len(evidence["seatPolls"])} seat polls)')
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')
    print(f'wrote {rel(target)} ({len(evidence["nationalPolls"])} national polls, {len(evidence["seatPolls"])} seat polls)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
