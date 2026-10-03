"""Thin outcome-separated adapters from canonical Stage25 IDs into existing kernels."""
from copy import deepcopy
from fractions import Fraction
from math import isfinite

from scripts.checkpoints import stage25_availability as available
from scripts.checkpoints import complete_share_features as features
from scripts.checkpoints.complete_share_feature_rank import PROBES, design, rank_details
from scripts.checkpoints.stage22_fit import source_s
from .common import GEO, read, keyed


def datasets():
    return ({y: read(p) for y, p in available.ELECTIONS.items()},
            {y: read(p) for y, p in available.SPLITS.items()})


def inventory(elections, splits, geography, availability, mapping, continuity_rows):
    seats = {y: keyed(doc['electorates'], 'id') for y, doc in elections.items()}
    matrices = {y: keyed(doc['matrices'], 'electorateId') for y, doc in splits.items()}
    mapped = available.mapped_contests(mapping)
    continuity = features.continuity_index(continuity_rows)
    geo = keyed(geography['records'], 'geographyId')
    shares, responses, coverage, witnesses = [], [], [], []
    for item in availability['records']:
        g = geo[item['geographyId']]
        sy, ty = g['sourceYear'], g['targetYear']
        if item['sourceYear'] != sy or item['targetYear'] != ty:
            raise ValueError('Canonical availability/geography mismatch')
        cid = g['targetElectorateId']
        eligible = g['certifiedTwoSidedExact'] and g['scope'] == 'general'
        status = {'geographyId': g['geographyId'], 'targetYear': ty, 'scope': g['scope'],
                  'targetElectorateId': cid, 'candidateCount': len(item['candidateOccurrenceIds']),
                  'originalFrame': g['originalFrame'], 'certifiedTwoSidedExact': g['certifiedTwoSidedExact']}
        reason = ('maori_coverage_only' if g['scope'] != 'general' else
                  'not_certified_two_sided_exact' if not eligible else
                  'cancelled_or_unheld' if g['contestStatus'] == 'cancelled_or_unheld' else None)
        if reason:
            status.update(status='abstain', reason=reason)
            coverage.append(status)
            continue
        source = seats[sy][g['dominantPredecessorId']]
        target = seats[ty][cid]
        candidates, problem = available.target_candidates(mapped.get((ty, cid)), target,
                   {p['partyKey'] for seat in elections[ty]['electorates'] for p in seat['parties']})
        if problem or item['sOnly']['status'] != 'available':
            raise ValueError(f'Pinned available slate no longer supported: {cid}: {problem}')
        matrix = matrices[sy].get(source['id'])
        if matrix is None or matrix.get('behaviouralEvidence') is False:
            raise ValueError('Missing supported source split matrix')
        party_rows = features.source_rows(matrix, source)
        row = {'geographyId': g['geographyId'], 'sourceYear': sy, 'targetYear': ty,
               'sourceElectorateId': source['id'], 'targetElectorateId': cid,
               'scope': g['scope'], 'originalFrame': g['originalFrame'],
               'status': 'constructed', 'reason': None, 'candidates': []}
        for c in candidates:
            f = features._feature(c, source, target, party_rows, matrix, continuity, sy, ty)
            # V is not an authorized feature. None is the unused legacy kernel slot.
            for field in ('sourceCandidateShare', 'sourceCandidateVotes', 'sourceValidCandidateVotes',
                          'vEvidenceTier'):
                f.pop(field, None)
            f['v0'] = None
            original = next(x for x in target['candidates'] if x['id'] == f['targetOccurrenceId'])
            f['originalAffiliation'] = original['party']
            if not isfinite(f['targetPartySupport']) or not 0 <= f['targetPartySupport'] <= 1:
                raise ValueError('Invalid conditional party share')
            if f['s0Reported'] is not None:
                for scenario in ('lower', 'upper'):
                    values = features.coupled_row_witness(party_rows[f['sourcePartyKey']],
                                                         f['sourceCandidateId'], scenario)
                    witnesses.append({'targetOccurrenceId': f['targetOccurrenceId'],
                                      'sourceMatrixId': matrix['id'], 'sourcePartyKey': f['sourcePartyKey'],
                                      'scenario': scenario, 'rowPercentWitness': [str(v) for v in values]})
            row['candidates'].append(f)
        if {c['targetOccurrenceId'] for c in row['candidates']} != set(item['candidateOccurrenceIds']):
            raise ValueError('Canonical occurrence frame changed')
        shares.append(row)
        for r in item['natLab']:
            if r['status'] != 'available':
                continue
            party = r['partyKey']
            sc = [c for c in source['candidates'] if c['partyKey'] == party]
            tc = [c for c in row['candidates'] if c['targetPartyKey'] == party]
            if len(sc) != 1 or len(tc) != 1 or source['validCandidateVotes'] <= 0:
                raise ValueError('Missing unique source candidate or denominator')
            p0 = next(p['votes'] for p in source['parties'] if p['partyKey'] == party) / source['validPartyVotes']
            p1 = tc[0]['targetPartySupport']
            won = int(source['winnerCandidateId'] == sc[0]['id'])
            if bool(won) != r['sourceVictory']:
                raise ValueError('Pinned source victory mismatch')
            responses.append({'id': r['recordId'], 'geographyId': g['geographyId'],
                              'party': party, 'sourceYear': sy, 'targetYear': ty,
                              'electorateId': cid, 'targetOccurrenceId': tc[0]['targetOccurrenceId'],
                              'sourceOccurrenceId': sc[0]['id'], 'originalFrame': g['originalFrame'],
                              'c0': sc[0]['votes'] / source['validCandidateVotes'],
                              'p0': p0, 'x': p1 - p0, 'sourceWon': won,
                              'partyInputs': {'actual_observed_local_party': [p1, p1]}})
        status.update(status='available', reason=None)
        coverage.append(status)
    return {'shareRecords': shares, 'responseRecords': responses,
            'fullFrame': coverage, 'roundingWitnesses': witnesses}


