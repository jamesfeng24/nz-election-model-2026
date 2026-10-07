"""Stage69: voting-place notional 2023 baselines on the 2026 general electorates.

python -m scripts.voting_place_notionals.run [--check]

Reads preserved raw bytes, the cached geocodes and the meshblock frame; writes deterministic artifacts to
data/processed/voting-place-notionals/. Does not touch Stage64 outputs or any model stage. Design: docs/stage69-voting-place-notionals.md.
"""
import csv
import io
import math

import numpy as np

from scripts.electorate_baseline.build import nfc, third_party

from . import engine
from .common import (CSV_2023, GEOCODE_RAW, GEOMETRY_2020, GEOMETRY_2025, PREFIX, ROOT, arguments, digest, read, save)
from .frame import FRAME, read_rows
from .allocate import seat_frames
from .parse import candidate_path, general_numbers, parse_file, reconcile
from .places import load_polygons, load_tables, seat_codes
from .sites import locate
from .votes import candidate_labels, candidate_projection, is_cancelled

SEED, DRAWS = 20261006, 1000
NAT, LAB = 'National Party', 'Labour Party'
MAIN = [NAT, LAB, 'Green Party', 'ACT New Zealand', 'New Zealand First Party', 'The Opportunities Party (TOP)', 'Te Pāti Māori']
PARTY_FILE = CSV_2023 + 'party-votes-by-voting-place-%d.csv'
ELECTORATE_PARTY_FILE = CSV_2023 + 'votes-for-registered-parties-by-electorate.csv'
REGISTER = 'data/processed/electorate-baseline/register.json'
ELECTION_2023 = 'data/processed/elections/2023.json'
TALLY = 'data/raw/electorate-baseline/2026-10-06/tallyroom-nz-2025-redistribution-notional.csv'
MATERIAL_MARGIN, MATERIAL_LOG, EXACT_TOLERANCE = 2.0, 0.10, 1e-6
PARTY_ALIASES = {'Leighton Baker Party': 'Leighton Baker', 'New Zealand Loyal': 'NZ Loyal'}


def party_paths():
    return {n: PARTY_FILE % n for n in general_numbers()}


def party_files_present():
    return all((ROOT / p).exists() for p in party_paths().values())


def exact_pairs(rows):
    """(source, target) pairs whose meshblock sets coincide: every meshblock of each lies in the other."""
    by_source, by_target = {}, {}
    for r in rows:
        by_source.setdefault(r['source'], set()).add(r['meshblock'])
        by_target.setdefault(r['target'], set()).add(r['meshblock'])
    return sorted((s, t) for s, m in by_source.items() for t, o in by_target.items() if m == o)


def party_labels():
    rows = list(csv.reader(io.StringIO((ROOT / ELECTORATE_PARTY_FILE).read_text(encoding='utf-8-sig'))))
    head = rows[1]
    return [nfc(c) for c in head[1:head.index('Total Valid Party Votes')]]


def party_projection(table, labels):
    """[C_file x L] 0/1 map from a party-by-place file's columns to the 17 registered parties; totals and informal are dropped."""
    columns = [nfc(c).strip() for c in table['columns']]
    projection = np.zeros((len(columns), len(labels)))
    mapped = set()
    for k, name in enumerate(columns):
        name = PARTY_ALIASES.get(name, name)
        if name in labels:
            projection[k, labels.index(name)] = 1.0
            mapped.add(name)
    if mapped != set(labels):
        raise ValueError('Party columns of file %s do not match the 17 registered parties: %s' % (table['name'], sorted(set(labels) - mapped)))
    return projection


def shares(vector):
    total = float(np.sum(vector))
    return vector / total if total > 0 else vector * math.nan


def margin_points(vector, labels):
    s = shares(vector)
    return 100.0 * (s[labels.index(NAT)] - s[labels.index(LAB)])


