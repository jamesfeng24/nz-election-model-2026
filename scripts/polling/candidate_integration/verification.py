"""Independent direct arithmetic from cached national draws and official votes."""
import argparse
from math import exp, fsum, isfinite, sqrt
import numpy as np
from scripts.checkpoints.stage25_availability import ELECTIONS
from .common import (
    ROOT, OUT, DESIGN, PARTY, METHODS, PAIRS, read, save, sha,
    verify_inputs, verify_phase, preserve,
)

SHARE_TOL = 1e-12
METRIC_TOL = 2e-9


def close(actual, expected, tolerance):
    if not isfinite(actual) or not isfinite(expected) or abs(actual-expected) > tolerance:
        raise ValueError('Independent arithmetic disagreement')


def average(values):
    values = list(values)
    return fsum(values)/len(values)


def source_affinity(category, source):
    if category['relationship'] == 'entrant':
        if source['sourceLocalShare'] is not None:
            raise ValueError('Unexpected entrant source evidence')
        return 1.
    if category['relationship'] != 'continuing':
        raise ValueError('Unsupported source relation')
    return source['sourceLocalShare']/category['sourceNationalShare']


def exponent(candidate, parameters, means):
    terms = []
    for name, coefficient in parameters['coefficients'].items():
        value = candidate['s0Reported'] if name == 'S' else candidate['R']['broad']['valueFraction']
        if value is not None:
            terms.append(coefficient*(value-means[name]))
    return fsum(terms)


def direct_candidate(fine, roster, affinity, row, parameters, means):
    masses = [x*a for x, a in zip(fine, affinity)]
    total = fsum(masses)
    local = {r['ballotGroupKey']: mass/total for r, mass in zip(roster, masses)}
    intensities = [(local[c['partyBallotGroupKey']] if c['partyBallotGroupKey'] is not None else 0)
                   + parameters['kappa'] for c in row['candidates']]
    intensities = [w*exp(exponent(c, parameters, means)) for c, w in zip(row['candidates'], intensities)]
    total = fsum(intensities)
    return [w/total for w in intensities]


def verify_allocations(inventory, counts):
    results = {}
    for case in inventory['cases']:
        with np.load(ROOT/f"data/processed/polling/external-comparison/fits/{case['year']}/attempt1.npz", allow_pickle=False) as data:
            coarse = data['electionDay'].reshape(-1, len(case['rawCategories']))
        for policy, weights in case['weights'].items():
            saved = read(OUT/f"national/{case['year']}-{policy}.json.gz")
            if saved['drawIds'] != case['nationalDrawIds'] or saved['chainShape'] != case['chainShape']:
                raise ValueError('Independent national draw identity disagreement')
            raw_index = {cid: case['rawCategories'].index(label) for label, cid in case['explicitMapping'].items()}
            fractions = {r['categoryId']: r['allocationFraction'] for r in weights}
            other_index = case['rawCategories'].index('Other')
            for raw, allocated in zip(coarse, saved['arrays']):
                if len(allocated) != len(case['roster']):
                    raise ValueError('Incomplete allocated vector')
                independent = [float(raw[raw_index[r['categoryId']]]) if r['categoryId'] in raw_index
                               else float(raw[other_index])*fractions[r['categoryId']] for r in case['roster']]
                for a, b in zip(independent, allocated):
                    close(a, b, SHARE_TOL)
                    if a < 0:
                        raise ValueError('Negative national allocation')
                close(fsum(allocated), 1., SHARE_TOL)
                close(fsum(v for r, v in zip(case['roster'], allocated) if r['categoryId'] in fractions), float(raw[other_index]), SHARE_TOL)
                counts['nationalVectors'] += 1
            if len(saved['arrays']) != len(coarse):
                raise ValueError('National draw count disagreement')
            results[(case['year'], policy)] = saved['arrays']
    return results


def verify_expected_shares(inventory, construction, fine, design, party, counts):
    rows = {r['targetElectorateId']: r for r in design['contestRecords']}
    source = {r['targetElectorateId']: r for r in party['partyFrame']}
    groups = {r['targetYear']: {c['categoryId']: c for c in r['categories']} for r in party['categoryRelationships']}
    cases = {c['year']: c for c in inventory['cases']}
    checked = []
    for output in construction['cases']:
        case = cases[output['year']]
        records = {r['targetElectorateId']: r for r in output['records']}
        selected = (case['evaluationIds'][0], case['evaluationIds'][-1])
        for cid in selected:
            row = rows[cid]
            source_categories = {r['categoryId']: r for r in source[cid]['sourceCategories']}
            affinity = [source_affinity(groups[case['year']][r['categoryId']], source_categories[r['categoryId']]) for r in case['roster']]
            for model in METHODS:
                parameters = case['fits'][model]['parameters']
                values = [direct_candidate(draw, case['roster'], affinity, row, parameters, case['trainingOnlyMeans'])
                          for draw in fine[(case['year'], output['policy'])]]
                expected = [average(q[j] for q in values) for j in range(len(row['candidates']))]
                for c, q in zip(row['candidates'], expected):
                    close(q, records[cid]['methods'][model]['candidateShares'][c['targetOccurrenceId']], SHARE_TOL)
                    counts['expectedCandidateShares'] += 1
                close(fsum(expected), 1., SHARE_TOL)
                counts['representativeDrawCandidateVectors'] += len(values)
                checked.append({'year': case['year'], 'policy': output['policy'], 'contestId': cid,
                                'model': model, 'fitId': case['fits'][model]['fitId'], 'draws': len(values)})
    return checked


