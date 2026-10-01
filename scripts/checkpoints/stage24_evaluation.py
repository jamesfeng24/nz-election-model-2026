"""Evaluate fixed Stage24 four-cell candidate input substitution."""
import argparse
from collections import defaultdict
from hashlib import sha256
import math
from statistics import mean

from scripts.checkpoints.stage24_common import (
    PREFIX, STAGE22, STAGE23, digest, encode, read, verify_contract,
    write_or_check,
)

CELLS = ('A', 'B', 'C', 'D')
SCENARIOS = ('printed', 'selected_lower', 'selected_upper')
TIE_TOL = 1e-12
PARTY_BINS = ('<=-5', '(-5,-2]', '(-2,0]', '(0,2]', '(2,5]', '>5')


def group_names(candidate):
    party = candidate['partyBallotGroupKey']
    if party == 'nationalparty':
        return ('national', 'national_labour')
    if party == 'labourparty':
        return ('labour', 'national_labour')
    if party is None:
        return ('affirmative_no_party_group',)
    return ('other_mapped',)


def party_error_bin(value):
    if value <= -5:
        return PARTY_BINS[0]
    if value <= -2:
        return PARTY_BINS[1]
    if value <= 0:
        return PARTY_BINS[2]
    if value <= 2:
        return PARTY_BINS[3]
    if value <= 5:
        return PARTY_BINS[4]
    return PARTY_BINS[5]


def winner_set(shares):
    highest = max(shares.values())
    return sorted(cid for cid, value in shares.items() if highest - value <= TIE_TOL)


def candidate_error_row(candidate, predicted, observed):
    cid = candidate['candidateOccurrenceId']
    return {'candidateOccurrenceId': cid,
            'errorPP': 100 * (predicted[cid] - observed[cid]),
            'groups': group_names(candidate),
            'partyBallotGroupKey': candidate['partyBallotGroupKey']}


def score_contest(predicted, actual, candidates):
    observed = actual['candidateShares']
    candidate_ids = [c['candidateOccurrenceId'] for c in candidates]
    if (len(set(candidate_ids)) != len(candidate_ids) or
            set(predicted) != set(observed) or set(predicted) != set(candidate_ids) or
            abs(sum(predicted.values()) - 1) > 1e-12 or
            abs(sum(observed.values()) - 1) > 1e-9):
        raise ValueError('Four-cell candidate slate or conservation mismatch')
    errors = [candidate_error_row(c, predicted, observed) for c in candidates]
    winners = winner_set(predicted)
    actual_winner = actual['winnerCandidateId']
    if actual_winner not in observed:
        raise ValueError('Actual winner absent from complete slate')
    actual_margin = observed[actual_winner] - max(v for cid, v in observed.items()
                                                  if cid != actual_winner)
    predicted_margin = predicted[actual_winner] - max(v for cid, v in predicted.items()
                                                        if cid != actual_winner)
    return {'contestMaePP': mean(abs(c['errorPP']) for c in errors),
            'contestMsePP2': mean(c['errorPP'] ** 2 for c in errors),
            'candidateErrors': errors,
            'predictedWinnerSet': winners,
            'uniqueCorrect': len(winners) == 1 and winners[0] == actual_winner,
            'tieContainsWinner': len(winners) > 1 and actual_winner in winners,
            'marginErrorPP': 100 * abs(predicted_margin - actual_margin)}


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def range_without_one(values):
    if len(values) < 2:
        return None
    total = sum(values)
    results = [(total - value) / (len(values) - 1) for value in values]
    return [min(results), max(results)]


def score_cells(rows):
    if not rows:
        return None
    n = len(rows)
    candidates = {cell: [c for row in rows for c in row['cells'][cell]['candidateErrors']]
                  for cell in CELLS}
    result = {}
    for cell in CELLS:
        scores = [row['cells'][cell] for row in rows]
        errors = [c['errorPP'] for c in candidates[cell]]
        result[cell] = {
            'contests': n, 'candidates': len(errors),
            'contestEqualMaePP': mean(s['contestMaePP'] for s in scores),
            'contestEqualRmsePP': math.sqrt(mean(s['contestMsePP2'] for s in scores)),
            'candidateEqualMaePP': mean(abs(e) for e in errors),
            'candidateEqualRmsePP': math.sqrt(mean(e * e for e in errors)),
            'fullSlateSignedBiasPPAccountingCheck': mean(errors),
            'uniquePredictedWinnerCount': sum(len(s['predictedWinnerSet']) == 1 for s in scores),
            'uniqueCorrectCount': sum(s['uniqueCorrect'] for s in scores),
            'uniqueWinnerAccuracyAllContests': sum(s['uniqueCorrect'] for s in scores) / n,
            'predictedTieCount': sum(len(s['predictedWinnerSet']) > 1 for s in scores),
            'tieContainsWinnerCount': sum(s['tieContainsWinner'] for s in scores),
            'meanAbsoluteActualWinnerMarginErrorPP': mean(s['marginErrorPP'] for s in scores),
        }
        if abs(result[cell]['fullSlateSignedBiasPPAccountingCheck']) > 1e-8:
            raise ValueError('Full-slate candidate share bias does not conserve')
    return result


