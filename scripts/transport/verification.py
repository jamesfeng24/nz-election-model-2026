"""Independent intensity/error arithmetic and exact rational transport identities."""
import argparse
from fractions import Fraction
from math import exp, fsum, sqrt
from statistics import mean
from .common import read, save, verify_inputs, preserve, digest, PREFIX, METHOD
from .geography import admitted


def fraction(value):return Fraction(value['numerator'],value['denominator'])


def party_checks(artifact):
    checks=0
    for transition,data in artifact['transitions'].items():
        cross=read(f'data/processed/boundaries/{transition}/crosswalk.json')
        original=read(f'data/processed/boundaries/{transition}/party-votes.json')
        for scope,scenario in data['scopes'].items():
            geo=cross['scopes'][scope];witness=scenario['witnessVariables']
            groups=geo['constraints'].get('groups') or [{'id':e['source']+'-'+e['target'],'source':e['source'],
                'targets':[e['target']],'lower':e['lower'],'upper':e['upper']} for e in geo['edges']]
            for group in groups:
                flow=sum(v['population'] for v in witness if v['groupId']==group['id'])
                if not group['lower']<=flow<=group['upper']:raise ValueError('Independent group interval failure')
                if any(v['sourceCode']!=group['source'] or v['targetCode'] not in group['targets'] for v in witness if v['groupId']==group['id']):raise ValueError('Wrong flow route')
            for control in geo['constraints']['destinationEquations']:
                if sum(v['population'] for v in witness if v['targetCode']==control['target'])!=control['sumIncomingPopulation']:raise ValueError('Independent population conservation')
            sources=original['scopes'][scope]['sources'];masses={p:Fraction(0) for p in scenario['partyCategories']}
            bounds={t['targetCode']:{p['partyKey']:p for p in t['parties']} for t in original['scopes'][scope]['targets']}
            for target in scenario['targetPartyVectors']:
                code=target['targetCode'];terms=[]
                for source in sources:
                    population=sum(v['population'] for v in witness if v['sourceCode']==source)
                    numerator=sum(v['population'] for v in witness if v['sourceCode']==source and v['targetCode']==code)
                    terms.append((source,Fraction(numerator,population)))
                denominator=sum((sources[s]['validVotes']*w for s,w in terms),Fraction(0))
                if denominator!=fraction(target['validPartyVotesExact']):raise ValueError('Independent valid-party denominator')
                for row in target['parties']:
                    key=row['partyKey']
                    value=sum((next(p['votes'] for p in sources[s]['parties'] if p['partyKey']==key)*w for s,w in terms),Fraction(0))
                    if value!=fraction(row['votesExact']) or value/denominator!=fraction(row['shareExact']):raise ValueError('Independent party allocation')
                    bound=bounds[code][key]
                    if not bound['votesLower']-1e-6<=float(value)<=bound['votesUpper']+1e-6 or not bound['shareLower']-1e-12<=float(value/denominator)<=bound['shareUpper']+1e-12:raise ValueError('Point outside retained joint bounds')
                    masses[key]+=value;checks+=1
                if sum(fraction(p['shareExact']) for p in target['parties'])!=1:raise ValueError('Incomplete simplex')
            if masses!=scenario['sourcePartyMass']:raise ValueError('Independent source party mass lost')
    return checks


def prediction_checks():
    inventory={r['targetElectorateId']:r for r in read(PREFIX+'/historical-inventory.json')['records']}
    construction=read(PREFIX+'/construction.json');evaluation=read(PREFIX+'/evaluation.json')
    largest=0;vectors=0;metric_checks=0
    for fold in construction['folds']:
        actual={s['id']:s for s in read(f"data/processed/elections/{fold['targetYear']}.json")['electorates']}
        fitted=fold['savedFit']['parameters'];theta=fitted['coefficients'];center=fold['trainingOnlyMeans']
        audit=next(f for f in evaluation['folds'] if f['targetYear']==fold['targetYear'])
        errors_by_branch={}
        for branch,predictions in fold['predictions'].items():
            view='strict' if branch.endswith('_strict') else 'broad'
            threshold=None if branch.startswith('fallback') else 95 if '95' in branch else 90
            errors_by_branch[branch]=[]
            for prediction in predictions:
                row=inventory[prediction['targetElectorateId']]
                use=row['transportTier']=='exact' or threshold is not None and admitted(row['geography'],threshold)
                intensities={}
                for c in row['candidates']:
                    sval=c['s0Reported'] if use else None;rval=c['R'][view]['valueFraction'] if use else None
                    z=(0 if sval is None else theta['S']*(sval-center['S']))+(0 if rval is None else theta['R']*(rval-center['R']))
                    intensities[c['targetOccurrenceId']]=(c['observedPartySupport']+fitted['kappa'])*exp(z)
                total=fsum(intensities.values());q={cid:v/total for cid,v in intensities.items()}
                largest=max(largest,max(abs(q[cid]-v) for cid,v in prediction['candidateShares'].items()))
                target=actual[row['targetElectorateId']];observed={c['id']:c['votes']/target['validCandidateVotes'] for c in target['candidates']}
                errors=[100*(q[cid]-observed[cid]) for cid in q]
                errors_by_branch[branch].append((mean(abs(e) for e in errors),mean(e*e for e in errors)))
                vectors+=1
            result=audit['samples']['common90']['metrics'][branch]
            mae=mean(v[0] for v in errors_by_branch[branch]);rmse=sqrt(mean(v[1] for v in errors_by_branch[branch]))
            if abs(mae-result['maePP'])>1e-12 or abs(rmse-result['rmsePP'])>1e-12:raise ValueError('Independent error arithmetic')
            metric_checks+=2
        for branch,effects in audit['samples']['common90']['pairs'].items():
            control=effects['fallbackControl']
            gain=mean(a[0]-b[0] for a,b in zip(errors_by_branch[control],errors_by_branch[branch]))
            if abs(gain-effects['maeGainPP'])>1e-12:raise ValueError('Independent paired gain')
            metric_checks+=1
    if largest>1e-12:raise ValueError('Independent candidate intensity calculation')
    return {'candidateVectors':vectors,'predictionAgreementTolerance':1e-12,
            'allPredictionsWithinTolerance':True,'metricIdentities':metric_checks}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify_inputs()
    result={'stage':41,'partyValuesChecked':party_checks(read(PREFIX+'/party-construction.json')),
            'predictions':prediction_checks(),'priorDataFilesUnchanged':preserve(),
            'inputOutputHashes':{n:digest(PREFIX+'/'+n) for n in ('party-construction.json','construction.json','evaluation.json','readiness-2026.json')},
            'method':'independent exp/rational/scalar arithmetic; no model fits or live predictions'}
    save('independent-verification.json',result,a.check);print(result)


if __name__=='__main__':main()
