"""Independent direct arithmetic; saved experts are never refitted or blended."""
import argparse
from fractions import Fraction
from math import sqrt
from statistics import mean
from scipy.stats import spearmanr
from .common import *
from scripts.models.complete_party_vector.inventory import evidence


def close(a, b, tolerance, label):
    if a is None or b is None or abs(a-b) > tolerance:
        raise ValueError('Independent Stage34 disagreement: '+label)


def check_distances(movement):
    count = 0
    for row in movement['national']:
        vectors = [(row['sourceAlignedShares'], row['targetAlignedShares'], row['totalVariationFraction'])]
        for x, y, expected in vectors:
            value = float(sum(abs(Fraction(str(x[k]))-Fraction(str(y[k]))) for k in x)/2)
            close(value, expected, 1e-12, 'national TV'); count += 1
    for row in movement['records']:
        if row['status'] != 'available':
            continue
        for field, vector in [('constructedLocalDistance', 'constructedTargetAlignedShares'), ('observedLocalDistance', 'observedTargetAlignedSharesEvaluationOnly')]:
            x, y = row['sourceAlignedShares'], row[vector]
            value = float(sum(abs(Fraction(str(x[k]))-Fraction(str(y[k]))) for k in x)/2)
            close(value, row[field], 1e-12, 'local TV'); count += 1
    return count


def check_errors(analysis, construction, actuals):
    saved = keyed(construction['folds'], 'id'); count = 0
    for f in analysis['folds']:
        predictions = {m: keyed(saved[f['foldId']]['predictions'][m], 'targetElectorateId') for m in METHODS}
        for r in f['records']:
            maes = {}; cid = r['targetElectorateId']; actual = actuals[cid]['candidateShares']
            for m in METHODS:
                q = predictions[m][cid]['candidateShares']; errors = [100*(q[k]-v) for k, v in actual.items()]
                maes[m] = sum(abs(e) for e in errors)/len(errors)
                close(maes[m], r['errors'][m]['maePP'], 1e-9, 'contest MAE')
                close(sum(e*e for e in errors)/len(errors), r['errors'][m]['msePP2'], 1e-9, 'contest MSE')
                count += 1
            close(maes[R]-maes[S], r['Gpp'], 1e-9, 'G sign')
            close(maes[S]-maes[JOINT], r['Jpp'], 1e-9, 'J sign')
    return count


def check_robustness(analysis, evaluation):
    saved = keyed(evaluation['pooled'], 'branch'); count = 0
    for b in analysis['branches']:
        if 'robustness' not in b:
            continue
        cases = [f for f in analysis['folds'] if f['branch']==b['branch'] and f['records']]
        for m, d in b['robustness']['methods'].items():
            folds = [sum(r['errors'][m]['maePP'] for r in f['records'])/len(f['records']) for f in cases]
            center = sum(folds)/len(folds); sd = sqrt(sum((x-center)**2 for x in folds)/len(folds))
            close(center, d['electionMaeDispersion']['equalElectionMeanPP'], 1e-9, 'equal-election mean')
            close(sd, d['electionMaeDispersion']['populationSDPP'], 1e-9, 'population SD')
            close(max(folds)-min(folds), d['electionMaeDispersion']['rangePP'], 1e-9, 'fold range')
            close(d['originalContestEqualPooledMaePP'], saved[b['branch']]['methods'][m]['contestEqualMaePP'], 1e-9, 'Stage33 pooled MAE')
            close(d['originalContestEqualPooledRmsePP'], saved[b['branch']]['methods'][m]['contestEqualRmsePP'], 1e-9, 'Stage33 pooled RMSE')
            count += 5
    return count


def weighted_association(cases, field):
    # Equal mean of each election's covariance/variance, independent from flattened weights.
    xy, xx, yy = [], [], []
    for f in cases:
        rows = [r for r in f['records'] if r['movementStatus']=='available']
        if not rows:
            continue
        x = [r[field] for r in rows]; y = [r['Gpp'] for r in rows]; a, b = mean(x), mean(y)
        xy.append(mean((s-a)*(t-b) for s, t in zip(x, y)))
        xx.append(mean((s-a)**2 for s in x)); yy.append(mean((t-b)**2 for t in y))
    vx, vy, cov = mean(xx), mean(yy), mean(xy)
    return .1*cov/vx, cov/sqrt(vx*vy)


