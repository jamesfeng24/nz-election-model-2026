"""Canonical party/source/fit inventory; no new vectors, predictions or scores."""
import argparse
from collections import Counter
import subprocess
from scripts.models.complete_party_vector.inventory import evidence,category_rows
from scripts.models.complete_party_vector.common import CONTINUITY,ALLIANCE,STAGE5_CONTRACT
from scripts.checkpoints.stage25_availability import mapped_contests,MAPPING
from .common import ROOT,DEST,BASE,GEO,S23,S24,S27,SCENARIOS,read,keyed,save,phase,digest

CODE=['scripts/models/expanded_party_substitution/'+n+'.py' for n in ('common','inventory')]
INPUTS=[GEO+n for n in ('geography.json','availability.json','fold-plan.json','source-contract.json')]
INPUTS += [S27+n for n in ('inventory.json','predictions.json','folds.json','input-contract.json','construction-manifest.json')]
INPUTS += [S23+n for n in ('input-inventory.json','construction.json','source-contract.json','specification.json','scores.json')]
INPUTS += [S24+n for n in ('input-inventory.json','predictions.json','analysis-contract.json','input-contract.json')]
INPUTS += [CONTINUITY,ALLIANCE,MAPPING,STAGE5_CONTRACT,
 'scripts/models/party_vote_transform/inputs.py','scripts/models/complete_party_vector/inventory.py',
 'scripts/models/complete_party_vector/construction.py','scripts/models/complete_party_vector/evaluation.py',
 'scripts/models/exact_geography_retests/adapters.py','scripts/checkpoints/stage24_construction.py',
 'scripts/checkpoints/stage24_evaluation.py','scripts/checkpoints/stage24_inventory.py','scripts/checkpoints/stage22_fit.py']


def party_frame(geography,elections,categories):
    seats={y:keyed(list(d['scopes']['general'].values()),'id') for y,d in elections.items()}
    records=[]
    for g in geography:
        base={k:g[k] for k in ('geographyId','sourceYear','targetYear','targetElectorateId','scope','originalFrame','certifiedTwoSidedExact','contestStatus')}
        base['sourceElectorateId']=g['dominantPredecessorId'];base['geographyArtifact']=GEO+'geography.json'
        if g['scope']!='general' or not g['certifiedTwoSidedExact']:
            records.append({**base,'partyInputStatus':'coverage_only','reason':'maori_coverage_only' if g['scope']!='general' else 'not_certified_two_sided_exact'});continue
        sy,ty=g['sourceYear'],g['targetYear'];source=seats[sy][base['sourceElectorateId']];target=seats[ty][g['targetElectorateId']]
        cats=categories[(sy,ty)];source_categories=[]
        if set(source['parties'])!={c['categoryId'] for c in cats if c['relationship']!='entrant'}:
            raise ValueError('Incomplete source official category roster')
        if set(target['parties'])!={c['categoryId'] for c in cats if c['relationship']!='exit'}:
            raise ValueError('Incomplete target category roster')
        for c in cats:
            if c['relationship']=='exit':continue
            r=source['parties'].get(c['categoryId'])
            status=('entrant_no_source_category' if c['relationship']=='entrant' and r is None else
                    'missing_continuing_source_row' if r is None else 'observed_zero' if r['votes']==0 else 'observed_positive')
            source_categories.append({'categoryId':c['categoryId'],'sourceLocalShare':r['share'] if r else None,
                'sourceLocalVotes':r['votes'] if r else None,'sourceLocalStatus':status})
        records.append({**base,'partyInputStatus':'available','reason':None,'sourceValidPartyVotes':source['validVotes'],
                        'sourceCategories':source_categories,'targetLocalOutcomesIncluded':False,
                        'sourcePublicationByForecastCutoff':'unknown_retrospective_preservation'})
    return records


def candidate_frame(data,mapping):
    mapped=mapped_contests(mapping);records=[]
    for r in data['shareRecords']:
        row={k:v for k,v in r.items() if k!='candidates'};row['candidates']=[]
        candidates=keyed(mapped[(r['targetYear'],r['targetElectorateId'])]['candidates'],'candidateOccurrenceId')
        if set(candidates)!={c['targetOccurrenceId'] for c in r['candidates']}:raise ValueError('Complete slate/mapping mismatch')
        seen=set()
        for c in r['candidates']:
            m=candidates[c['targetOccurrenceId']];group=c['targetPartyKey']
            if (m['partyKey'],m['sourceAffiliation'],m['mappingStatus'])!=(group,c['originalAffiliation'],c['mappingStatus']):raise ValueError('Candidate ballot mapping conflict')
            if group is None and (not c['mappingStatus'].startswith('verified_no_party_group_') or c['targetPartySupport']!=0):raise ValueError('Missing group not affirmative no-group')
            if group is not None:
                if group in seen:raise ValueError('Multiple local destinations for party group')
                seen.add(group)
            row['candidates'].append(c)
        records.append(row)
    return records


