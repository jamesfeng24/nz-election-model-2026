"""Stage73 assembly: one deterministic draw bank of national party votes and all 71 winners, fail-closed.

Each bank row is one simulated election: one national draw id feeds the MMP party vote and every general seat's
local party layer; the 2026 layer noise has shared election keys. A seat whose inputs are missing is recorded as
`unavailable` with a reason, never as zero or a default. The bank is publishable only when every gate check passes.
"""
import numpy as np
from scripts.manual_adjustment.schema import seat_frame
from scripts.nowcast_config.validate import check_classification, check_config, ConfigError
from . import fastmath, general, maori, national, streams
from .summaries import share_summaries
from .common import YEAR, OTHER, ROOT, TARGET_FRAME, read, require, digest, file_sha256, AssemblyError

SCHEMA_VERSION = 3


def live_slates(config, features=None, centred=None):
    """{seat: slate} for seats whose 2026 slate is complete, else {seat: reason}. The roster owner is Stage50."""
    if config['roster']['snapshotId'] is None:
        return {}, 'roster.snapshotId is pending (Stage50 final nominations)'
    features = read(config['candidate']['features']) if features is None else features
    centred = (read(config['candidate']['centredFeatures']) if centred is None else centred)['candidates']
    # General seats only: Maori seats come from the Maori layer, never from the general candidate model.
    complete = {s['targetElectorateId'] for s in features['seatRecords'] if s['slateComplete'] and s['scope'] == 'general'}
    slates = {}
    for c in features['candidateRecords']:
        if c['targetElectorateId'] in complete and c['active']:
            value = centred[c['targetOccurrenceId']]
            slates.setdefault(c['targetElectorateId'], []).append(
                {'id': c['targetOccurrenceId'], 'group': c['ballotGroupKey'], 'name': c['displayedName'],
                 'S': value['S'], 'R': value['R']})
    return slates, 'slate incomplete in the configured roster'


def live_classification(config):
    path = config['uncertainty']['classification']
    if not (ROOT / path).exists():
        return None, f'classification file missing: {path} (James, D107)'
    try:
        return check_classification(read(path)), None
    except ConfigError as error:
        raise AssemblyError(f'classification invalid: {error}')


def assemble(config, count, slates=None, classification=None, maori_records=None, workers=1, replicates=1):
    """Return the draw bank. Any injected slates, classification or Maori records mark it a synthetic fixture.

    `count` national draws, each repeated `replicates` times with independent layer noise (Stage63 layer
    replication): row r is national draw r // replicates. Local-party conditional locations depend on the national
    draw only, so the frozen solver's exact-row reuse computes them once per national draw."""
    require(isinstance(replicates, int) and replicates >= 1 and not replicates & (replicates - 1), 'replicates must be a power of two')
    synthetic = any(x is not None for x in (slates, classification, maori_records))
    check_config(config)
    draws, draw_ids, groups = national.load(config, count)
    keys, national2023, base = general.baseline(config)
    continuing = general.relationships(config)
    total = count * replicates
    fine = general.fine_national(np.repeat(draws, replicates, axis=0), groups, keys, national2023, continuing)
    parameters, fit_id = general.fold_parameters(config)
    scale_file = read(config['uncertainty']['scales'])
    party_scales = scale_file['layers']['local_party']['scales']
    candidate_scales = scale_file['layers']['candidate']['scales']
    multipliers = config['uncertainty']['candidateBalanceSeatMultiplier']
    frame = seat_frame()
    general_ids = sorted(frame['general'])
    require(set(base) == set(general_ids), 'baseline seats differ from the 2026 general frame')

    roster_reason = classification_reason = None
    if slates is None:
        slates, roster_reason = live_slates(config)
    if classification is None:
        classification, classification_reason = live_classification(config)

    party_rows, candidate_rows, records = {}, {}, {}
    for seat in general_ids:
        party_rows[seat] = general.party_row(seat, keys, base[seat], national2023, continuing)
        if seat not in slates:
            records[seat] = {'status': 'unavailable', 'reason': roster_reason or 'no slate supplied'}
        elif classification is None:
            records[seat] = {'status': 'unavailable', 'reason': classification_reason}
        else:
            candidate_rows[seat] = general.candidate_row(seat, slates[seat], party_rows[seat], parameters)
    rows = list(party_rows.values()) + list(candidate_rows.values())
    state = {'party': party_rows, 'candidate': candidate_rows, 'fine': fine, 'partyScales': party_scales,
             'candidateScales': candidate_scales, 'multipliers': multipliers, 'classification': classification}
    local_means = {}
    with streams.substituted(rows, total, config['simulation']['seedNamespace']), fastmath.accelerated():
        for seat, (local_mean, record) in zip(general_ids, run_seats(state, general_ids, workers)):
            local_means[seat] = local_mean
            if record is not None:
                records[seat] = record
    records.update(maori.simulate(config, total) if maori_records is None else maori_records)

    seats = [{'electorateId': seat, 'scope': 'general' if seat in frame['general'] else 'maori', **records[seat]}
             for seat in general_ids + sorted(frame['maori'])]
    return {'schemaVersion': SCHEMA_VERSION, 'stage': 73, 'electionYear': YEAR,
            'provenance': 'synthetic-fixture' if synthetic else 'live',
            'configVersion': config['configVersion'], 'estimand': config['estimand'],
            'modelStateAsOf': config['national']['modelStateAsOf'], 'dataCutoff': config['national']['dataCutoff'],
            'nationalStateKey': config['national']['stateKey'],
            'inputs': {'nationalSource': config['national']['source'], 'nationalSha256': file_sha256(config['national']['source']),
                       'baseline': config['baseline']['source'], 'scales': config['uncertainty']['scales'],
                       'candidateFitId': fit_id},
            'draws': total, 'nationalDraws': count, 'layerReplicates': replicates, 'drawIds': draw_ids,
            'partyVote': {'groups': groups, 'otherBucket': OTHER, 'shares': draws.tolist()},
            'seats': seats,
            'directory': directory(config, groups, frame, slates if classification is not None else {}, records),
            'diagnostics': {'reconciliation': reconciliation(config, groups, draws, keys, continuing, local_means)}}