def paired_row(row):
    m = {cell: row['cells'][cell]['contestMaePP'] for cell in CELLS}
    q = {cell: row['cells'][cell]['contestMsePP2'] for cell in CELLS}
    return {'targetElectorateId': row['targetElectorateId'],
            'sObservedMaeDifferencePP': m['B'] - m['A'],
            'sPredictedMaeDifferencePP': m['D'] - m['C'],
            'baselineSubstitutionDamagePP': m['C'] - m['A'],
            'sSubstitutionDamagePP': m['D'] - m['B'],
            'interactionPP': (m['D'] - m['C']) - (m['B'] - m['A']),
            'sObservedMseDifferencePP2': q['B'] - q['A'],
            'sPredictedMseDifferencePP2': q['D'] - q['C'],
            'baselineSubstitutionMseDifferencePP2': q['C'] - q['A'],
            'sSubstitutionMseDifferencePP2': q['D'] - q['B']}


def paired_summary(rows, cells):
    pairs = [paired_row(row) for row in rows]
    metrics = {key: mean(p[key] for p in pairs) for key in pairs[0] if key != 'targetElectorateId'}
    direct = ((cells['D']['contestEqualMaePP'] - cells['C']['contestEqualMaePP']) -
              (cells['B']['contestEqualMaePP'] - cells['A']['contestEqualMaePP']))
    if abs(direct - metrics['interactionPP']) > 1e-12:
        raise ValueError('Four-cell interaction algebra failed')
    metrics['interactionFromFourMeansPP'] = direct
    metrics['rmseDifferencesPP'] = {
        'S_observed_B_minus_A': cells['B']['contestEqualRmsePP'] - cells['A']['contestEqualRmsePP'],
        'S_predicted_D_minus_C': cells['D']['contestEqualRmsePP'] - cells['C']['contestEqualRmsePP'],
        'baseline_substitution_C_minus_A': cells['C']['contestEqualRmsePP'] - cells['A']['contestEqualRmsePP'],
        'S_substitution_D_minus_B': cells['D']['contestEqualRmsePP'] - cells['B']['contestEqualRmsePP'],
    }
    values = [p['interactionPP'] for p in pairs]
    metrics['interactionContestDistributionPP'] = {
        'min': min(values), 'p25': percentile(values, .25),
        'median': percentile(values, .5), 'p75': percentile(values, .75),
        'max': max(values),
        'leaveOneContestOutMeanRange': range_without_one(values)}
    metrics['leaveOneContestOutPairedMaeDifferenceRangePP'] = {
        name: range_without_one([p[name] for p in pairs])
        for name in ('sObservedMaeDifferencePP', 'sPredictedMaeDifferencePP')}
    metrics['fiveLargestAbsoluteInteractionContests'] = sorted(
        pairs, key=lambda p: (-abs(p['interactionPP']), p['targetElectorateId']))[:5]
    for name in ('baselineSubstitutionDamagePP', 'sSubstitutionDamagePP'):
        metrics['fiveLargestAbsolute' + name[0].upper() + name[1:]] = sorted(
            pairs, key=lambda p: (-abs(p[name]), p['targetElectorateId']))[:5]
    return metrics, pairs