def metric_block(errors):
    absolute = [average(abs(e) for e in block) for block in errors]
    squared = [average(e*e for e in block) for block in errors]
    flat = [e for block in errors for e in block]
    return {'contestEqualMaePP': average(absolute), 'contestEqualRmsePP': sqrt(average(squared)),
            'candidateEqualMaePP': average(abs(e) for e in flat),
            'candidateEqualRmsePP': sqrt(average(e*e for e in flat)),
            'fullSlateSignedBiasPPAccounting': average(flat)}


def verify_scores(construction, evaluation, counts):
    seats = {r['id']: r for year, path in ELECTIONS.items() if year in (2017, 2020, 2023)
             for r in read(ROOT/path)['electorates']}
    scores = {(r['year'], r['policy']): r for r in evaluation['cases']}
    pooled = {}
    for case in construction['cases']:
        saved = scores[(case['year'], case['policy'])]
        scored_rows = {r['targetElectorateId']: r for r in saved['records']}
        errors = {m: [] for m in METHODS}
        for row in case['records']:
            seat = seats[row['targetElectorateId']]
            actual = {c['id']: c['votes']/seat['validCandidateVotes'] for c in seat['candidates']}
            if sum(c['votes'] for c in seat['candidates']) != seat['validCandidateVotes']:
                raise ValueError('Independent candidate denominator disagreement')
            for model in METHODS:
                q = row['methods'][model]['candidateShares']
                if set(q) != set(actual):
                    raise ValueError('Independent complete slate disagreement')
                delta = [100*(q[cid]-actual[cid]) for cid in actual]
                close(average(delta), 0, METRIC_TOL)
                errors[model].append(delta)
                scored = scored_rows[row['targetElectorateId']]['scores'][model]
                close(average(abs(v) for v in delta), scored['contestMaePP'], METRIC_TOL)
                close(average(v*v for v in delta), scored['contestMsePP2'], METRIC_TOL)
                counts['contestMetricChecks'] += 2
        for model in METHODS:
            for key, value in metric_block(errors[model]).items():
                close(value, saved['methods'][model][key], METRIC_TOL)
                counts['foldAndPooledMetricChecks'] += 1
            pooled.setdefault((case['policy'], model), []).extend(errors[model])
        for model, control in PAIRS:
            gains = [average(abs(v) for v in a)-average(abs(v) for v in b)
                     for a, b in zip(errors[control], errors[model])]
            reported = saved['pairs'][model+'__versus__'+control]
            close(average(gains), reported['maeImprovementPP'], METRIC_TOL)
            close(metric_block(errors[control])['contestEqualRmsePP']-metric_block(errors[model])['contestEqualRmsePP'],
                  reported['rmseImprovementPP'], METRIC_TOL)
            counts['pairedComparisonChecks'] += 2
    for case in evaluation['pooled']:
        for model in METHODS:
            for key, value in metric_block(pooled[(case['policy'], model)]).items():
                close(value, case['methods'][model][key], METRIC_TOL)
                counts['foldAndPooledMetricChecks'] += 1
        for model, control in PAIRS:
            delta = metric_block(pooled[(case['policy'], control)])['contestEqualMaePP']-metric_block(pooled[(case['policy'], model)])['contestEqualMaePP']
            close(delta, case['pairs'][model+'__versus__'+control]['maeImprovementPP'], METRIC_TOL)
            counts['pairedComparisonChecks'] += 1


def build():
    verify_inputs(); verify_phase('construction'); verify_phase('evaluation')
    inventory = read(OUT/'inventory.json'); construction = read(OUT/'construction.json')
    evaluation = read(OUT/'evaluation.json'); design = read(DESIGN/'inventory.json'); party = read(PARTY/'input-inventory.json')
    counts = {'nationalVectors': 0, 'expectedCandidateShares': 0, 'representativeDrawCandidateVectors': 0,
              'contestMetricChecks': 0, 'foldAndPooledMetricChecks': 0, 'pairedComparisonChecks': 0}
    fine = verify_allocations(inventory, counts)
    representatives = verify_expected_shares(inventory, construction, fine, design, party, counts)
    verify_scores(construction, evaluation, counts)
    return {'stage': 39, 'counts': counts, 'representativeChecks': representatives,
            'shareTolerance': SHARE_TOL, 'metricTolerancePP': METRIC_TOL,
            'arithmetic': 'scalar direct affinities/intensities and fsum averaging; original official valid-candidate denominators',
            'cutoffScope': 'three cached gauss cases exactly56 days; inferred publication and retrospective roster; election-week target',
            'actualOutcomesRole': 'official candidate votes enter independent scoring only, after sealed prediction checkpoint',
            'inferenceOrRefittingPerformed': False, 'preservedPriorFiles': preserve(),
            'verificationCodeSha256': sha(ROOT/'scripts/polling/candidate_integration/verification.py'),
            'operationalSelection': None}


def run(check=False):
    result = build(); save('independent-verification.json', result, check)
    print('Independent Stage39 checks', result['counts'], 'prior files', result['preservedPriorFiles'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true')
    run(parser.parse_args().check)
