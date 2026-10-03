"""Frozen share, ranking, margin and paired-score diagnostics."""
from math import sqrt
from statistics import mean
from scripts.checkpoints.stage24_evaluation import winner_set,range_without_one
from .common import METHODS,PAIRS,keyed

GROUPS=('national','labour','national_labour','other_mapped','affirmative_no_party_group',
        'both_features','S_only','R_only','neither_feature')


def groups(c,view):
    g=c['partyBallotGroupKey']
    party=('national','national_labour') if g=='nationalparty' else ('labour','national_labour') if g=='labourparty' else ('affirmative_no_party_group',) if g is None else ('other_mapped',)
    return party+(c['R'][view]['availabilityPattern'],)


def score(predicted,actual,row,view):
    observed=actual['candidateShares'];ids=[c['targetOccurrenceId'] for c in row['candidates']]
    if set(predicted)!=set(observed) or set(ids)!=set(predicted) or len(ids)!=len(set(ids)):raise ValueError('Scoring slate IDs differ')
    if any(v<0 for v in predicted.values()) or abs(sum(predicted.values())-1)>1e-12 or abs(sum(observed.values())-1)>1e-12:raise ValueError('Scoring share denominator mismatch')
    errors=[{'candidateOccurrenceId':c['targetOccurrenceId'],'errorPP':100*(predicted[c['targetOccurrenceId']]-observed[c['targetOccurrenceId']]),'groups':groups(c,view)} for c in row['candidates']]
    winners=winner_set(predicted);winner=actual['winnerCandidateId']
    if winner not in observed or abs(observed[winner]-max(observed.values()))>1e-12:raise ValueError('Official winner does not match valid share maximum')
    runner_level=max(v for cid,v in observed.items() if cid!=winner)
    runners=[cid for cid,v in observed.items() if cid!=winner and abs(v-runner_level)<=1e-12]
    actual_gap=observed[winner]-runner_level
    gaps=[predicted[winner]-predicted[cid] for cid in runners]
    sorted_q=sorted(predicted.values(),reverse=True);predicted_gap=sorted_q[0]-sorted_q[1]
    bias=mean(e['errorPP'] for e in errors)
    if abs(bias)>1e-8:raise ValueError('Full slate bias fails conservation')
    return {'contestMaePP':mean(abs(e['errorPP']) for e in errors),'contestMsePP2':mean(e['errorPP']*e['errorPP'] for e in errors),
        'candidateErrors':errors,'fullSlateBiasPPAccounting':bias,'predictedWinnerSet':winners,
        'uniqueCorrect':len(winners)==1 and winners[0]==winner,'tieContainsWinner':len(winners)>1 and winner in winners,
        'actualTopTwoMarginAbsoluteErrorPP':mean(100*abs(g-actual_gap) for g in gaps),
        'actualTopTwoMarginSignedErrorPP':mean(100*(g-actual_gap) for g in gaps),
        'predictedTopTwoGapAbsoluteErrorPP':100*abs(predicted_gap-actual_gap),
        'observedWinnerId':winner,'observedRunnerUpIds':runners}


def aggregate(scores):
    if not scores:return None
    errors=[c['errorPP'] for s in scores for c in s['candidateErrors']];n=len(scores)
    return {'contests':n,'candidates':len(errors),'contestEqualMaePP':mean(s['contestMaePP'] for s in scores),
        'contestEqualRmsePP':sqrt(mean(s['contestMsePP2'] for s in scores)),
        'candidateEqualMaePP':mean(abs(v) for v in errors),'candidateEqualRmsePP':sqrt(mean(v*v for v in errors)),
        'fullSlateSignedBiasPPAccounting':mean(errors),'uniqueCorrect':sum(s['uniqueCorrect'] for s in scores),
        'uniqueWinnerAccuracyAllContests':sum(s['uniqueCorrect'] for s in scores)/n,
        'uniquePredictionCount':sum(len(s['predictedWinnerSet'])==1 for s in scores),
        'tieCount':sum(len(s['predictedWinnerSet'])>1 for s in scores),'tieInclusionCount':sum(s['tieContainsWinner'] for s in scores),
        'actualTopTwoMarginMaePP':mean(s['actualTopTwoMarginAbsoluteErrorPP'] for s in scores),
        'actualTopTwoMarginBiasPP':mean(s['actualTopTwoMarginSignedErrorPP'] for s in scores),
        'predictedTopTwoGapMaePP':mean(s['predictedTopTwoGapAbsoluteErrorPP'] for s in scores)}


def group_metrics(rows):
    result={}
    for group in GROUPS:
        selected=[r for r in rows if any(group in c['groups'] for c in r['scores']['baseline']['candidateErrors'])]
        methods={}
        for method in METHODS:
            blocks=[[c['errorPP'] for c in r['scores'][method]['candidateErrors'] if group in c['groups']] for r in selected]
            errors=[e for b in blocks for e in b]
            methods[method]=None if not errors else {'candidateEqualMaePP':mean(abs(e) for e in errors),
                'candidateEqualRmsePP':sqrt(mean(e*e for e in errors)),'candidateEqualSignedBiasPP':mean(errors),
                'presentContestEqualMaePP':mean(mean(abs(e) for e in b) for b in blocks),
                'presentContestEqualRmsePP':sqrt(mean(mean(e*e for e in b) for b in blocks))}
        count=sum(group in c['groups'] for r in selected for c in r['scores']['baseline']['candidateErrors'])
        gains={a+'__versus__'+b:None if not selected else methods[b]['candidateEqualMaePP']-methods[a]['candidateEqualMaePP'] for a,b in PAIRS}
        result[group]={'candidates':count,'presentContests':len(selected),'methods':methods,'candidateEqualMaeImprovementPP':gains}
    return result


def summary(rows):
    if not rows:return {'contests':0,'candidates':0,'methods':None,'pairs':None,'groups':None}
    models={m:aggregate([r['scores'][m] for r in rows]) for m in METHODS};pairs={}
    for model,control in PAIRS:
        records=[{'targetElectorateId':r['targetElectorateId'],
            'maeImprovementPP':r['scores'][control]['contestMaePP']-r['scores'][model]['contestMaePP'],
            'mseImprovementPP2':r['scores'][control]['contestMsePP2']-r['scores'][model]['contestMsePP2']} for r in rows]
        values=[r['maeImprovementPP'] for r in records]
        pairs[model+'__versus__'+control]={'maeImprovementPP':mean(values),
            'mseImprovementPP2':mean(r['mseImprovementPP2'] for r in records),
            'rmseImprovementPP':models[control]['contestEqualRmsePP']-models[model]['contestEqualRmsePP'],
            'candidateEqualMaeImprovementPP':models[control]['candidateEqualMaePP']-models[model]['candidateEqualMaePP'],
            'improvedContests':sum(v>0 for v in values),'worsenedContests':sum(v<0 for v in values),
            'fixedFitLeaveOneContestOutMaeGainRangePP':range_without_one(values),
            'fiveLargestAbsoluteEffects':sorted(records,key=lambda r:(-abs(r['maeImprovementPP']),r['targetElectorateId']))[:5],
            'pairedContestRecords':records}
    return {'contests':len(rows),'candidates':models['baseline']['candidates'],
            'weighting':'one_per_contest; group_primary_one_per_candidate; present_contest_group_sensitivity',
            'methods':models,'pairs':pairs,'groups':group_metrics(rows)}
