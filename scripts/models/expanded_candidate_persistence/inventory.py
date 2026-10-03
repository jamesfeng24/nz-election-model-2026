"""Outcome-independent accepted-link/geography joins; no fitting or scoring."""
import argparse
from collections import Counter, defaultdict
from math import isfinite
import subprocess

from scripts.evidence.practical_candidate_linkage.names import strict_member
from .common import ROOT, DEST, LINK, GEO, RES, BASE, SCALES, read, unique, save, manifest, digest

CODE=['scripts/models/expanded_candidate_persistence/'+p+'.py' for p in ('common','inventory')]
INPUTS=[RES+'occurrences.json',RES+'references.json',RES+'specification.json',RES+'input-contract.json',
        'data/source-plans/stage6-7-supporting-candidate-sources.json',
        LINK+'accepted-relationships.json',LINK+'proposed-links.json',LINK+'persons.json',LINK+'readiness.json',
        LINK+'contract.json',LINK+'input-contract.json',LINK+'aliases.json',
        GEO+'geography.json',GEO+'fold-plan.json',GEO+'source-contract.json',
        'data/processed/models/candidate-persistence/specification.json',
        'data/processed/models/candidate-persistence/selection.json',
        'scripts/models/candidate_persistence/model.py','scripts/models/candidate_overperformance/normalize.py',
        'scripts/models/conditional_nat_lab_response/model.py',
        'scripts/models/asymmetric_response_test/numerics.py',
        'scripts/checkpoints/complete_share_feature_rank.py',
        'requirements-boundaries.txt']


def value(row,scale):
    if scale=='additive':return row['normalizedPremium']
    return row.get('methods',{}).get(scale,{}).get('residual')


def usable(row,scale):
    result=value(row,scale)
    return result is not None and isfinite(result)


def membership_chains(geography):
    adjacency=defaultdict(set)
    for g in geography:
        if not g['certifiedTwoSidedExact']:continue
        a,b=g['dominantPredecessorId'],g['targetElectorateId']
        adjacency[a].add(b);adjacency[b].add(a)
    indexed={}
    for start in sorted(adjacency):
        if start in indexed:continue
        component=set();pending=[start]
        while pending:
            node=pending.pop()
            if node in component:continue
            component.add(node);pending.extend(adjacency[node]-component)
        label='certified-membership-chain:'+min(component)
        indexed.update({i:label for i in component})
    return indexed


def person_index(groups):
    result={}
    for g in groups:
        for cid in g['candidateOccurrenceIds']:
            if cid in result:raise ValueError('Occurrence in two provisional groups')
            result[cid]=g['provisionalGroupId']
    return result


