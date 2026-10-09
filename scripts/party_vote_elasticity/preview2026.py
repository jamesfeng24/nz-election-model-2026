"""Stage81 2026 readout (general seats only): what each arm does to the live local party layer. Not part of the adoption rule
except the materiality override. The Maori seats are not run (their fallback is not yet wired)."""
import copy
import numpy as np
from scripts.nowcast_assembly import assemble, general, national
from scripts.nowcast_assembly.common import CONFIG, read
from scripts.nowcast_config.validate import check_classification
from .transforms import swing

NORTHLAND = 'Northland'
CLASSIFICATION = 'data/source-plans/party-vote-elasticity/classification-pr104-copy.json'  # byte copy of PR #104's list (James, D107)


def setting(arm_or_arms):
    if isinstance(arm_or_arms, str):
        return {'transform': arm_or_arms}
    return {'transform': 'mixture', 'arms': list(arm_or_arms)}


def deterministic(config, arms, count=4096):
    """At the national mean: per arm, general seats with National ahead of Labour on party vote, the mean lead change,
    and each seat's leading group."""
    draws, _, groups = national.load(config, count)
    keys, national2023, base = general.baseline(config)
    continuing = general.relationships(config)
    fine = general.fine_national(draws.mean(axis=0, keepdims=True), groups, keys, national2023, continuing)
    seats = sorted(base)
    role = [general.role(continuing.get(k, k)) if k in continuing else 'other' for k in keys]
    nat = [i for i, r in enumerate(role) if r == 'national']
    lab = [i for i, r in enumerate(role) if r == 'labour']
    group_of = [continuing.get(k, f'source2023:{k}') for k in keys]
    names = {r['targetElectorateId']: r['canonicalName'] for r in read('data/processed/forecast-readiness/snapshots/2026-10-05/target-frame.json')['records']}
    out = {'nationalMeanShares': {g: float(draws[:, j].mean()) for j, g in enumerate(groups)}, 'arms': {}}
    start = {s: base[s] for s in seats}
    margin0 = np.array([start[s][nat].sum() - start[s][lab].sum() for s in seats])
    lead_group = {}
    for arm in arms:
        q = {s: swing(arm, base[s], national2023, fine)[0] for s in seats}
        margin = np.array([q[s][nat].sum() - q[s][lab].sum() for s in seats])
        top = {}
        for s in seats:
            totals = {}
            for k, v in zip(group_of, q[s]):
                totals[k] = totals.get(k, 0.0) + v
            top[s] = max(totals, key=totals.get)
        lead_group[arm] = top
        out['arms'][arm] = {'seatsNationalAheadOfLabour': int((margin > 0).sum()),
                            'meanMarginChangePP': float(100 * (margin - margin0).mean()),
                            'meanMargin2023PP': float(100 * margin0.mean()), 'meanMarginNowPP': float(100 * margin.mean()),
                            'northland': {g: float(sum(v for k, v in zip(group_of, q['nz-general-2026-boundary-' + _code(base, names, NORTHLAND)]) if k == g))
                                          for g in sorted(set(group_of))}}
    differing = [s for s in seats if len({lead_group[a][s] for a in arms}) > 1]
    counts = [out['arms'][a]['seatsNationalAheadOfLabour'] for a in arms]
    out['seatsWhoseTopGroupDiffers'] = [names.get(s, s) for s in differing]
    out['nationalAheadRange'] = max(counts) - min(counts)
    out['invariance'] = {'invariant': (max(counts) - min(counts) <= 2) and not differing, 'arms': list(arms),
                         'nationalAheadCounts': dict(zip(arms, counts)), 'seatsWhoseTopGroupDiffers': len(differing)}
    return out


def _code(base, names, name):
    return next(s for s in base if names.get(s) == name).split('-')[-1]


def simulated(config, labels, count=512, workers=4):
    """Development-size run of the live general-seat layer with common random numbers across settings."""
    result = {}
    for label, spec in labels.items():
        cfg = copy.deepcopy(config)
        if spec is not None:
            cfg['localParty'] = setting(spec)
        bank = assemble.assemble(cfg, count, classification=check_classification(read(CLASSIFICATION)), workers=workers)
        seats = {}
        for s in bank['seats']:
            if s['scope'] != 'general' or s['status'] != 'simulated':
                continue
            winners = np.array(s['winners'])
            party = np.array(s['candidateParty'], dtype=object)[winners]
            seats[s['electorateId']] = {p: float((party == p).mean()) for p in sorted(set(party.tolist()))}
            seats[s['electorateId']]['_candidates'] = {c: float((winners == i).mean()) for i, c in enumerate(s['candidates']) if (winners == i).any()}
        result[label] = {'seats': seats, 'reconciliationMaxAbsGapPP': bank['diagnostics']['reconciliation']['maxAbsGapPP'],
                         'draws': bank['draws']}
    return result