def compute_kind(name, kind_tables, projections, labels, located, seats, source_of, poly2025):
    prepared = engine.prepare(kind_tables, projections, located, source_of)
    per_arm, diagnostics = engine.arms(prepared, seats, located, poly2025)
    old_totals = {n: item['matrix'].sum(axis=0) + item['other'] for n, item in prepared.items()}
    targets = {arm: engine.to_targets(per_arm[arm], seats, source_of) for arm in per_arm}
    conservation = max(abs(sum(float(np.sum(v)) for v in targets[arm].values()) - float(sum(np.sum(t) for t in old_totals.values())))
                       for arm in ('V', 'P', 'S'))
    per_seat_ok = max(abs(float(per_arm[arm][n].sum()) - float(old_totals[n].sum())) for arm in ('V', 'P', 'S') for n in prepared)
    column_ok = max(float(np.abs(per_arm[arm][n].sum(axis=0) - old_totals[n]).max()) for arm in ('V', 'P', 'S') for n in prepared)
    return {'kind': name, 'labels': labels, 'prepared': prepared, 'perArm': per_arm, 'targets': targets, 'oldTotals': old_totals,
            'diagnostics': diagnostics, 'conservationNational': conservation, 'conservationOldSeat': per_seat_ok,
            'conservationOldSeatColumns': column_ok}


def run_draws(kinds, seats, located, source_of, labels_by_kind):
    """Seeded uncertainty draws shared across kinds; returns the fixed target order and {kind: array [R x T x L]}.

    Uses the legacy RandomState (MT19937), whose stream numpy guarantees never to change, so regeneration is portable.
    """
    rng = np.random.RandomState(SEED)
    numbers = sorted({n for res in kinds.values() for n in res['prepared']})
    venues = sorted({v for res in kinds.values() for item in res['prepared'].values() for v in item['sites']})
    sources = sorted({source_of[n] for n in numbers})
    all_targets = sorted({t for s in sources for t in seats[s]['targets']})
    index = {t: k for k, t in enumerate(all_targets)}
    prepared_kinds = {k: v['prepared'] for k, v in kinds.items()}
    out = {k: np.zeros((DRAWS, len(all_targets), len(labels_by_kind[k]))) for k in kinds}
    sigma = np.array([located[v]['sigma'] for v in venues])
    for r in range(DRAWS):
        noise = rng.standard_normal((len(venues), 2)) * sigma[:, None]
        jitter = dict(zip(venues, noise))
        population = {s: seats[s]['lower'] + rng.rand(len(seats[s]['lower'])) * (seats[s]['upper'] - seats[s]['lower'])
                      for s in sources}
        lam = float(rng.rand())
        draw = engine.draw(prepared_kinds, seats, located, jitter, population, lam)
        for kind, per_seat in draw.items():
            for t, vec in engine.to_targets(per_seat, seats, source_of).items():
                out[kind][r, index[t]] = vec
    return all_targets, out


def interval(values, probabilities=(5, 50, 95)):
    return [float(x) for x in np.percentile(values, probabilities)]


def catchment_diagnostic(prepared, seats, located):
    """Spearman correlation, per old seat with at least 8 sites, between a site's valid votes and its catchment population."""
    from scipy.stats import spearmanr
    from . import allocate as al
    values = {}
    for n, item in prepared.items():
        if len(item['sites']) < 8:
            continue
        pop = al.catchment_population(seats[item['source']], engine.site_xy(item, located))
        votes = item['matrix'].sum(axis=1)
        values[n] = float(spearmanr(votes, pop).statistic)
    ordered = sorted(values.values())
    return {'seatsWithAtLeast8Sites': len(values), 'medianSpearman': float(np.median(ordered)), 'minSpearman': ordered[0],
            'maxSpearman': ordered[-1],
            'meaning': 'diagnostic only: how well catchment population predicts a place\'s votes; not used in any estimate'}


