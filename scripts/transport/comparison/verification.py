"""Independent raw-component, fixed-fit and score arithmetic; no principal runner."""
import argparse
from fractions import Fraction
from math import exp, fsum, sqrt
from statistics import mean
from .common import BRANCHES, PREFIX, read, save, verify

TOLERANCE = 1e-12


def centered_feature(feature, center):
    masses = [Fraction(c['partyMassExact']) for c in feature['components']]
    total = sum(masses, Fraction())
    if total <= 0:
        return 0.0
    return fsum(float(m / total) * (c['valueFraction'] - center)
        for m, c in zip(masses, feature['components']) if c['valueFraction'] is not None)


def independent_prediction(row, fit, means, branch):
    params = fit['parameters']
    keys = ('S',) if branch == 'S' else ('S', 'RStrict' if branch == 'joint_strict' else 'R')
    values = []
    for candidate in row['candidates']:
        features = [centered_feature(candidate['continuous'][k], means['S' if k == 'S' else 'R']) for k in keys]
        values.append((candidate['observedPartySupport'] + params['kappa']) * exp(fsum(t * x for t, x in zip(params['theta'], features))))
    total = fsum(values)
    return {c['targetOccurrenceId']: w / total for c, w in zip(row['candidates'], values)}


def score_independently(predicted, target, row):
    actual = {c['id']: c['votes'] / target['validCandidateVotes'] for c in target['candidates']}
    if set(predicted) != set(actual):
        raise ValueError('Independent scoring slate mismatch')
    errors = {cid: 100 * (q - actual[cid]) for cid, q in predicted.items()}
    highest = max(predicted.values())
    winners = sorted(cid for cid, q in predicted.items() if highest - q <= TOLERANCE)
    winner = target['winnerCandidateId']
    runner_level = max(q for cid, q in actual.items() if cid != winner)
    runners = [cid for cid, q in actual.items() if cid != winner and abs(q - runner_level) <= TOLERANCE]
    gap = actual[winner] - runner_level
    margin_errors = [100 * (predicted[winner] - predicted[cid] - gap) for cid in runners]
    sorted_prediction = sorted(predicted.values(), reverse=True)
    return {'contestMaePP': mean(abs(e) for e in errors.values()),
        'contestMsePP2': mean(e * e for e in errors.values()), 'errors': errors,
        'fullSlateBiasPPAccounting': mean(errors.values()), 'predictedWinnerSet': winners,
        'uniqueCorrect': len(winners) == 1 and winners[0] == winner,
        'tieContainsWinner': len(winners) > 1 and winner in winners,
        'actualTopTwoMarginAbsoluteErrorPP': mean(abs(e) for e in margin_errors),
        'actualTopTwoMarginSignedErrorPP': mean(margin_errors),
        'predictedTopTwoGapAbsoluteErrorPP': 100 * abs(sorted_prediction[0] - sorted_prediction[1] - gap)}


def aggregate_independently(scores):
    errors = [e for s in scores for e in s['errors'].values()]
    return {'contests': len(scores), 'candidates': len(errors),
        'contestEqualMaePP': mean(s['contestMaePP'] for s in scores),
        'contestEqualRmsePP': sqrt(mean(s['contestMsePP2'] for s in scores)),
        'candidateEqualMaePP': mean(abs(e) for e in errors),
        'candidateEqualRmsePP': sqrt(mean(e * e for e in errors)),
        'fullSlateSignedBiasPPAccounting': mean(errors),
        'uniqueCorrect': sum(s['uniqueCorrect'] for s in scores),
        'uniqueWinnerAccuracyAllContests': mean(s['uniqueCorrect'] for s in scores),
        'uniquePredictionCount': sum(len(s['predictedWinnerSet']) == 1 for s in scores),
        'tieCount': sum(len(s['predictedWinnerSet']) > 1 for s in scores),
        'tieInclusionCount': sum(s['tieContainsWinner'] for s in scores),
        'actualTopTwoMarginMaePP': mean(s['actualTopTwoMarginAbsoluteErrorPP'] for s in scores),
        'actualTopTwoMarginBiasPP': mean(s['actualTopTwoMarginSignedErrorPP'] for s in scores),
        'predictedTopTwoGapMaePP': mean(s['predictedTopTwoGapAbsoluteErrorPP'] for s in scores)}