def build(residuals=None,edges=None,accepted=None,geography=None,persons=None):
    residuals=read(RES+'occurrences.json')['records'] if residuals is None else residuals
    edges=read(LINK+'proposed-links.json')['records'] if edges is None else edges
    accepted=read(LINK+'accepted-relationships.json') if accepted is None else accepted
    geography=read(GEO+'geography.json')['records'] if geography is None else geography
    persons=read(LINK+'persons.json') if persons is None else persons
    occurrences=unique(residuals,'candidateOccurrenceId');unique(edges,'edgeId')
    geo=unique(geography,'geographyId');chains=membership_chains(geography)
    broad,strict=set(accepted['broadEdgeIds']),set(accepted['strictEdgeIds'])
    if len(broad)!=len(accepted['broadEdgeIds']) or len(strict)!=len(accepted['strictEdgeIds']) or not strict<=broad:
        raise ValueError('Duplicate or incompatible accepted views')
    if not broad<=set(e['edgeId'] for e in edges):raise ValueError('Dangling accepted edge')
    people={v:person_index(persons[v]) for v in ('broad','strict')}
    pairs=[]
    for edge in edges:
        a,b=occurrences[edge['sourceOccurrenceId']],occurrences[edge['targetOccurrenceId']]
        if (a['year'],b['year'],a['electorateId'],b['electorateId'])!=(edge['sourceYear'],edge['targetYear'],edge['sourceElectorateId'],edge['targetElectorateId']):
            raise ValueError('Election-local occurrence join mismatch')
        reasons=[];g=geo.get(edge['primaryGeographyId'])
        exact=(g is not None and g['certifiedTwoSidedExact']
               and a['candidateContestStatus']=='held' and b['candidateContestStatus']=='held'
               and (g['sourceYear'],g['targetYear'],g['dominantPredecessorId'],g['targetElectorateId'],g['scope'])==
                   (a['year'],b['year'],a['electorateId'],b['electorateId'],a['electorateType'])
               and a['electorateType']==b['electorateType'])
        if edge['primaryExactHeld']!=exact:raise ValueError('Stage26/canonical exact geography disagreement')
        if edge['edgeId'] not in broad:reasons.append('relationship_not_accepted')
        if not exact:reasons.append('not_exact_held_geography')
        if a['candidateContestStatus']!='held' or b['candidateContestStatus']!='held':reasons.append('cancelled_or_unheld')
        if edge['edgeId'] in broad:
            if edge['label'] not in ('documentary_same_person','accepted_algorithmic_same_person'):
                raise ValueError('Accepted relationship label conflict')
            if (edge['edgeId'] in strict)!=strict_member(edge):raise ValueError('Strict-view rule mismatch')
            for view in ('broad','strict'):
                if edge['edgeId'] not in (broad if view=='broad' else strict):continue
                if a['candidateOccurrenceId'] not in people[view] or people[view][a['candidateOccurrenceId']]!=people[view].get(b['candidateOccurrenceId']):
                    raise ValueError('Accepted edge/provisional component mismatch')
        scale_eligibility={}
        for scale in SCALES:
            errors=reasons.copy()
            if not usable(a,scale):errors.append('missing_source_residual')
            if not usable(b,scale):errors.append('missing_target_residual')
            scale_eligibility[scale]={'broad':not errors,'strict':not errors and edge['edgeId'] in strict,'exclusionReasons':errors}
        pair={'id':edge['edgeId'],'sourceOccurrenceId':a['candidateOccurrenceId'],'targetOccurrenceId':b['candidateOccurrenceId'],
              'sourceYear':a['year'],'targetYear':b['year'],'scope':a['electorateType'],
              'sourceElectorateId':a['electorateId'],'targetElectorateId':b['electorateId'],
              'sourcePartyKey':a['partyKey'],'targetPartyKey':b['partyKey'],
              'sourceOriginalName':a['sourceCandidateName'],'targetOriginalName':b['sourceCandidateName'],
              'geographyId':edge['primaryGeographyId'],'seatMembershipChainId':chains.get(b['electorateId']) if exact else None,
              'originalFrame':g['originalFrame'] if g else False,
              'linkageLabel':edge['label'],'ruleFlags':edge['ruleFlags'],
              'broadPersonGroupId':people['broad'].get(a['candidateOccurrenceId']) if edge['edgeId'] in broad else None,
              'strictPersonGroupId':people['strict'].get(a['candidateOccurrenceId']) if edge['edgeId'] in strict else None,
              'scaleEligibility':scale_eligibility,'sourceResiduals':{scale:value(a,scale) for scale in SCALES},
              'sourceReferenceId':a['referenceId'],
              'sourceReferenceRole':'completed_source_election_predictor; frozen_whole_contest_leave_one_out',
              'targetOutcomeContract':{'artifact':RES+'occurrences.json','recordId':b['candidateOccurrenceId'],
                                      'role':'evaluation_only_for_holdout; permitted_earlier_training_response'},
              'linkageAvailability':edge['publicationByForecastCutoff'], 'careerHistoryRequired':False}
        pairs.append(pair)
    pairs.sort(key=lambda r:(r['targetYear'],r['id']))
    occurrence_ledger=[{'candidateOccurrenceId':r['candidateOccurrenceId'],'year':r['year'],
                        'electorateId':r['electorateId'],'scope':r['electorateType'],
                        'sourceRecordArtifact':RES+'occurrences.json','contestStatus':r['candidateContestStatus'],
                        'normalizationReason':r['normalizationReason'],
                        'residualDefined':{s:usable(r,s) for s in SCALES}}
                       for r in residuals]
    coverage=[]
    for sy,ty in sorted({(g['sourceYear'],g['targetYear']) for g in geography}):
        for scope in ('general','maori'):
            subset=[r for r in pairs if (r['sourceYear'],r['targetYear'],r['scope'])==(sy,ty,scope)]
            coverage.append({'sourceYear':sy,'targetYear':ty,'scope':scope,'proposals':len(subset),
                'scales':{s:{v:sum(r['scaleEligibility'][s][v] for r in subset) for v in ('broad','strict')} for s in SCALES}})
    return {'stage':30,'pairs':pairs,'allOriginalOccurrences':occurrence_ledger,
            'fullGeographicFrame':geography,'coverage':coverage,
            'targetResidualValuesIncluded':False,'admissionUsesWinnerOrInheritedConfidence':False}