def place_artifact(located, unlocated, tables, kinds_c, seats, source_of, codes):
    entries = []
    for venue, rec in sorted(located.items()):
        entries.append({'venue': venue, 'tier': rec['tier'], 'query': rec['query'], 'rank': rec['rank'], 'lat': round(rec['lat'], 6),
                        'lon': round(rec['lon'], 6), 'x': round(rec['x'], 1), 'y': round(rec['y'], 1), 'sigmaMetres': rec['sigma'],
                        'osmType': rec['osmType'], 'osmId': rec['osmId'], 'osmClass': rec['osmClass'], 'osmKind': rec['osmKind'],
                        'houseNumber': rec['houseNumber'], 'insideSeats2020': rec['insideSeats']})
    per_seat = []
    for n in sorted(kinds_c['prepared']):
        item = kinds_c['prepared'][n]
        table = tables[n]
        placed = float(item['matrix'].sum())
        unloc = float(item['unlocated'].sum())
        special = float(sum(sum(v[:-2]) for v in table['specials'].values()))
        suppressed = float(sum(table['suppressed'][:-2])) if table['suppressed'] else 0.0
        ordinary = placed + unloc
        d = kinds_c['diagnostics'][n]
        per_seat.append({'fileNumber': n, 'seat': table['name'], 'source2020Code': source_of[n], 'locatedSites': d['sites'],
                         'locatedValidVotes': placed, 'unlocatedPlaceValidVotes': unloc, 'specialValidVotes': special,
                         'fewerThanSixValidVotes': suppressed,
                         'locatedShareOfOrdinaryVotes': placed / ordinary if ordinary else None,
                         'emptyCatchmentSites': d['emptyCatchmentSites'], 'sitesSnappedToNearestEligibleSeat': d['snappedSites']})
    tiers = {}
    for e in entries:
        tiers[e['tier']] = tiers.get(e['tier'], 0) + 1
    tot_placed = sum(s['locatedValidVotes'] for s in per_seat)
    tot_unloc = sum(s['unlocatedPlaceValidVotes'] for s in per_seat)
    return {'schemaVersion': 1, 'stage': 69, 'locatedVenues': len(entries), 'unlocatedNonRovingVenues': sorted(unlocated),
            'tierCounts': dict(sorted(tiers.items())), 'nationalLocatedShareOfOrdinaryCandidateVotes': tot_placed / (tot_placed + tot_unloc),
            'perSeat': per_seat, 'venues': entries}


def target_roster(poly2025, exact):
    """All 64 general targets: code, name, and the source seat if exact."""
    exact_by_target = {t: s for s, t in exact}
    return [{'code': code, 'name': nfc(name), 'exactSource': exact_by_target.get(code)}
            for code, (name, _) in sorted(poly2025.items())]


def stage64_party_shares(labels):
    register = read(REGISTER)
    keys = {p['sourceHeader']: p['partyKey'] for p in read(ELECTION_2023)['electorates'][0]['parties']}
    result = {}
    for target in register['targets']:
        if target['name'] and target.get('boundaryCode') and target['officialDisplayCode'].startswith(('N', 'S')):
            shares = target['partyBaseline']['partyShares']
            result[target['boundaryCode']] = {l: shares[keys[l]]['scenario'] for l in labels}
    return result


def tally_by_name():
    table, _ = third_party()
    return table


def log_ratio(share_a, share_b):
    return math.log(share_a / share_b) if share_a > 0 and share_b > 0 else None


def seat_view(vector, labels):
    s = shares(vector)
    order = np.argsort(-s)
    return {'shares': {l: float(s[k]) for k, l in enumerate(labels)}, 'leader': labels[order[0]], 'second': labels[order[1]],
            'leaderMarginPoints': float(100 * (s[order[0]] - s[order[1]])),
            'nationalMinusLabourPoints': margin_points(vector, labels) if NAT in labels and LAB in labels else None}


def draw_summary(draws, labels, t_index):
    """Quantiles of main-label shares and the National-Labour margin, and the probability each main label leads."""
    block = draws[:, t_index, :]
    total = block.sum(axis=1, keepdims=True)
    share = np.divide(block, total, out=np.zeros_like(block), where=total > 0)
    out = {'shares': {l: interval(share[:, labels.index(l)]) for l in MAIN if l in labels}}
    if NAT in labels and LAB in labels:
        margin = 100 * (share[:, labels.index(NAT)] - share[:, labels.index(LAB)])
        out['nationalMinusLabourPoints'] = interval(margin)
        out['probabilityNationalAheadOfLabour'] = float((margin > 0).mean())
    lead = share.argmax(axis=1)
    out['probabilityLeader'] = {l: float((lead == labels.index(l)).mean()) for l in MAIN if l in labels}
    return out