def member(candidate, name, branch):
    group = candidate['partyBallotGroupKey']
    if name in ('R_supported', 'R_unsupported'):
        support = candidate['continuous']['R']['supportedWeight'] > 0
        return support if name == 'R_supported' else not support
    return name == ('national' if group == 'nationalparty' else 'labour' if group == 'labourparty'
        else 'affirmative_no_party_group' if group is None else 'other_mapped')


def verify_summary(rows, saved, check):
    if not rows:
        check(saved['contests'], 0)
        return
    metrics = {b: aggregate_independently([r['scores'][b] for r in rows]) for b in BRANCHES}
    for branch, calculated in metrics.items():
        for key, value in calculated.items():
            check(saved['metrics'][branch][key], value)
    for branch in ('joint', 'joint_strict'):
        differences = [r['scores'][branch]['contestMaePP'] - r['scores']['S']['contestMaePP'] for r in rows]
        pair = saved['pairs'][branch]
        check(pair['jointMinusSMaePP'], mean(differences))
        check(pair['jointMinusSRmsePP'], metrics[branch]['contestEqualRmsePP'] - metrics['S']['contestEqualRmsePP'])
        for key, value in (('improvedContests', sum(v < 0 for v in differences)),
                           ('worsenedContests', sum(v > 0 for v in differences)),
                           ('unchangedContests', sum(v == 0 for v in differences))):
            check(pair[key], value)
        for recorded, row, difference in zip(pair['pairedContests'], rows, differences):
            if recorded['targetElectorateId'] != row['row']['targetElectorateId']:
                raise ValueError('Independent paired IDs differ')
            check(recorded['jointMinusSMaePP'], difference)
            check(recorded['jointMinusSMsePP2'], row['scores'][branch]['contestMsePP2'] - row['scores']['S']['contestMsePP2'])
    for name, group in saved['groups'].items():
        for branch in BRANCHES:
            blocks = [[r['scores'][branch]['errors'][c['targetOccurrenceId']] for c in r['row']['candidates']
                if member(c, name, branch)] for r in rows]
            errors = [e for block in blocks for e in block]
            check(group['counts'][branch]['candidates'], len(errors))
            check(group['counts'][branch]['presentContests'], sum(bool(block) for block in blocks))
            if errors:
                for key, value in (('maePP', mean(abs(e) for e in errors)),
                                   ('rmsePP', sqrt(mean(e * e for e in errors))), ('biasPP', mean(errors))):
                    check(group['metrics'][branch][key], value)
    for name, support in saved['support'].items():
        blocks = [[c['continuous'][name]['supportedWeight'] for c in r['row']['candidates']] for r in rows]
        weights = [w for block in blocks for w in block]
        for key, value in (('candidatesWithSupportedMass', sum(w > 0 for w in weights)),
                           ('candidateEqualMeanSupportedMass', mean(weights)),
                           ('contestEqualMeanSupportedMass', mean(mean(block) for block in blocks)),
                           ('contestsWithAnySupportedMass', sum(any(w > 0 for w in block) for block in blocks))):
            check(support[key], value)


