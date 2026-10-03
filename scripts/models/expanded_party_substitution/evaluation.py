"""Paired four-cell share/ranking errors; no fitted parameter or outcome routing."""
import argparse
from statistics import mean
from scripts.checkpoints import stage24_evaluation as e
from scripts.models.exact_geography_retests.adapters import datasets
from .common import local,save,phase,verify_inputs,preserve,keyed,SCENARIOS,PROTOCOLS
from . import party_evaluation
from .integrity import verify_phase


def candidate_actuals(elections,inventory):
    seats={r['id']:r for d in elections.values() for r in d['electorates']};result={}
    for r in inventory['candidateRecords']:
        seat=seats[r['targetElectorateId']];shares={c['id']:c['votes']/seat['validCandidateVotes'] for c in seat['candidates']}
        if set(shares)!={c['targetOccurrenceId'] for c in r['candidates']}:raise ValueError('Evaluation slate changed')
        result[r['targetElectorateId']]={'candidateShares':shares,'winnerCandidateId':seat['winnerCandidateId']}
    return result


def score_cell(shares,actual,candidates):
    score=e.score_contest(shares,actual,candidates)
    # Same registered MSE, explicit multiplication for scalar serialization.
    score['contestMsePP2']=mean(c['errorPP']*c['errorPP'] for c in score['candidateErrors'])
    return score


def summary(rows):
    if not rows:return {'contests':0,'candidates':0,'cells':None,'paired':None,'groups':None}
    scores=e.score_cells(rows);paired,pairs=e.paired_summary(rows,scores)
    paired.update(observedSAdvantagePp=-paired['sObservedMaeDifferencePP'],constructedSAdvantagePp=-paired['sPredictedMaeDifferencePP'])
    return {'contests':len(rows),'candidates':sum(len(r['cells']['A']['candidateErrors']) for r in rows),
            'weighting':'one_per_contest; group_primary_one_per_candidate',
            'cells':scores,'paired':paired,'pairedContestRecords':pairs,'groups':e.group_summary(rows),
            'rankingTransitions':[e.ranking_transitions(rows,'A','C'),e.ranking_transitions(rows,'B','D')]}


def evaluate_case(fold,actuals,scenario):
    block=fold['scenarios'][scenario]
    base={'foldId':fold['foldId'],'targetYear':fold['targetYear'],'protocol':fold['protocol'],'scenario':scenario,
          'expectedContests':len(fold['expectedEvaluationIds']),'mappingAbstentions':fold['abstentions']}
    if block['status']!='constructed':return {**base,'status':'abstain','reason':block['reason'],'records':[],**summary([])}
    cells={c:keyed(rows,'targetElectorateId') for c,rows in block['cells'].items()}
    ids=fold['commonEvaluationIds'];contests=keyed(fold['contests'],'targetElectorateId')
    if any(set(m)!=set(ids) for m in cells.values()):raise ValueError('Four-cell samples differ')
    rows=[]
    for cid in ids:
        r=contests[cid];scores={c:score_cell(cells[c][cid]['candidateShares'],actuals[cid],r['candidates']) for c in e.CELLS}
        rows.append({'targetYear':fold['targetYear'],'targetElectorateId':cid,'originalFrame':r['originalFrame'],'cells':scores})
    return {**base,'status':'evaluated','records':rows,**summary(rows),
            'majorPartyInputError':e.major_party_input_diagnostic(rows,fold['contests']),
            'originalCommon':summary([r for r in rows if r['originalFrame']]),
            'new2014_2020':summary([r for r in rows if not r['originalFrame']])}


def build(candidate=None,inventory=None,party=None,actuals=None):
    candidate=local('candidate-predictions.json') if candidate is None else candidate
    inventory=local('input-inventory.json') if inventory is None else inventory
    party=local('party-vectors.json') if party is None else party
    actuals=candidate_actuals(datasets()[0],inventory) if actuals is None else actuals
    folds=[evaluate_case(f,actuals,s) for f in candidate['folds'] for s in SCENARIOS]
    pooled=[]
    for protocol in PROTOCOLS:
        for scenario in SCENARIOS:
            selected=[f for f in folds if (f['protocol'],f['scenario'])==(protocol,scenario)]
            rows=[r for f in selected for r in f['records']]
            pooled.append({'protocol':protocol,'scenario':scenario,**summary(rows),
                'fittedTargetYears':[f['targetYear'] for f in selected if f['status']=='evaluated'],
                'noFitTargetYears':[f['targetYear'] for f in selected if f['status']=='abstain'],
                'originalCommon':summary([r for r in rows if r['originalFrame']]),
                'new2014_2020':summary([r for r in rows if not r['originalFrame']])})
    return {'stage':31,'folds':folds,'pooled':pooled,
            'partyDiagnostics':party_evaluation.build(party,inventory),'operationalSelection':None,
            'interpretation':'conditional_development_not_as_of_forecast; no_new_selection_screen'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify_inputs()
    verify_phase('construction');result=build();save('evaluation.json',result,a.check)
    phase('evaluation',['evaluation.json'],['scripts/models/expanded_party_substitution/'+n+'.py' for n in ('party_evaluation','evaluation','integrity')],a.check)
    print('Fitted primary printed folds:',[(f['targetYear'],f['paired']['interactionPP']) for f in result['folds'] if f['protocol']=='expanding_window' and f['scenario']=='printed' and f['status']=='evaluated'],'prior preserved',preserve())


if __name__=='__main__':main()