def kind_artifact(res, roster, draws, all_targets, extras):
    """Per-target notional for one vote kind, arms V/P/S, ordinary-only O, draw summary and comparators."""
    labels = res['labels']
    index = {t: k for k, t in enumerate(all_targets)}
    rows = []
    for t in roster:
        code = t['code']
        if code not in res['targets']['V']:
            rows.append({**t, 'status': 'missing', 'reason': extras.get('missingReason', 'no notional')})
            continue
        row = {**t, 'status': 'ok', 'votes': {arm: {l: float(res['targets'][arm][code][k]) for k, l in enumerate(labels)}
                                             for arm in ('V', 'P', 'S', 'A')},
               'V': seat_view(res['targets']['V'][code], labels), 'P': seat_view(res['targets']['P'][code], labels),
               'S': seat_view(res['targets']['S'][code], labels), 'A': seat_view(res['targets']['A'][code], labels),
               'draws': draw_summary(draws, labels, index[code])}
        if t['exactSource'] is not None:
            row['ordinaryOnlyShares'] = seat_view(res['targets']['O'][code], labels)['shares']
        rows.append(row)
    return rows


def compare_party(rows, labels, w_shares, tally, exact_checks):
    """V against Stage64 (W) and the Tally Room (T) at the 64 general seats; material-difference and agreement counts."""
    out, big, leaders = [], 0, 0
    squares_v, squares_w, agree_v, agree_w, n_t = [], [], 0, 0, 0
    flips = []
    for row in rows:
        if row['status'] != 'ok':
            continue
        code, name = row['code'], row['name']
        w = w_shares[code]
        w_order = sorted(labels, key=lambda l: -w[l])
        v = row['V']['shares']
        margin_w = 100 * (w[NAT] - w[LAB])
        margin_v = row['V']['nationalMinusLabourPoints']
        lr_v = log_ratio(v[w_order[0]], v[w_order[1]])
        lr_w = log_ratio(w[w_order[0]], w[w_order[1]])
        material = {'leaderDiffers': row['V']['leader'] != w_order[0],
                    'marginDiffersPoints': abs(margin_v - margin_w),
                    'topTwoLogRatioDiffers': abs(lr_v - lr_w)}
        material['isMaterial'] = bool(material['leaderDiffers'] or material['marginDiffersPoints'] >= MATERIAL_MARGIN
                                      or material['topTwoLogRatioDiffers'] >= MATERIAL_LOG)
        entry = {'code': code, 'name': name, 'exact': row['exactSource'] is not None, 'wLeader': w_order[0], 'vLeader': row['V']['leader'],
                 'wNationalMinusLabourPoints': margin_w, 'vNationalMinusLabourPoints': margin_v, 'material': material}
        t = tally.get(name)
        if t is None:
            raise ValueError('No Tally Room row for general seat ' + name)
        t1, t2 = nfc(t['partyFirst'][0]).strip(), nfc(t['partySecond'][0]).strip()
        lr_t = log_ratio(t['partyFirst'][1], t['partySecond'][1])
        entry['tally'] = {'first': t1, 'second': t2, 'logRatio': lr_t, 'vLogRatio': log_ratio(v[t1], v[t2]),
                          'wLogRatio': log_ratio(w[t1], w[t2]), 'vLeaderAgrees': row['V']['leader'] == t1,
                          'wLeaderAgrees': w_order[0] == t1}
        entry['tally']['vAbsDiff'] = abs(entry['tally']['vLogRatio'] - lr_t)
        entry['tally']['wAbsDiff'] = abs(entry['tally']['wLogRatio'] - lr_t)
        if not entry['exact']:
            squares_v.append(entry['tally']['vAbsDiff'] ** 2)
            squares_w.append(entry['tally']['wAbsDiff'] ** 2)
            agree_v += entry['tally']['vLeaderAgrees']
            agree_w += entry['tally']['wLeaderAgrees']
            n_t += 1
        if material['isMaterial']:
            big += 1
        if material['leaderDiffers']:
            flips.append(name)
        out.append(entry)
    summary = {'seats': len(out), 'materialSeats': big, 'leaderDiffersSeats': sorted(flips),
               'changedSeatsComparedWithTally': n_t,
               'rmseTopTwoLogRatioVsTallyChangedSeats': {'V': math.sqrt(sum(squares_v) / len(squares_v)),
                                                         'W': math.sqrt(sum(squares_w) / len(squares_w))},
               'leaderAgreesWithTallyChangedSeats': {'V': agree_v, 'W': agree_w}}
    return out, summary