def folds(inventory):
    result=[]
    transitions=sorted({(r['sourceYear'],r['targetYear']) for r in inventory['fullGeographicFrame']})
    for view in ('broad','strict'):
        for scope in ('general','maori'):
            for scale in SCALES:
                rows=[r for r in inventory['pairs'] if r['scope']==scope and r['scaleEligibility'][scale][view]]
                for protocol in ('expanding_window','more_separated'):
                    for sy,ty in transitions:
                        train=[r for r in rows if r['targetYear']<ty and (r['targetYear']<=sy if protocol=='expanding_window' else r['targetYear']<sy)]
                        test=[r for r in rows if (r['sourceYear'],r['targetYear'])==(sy,ty)]
                        result.append({'id':f'{view}:{scope}:{scale}:{protocol}:{sy}-{ty}',
                            'view':view,'scope':scope,'scale':scale,'protocol':protocol,'sourceYear':sy,'targetYear':ty,
                            'trainingIds':[r['id'] for r in train],'evaluationIds':[r['id'] for r in test]})
    return {'folds':result,'scope':'Stage25_transition_chronology; Stage26_own_relation_IDs_not_identity_free_model_IDs'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    DEST.mkdir(parents=True,exist_ok=True)
    data=build();plan=folds(data)
    for name,value in [('inventory.json',data),('fold-plan.json',plan)]:save(name,value,args.check)
    if not args.check:
        paths=INPUTS+[str((DEST/'specification.json').relative_to(ROOT))]
        save('input-contract.json',{'inputSha256':{path:digest(path) for path in paths},
            'sourceDependencyContracts':[LINK+'input-contract.json',GEO+'source-contract.json',RES+'input-contract.json',
              'data/source-plans/stage6-7-supporting-candidate-sources.json'],
            'wholeRegistryPinned':False})
        tree=subprocess.check_output(['git','ls-tree','-r','-z',BASE,'data'],cwd=ROOT)
        files={path.decode():meta.split()[2].decode() for e in tree.split(b'\0') if e for meta,path in [e.split(b'\t',1)]}
        save('prior-data-contract.json',{'baseCommit':BASE,'gitBlobSha1':files})
    manifest('prefit',['specification.json','inventory.json','fold-plan.json','input-contract.json','prior-data-contract.json'],CODE,args.check)
    print({'occurrences':len(data['allOriginalOccurrences']),'proposals':len(data['pairs']),
           'broadAdditive':sum(r['scaleEligibility']['additive']['broad'] for r in data['pairs']),
           'strictAdditive':sum(r['scaleEligibility']['additive']['strict'] for r in data['pairs'])})


if __name__=='__main__':main()
