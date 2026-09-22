"""Deterministic historical predictions, marginal uncertainty and vector diagnostics."""
from scripts.models.party_vote_transform.inputs import canonical,key
from scripts.models.party_vote_transform.formulas import METHODS,transform,prediction_bounds


def local_key(name,code):
    if name=='Rangit?¢kei':
        if code!='043':raise ValueError('Ambiguous2014 typography')
        return key('Rangitīkei')
    return key(name)


def build_records(inputs,elections,continuities,spec):
    records=[];vectors=[]
    readiness=inputs.json('data/processed/boundaries/backtesting-readiness.json')
    expected=[(r['sourceYear'],r['targetYear']) for r in readiness['comparisons']]
    if sorted(expected)!=sorted((r['sourceYear'],r['targetYear']) for r in spec['transitions']):raise ValueError('Transition leakage/mismatch')
    for t in spec['transitions']:
        s,d=t['sourceYear'],t['targetYear'];synthetic=not t['primary'];baseline=None
        if synthetic:
            baseline=inputs.json(f'data/processed/boundaries/{s}-{d}/party-votes.json')
            for cid,p in elections[s]['parties'].items():
                mass=sum(r['sourceVotes'] for scope in baseline['scopes'].values() for r in scope['partyMassConservation'] if canonical(r['partyKey'])==cid)
                if mass!=p['votes']:raise ValueError('Synthetic source national mass mismatch')
        eligible=[r for r in continuities if r['sourceYear']==s and r['targetYear']==d and r['status']=='eligible']
        for kind,target_records in elections[d]['scopes'].items():
            if synthetic:
                source={local_key(r['targetName'],r['targetCode']):r for r in baseline['scopes'][kind]['targets']}
            else:source=elections[s]['scopes'][kind]
            if set(source)!=set(target_records):raise ValueError('Same-boundary target join mismatch')
            for name,target in sorted(target_records.items()):
                ps={canonical(p['partyKey']):p for p in source[name]['parties']} if synthetic else source[name]['parties']
                group=[]
                for identity in eligible:
                    cid=identity['canonicalPartyId'];p0,p1=identity['source']['share'],identity['target']['share'];a=ps[cid];b=target['parties'][cid]
                    if synthetic:
                        lower,upper=a['shareLower'],a['shareUpper'];point=a['share']
                        numerical={'minimumShareBracket':a['minimumShareBracket'],'maximumShareBracket':a['maximumShareBracket'],'minimumShareGap':a['optimizationGaps']['minimumShare'],'maximumShareGap':a['optimizationGaps']['maximumShare']}
                    else:lower=upper=point=a['share'];numerical=None
                    predictions={}
                    for method in METHODS:
                        pred=prediction_bounds(method,lower,upper,p0,p1,b['share'])
                        exact=transform(method,point,p0,p1) if point is not None else None
                        pred.update({'point':None if exact is None else exact['prediction'],'rawPoint':None if exact is None else exact['raw'],
                            'absoluteError':None if exact is None else abs(exact['prediction']-b['share']),
                            'squaredError':None if exact is None else (exact['prediction']-b['share'])**2,
                            'signedError':None if exact is None else exact['prediction']-b['share']})
                        if numerical:
                            pred['numericalPredictionExtremumBrackets']={k:[transform(method,v,p0,p1)['prediction'] for v in numerical[k]] for k in ['minimumShareBracket','maximumShareBracket']}
                        predictions[method]=pred
                    row={'id':f'{s}-{d}:{target["id"]}:{cid}','sourceYear':s,'targetYear':d,'boundaryRegime':t['boundaryRegime'],
                         'boundarySourceClass':'synthetic_bounds' if synthetic else 'observed','primary':t['primary'],'electorateId':target['id'],'electorateName':target['name'],'electorateType':kind,
                         'canonicalPartyId':cid,'sourcePartyLabel':identity['source']['label'],'targetPartyLabel':identity['target']['label'],
                         'sourceLocalShare':point,'sourceLocalShareLower':lower,'sourceLocalShareUpper':upper,'sourceNationalShare':p0,'targetNationalShare':p1,
                         'actualTargetShare':b['share'],'actualTargetPartyVotes':b['votes'],'targetValidPartyVotes':target['validVotes'],'numericalReconstruction':numerical,
                         'quality':'coupled geographic outer bounds; numerical brackets separate; no midpoint' if synthetic else 'observed same-boundary evidence','predictions':predictions}
                    records.append(row);group.append(row)
                vectors.append({'sourceYear':s,'targetYear':d,'electorateId':target['id'],'electorateType':kind,
                    'actualEligibleShareSum':sum(r['actualTargetShare'] for r in group),'eligibleParties':len(group),
                    'methods':{m:{'sumLower':sum(r['predictions'][m]['lower'] for r in group),'sumUpper':sum(r['predictions'][m]['upper'] for r in group),
                        'deviationLower':sum(r['predictions'][m]['lower']-r['actualTargetShare'] for r in group),'deviationUpper':sum(r['predictions'][m]['upper']-r['actualTargetShare'] for r in group),
                        'possibleClippingCount':sum(r['predictions'][m]['clippingPossible'] for r in group),
                        'maximumRawBoundViolation':max(max(0,-r['predictions'][m]['rawLower'],r['predictions'][m]['rawUpper']-1) for r in group)} for m in METHODS}})
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate backtest observation')
    return records,vectors