def group_summary(rows):
    groups = ('national', 'labour', 'national_labour', 'other_mapped',
              'affirmative_no_party_group')
    output = {}
    for group in groups:
        present = []
        errors = {cell: [] for cell in CELLS}
        contest_errors = {cell: [] for cell in CELLS}
        for row in rows:
            ids = [c['candidateOccurrenceId'] for c in row['cells']['A']['candidateErrors']
                   if group in c['groups']]
            if not ids:
                continue
            present.append(row['targetElectorateId'])
            for cell in CELLS:
                selected = [c['errorPP'] for c in row['cells'][cell]['candidateErrors']
                            if c['candidateOccurrenceId'] in ids]
                errors[cell].extend(selected)
                contest_errors[cell].append(selected)
        if not present:
            output[group] = {'candidates': 0, 'contestsContainingGroup': 0, 'cells': None}
            continue
        cells = {}
        for cell in CELLS:
            sample = errors[cell]
            cells[cell] = {'candidateEqualMaePP': mean(abs(x) for x in sample),
                           'candidateEqualRmsePP': math.sqrt(mean(x * x for x in sample)),
                           'candidateEqualSignedBiasPP': mean(sample),
                           'presentContestEqualMaePP': mean(mean(abs(x) for x in e)
                                                             for e in contest_errors[cell]),
                           'presentContestEqualRmsePP': math.sqrt(mean(mean(x*x for x in e)
                                                                      for e in contest_errors[cell]))}
        mae = {cell: cells[cell]['candidateEqualMaePP'] for cell in CELLS}
        output[group] = {'candidates': len(errors['A']),
                         'contestsContainingGroup': len(present),
                         'cells': cells,
                         'pairedCandidateEqualMaePP': {
                             'S_observed_B_minus_A': mae['B'] - mae['A'],
                             'S_predicted_D_minus_C': mae['D'] - mae['C'],
                             'baseline_substitution_C_minus_A': mae['C'] - mae['A'],
                             'S_substitution_D_minus_B': mae['D'] - mae['B'],
                             'interaction': (mae['D'] - mae['C']) - (mae['B'] - mae['A'])}}
    return output


def ranking_transitions(rows, before, after):
    changed = correct_to_wrong = wrong_to_correct = tie_changed = 0
    examples = []
    for row in rows:
        a, b = row['cells'][before], row['cells'][after]
        if a['predictedWinnerSet'] != b['predictedWinnerSet']:
            changed += 1
            examples.append({'targetElectorateId': row['targetElectorateId'],
                             'before': a['predictedWinnerSet'],
                             'after': b['predictedWinnerSet'],
                             'beforeUniqueCorrect': a['uniqueCorrect'],
                             'afterUniqueCorrect': b['uniqueCorrect']})
        correct_to_wrong += bool(a['uniqueCorrect'] and not b['uniqueCorrect'])
        wrong_to_correct += bool(not a['uniqueCorrect'] and b['uniqueCorrect'])
        tie_changed += (len(a['predictedWinnerSet']) > 1) != (len(b['predictedWinnerSet']) > 1)
    return {'comparison': before + '_to_' + after,
            'changedPredictedWinnerSets': changed,
            'uniqueCorrectToNotUniqueCorrect': correct_to_wrong,
            'notUniqueCorrectToUniqueCorrect': wrong_to_correct,
            'tieStatusChanged': tie_changed,
            'changedSetExamples': examples}


def major_party_input_diagnostic(rows, contests):
    seat_index = {r['targetElectorateId']: r for r in contests}
    result = []
    bins = {party: {name: [] for name in PARTY_BINS}
            for party in ('nationalparty', 'labourparty')}
    for row in rows:
        candidates = {c['candidateOccurrenceId']: c
                      for c in seat_index[row['targetElectorateId']]['candidates']}
        errors = {cell: {c['candidateOccurrenceId']: c['errorPP']
                         for c in row['cells'][cell]['candidateErrors']} for cell in CELLS}
        for cid, c in candidates.items():
            party = c['partyBallotGroupKey']
            if party not in bins:
                continue
            delta = 100 * (c['predictedTargetPartySupport'] - c['observedTargetPartySupport'])
            record = {'targetElectorateId': row['targetElectorateId'],
                      'candidateOccurrenceId': cid, 'partyBallotGroupKey': party,
                      'partyInputErrorPP': delta,
                      'baselineAbsoluteCandidateErrorChangePP': abs(errors['C'][cid]) - abs(errors['A'][cid]),
                      'sAbsoluteCandidateErrorChangePP': abs(errors['D'][cid]) - abs(errors['B'][cid])}
            result.append(record)
            bins[party][party_error_bin(delta)].append(record)
    summaries = {party: [{'partyInputErrorBinPP': label, 'candidates': len(values),
                          'meanPartyInputErrorPP': mean(x['partyInputErrorPP'] for x in values) if values else None,
                          'meanBaselineAbsoluteCandidateErrorChangePP': mean(x['baselineAbsoluteCandidateErrorChangePP'] for x in values) if values else None,
                          'meanSAbsoluteCandidateErrorChangePP': mean(x['sAbsoluteCandidateErrorChangePP'] for x in values) if values else None}
                         for label, values in buckets.items()]
                 for party, buckets in bins.items()}
    return {'candidateRecords': result, 'fixedBinSummary': summaries}