def check_associations(analysis):
    count = 0
    for b in analysis['branches']:
        cases = [f for f in analysis['folds'] if f['branch']==b['branch'] and f['records']]
        for field, result in b['withinElectionCentered'].items():
            slope, correlation = weighted_association(cases, field)
            close(slope, result['slopeGainPPPer10ppMovement'], 1e-9, 'centered slope')
            close(correlation, result['pearson'], 1e-9, 'centered correlation'); count += 2
        for deletion in b['fixedPredictionDeleteOneElection']:
            retained = [f for f in cases if f['targetYear']!=deletion['deletedTargetYear']]
            for field, result in deletion['associations'].items():
                slope, correlation = weighted_association(retained, field)
                close(slope, result['slopeGainPPPer10ppMovement'], 1e-9, 'delete-one centered slope')
                close(correlation, result['pearson'], 1e-9, 'delete-one centered correlation'); count += 2
    return count



def check_preserved_counts(movement, analysis):
    elections = evidence()[0]; n = 0
    for row in movement['national']:
        a, b = elections[row['sourceYear']], elections[row['targetYear']]
        keys = set(a['parties']) | set(b['parties'])
        value = sum(abs((Fraction(a['parties'][k]['votes'], a['nationalValidVotes']) if k in a['parties'] else 0)-
                        (Fraction(b['parties'][k]['votes'], b['nationalValidVotes']) if k in b['parties'] else 0)) for k in keys)/2
        close(float(value), row['totalVariationFraction'], 1e-12, 'raw national denominators'); n += 1
    index = keyed(movement['records'], 'targetElectorateId')
    for fold in analysis['folds']:
        if fold['branch']!='primary' or not fold['records']:
            continue
        row = index[fold['records'][0]['targetElectorateId']]
        a = next(s for s in elections[row['sourceYear']]['scopes']['general'].values() if s['id']==row['sourceElectorateId'])
        b = next(s for s in elections[row['targetYear']]['scopes']['general'].values() if s['id']==row['targetElectorateId'])
        keys = set(a['parties']) | set(b['parties'])
        value = sum(abs((Fraction(a['parties'][k]['votes'], a['validVotes']) if k in a['parties'] else 0)-
                        (Fraction(b['parties'][k]['votes'], b['validVotes']) if k in b['parties'] else 0)) for k in keys)/2
        close(float(value), row['observedLocalDistance'], 1e-12, 'raw local denominators'); n += 1
    return n



def check_rank_associations(analysis):
    count = 0
    for f in analysis['folds']:
        if not f['records']:
            continue
        for field, result in f['associations'].items():
            rows = [r for r in f['records'] if r['movementStatus']=='available']
            coefficient = float(spearmanr([r[field] for r in rows], [r['Gpp'] for r in rows]).statistic)
            close(coefficient, result['spearman'], 1e-9, 'independent tied-rank Spearman'); count += 1
    return count


def build():
    a = local('analysis.json'); e = read(S33+'evaluation.json')
    return {'stage': 34, 'counts': {'distances': check_distances(local('movement.json')),
        'preservedCountDenominatorChecks': check_preserved_counts(local('movement.json'), a),
        'contestModelErrors': check_errors(a, read(S33+'construction.json'), e['evaluationOnlyActuals']),
        'robustnessIdentities': check_robustness(a, e), 'centeredAssociationIdentities': check_associations(a), 'spearmanChecks': check_rank_associations(a)},
        'tolerances': {'distanceFraction': 1e-12, 'errorPP': 1e-9, 'association': 1e-9},
        'method': 'rational_direct_TV; direct_saved_prediction_errors; alternate_environment_covariance_formula; no_fits',
        'priorBytesPreserved': preserve(), 'operationalSelection': None}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); a = p.parse_args()
    verify_inputs(); verify_phase('movement'); verify_phase('analysis')
    result = build(); save('independent-verification.json', result, a.check)
    phase('verification', ['independent-verification.json'], ['verification'], a.check)
    print(result)


if __name__ == '__main__':
    main()