def build(elections=None,data=None,saved=None,geography=None,mapping=None):
    elections=evidence()[0] if elections is None else elections
    data=read(S27+'inventory.json') if data is None else data
    saved=read(S27+'predictions.json') if saved is None else saved
    geography=read(GEO+'geography.json')['records'] if geography is None else geography
    mapping=read(MAPPING) if mapping is None else mapping
    keyed(geography,'geographyId');transitions=sorted({(g['sourceYear'],g['targetYear']) for g in geography})
    cats={t:category_rows(elections,*t,read(CONTINUITY)['records']) for t in transitions}
    party=party_frame(geography,elections,cats);candidates=candidate_frame(data,mapping)
    candidate_index=keyed(candidates,'targetElectorateId');geo=keyed(geography,'geographyId')
    for r in candidates:
        g=geo[r['geographyId']]
        if not g['certifiedTwoSidedExact'] or g['scope']!='general' or (g['dominantPredecessorId'],g['targetElectorateId'])!=(r['sourceElectorateId'],r['targetElectorateId']):raise ValueError('Stage27/canonical geography conflict')
    folds=[]
    for case in saved['candidateCases']:
        if case['trainingVariant']!='expanded':continue
        ids=case['evaluationIds'];rows=[candidate_index[i] for i in ids]
        if any(r['targetYear']!=case['targetYear'] for r in rows):raise ValueError('Wrong saved-fold target IDs')
        folds.append({'foldId':case['foldId'],'targetYear':case['targetYear'],'protocol':case['chronologyProtocol'],
            'trainingIds':case['trainingIds'],'evaluationIds':ids,
            'evaluationCandidateIds':[c['targetOccurrenceId'] for r in rows for c in r['candidates']],
            'scenarios':{s:{'fits':case['scenarios'][s]['fits'],'trainingOnlyMeans':case['scenarios'][s]['trainingOnlyMeans']} for s in SCENARIOS},
            'savedPredictionArtifact':S27+'predictions.json'})
    keyed(folds,'foldId')
    coverage=[]
    for _,y in transitions:
        rows=[r for r in candidates if r['targetYear']==y]
        coverage.append({'targetYear':y,'heldGeneralContests':len(rows),'candidateOccurrences':sum(len(r['candidates']) for r in rows),
            'partyVectorsAvailable':sum(r['targetYear']==y and r['partyInputStatus']=='available' for r in party),
            'fullFrameReasons':dict(Counter(r['reason'] or 'available' for r in party if r['targetYear']==y))})
    return {'stage':31,'role':'frozen_preconstruction_inventory_no_new_predictions_or_scores','categoryRelationships':[
            {'sourceYear':s,'targetYear':t,'categories':cats[(s,t)]} for s,t in transitions],
        'partyFrame':party,'candidateRecords':candidates,'folds':folds,'coverage':coverage,
        'nationalPopulation':[{ 'year':y,'validPartyVotes':d['nationalValidVotes'],'generalElectorates':len(d['scopes']['general']),
                              'maoriElectorates':len(d['scopes']['maori'])} for y,d in elections.items()],
        'geographyFrameReferencedNotReconstructed':True,'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();DEST.mkdir(parents=True,exist_ok=True)
    doc=build();save('input-inventory.json',doc,a.check)
    if not a.check:
        _,paths=evidence();inputs=sorted(set(INPUTS)|set(paths)|{'data/processed/models/expanded-party-substitution/specification.json'})
        save('input-contract.json',{'inputSha256':{p:digest(p) for p in inputs},'requiredSourceContracts':[GEO+'source-contract.json',S23+'source-contract.json'],
                                   'wholeRegistryPinned':False,'evaluationOnlyDependencies':['processed_election_candidate_outcomes_and_target_party_actuals']})
        tree=subprocess.check_output(['git','ls-tree','-r','-z',BASE,'data'],cwd=ROOT)
        files={p.decode():m.split()[2].decode() for e in tree.split(b'\0') if e for m,p in [e.split(b'\t',1)]}
        save('prior-data-contract.json',{'baseCommit':BASE,'gitBlobSha1':files})
    phase('prefit',['specification.json','input-inventory.json','input-contract.json','prior-data-contract.json'],CODE,a.check)
    print(doc['coverage'])


if __name__=='__main__':main()