def evaluate_fold(fold, inventory, actuals, scenario):
    if fold['targetYear'] != inventory['targetYear']:
        raise ValueError('Evaluation fold/year mismatch')
    contests = inventory['contests']
    contest_index = {r['targetElectorateId']: r for r in contests}
    indexed = {cell: {r['targetElectorateId']: r['candidateShares']
                     for r in fold['scenarios'][scenario][cell]} for cell in CELLS}
    ids = fold['commonEvaluationContestIds']
    if any(set(indexed[cell]) != set(ids) for cell in CELLS):
        raise ValueError('Four-cell contest applicability mismatch')
    rows = []
    for cid in ids:
        contest = contest_index[cid]
        target = actuals[cid]
        cells = {cell: score_contest(indexed[cell][cid], target, contest['candidates'])
                 for cell in CELLS}
        rows.append({'targetYear': fold['targetYear'], 'targetElectorateId': cid,
                     'cells': cells})
    score = score_cells(rows)
    paired, paired_rows = paired_summary(rows, score)
    return {'targetYear': fold['targetYear'], 'scenario': scenario,
            'coverage': {'contests': len(rows),
                         'candidates': sum(len(r['cells']['A']['candidateErrors']) for r in rows),
                         'abstentions': []},
            'cells': score, 'paired': paired,
            'groups': group_summary(rows),
            'rankingTransitions': [ranking_transitions(rows, 'A', 'C'),
                                   ranking_transitions(rows, 'B', 'D')],
            'majorPartyInputError': major_party_input_diagnostic(rows, contests),
            'contestRecords': rows}


def build():
    verify_contract()
    manifest = read(PREFIX + 'construction-manifest.json')
    if digest(PREFIX + 'predictions.json') != manifest['outputSha256']:
        raise ValueError('Changed committed Stage24 construction')
    predictions = read(PREFIX + 'predictions.json')
    inventory = read(PREFIX + 'input-inventory.json')
    actuals = {r['targetElectorateId']: r for r in read(STAGE22 + 'actuals.json')['records']}
    if len(actuals) != 191:
        raise ValueError('Saved Stage22 actual frame changed')
    if len(predictions['folds']) != len(inventory['folds']) or len(predictions['folds']) != 2:
        raise ValueError('Stage24 construction/inventory fold count changed')
    folds = []
    pooled = {scenario: [] for scenario in SCENARIOS}
    for fold, source in zip(predictions['folds'], inventory['folds']):
        if fold['targetYear'] != source['targetYear']:
            raise ValueError('Stage24 construction/inventory order changed')
        for scenario in SCENARIOS:
            evaluated = evaluate_fold(fold, source, actuals, scenario)
            folds.append(evaluated)
            pooled[scenario].extend(evaluated['contestRecords'])
    pooled_summary = {}
    for scenario, rows in pooled.items():
        scores = score_cells(rows)
        pairs, _ = paired_summary(rows, scores)
        pooled_summary[scenario] = {'coverage': {'contests': len(rows),
                                                'candidates': sum(len(r['cells']['A']['candidateErrors']) for r in rows)},
                                    'cells': scores, 'paired': pairs,
                                    'groups': group_summary(rows),
                                    'rankingTransitions': [ranking_transitions(rows, 'A', 'C'),
                                                           ranking_transitions(rows, 'B', 'D')]}
    stage23 = read(STAGE23 + 'scores.json')['fullPopulationNationalGaps']
    return {'schemaVersion': 1, 'stage': 24,
            'role': 'four_cell_fixed_parameter_development_evaluation_only',
            'fullFrameCoverage': {'total': 213, 'fittedHeldGeneral2017': 64,
                                  'fittedHeldGeneral2023': 64,
                                  'noFitted2011': 63, 'maoriCoverageOnly': 21,
                                  'cancelledPortWaikato': 1},
            'folds': folds, 'pooled128ContestEqual': pooled_summary,
            'stage23NationalGapContext': stage23,
            'informationSet': 'observed_local_reference_vs_predicted_local_conditional_on_observed_target_national_support_and_retrospective_slate',
            'operationalSelection': None}


def outputs():
    diagnostics = build()
    manifest = {'schemaVersion': 1, 'stage': 24,
                'phase': 'evaluation_only_after_committed_construction',
                'inputSha256': {path: digest(path) for path in (
                    PREFIX + 'input-contract.json', PREFIX + 'input-inventory.json',
                    PREFIX + 'analysis-contract.json', PREFIX + 'predictions.json',
                    PREFIX + 'construction-manifest.json', STAGE22 + 'actuals.json',
                    STAGE23 + 'scores.json')},
                'codeSha256': digest('scripts/checkpoints/stage24_evaluation.py'),
                'outputSha256': sha256(encode(diagnostics)).hexdigest()}
    return diagnostics, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    diagnostics, manifest = outputs()
    write_or_check('diagnostics.json', diagnostics, args.check)
    write_or_check('evaluation-manifest.json', manifest, args.check)
    print({f['targetYear']: f['paired']['interactionPP']
           for f in diagnostics['folds'] if f['scenario'] == 'printed'})


if __name__ == '__main__':
    main()