_STATE = {}


def seat_result(seat):
    """One general seat: local party means always; candidate winners when a slate and a class exist."""
    s = _STATE
    candidate = s['candidate'].get(seat)
    kind = s['classification'][seat] if candidate else None
    local, q = general.simulate(s['party'][seat], candidate, s['fine'], s['partyScales'], s['candidateScales'],
                                s['multipliers'][kind] if kind else 1.0)
    if q is None:
        return local.mean(axis=0), None
    require(np.isfinite(q).all() and np.allclose(q.sum(axis=1), 1, atol=1e-9), f'{seat}: candidate shares do not close')
    winner = q.argmax(axis=1)
    return local.mean(axis=0), {'status': 'simulated', 'class': kind, 'multiplier': s['multipliers'][kind],
                                'candidates': candidate['ids'], 'candidateParty': candidate['partyOf'],
                                'candidateShares': share_summaries(candidate['ids'], q),
                                'winners': winner.astype(int).tolist()}



def run_seats(state, seats, workers):
    """Seats are independent given the shared national rows and the substituted stream, so they may run in forked
    worker processes (inheriting the substitution); results are returned in seat order, so output is identical."""
    _STATE.clear()
    _STATE.update(state)
    try:
        if workers == 1:
            return [seat_result(seat) for seat in seats]
        import multiprocessing
        with multiprocessing.get_context('fork').Pool(workers) as pool:
            return pool.map(seat_result, seats, chunksize=1)
    finally:
        _STATE.clear()


def directory(config, groups, frame, slates, records):
    """Display directory for the export: national groups, the 71 electorates and the candidates of simulated seats.
    A candidate whose party has no national group (a minor party inside Other) carries partyId null and its
    ballot-group key in partyLabel, never an invented national share."""
    names = {r['targetGroupKey']: r['registeredName'] for r in read(config['partyRelationships'])['records']}
    display = config['national']['display']
    require(set(display) == set(groups), 'national.display must name every national group')
    parties = [{'partyId': g, 'name': config['national']['otherName'] if g == OTHER else names[g], 'abbreviation': display[g]}
               for g in groups]
    electorates = [{'electorateId': r['targetElectorateId'], 'name': r['canonicalName'], 'kind': r['scope']}
                   for r in read(TARGET_FRAME)['records']]
    require(sorted(e['electorateId'] for e in electorates) == sorted(frame['general'] | frame['maori']), 'target frame differs')
    candidates = []
    for seat, record in records.items():
        if record['status'] != 'simulated':
            continue
        labels = record.get('candidateNames') or [c['name'] for c in slates[seat]]
        for candidate, name, party in zip(record['candidates'], labels, record['candidateParty']):
            candidates.append({'candidateId': candidate, 'name': name, 'electorateId': seat,
                               'partyId': party if party in groups else None, 'partyLabel': party})
    return {'parties': parties, 'electorates': electorates, 'candidates': candidates}


