"""Synthetic party-vote baselines conditional on coupled population crosswalks."""
import argparse
import hashlib
import json
from fractions import Fraction
from scripts.boundaries.census_2013 import ROOT
from scripts.boundaries.contract import system, fraction, TRANSITIONS
from scripts.boundaries.party_inputs import load
from scripts.boundaries.notional_bounds import TargetEnvelope


def party_inventory(records):
    definitions={}
    expected=None
    for r in records.values():
        keys={p['partyKey'] for p in r['parties']}
        if len(keys)!=len(r['parties']) or (expected is not None and keys!=expected):raise ValueError('Party inventory mismatch')
        expected=keys
        if sum(p['votes'] for p in r['parties'])!=r['validVotes']:raise ValueError('Source vote conservation')
        for p in r['parties']:
            if p['partyKey'] in definitions and definitions[p['partyKey']]!=p['partyName']:
                raise ValueError('Unresolved source party label variation')
            definitions[p['partyKey']]=p['partyName']
    return definitions


def scope_baseline(scope,records,max_nodes):
    p=system(scope)
    parties=party_inventory(records)
    votes={s:{q['partyKey']:q['votes'] for q in r['parties']} for s,r in records.items()}
    witness=p.solve(p.vector())
    mass=[]
    for party in sorted(parties):
        observed=sum(v[party] for v in votes.values())
        reconstructed=sum(votes[s][party]*sum(witness*p.vector(s,t))/sum(witness*p.vector(s))
                          for s,t in p.edge_inventory())
        if abs(reconstructed-observed)>1e-7:raise ValueError('Party mass conservation failed')
        mass.append({'partyKey':party,'sourceVotes':observed,'targetVoteSumForEveryFeasibleAllocation':observed})
    targets=[]
    maximum_vote_gap=maximum_share_gap=0.0
    for target in scope['targets']:
        envelope=TargetEnvelope(p,scope,target['code'])
        denominators=[records[s]['validVotes'] for s in envelope.sources]
        rows=[]
        for party in sorted(parties):
            coefficients=[votes[s][party] for s in envelope.sources]
            intervals=[]
            for den in [None,denominators]:
                lo=envelope.bound(coefficients,den,max_nodes=max_nodes)
                hi=envelope.bound(coefficients,den,maximize=True,max_nodes=max_nodes)
                intervals.append((lo,hi))
            (vl,vu),(sl,su)=intervals
            maximum_vote_gap=max(maximum_vote_gap,vl['gap'],vu['gap'])
            maximum_share_gap=max(maximum_share_gap,sl['gap'],su['gap'])
            exact_votes=None
            if all(fraction(e['weightLower'])==fraction(e['weightUpper']) for e in envelope.edges):
                exact_votes=float(sum(Fraction(v)*fraction(e['weightLower']) for v,e in zip(coefficients,envelope.edges)))
            shares={Fraction(v,d) for v,d in zip(coefficients,denominators)}
            exact_share=float(next(iter(shares))) if len(shares)==1 else None
            rows.append({'partyKey':party,'sourcePartyName':parties[party],
                'votes':exact_votes,'votesLower':vl['outer'],'votesUpper':vu['outer'],
                'share':exact_share,'shareLower':sl['outer'],'shareUpper':su['outer'],
                'minimumVotesBracket':[vl['outer'],vl['attainable']],
                'maximumVotesBracket':[vu['attainable'],vu['outer']],
                'minimumShareBracket':[sl['outer'],sl['attainable']],
                'maximumShareBracket':[su['attainable'],su['outer']],
                'optimizationGaps':{'minimumVotes':vl['gap'],'maximumVotes':vu['gap'],
                    'minimumShare':sl['gap'],'maximumShare':su['gap']}})
        targets.append({'targetCode':target['code'],'targetName':target['name'],'parties':rows,
            'sourceCodes':envelope.sources})
    return {'sources':records,'targets':targets,'partyMassConservation':mass,
            'maximumNumericalExtremumGapVotes':maximum_vote_gap,
            'maximumNumericalExtremumGapShare':maximum_share_gap}


def build(transition,max_nodes=64):
    path=f'data/processed/boundaries/{transition}/crosswalk.json'
    raw=(ROOT/path).read_bytes();crosswalk=json.loads(raw)
    records,hashes=load(int(transition[:4]),crosswalk)
    hashes[path]=hashlib.sha256(raw).hexdigest()
    scopes={k:scope_baseline(crosswalk['scopes'][k],r,max_nodes) for k,r in records.items()}
    registry=json.loads((ROOT/'data/sources.json').read_bytes())['sources']
    return {'schemaVersion':1,'transitionId':transition,'dataClass':'synthetic_notional_party_vote_bounds',
        'inputHashes':hashes,'sourceRegistryIds':sorted(s['id'] for s in registry if s['rawPath'] in hashes),
        'scopes':scopes,'nominalAllocation':None,
        'equations':{'partyVotes':'V[target,party] = sum_source observedVotes[source,party] * w[source,target]',
            'validVotes':'V[target] = sum_source observedValidVotes[source] * w[source,target]',
            'share':'V[target,party] / V[target]',
            'massConservation':'sum_target V[target,party] = sum_source observedVotes[source,party], for every jointly feasible crosswalk'},
        'optimizer':{'method':'deterministic global spatial branch-and-bound, McCormick LP outer bounds plus feasible attainable brackets',
            'maxNodesPerExtremum':max_nodes,'voteGapTarget':0.25,'shareGapTarget':2e-6,
            'gapMeaning':'Remaining certified numerical enclosure gap, distinct from geographic identification uncertainty. Node limit may be reached; nonzero gaps are never represented as exact extrema.',
            'sourceFeasibleSet':'Crosswalk groups/destination equations remain binding. Do not independently choose published marginal vote/share endpoints.'},
        'limitations':['Population-weighted within-source uniform party distribution is a synthetic reconstruction assumption, not observed local voting behaviour.',
            'No fitted model, candidate-person linking or historical TOP→Opportunity mapping.',
            'Party names/keys remain election-local. Māori supporting votes come from preserved official tables and reconcile nationally.',
            'Port Waikato party votes remain substantive; no candidate or split inference is made here.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transition',choices=TRANSITIONS,required=True)
    parser.add_argument('--max-nodes',type=int,default=64)
    parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.max_nodes<3:raise ValueError('At least three search nodes required')
    result=build(args.transition,args.max_nodes)
    raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    folder=ROOT/f'data/processed/boundaries/{args.transition}'
    paths=['scripts/boundaries/'+x+'.py' for x in ['notional','notional_bounds','party_inputs','coupled','contract']]
    manifest={'schemaVersion':1,'inputHashes':result['inputHashes'],
              'codeHashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
              'outputSha256':hashlib.sha256(raw).hexdigest()}
    for name,content in {'party-votes.json':raw,'party-votes-manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()}.items():
        path=folder/name
        if args.check:
            if not path.exists() or path.read_bytes()!=content:raise ValueError('Stale '+str(path))
        else:path.write_bytes(content)
    print(json.dumps({k:{'targets':len(s['targets']),'partyRecords':sum(len(t['parties']) for t in s['targets']),
                        'maximumVoteGap':s['maximumNumericalExtremumGapVotes'],'maximumShareGap':s['maximumNumericalExtremumGapShare']} for k,s in result['scopes'].items()}))


if __name__=='__main__':main()