def baseline_artifact(res, roster, labels, arm='V'):
    """Drop-in for the `transitions.2023-2026.scopes.general` fields the nowcast assembly reads from the baseline source.

    Same field names as data/processed/forecast-transport/party-construction.json (`partyCategories`, `nationalSourceSharesExact`,
    `targetPartyVectors[].parties[].shareExact`, `validPartyVotes`), so adopting this baseline is a pointer change plus this file.
    """
    from fractions import Fraction
    keys = {p['sourceHeader']: p['partyKey'] for p in read(ELECTION_2023)['electorates'][0]['parties']}
    order = sorted(labels, key=lambda l: keys[l])
    national = sum(res['oldTotals'].values())
    total = int(round(float(np.sum(national))))
    vectors = []
    for t in roster:
        vector = res['targets'][arm][t['code']]
        valid = float(np.sum(vector))
        parties = []
        for label in order:
            share = float(vector[labels.index(label)]) / valid
            ratio = Fraction(share).limit_denominator(10 ** 15)
            parties.append({'partyKey': keys[label], 'share': share, 'shareExact': {'numerator': ratio.numerator, 'denominator': ratio.denominator}})
        vectors.append({'targetCode': t['code'], 'targetName': t['name'], 'validPartyVotes': valid, 'parties': parties})
    return {'schemaVersion': 1, 'stage': 69, 'arm': arm, 'status': 'voting_place_allocation_not_adopted',
            'partyCategories': [keys[l] for l in order],
            'nationalSourceSharesExact': {keys[l]: {'numerator': int(round(float(national[labels.index(l)]))), 'denominator': total} for l in order},
            'targetPartyVectors': vectors}


def compare_candidate(rows, labels, tally):
    out, squares, agree, n = [], [], 0, 0
    for row in rows:
        if row['status'] != 'ok':
            continue
        t = tally[row['name']]
        c1, c2 = nfc(t['candidateFirst'][0]).strip(), nfc(t['candidateSecond'][0]).strip()
        v = row['V']['shares']
        entry = {'code': row['code'], 'name': row['name'], 'exact': row['exactSource'] is not None, 'vLeader': row['V']['leader'],
                 'tallyFirst': c1, 'tallySecond': c2, 'vLeaderAgrees': row['V']['leader'] == c1}
        if c1 in v and c2 in v and v[c1] > 0 and v[c2] > 0:
            entry['tallyLogRatio'] = log_ratio(t['candidateFirstShare'], t['candidateSecondShare'])
            entry['vLogRatio'] = log_ratio(v[c1], v[c2])
            entry['absDiff'] = abs(entry['vLogRatio'] - entry['tallyLogRatio'])
            if not entry['exact']:
                squares.append(entry['absDiff'] ** 2)
        if not entry['exact']:
            agree += entry['vLeaderAgrees']
            n += 1
        out.append(entry)
    return out, {'changedSeatsCompared': n, 'leaderAgreesWithTallyChangedSeats': agree,
                 'rmseFirstSecondLogRatioChangedSeats': math.sqrt(sum(squares) / len(squares)) if squares else None}


def flows_artifact(kind_c, seats, source_of, roster):
    names = {t['code']: t['name'] for t in roster}
    out = []
    from . import allocate as al
    for n in sorted(kind_c['prepared']):
        item = kind_c['prepared'][n]
        seat = seats[item['source']]
        a = al.population_flow(seat)
        b = kind_c['perArm']['V'][n].sum(axis=1) / kind_c['perArm']['V'][n].sum()
        out.append({'fileNumber': n, 'source2020Code': item['source'],
                    'edges': [{'target': t, 'targetName': names[t], 'populationShare': float(a[k]), 'voteAllocatedShareV': float(b[k])}
                              for k, t in enumerate(seat['targets']) if a[k] > 0 or b[k] > 0]})
    return out


def tally_hypothesis(rows_party, tally, tolerance_points=0.1):
    """At exact seats, ordinary-only shares of the Tally Room's first party against its published percentage."""
    diffs = []
    for row in rows_party:
        if row['status'] != 'ok' or row['exactSource'] is None:
            continue
        t = tally[row['name']]
        first = nfc(t['partyFirst'][0]).strip()
        diffs.append({'seat': row['name'], 'party': first, 'tallyPercent': 100 * t['partyFirst'][1],
                      'ordinaryOnlyPercent': 100 * row['ordinaryOnlyShares'][first],
                      'allVotesPercent': 100 * row['V']['shares'][first]})
    for d in diffs:
        d['ordinaryOnlyAbsDiffPoints'] = abs(d['tallyPercent'] - d['ordinaryOnlyPercent'])
        d['allVotesAbsDiffPoints'] = abs(d['tallyPercent'] - d['allVotesPercent'])
    return {'seats': diffs, 'maxOrdinaryOnlyAbsDiffPoints': max(d['ordinaryOnlyAbsDiffPoints'] for d in diffs) if diffs else None,
            'maxAllVotesAbsDiffPoints': max(d['allVotesAbsDiffPoints'] for d in diffs) if diffs else None,
            'passes': bool(diffs) and max(d['ordinaryOnlyAbsDiffPoints'] for d in diffs) <= tolerance_points}