def s_means(rows, scenario):
    numerator = denominator = 0.0
    for row in rows:
        weight = 1 / len(row['candidates'])
        for c in row['candidates']:
            value = source_s(c, scenario)
            if value is not None:
                numerator += value * weight
                denominator += weight
    if not denominator:
        raise ValueError('No supported S training evidence')
    return {'S': numerator / denominator, 'V': 0.0}


def rank_gate(rows, means, scenario):
    updated = deepcopy(rows)
    for r in updated:
        for c in r['candidates']:
            c['s0Reported'] = source_s(c, scenario)
    probes = []
    for kappa in PROBES:
        matrix = design(updated, means, kappa)
        details = rank_details(matrix, [0, 1])
        s = rank_details(matrix, [1])
        probes.append({'kappa': kappa, 'floorAndS': details, 'S': s})
    supported = sum(any(c['s0Reported'] is not None for c in r['candidates']) for r in rows)
    passed = len(rows) >= 20 and supported >= 20 and all(
        p['floorAndS']['rank'] == 2 and not p['floorAndS']['weakCondition']
        and p['S']['rank'] == 1 for p in probes)
    return {'passes': passed, 'contests': len(rows), 'sSupportedContests': supported,
            'probes': probes}


def permitted_fold(fold, records, training_key='trainingIds'):
    key = 'targetElectorateId' if fold['family'] == 'complete_share_baseline_s' else 'id'
    by_id = keyed(records, key)
    train = [by_id[k] for k in fold[training_key]]
    test = [by_id[k] for k in fold['evaluationIds']]
    if set(fold[training_key]) & set(fold['evaluationIds']):
        raise ValueError('Training/evaluation IDs overlap')
    for row in train:
        if row['targetYear'] >= fold['targetYear'] or row['targetYear'] > fold['sourceYear']:
            raise ValueError('Target/later or incomplete training outcome')
        if fold['chronologyProtocol'] == 'more_separated' and row['targetYear'] >= fold['sourceYear']:
            raise ValueError('More-separated chronology violation')
    if any(r['targetYear'] != fold['targetYear'] for r in test):
        raise ValueError('Wrong holdout IDs')
    return train, test


def response_training(rows, elections):
    seats = {s['id']: s for d in elections.values() for s in d['electorates']}
    result = []
    for r in rows:
        seat = seats[r['electorateId']]
        candidate = next(c for c in seat['candidates'] if c['id'] == r['targetOccurrenceId'])
        if seat['validCandidateVotes'] <= 0:
            raise ValueError('Missing training denominator')
        c1 = candidate['votes'] / seat['validCandidateVotes']
        result.append({**r, 'y': c1 - r['c0']})
    return result
