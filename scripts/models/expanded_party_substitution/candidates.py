"""Same saved candidate equation, coefficients and means; only party input changes."""
from copy import deepcopy
from scripts.checkpoints.stage24_construction import adapter_rows,portable_predictions,reproduce_observed
from scripts.checkpoints.stage24_inventory import candidate_inputs
from .parties import ballot_vector
from .common import read,keyed,S24,S27,SCENARIOS

METHODS={'A':'baseline','B':'baseline_plus_S','C':'baseline','D':'baseline_plus_S'}


def attach_inputs(row,vector):
    if (row['targetElectorateId'],row['targetYear'])!=(vector['targetElectorateId'],vector['targetYear']):raise ValueError('Wrong party-vector seat/year')
    party=ballot_vector(vector);candidates=[];seen=set()
    for c in row['candidates']:
        mapping={'candidateOccurrenceId':c['targetOccurrenceId'],'partyKey':c['targetPartyKey'],
                 'mappingStatus':c['mappingStatus'],'sourceAffiliation':c['originalAffiliation']}
        item=candidate_inputs(c,mapping,party)
        group=item['partyBallotGroupKey']
        if group is not None:
            if group in seen:raise ValueError('Duplicate local candidate group destination')
            seen.add(group)
        candidates.append(item)
    keyed(candidates,'candidateOccurrenceId')
    return {'targetElectorateId':row['targetElectorateId'],'targetYear':row['targetYear'],
            'originalFrame':row['originalFrame'],'partyBallotGroupShares':party,'candidates':candidates}


def apply_saved(contests,block,scenario,input_type):
    rows=adapter_rows(contests,input_type)
    return {m:portable_predictions(rows,block['trainingOnlyMeans'],scenario,m,block['fits'][m])
            for m in ('baseline','baseline_plus_S')}


def build_case(fold,rows,vectors,reference):
    selected=[];abstentions=[]
    for cid in fold['evaluationIds']:
        try:selected.append(attach_inputs(rows[cid],vectors[cid]))
        except (ValueError,KeyError) as exc:abstentions.append({'targetElectorateId':cid,'reason':str(exc),'allFourCellsAbstain':True})
    ids=[r['targetElectorateId'] for r in selected];scenarios={};checks=[]
    for scenario in SCENARIOS:
        block=fold['scenarios'][scenario]
        statuses={m:block['fits'][m]['status'] for m in ('baseline','baseline_plus_S')}
        if any(s!='fitted' for s in statuses.values()):
            scenarios[scenario]={'status':'abstain','reason':'saved_fit_unavailable','savedFitStatuses':statuses,'cells':{c:[] for c in METHODS}}
            continue
        observed=apply_saved(selected,block,scenario,'observed')
        ref=reference['scenarios'][scenario]['predictions']
        for m in observed:
            saved=[r for r in ref[m] if r['targetElectorateId'] in set(ids)]
            reproduce_observed(observed[m],saved,m)
            checks.append({'scenario':scenario,'method':m,'absoluteShareTolerance':1e-12,'passed':True})
        # Only after both observed branches reproduce do C/D run.
        predicted=apply_saved(selected,block,scenario,'predicted')
        scenarios[scenario]={'status':'constructed','cells':{'A':observed['baseline'],'B':observed['baseline_plus_S'],
            'C':predicted['baseline'],'D':predicted['baseline_plus_S']}}
    return {'foldId':fold['foldId'],'targetYear':fold['targetYear'],'protocol':fold['protocol'],
            'expectedEvaluationIds':fold['evaluationIds'],'commonEvaluationIds':ids,
            'candidateIds':[c['candidateOccurrenceId'] for r in selected for c in r['candidates']],
            'contests':selected,'abstentions':abstentions,'scenarios':scenarios,'observedReproduction':checks}


def build(inventory,party,saved=None):
    saved=read(S27+'predictions.json') if saved is None else saved
    cases=keyed([f for f in saved['candidateCases'] if f['trainingVariant']=='expanded'],'foldId')
    rows=keyed(inventory['candidateRecords'],'targetElectorateId');vectors=keyed(party['records'],'targetElectorateId')
    result=[]
    for fold in inventory['folds']:
        reference=cases[fold['foldId']]
        if fold['trainingIds']!=reference['trainingIds'] or fold['evaluationIds']!=reference['evaluationIds']:raise ValueError('Saved fit chronology/sample changed')
        for s in SCENARIOS:
            if fold['scenarios'][s]!= {k:reference['scenarios'][s][k] for k in ('fits','trainingOnlyMeans')}:raise ValueError('Saved parameters/means changed')
        result.append(build_case(fold,rows,vectors,reference))
    return {'stage':31,'role':'fixed_parameter_four_cells_no_candidate_actuals','folds':result,'operationalSelection':None}


def compatibility(inventory,party):
    old=read(S24+'input-inventory.json');saved=keyed(read(S24+'predictions.json')['folds'],'targetYear')
    vectors=keyed(party['records'],'targetElectorateId');rows=keyed(inventory['candidateRecords'],'targetElectorateId')
    stage27=read(S27+'predictions.json')['candidateCases'];checks=[]
    for f in old['folds']:
        # Matching original-training Stage24 parameters, never expanded fits.
        selected=[]
        for r in f['contests']:
            row=deepcopy(r);party_inputs=ballot_vector(vectors[r['targetElectorateId']])
            for c in row['candidates']:
                c['predictedTargetPartySupport']=0 if c['partyBallotGroupKey'] is None else party_inputs[c['partyBallotGroupKey']]
            selected.append(row)
        for s in SCENARIOS:
            block={'trainingOnlyMeans':f['scenarios'][s]['trainingOnlyMeans'],'fits':f['scenarios'][s]['parameters']}
            for kind,cells in [('observed',('A','B')),('predicted',('C','D'))]:
                current=apply_saved(selected,block,s,kind)
                for cell,m in zip(cells,('baseline','baseline_plus_S')):
                    reproduce_observed(current[m],saved[f['targetYear']]['scenarios'][s][cell],cell)
                    checks.append({'targetYear':f['targetYear'],'scenario':s,'cell':cell,'comparison':'Stage24_matching_saved_original_fit','tolerance':1e-12,'passed':True})
            case=next(x for x in stage27 if x['trainingVariant']=='original_only' and x['chronologyProtocol']=='expanding_window' and x['targetYear']==f['targetYear'])
            if case['trainingIds']!=f['trainingContestIds']:raise ValueError('Original training IDs not compatible')
            current=apply_saved([attach_inputs(rows[c],vectors[c]) for c in case['evaluationIds']],case['scenarios'][s],s,'predicted')
            for cell,m in [('C','baseline'),('D','baseline_plus_S')]:
                a=keyed(current[m],'targetElectorateId');b=keyed(saved[f['targetYear']]['scenarios'][s][cell],'targetElectorateId')
                gap=max(abs(a[c]['candidateShares'][cid]-v) for c,r in b.items() for cid,v in r['candidateShares'].items())
                if gap>1e-7:raise ValueError('Stage27 original-only compatibility exceeds inherited solver agreement')
                checks.append({'targetYear':f['targetYear'],'scenario':s,'cell':cell,'comparison':'Stage27_original_only_vs_Stage24_context_not_expanded','maximumAbsoluteShareDifference':gap,'tolerance':1e-7,'passed':True})
    return checks