def exact_seat_checks(res, roster, source_of, number_of_source):
    """V, P and S at exact seats against the official old-seat vector (zero tolerance except float round-off)."""
    worst, count = 0.0, 0
    for t in roster:
        if t['exactSource'] is None:
            continue
        n = number_of_source[t['exactSource']]
        if n not in res['oldTotals']:
            continue  # cancelled Port Waikato candidate table
        official = res['oldTotals'][n]
        for arm in ('V', 'P', 'S'):
            worst = max(worst, float(np.abs(res['targets'][arm][t['code']] - official).max()))
        count += 1
    return {'exactSeatsChecked': count, 'maxAbsVoteDifference': worst, 'passes': worst <= EXACT_TOLERANCE}


def input_paths(party_present):
    paths = [candidate_path(n) for n in range(1, 73)] + [GEOCODE_RAW, FRAME, GEOMETRY_2020, GEOMETRY_2025, REGISTER, ELECTION_2023,
                                                          TALLY, ELECTORATE_PARTY_FILE]
    if party_present:
        paths += [PARTY_FILE % n for n in range(1, 73) if (ROOT / (PARTY_FILE % n)).exists()]
    return sorted(set(paths))


CODE = ['scripts/voting_place_notionals/' + n for n in ('common.py', 'parse.py', 'nztm.py', 'places.py', 'geocode.py', 'sites.py',
                                                       'frame.py', 'votes.py', 'allocate.py', 'engine.py', 'run.py')]


