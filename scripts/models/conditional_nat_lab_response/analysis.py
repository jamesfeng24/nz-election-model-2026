"""Chronological source-victory review on a fixed, evidence-independent frame."""
from .common import PARTIES
from .model import MODES, fit, predict, score, training_rows


def assemble(inventory, elections, stage5):
    """Numerical adapter keeps candidate targets separate from predictor fields."""
    by_candidate = {c['id']: (c, seat) for doc in elections.values()
                    for seat in doc['electorates'] for c in seat['candidates']}
    party_inputs = {r['id']: r for r in stage5}
    rows = []
    for entry in inventory['records']:
        if not entry['eligible']:
            continue
        c0, s0 = by_candidate[entry['sourceOccurrenceId']]
        c1, s1 = by_candidate[entry['targetOccurrenceId']]
        for seat in (s0, s1):
            if seat['validCandidateVotes'] <= 0 or seat['validPartyVotes'] <= 0:
                raise ValueError('Missing valid-vote denominator')
        baseline = party_inputs[entry['id']]
        party = entry['party']
        p0 = next(p['votes'] for p in s0['parties'] if p['partyKey'] == party) / s0['validPartyVotes']
        p1 = next(p['votes'] for p in s1['parties'] if p['partyKey'] == party) / s1['validPartyVotes']
        if (baseline['sourceLocalShareLower'] != baseline['sourceLocalShareUpper']
                or abs(p0 - baseline['sourceLocalShare']) > 1e-12
                or abs(p1 - baseline['actualTargetShare']) > 1e-12):
            raise ValueError('Uncertain or changed observed structural party input')
        source, target = c0['votes']/s0['validCandidateVotes'], c1['votes']/s1['validCandidateVotes']
        if not 0 <= source <= 1 or not 0 <= target <= 1:
            raise ValueError('Invalid observed candidate share')
        inputs = {'actual_observed_local_party': [p1, p1]}
        inputs.update({m: [baseline['predictions'][m]['lower'], baseline['predictions'][m]['upper']]
                       for m in MODES[1:]})
        rows.append({'id': entry['id'], 'party': party, 'sourceYear': entry['sourceYear'],
                     'targetYear': entry['targetYear'], 'electorateId': entry['electorateId'],
                     'c0': source, 'c1': target, 'p0': p0, 'x': p1-p0, 'y': target-source,
                     'sourceWon': int(entry['sourcePartySeatWon']), 'partyInputs': inputs})
    return rows


def analyses(rows, spec):
    descriptive, folds = [], []
    for party in PARTIES:
        own = [r for r in rows if r['party'] == party]
        for name, definition in spec['models'].items():
            descriptive.append({'party': party, 'model': name, 'usage': 'full_sample_descriptive_only',
                                'fit': fit(own, definition)})
        for target_year in (2011, 2017, 2023):
            test = [r for r in own if r['targetYear'] == target_year]
            train = training_rows(own, test)
            for name, definition in spec['models'].items():
                fitted = fit(train, definition)
                for mode in MODES:
                    available = fitted['status'] == 'available'
                    predictions = [predict(row, fitted, mode) for row in test] if available else []
                    if available and any(p is None for p in predictions):
                        raise ValueError('Incomplete source-status prediction on frozen full frame')
                    metrics = score(predictions, test) if available else None
                    groups = []
                    if available:
                        for status in (0, 1):
                            subset = [r for r in test if r['sourceWon'] == status]
                            ids = {r['id'] for r in subset}
                            groups.append({'sourceWon': status,
                                'metrics': score([p for p in predictions if p['id'] in ids], subset)})
                    folds.append({'party': party, 'targetYear': target_year, 'mode': mode,
                        'model': name, 'fit': fitted, 'eligibleCount': len(test),
                        'abstentionCount': 0 if available else len(test), 'metrics': metrics,
                        'sourceStatusMetrics': groups, 'predictions': predictions})
    return {'schemaVersion': 1, 'stage': 16, 'descriptiveFits': descriptive, 'folds': folds}


def comparisons(results, rows, spec):
    pairs = spec['primaryComparisons'] + spec['contextComparisons']
    index = {(r['party'], r['targetYear'], r['mode'], r['model']): r for r in results['folds']}
    output = []
    for party in PARTIES:
        for candidate, benchmark in pairs:
            modes = []
            for mode in MODES:
                holdouts, combined = [], {candidate: [], benchmark: []}
                for year in (2017, 2023):
                    c, b = (index[party, year, mode, m] for m in (candidate, benchmark))
                    if c['metrics'] is None or b['metrics'] is None:
                        holdouts.append({'targetYear': year, 'status': 'unavailable'})
                        continue
                    if c['metrics']['recordIds'] != b['metrics']['recordIds']:
                        raise ValueError('Unequal comparison samples')
                    gain = [b['metrics']['maePP'][0]-c['metrics']['maePP'][1],
                            b['metrics']['maePP'][1]-c['metrics']['maePP'][0]]
                    holdouts.append({'targetYear': year, 'status': 'available', 'maeGainPP': gain,
                        'rmseGainPP': [b['metrics']['rmsePP'][0]-c['metrics']['rmsePP'][1],
                                       b['metrics']['rmsePP'][1]-c['metrics']['rmsePP'][0]]})
                    for record in (c, b):
                        combined[record['model']].extend(record['predictions'])
                test_ids = {p['id'] for p in combined[candidate]}
                actual = [r for r in rows if r['id'] in test_ids]
                metrics = {m: score(combined[m], actual) for m in (candidate, benchmark)}
                aggregate = ([metrics[benchmark]['maePP'][0]-metrics[candidate]['maePP'][1],
                              metrics[benchmark]['maePP'][1]-metrics[candidate]['maePP'][0]]
                             if actual else None)
                modes.append({'mode': mode, 'holdouts': holdouts, 'aggregateMetrics': metrics,
                              'aggregateMAEGainPP': aggregate})
            available = [m for m in modes if m['aggregateMAEGainPP'] is not None]
            lower = min((m['aggregateMAEGainPP'][0] for m in available), default=None)
            upper = max((m['aggregateMAEGainPP'][1] for m in available), default=None)
            stable = len(available) == len(MODES) and all(
                len(m['holdouts']) == 2 and all(h['status'] == 'available' and h['maeGainPP'][0] > 0
                                                for h in m['holdouts']) for m in available)
            output.append({'party': party, 'candidateModel': candidate, 'benchmarkModel': benchmark,
                'modes': modes, 'allHoldoutsImproveInEveryMode': stable,
                'minimumAggregateMAEGainPP': lower, 'maximumAggregateMAEGainPP': upper,
                'passesIndicative025Screen': stable and lower is not None and lower >= .25,
                'materialTransformSensitivity': (lower is not None and
                                                  (upper-lower >= .25 or lower < 0 < upper)),
                'notOperationalSelection': True})
    return {'schemaVersion': 1, 'comparisons': output,
            'selectedOperationalBeta': None, 'selectedOperationalSourceVictoryEffect': None}
