"""Stage51 incumbent changes joined to Stage7 residuals, with the frozen inclusion rules (no scoring)."""
import math
import unicodedata
from collections import Counter, defaultdict
from .common import ELECTIONS, LEDGER, OCCURRENCES, STAGE10_INVENTORY, design, read


def fold_name(name):
    return unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()


def occurrence_index():
    return {r['candidateOccurrenceId']: r for r in read(OCCURRENCES)['records']}


def finite(value):
    return value is not None and math.isfinite(value)


def rows():
    """One row per ledger seat: both residuals, transition facts and the frozen sample flags."""
    spec = design()['sample']
    occ = occurrence_index()
    primary, extended = spec['primary'], spec['extendedSensitivity']
    no_list = set(spec['excludeNoListOnlySensitivity']['primaryMinusTags'])
    out = []
    for r in sorted(read(LEDGER)['records'], key=lambda x: x['key']):
        transition = r.get('transition') or {}
        target = r.get('primaryTargetCandidate')
        r_old = occ[r['sourceWinner']['occurrenceId']].get('normalizedPremium')
        r_new = occ[target['occurrenceId']].get('normalizedPremium') if target else None
        both = finite(r_old) and finite(r_new)
        kind, tags = transition.get('transitionType'), sorted(transition.get('tags', []))
        change = r['relation'] == 'candidate_change'
        reasons = []
        if change:
            if r['scope'] != primary['scope']:
                reasons.append('maori_scope')
            if kind not in primary['transitionTypes']:
                reasons.append('type_' + kind)
            reasons += ['tag_' + t for t in tags if t in primary['excludedTags']]
            if not both:
                reasons.append('missing_residual')
        is_primary = change and not reasons
        is_extended = (change and r['scope'] == extended['scope'] and kind in extended['transitionTypes'] and both)
        out.append({
            'key': r['key'], 'party': r['party'], 'scope': r['scope'], 'relation': r['relation'],
            'sourceYear': r['sourceYear'], 'targetYear': r['targetYear'], 'seat': r['key'].split('|')[2],
            'transitionType': kind, 'tags': tags,
            'sourceOccurrenceId': r['sourceWinner']['occurrenceId'],
            'targetOccurrenceId': target['occurrenceId'] if target else None,
            'RoldFraction': r_old, 'RnewFraction': r_new,
            'primary': is_primary, 'extended': is_extended,
            'primaryNoListOnly': is_primary and not (set(tags) & no_list),
            'continuationReference': (r['relation'] == 'continuation' and r['scope'] == 'general' and both),
            'exclusionReasons': reasons})
    return out


SAMPLES = ('primary', 'extended', 'primaryNoListOnly')


def select(table, name, below=None):
    selected = [r for r in table if r[name]]
    return [r for r in selected if below is None or r['targetYear'] < below]


def summarise(table):
    change = [r for r in table if r['relation'] == 'candidate_change']
    by_type = Counter((r['scope'], r['transitionType']) for r in change)
    excluded = Counter()
    for r in change:
        if r['primary']:
            continue
        for reason in (r['exclusionReasons'] or ['unreasoned']):
            excluded[reason] += 1
    pair = Counter((r['sourceYear'], r['targetYear']) for r in table if r['primary'])
    maori = [r for r in table if r['scope'] == 'maori']
    in_any = [r['key'] for r in maori if r['primary'] or r['extended'] or r['primaryNoListOnly'] or r['continuationReference']]
    return {'ledgerSeats': len(table), 'candidateChanges': len(change),
            'continuations': sum(r['relation'] == 'continuation' for r in table),
            'maoriExcludedByElectorateType': {
                'rows': len(maori), 'candidateChanges': sum(r['relation'] == 'candidate_change' for r in maori),
                'continuations': sum(r['relation'] == 'continuation' for r in maori),
                'rowsInAnySampleOrReference': in_any,
                'filter': 'ledger scope (electorate type), never party',
                'seats': [{'key': r['key'], 'party': r['party'], 'relation': r['relation'], 'transitionType': r['transitionType']}
                          for r in maori]},
            'changesByScopeAndType': {f'{a}:{b}': n for (a, b), n in sorted(by_type.items())},
            'primary': sum(r['primary'] for r in table), 'extended': sum(r['extended'] for r in table),
            'primaryNoListOnly': sum(r['primaryNoListOnly'] for r in table),
            'continuationReference': sum(r['continuationReference'] for r in table),
            'primaryByPair': {f'{a}-{b}': n for (a, b), n in sorted(pair.items())},
            'changesExcludedFromPrimaryByReason': dict(sorted(excluded.items()))}


def stage10_gap(table):
    """Why some ledger seats are absent from the Stage10 inventory (verifiable, no inference beyond names)."""
    inventory = read(STAGE10_INVENTORY)['records']
    general = {y: sorted(e['name'] for e in read(p)['electorates'] if e['kind'] == 'general') for y, p in ELECTIONS.items()}
    inventory_seats = defaultdict(set)
    for r in inventory:
        if r['electorateType'] == 'general':
            inventory_seats[(r['sourceYear'], r['targetYear'])].add(r['electorateName'])
    pairs, ledger_hits = [], []
    for (s, t) in ((2008, 2011), (2011, 2014), (2014, 2017), (2017, 2020), (2020, 2023)):
        missing = sorted(set(general[s]) - inventory_seats[(s, t)])
        target_names = {fold_name(n): n for n in general[t]}
        detail = []
        for name in missing:
            folded = fold_name(name)
            exact = name in general[t]
            detail.append({'seat': name, 'inTargetElectionByExactName': exact,
                           'accentFoldedMatchInTargetElection': target_names.get(folded) if not exact else name,
                           'cause': ('target_name_differs_only_by_macron' if (not exact and folded in target_names
                                                                                and target_names[folded] != name)
                                     else 'not_a_same_named_seat_in_target_election' if not exact else 'exact_name_present')})
        pairs.append({'sourceYear': s, 'targetYear': t, 'generalSeatsInSourceElection': len(general[s]),
                      'seatsInStage10Inventory': len(inventory_seats[(s, t)]), 'missing': detail})
        folded_missing = {d['seat'] for d in detail}
        for r in table:
            if (r['sourceYear'], r['targetYear']) == (s, t) and r['scope'] == 'general' and r['seat'] in folded_missing:
                ledger_hits.append({'key': r['key'], 'relation': r['relation'], 'transitionType': r['transitionType'],
                                    'primary': r['primary'], 'RoldPP': 100 * r['RoldFraction'], 'RnewPP': 100 * r['RnewFraction']
                                    if r['RnewFraction'] is not None else None})
    return {'method': 'general-seat names of each source election compared with the Stage10 inventory records of the same '
                      'transition, then with accent-folded target-election names',
            'pairs': pairs, 'ledgerRowsInMissingSeats': sorted(ledger_hits, key=lambda h: h['key'])}