def build():
    all_tables = {n: parse_file(candidate_path(n)) for n in range(1, 73)}
    reconciliation = {}
    for n, table in all_tables.items():
        ok, _ = reconcile(table)
        reconciliation[n] = ok
    tables = {n: all_tables[n] for n in general_numbers()}
    located, unlocated, poly2020, codes = locate(tables)
    rows = read_rows()
    seats = seat_frames(rows)
    source_of = dict(codes)
    if not set(source_of.values()) <= seats.keys() or len(seats) != len(source_of):
        raise ValueError('2020 seat codes of the files and the meshblock frame disagree')
    number_of_source = {c: n for n, c in source_of.items()}
    poly2025_full = load_polygons(GEOMETRY_2025, 2025)
    poly2025 = {code: poly for code, (_, poly) in poly2025_full.items()}
    exact = exact_pairs(rows)
    roster = target_roster(poly2025_full, exact)

    labels_c = candidate_labels(tables)
    cand_tables = {n: t for n, t in tables.items() if not is_cancelled(t)}
    cancelled = sorted(n for n, t in tables.items() if is_cancelled(t))
    cand_proj = {n: candidate_projection(t, labels_c) for n, t in cand_tables.items()}
    res_c = compute_kind('candidate', cand_tables, cand_proj, labels_c, located, seats, source_of, poly2025)
    kinds, labels_by_kind = {'candidate': res_c}, {'candidate': labels_c}
    party_present = party_files_present()
    res_p = None
    if party_present:
        labels_p = party_labels()
        party_tables = {n: parse_file(PARTY_FILE % n) for n in general_numbers()}
        for n, t in party_tables.items():
            ok, _ = reconcile(t)
            reconciliation['party-%d' % n] = ok
        party_proj = {n: party_projection(t, labels_p) for n, t in party_tables.items()}
        res_p = compute_kind('party', party_tables, party_proj, labels_p, located, seats, source_of, poly2025)
        kinds['party'], labels_by_kind['party'] = res_p, labels_p
    all_targets, draws = run_draws(kinds, seats, located, source_of, labels_by_kind)

    tally = tally_by_name()
    missing_tally = [t['name'] for t in roster if t['name'] not in tally]
    if missing_tally:
        raise ValueError('Tally Room join failed for: %s' % missing_tally)

    rows_c = kind_artifact(res_c, roster, draws['candidate'], all_targets, {'missingReason': 'Port Waikato 2023 candidate poll cancelled (candidate death); the published table holds no votes'})
    cand_compare, cand_summary = compare_candidate(rows_c, labels_c, tally)
    artifacts = {
        'places.json': place_artifact(located, unlocated, tables, res_c, seats, source_of, codes),
        'flows.json': {'schemaVersion': 1, 'stage': 69, 'basis': 'candidate valid votes; V arm', 'oldSeats': flows_artifact(res_c, seats, source_of, roster)},
        'notional-candidate.json': {'schemaVersion': 1, 'stage': 69, 'labels': labels_c, 'cancelledFiles': cancelled, 'seats': rows_c},
    }
    checks = {'tablesReconcile': {'all': all(reconciliation.values()), 'count': len(reconciliation), 'failed': sorted(str(k) for k, v in reconciliation.items() if not v)},
              'candidate': {'conservationNationalMaxAbs': res_c['conservationNational'],
                            'conservationOldSeatMaxAbs': res_c['conservationOldSeat'],
                            'conservationOldSeatColumnsMaxAbs': res_c['conservationOldSeatColumns'],
                            'exactSeats': exact_seat_checks(res_c, roster, source_of, number_of_source)},
              'locatedShareOfOrdinaryCandidateVotes': artifacts['places.json']['nationalLocatedShareOfOrdinaryCandidateVotes'],
              'exactSeatPairs': len(exact), 'draws': DRAWS, 'seed': SEED}
    checks['catchmentDiagnostic'] = catchment_diagnostic(res_c['prepared'], seats, located)
    comparison = {'schemaVersion': 1, 'stage': 69, 'candidate': {'summary': cand_summary, 'seats': cand_compare}, 'checks': checks,
                  'partyVoteFilesPresent': party_present}
    if res_p is not None:
        rows_p = kind_artifact(res_p, roster, draws['party'], all_targets, {})
        w = stage64_party_shares(labels_p)
        party_compare, party_summary = compare_party(rows_p, labels_p, w, tally, None)
        official = {}
        for number, table in party_tables.items():
            official[number] = float(sum(table['total'][:len(labels_p)]))
        artifacts['notional-party.json'] = {'schemaVersion': 1, 'stage': 69, 'labels': labels_p, 'seats': rows_p}
        artifacts['baseline-party-vectors.json'] = baseline_artifact(res_p, roster, labels_p)
        checks['party'] = {'conservationNationalMaxAbs': res_p['conservationNational'],
                           'conservationOldSeatMaxAbs': res_p['conservationOldSeat'],
                           'conservationOldSeatColumnsMaxAbs': res_p['conservationOldSeatColumns'],
                           'exactSeats': exact_seat_checks(res_p, roster, source_of, number_of_source),
                           'tallyOrdinaryOnlyHypothesis': tally_hypothesis(rows_p, tally)}
        comparison['party'] = {'summary': party_summary, 'seats': party_compare}
    artifacts['comparison.json'] = comparison
    return artifacts, input_paths(party_present)


def verify_inputs():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage69 consumed input: ' + path)


def main():
    args = arguments()
    if args.check:
        verify_inputs()
    artifacts, paths = build()
    if not args.check:
        save('input-contract.json', {'inputHashes': {p: digest(p) for p in paths}, 'dataSourcesJsonTouched': False,
                                     'registry': PREFIX + '/source-registry.json'})
    for name, value in artifacts.items():
        save(name, value, args.check)
    manifest = {'stage': 69, 'consumedInputs': read(PREFIX + '/input-contract.json')['inputHashes'],
                'derivedArtifacts': {f'{PREFIX}/{n}': digest(f'{PREFIX}/{n}') for n in artifacts},
                'code': {p: digest(p) for p in CODE}, 'dataSourcesJsonTouched': False, 'modelOrScaleChanged': False,
                'stage64OutputsChanged': False, 'hashesAreNotProofOfLinuxReproduction': True}
    save('manifest.json', manifest, args.check)
    print('Stage69 artifacts ok' if args.check else 'wrote %d artifacts' % (len(artifacts) + 2))


if __name__ == '__main__':
    main()
