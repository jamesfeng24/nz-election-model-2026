"""Offline same-boundary contract and notional output integrity audit; no model fitting."""
import argparse
import hashlib
import json
import math
from scripts.boundaries.census_2013 import ROOT
from scripts.boundaries.contract import TRANSITIONS
from scripts.transform.historical import key

REGIMES = {2008:'2007', 2011:'2007', 2014:'2014', 2017:'2014', 2020:'2020', 2023:'2020', 2026:'2025'}


def read(path, hashes):
    raw=(ROOT/path).read_bytes()
    hashes[path]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def verify_hashes(hashes):
    for path, expected in hashes.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Changed reconstruction input: '+path)


def names(rows, field):
    result=set()
    for r in rows:
        label=r[field]
        if label=='Rangit?¢kei':
            if r.get('targetCode',r.get('code'))!='043':raise ValueError('Ambiguous source typography join')
            label='Rangitīkei'
        result.add(key(label))
    if len(result)!=len(rows):raise ValueError('Duplicate electorate join')
    return result


def audit_party(data):
    if data['nominalAllocation'] is not None:raise ValueError('Unexpected nominal allocation')
    result={}
    for kind, scope in data['scopes'].items():
        sources=scope['sources']
        totals={r['partyKey']:sum(p['votes'] for s in sources.values() for p in s['parties'] if p['partyKey']==r['partyKey']) for r in scope['partyMassConservation']}
        for r in scope['partyMassConservation']:
            if r['sourceVotes']!=totals[r['partyKey']] or r['targetVoteSumForEveryFeasibleAllocation']!=totals[r['partyKey']]:
                raise ValueError('Changed party mass control')
        expected=set(totals)
        gaps=[]
        for target in scope['targets']:
            if not set(target['sourceCodes'])<=set(sources):raise ValueError('Invalid source reference')
            if len(target['parties'])!=len(expected) or {r['partyKey'] for r in target['parties']}!=expected:raise ValueError('Party coverage')
            for row in target['parties']:
                for quantity in ['Votes','Share']:
                    lo,hi=row['minimum'+quantity+'Bracket'],row['maximum'+quantity+'Bracket']
                    if not all(math.isfinite(v) for v in lo+hi) or not 0<=lo[0]<=lo[1]<=hi[1] or not lo[0]<=hi[0]<=hi[1]:raise ValueError('Invalid extremum bracket')
                    stem=quantity.lower()
                    if row[stem+'Lower']!=lo[0] or row[stem+'Upper']!=hi[1]:raise ValueError('Lost numerical bracket')
                    if quantity=='Share' and hi[1]>1:raise ValueError('Share outside range')
                    for label, bracket in [('minimum',lo),('maximum',hi)]:
                        gap=row['optimizationGaps'][label+quantity]
                        if gap+1e-8<bracket[1]-bracket[0]:raise ValueError('Understated optimization gap')
                    if row[stem] is not None and not lo[0]-1e-8<=row[stem]<=hi[1]+1e-8:raise ValueError('Point outside bounds')
                gaps.append(max(row['optimizationGaps']['minimumVotes'],row['optimizationGaps']['maximumVotes']))
        result[kind]={'targets':len(scope['targets']),'partyRecords':sum(len(t['parties']) for t in scope['targets']),
                      'sourceVotes':sum(totals.values()),'partyConservationControls':len(totals),
                      'maximumNumericalGapVotes':max(gaps)}
    return result


def build():
    hashes={}; observed={}; synthetic={}; audits={}
    for year in REGIMES:
        if year==2026:continue
        observed[year]=read(f'data/processed/elections/{year}.json',hashes)
    for transition in TRANSITIONS:
        folder=f'data/processed/boundaries/{transition}'
        data=read(folder+'/party-votes.json',hashes)
        manifest=read(folder+'/party-votes-manifest.json',hashes)
        if manifest['outputSha256']!=hashes[folder+'/party-votes.json']:raise ValueError('Changed notional output')
        verify_hashes(manifest['codeHashes']);verify_hashes(data['inputHashes'])
        crosswalk=read(folder+'/crosswalk.json',hashes)
        src,dst=map(int,transition.split('-'))
        metadata=crosswalk['transition']
        if (metadata['sourceElectionYear'],metadata['targetElectionYear'])!=(src,dst):raise ValueError('Wrong transition years')
        for role,year in [('source',src),('target',dst)]:
            boundary=metadata.get(role+'BoundaryVersion',metadata.get(role+'BoundaryId'))
            if boundary not in [REGIMES[year], 'stats-nz-electorates-'+REGIMES[year], 'stats-nz-electorates-final-'+REGIMES[year]]:raise ValueError('Boundary regime mismatch')
        if names(data['scopes']['general']['targets'],'targetName')!=names(crosswalk['scopes']['general']['targets'],'name'):raise ValueError('Target inventory mismatch')
        audits[transition]=audit_party(data);synthetic[src]=data
    comparisons=[]
    for src,dst in [(2008,2011),(2011,2014),(2014,2017),(2017,2020),(2020,2023)]:
        adjusted=src in [2011,2017]
        left=synthetic[src]['scopes']['general']['targets'] if adjusted else observed[src]['electorates']
        left_names=names(left,'targetName' if adjusted else 'name')
        right_names=names(observed[dst]['electorates'],'name')
        if left_names!=right_names:raise ValueError('Comparison electorate mismatch')
        if not adjusted and REGIMES[src]!=REGIMES[dst]:raise ValueError('Unadjusted boundary change')
        comparisons.append({'sourceYear':src,'targetYear':dst,'boundaryRegime':REGIMES[dst],
                            'leftClass':'synthetic_bounds' if adjusted else 'observed',
                            'rightClass':'observed','generalElectorates':len(right_names),
                            'status':'same_boundary_inventory_validated'})
    return {'schemaVersion':1,'status':'validated_data_contract_not_model_backtest','inputHashes':hashes,
            'partyAudits':audits,'comparisons':comparisons,
            'sourceLocalNameMappings':[{'transition':'2011-2014','targetCode':'043','sourceLabel':'Rangit?¢kei','electionLabel':'Rangitīkei','evidence':'Same official electorate number043; Schedule C sourceName Rangitῑkei. Raw and crosswalk source labels preserved.'}],
            'futureBaseline':{'sourceYear':2023,'targetYear':2026,'boundaryRegime':'2025','class':'synthetic_bounds','generalElectorates':64},
            'limitations':['Same-boundary membership is checked using preserved boundary regimes and normalized source-local electorate labels; observed IDs remain unchanged.',
                          'Party identities across elections are not harmonized by this contract. No model fitted.',
                          'Marginal bound endpoints cannot be selected independently; optimization gaps remain separate from geographic uncertainty.']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
    data=build();raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
    path=ROOT/'data/processed/boundaries/backtesting-readiness.json'
    if args.check:
        if path.read_bytes()!=raw:raise ValueError('Stale readiness audit')
    else:path.write_bytes(raw)
    print('Five same-boundary comparisons and three party baselines passed')

if __name__=='__main__':main()