def build():
    construction = read(PREFIX + '/construction.json')
    evaluation = read(PREFIX + '/evaluation.json')
    inventory = read('data/processed/continuous-transport/inventory.json')
    originals = {r['targetElectorateId']: r for r in inventory['records']}
    maxima = {'prediction': 0.0, 'arithmetic': 0.0}
    counts = {'vectors': 0, 'candidatePredictions': 0, 'arithmeticChecks': 0, 'rankingSets': 0}

    def check(recorded, calculated):
        difference = abs(recorded - calculated)
        maxima['arithmetic'] = max(maxima['arithmetic'], difference)
        counts['arithmeticChecks'] += 1
        if difference > TOLERANCE:
            raise ValueError('Independent arithmetic mismatch: ' + str((recorded, calculated)))

    all_rows = []
    summaries = []
    for fold, evaluated in zip(construction['folds'], evaluation['folds']):
        year = fold['targetYear']
        targets = {s['id']: s for s in read(f'data/processed/elections/{year}.json')['electorates']}
        saved = {b: {p['targetElectorateId']: p for p in fold['predictions'][b]} for b in BRANCHES}
        rows = []
        for cid, reference in saved['S'].items():
            row = originals[cid]
            scores = {}
            for branch in BRANCHES:
                q = independent_prediction(row, fold['fits']['S' if branch == 'S' else 'joint'], fold['trainingOnlyMeans'], branch)
                expected = saved[branch][cid]['candidateShares']
                if q.keys() != expected.keys():
                    raise ValueError('Independent prediction IDs differ')
                difference = max(abs(q[k] - expected[k]) for k in q)
                maxima['prediction'] = max(maxima['prediction'], difference)
                if difference > TOLERANCE:
                    raise ValueError('Independent prediction mismatch')
                counts['vectors'] += 1
                counts['candidatePredictions'] += len(q)
                scores[branch] = score_independently(q, targets[cid], row)
            rows.append({'row': row, 'scores': scores})
        recorded_rows = {r['targetElectorateId']: r for r in evaluated['records']}
        for row in rows:
            for branch in BRANCHES:
                expected = recorded_rows[row['row']['targetElectorateId']]['scores'][branch]
                calculated = row['scores'][branch]
                if expected['predictedWinnerSet'] != calculated['predictedWinnerSet']:
                    raise ValueError('Independent winner/tie mismatch')
                counts['rankingSets'] += 1
                for key in ('contestMaePP', 'contestMsePP2', 'fullSlateBiasPPAccounting',
                            'actualTopTwoMarginAbsoluteErrorPP', 'actualTopTwoMarginSignedErrorPP',
                            'predictedTopTwoGapAbsoluteErrorPP'):
                    check(expected[key], calculated[key])
        samples = {'full': rows, **{t: [r for r in rows if r['row']['transportTier'] == t]
            for t in ('exact', 'approximate_95', 'approximate_90', 'fallback')}}
        samples['cumulative95'] = [r for r in rows if r['row']['transportTier'] in ('exact', 'approximate_95')]
        for key in ('R', 'RStrict'):
            for has in (True, False):
                samples[key + ('_any' if has else '_none')] = [r for r in rows
                    if any(c['continuous'][key]['supportedWeight'] > 0 for c in r['row']['candidates']) == has]
        for name, sample in samples.items():
            verify_summary(sample, evaluated['samples'][name], check)
        metrics = {b: aggregate_independently([r['scores'][b] for r in rows]) for b in BRANCHES}
        summaries.append({'targetYear': year, 'maePP': {b: m['contestEqualMaePP'] for b, m in metrics.items()},
            'jointMinusSMaePP': metrics['joint']['contestEqualMaePP'] - metrics['S']['contestEqualMaePP']})
        all_rows.extend(rows)
    verify_summary(all_rows, evaluation['pooled'], check)
    for branch in BRANCHES:
        fold_metrics = [aggregate_independently([r['scores'][branch] for r in all_rows
            if r['row']['targetYear'] == y]) for y in (2014, 2020)]
        check(evaluation['equalElection']['metrics'][branch]['maePP'], mean(m['contestEqualMaePP'] for m in fold_metrics))
        check(evaluation['equalElection']['metrics'][branch]['rmsePP'], sqrt(mean(m['contestEqualRmsePP'] ** 2 for m in fold_metrics)))
    for branch in ('joint', 'joint_strict'):
        check(evaluation['equalElection']['jointMinusSMaePP'][branch], mean(aggregate_independently([r['scores'][branch] for r in all_rows if r['row']['targetYear'] == y])['contestEqualMaePP'] - aggregate_independently([r['scores']['S'] for r in all_rows if r['row']['targetYear'] == y])['contestEqualMaePP'] for y in (2014, 2020)))
    return {'stage': 43, 'method': 'raw exact party masses and source values; plain math.exp; independently implemented metrics/groups/rankings/margins',
        'principalConstructionOrEvaluationFunctionsImported': False, 'tolerance': TOLERANCE,
        'counts': counts, 'maximumDifferencesRounded12Decimals': {k: round(v, 12) for k, v in maxima.items()},
        'agreementWithin1eMinus12': True, 'foldSummariesRounded12Decimals': [
            dict(s, maePP={k: round(v, 12) for k, v in s['maePP'].items()}, jointMinusSMaePP=round(s['jointMinusSMaePP'], 12)) for s in summaries]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    verify()
    value = build()
    save('independent-verification.json', value, args.check)
    print(value['counts'], 'independent agreement within1e-12')


if __name__ == '__main__':
    main()