def reconciliation(config, groups, draws, keys, continuing, local_means):
    """Release-gate diagnostic: party-vote-weighted mean of the general-seat local party means against the national
    mean, per core group, in percentage points. General seats only (Maori-roll voters are outside this layer)."""
    scope = read(config['baseline']['source'])['transitions']['2023-2026']['scopes']['general']
    weights = {general.seat_id(t['targetCode']): t['validPartyVotes'] for t in scope['targetPartyVectors']}
    total = sum(weights.values())
    out = {}
    for j, g in enumerate(groups):
        if g == OTHER:
            continue
        columns = [i for i, k in enumerate(keys) if continuing.get(k) == g]
        local = sum(weights[s] * local_means[s][columns].sum() for s in local_means) / total
        out[g] = {'nationalMeanPP': float(100 * draws[:, j].mean()), 'generalSeatWeightedLocalMeanPP': float(100 * local),
                  'gapPP': float(100 * (local - draws[:, j].mean()))}
    return {'byGroup': out, 'maxAbsGapPP': max(abs(v['gapPP']) for v in out.values()),
            'tolerance': None, 'note': 'diagnostic only; the tolerance is set with the publication gate (Stage74)'}


def gate(bank, config):
    """The Python-side publication gate. Returns (passed, checks); MMP, precision and schema checks are Stage74's."""
    frame = seat_frame()
    expected = sorted(frame['general']) + sorted(frame['maori'])
    count = bank['draws']
    checks = []

    def check(name, passed, detail=''):
        checks.append({'check': name, 'passed': bool(passed), 'detail': detail})

    try:
        check_config(config, require_complete=True)
        check('configComplete', True)
    except ConfigError as error:
        check('configComplete', False, str(error))
    check('provenanceLive', bank['provenance'] == 'live', bank['provenance'])
    check('nationalStateKey', bank['nationalStateKey'] == 'lastDataSupport' and bank['estimand'] == 'nowcast')
    national_count = bank['nationalDraws']
    check('oneDrawIdPerRow', len(bank['drawIds']) == national_count == len(set(bank['drawIds'])) == len(bank['partyVote']['shares'])
          and count == national_count * bank['layerReplicates'])
    shares = np.asarray(bank['partyVote']['shares'])
    check('partyVoteSimplex', np.isfinite(shares).all() and (shares >= 0).all() and np.allclose(shares.sum(axis=1), 1, atol=1e-9))
    ids = [s['electorateId'] for s in bank['seats']]
    check('universe71', ids == expected and len(ids) == 71, f'{len(ids)} seats')
    malformed = [s['electorateId'] for s in bank['seats']
                 if not (s['status'] == 'simulated' and len(s['winners']) == count
                         and all(0 <= w < len(s['candidates']) for w in s['winners']))
                 and not (s['status'] == 'unavailable' and s.get('reason'))]
    check('everySeatSimulatedOrExplicitlyUnavailable', not malformed, ', '.join(malformed))
    unavailable = [s['electorateId'] for s in bank['seats'] if s['status'] == 'unavailable']
    check('allWinnersPresent', not unavailable, f'{len(unavailable)} unavailable')
    multipliers = config['uncertainty']['candidateBalanceSeatMultiplier']
    wrong = [s['electorateId'] for s in bank['seats'] if s['scope'] == 'general' and s['status'] == 'simulated'
             and s['multiplier'] != multipliers[s['class']]]
    check('classificationMultipliers', not wrong, ', '.join(wrong))
    tolerance = config['release']['reconciliationTolerancePP']
    gap = bank['diagnostics']['reconciliation']['maxAbsGapPP']
    check('nationalReconciliation', gap <= tolerance, f'max gap {gap:.3f}pp, tolerance {tolerance}pp')
    return all(c['passed'] for c in checks), checks


def staleness(bank, config, as_of):
    """Label components older than the configured windows at the publication date. Stale is labelled, never hidden
    and never a reason to fill or drop a value; the labels go into the snapshot's limitations."""
    import datetime
    day = datetime.date.fromisoformat(as_of)
    windows = config['release']['staleDays']
    age = lambda value: (day - datetime.date.fromisoformat(value)).days
    labels = []
    national = age(bank['modelStateAsOf'])
    if national > windows['nationalState']:
        labels.append(f"National latent state is {national} days old (week of {bank['modelStateAsOf']}); window {windows['nationalState']} days.")
    for seat in bank['seats']:
        end = seat.get('pollFieldworkEnd')
        if end and age(end) > windows['maoriPoll']:
            labels.append(f"{seat['electorateId']}: electorate poll fieldwork ended {end} ({age(end)} days); window {windows['maoriPoll']} days.")
    return labels


def bank_digest(bank):
    return digest({k: v for k, v in bank.items() if k != 'diagnostics'})
