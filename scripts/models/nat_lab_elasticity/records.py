"""Party-seat pairs only; no candidate-person continuity assumptions."""
import hashlib
import json
import re
from pathlib import Path
from scripts.boundaries.census_2013 import ROOT
from scripts.transform.historical import key,candidate_table as legacy
from scripts.transform.modern_tables import candidate_table as modern
from scripts.models.source_provenance import validated_supporting_sources

DEST=ROOT/'data/processed/models/nat-lab-elasticity'
PARTIES=('nationalparty','labourparty')
TRANSITIONS={2008:(2011,'2007'),2014:(2017,'2014'),2020:(2023,'2020')}


def extract(election,party):
    if election.get('candidateContestStatus','held')!='held':return None,'cancelled_contest'
    total=election['validCandidateVotes']
    if total<=0 or sum(c['votes'] for c in election['candidates'])!=total:raise ValueError('Candidate denominator')
    for c in election['candidates']:
        if c.get('personId') is not None:raise ValueError('Unexpected person identity')
        if c['votes']<0 or abs(c['share']-c['votes']/total)>1e-10:raise ValueError('Candidate share/count mismatch')
    cs=[c for c in election['candidates'] if key(c['party'])==party]
    if not cs:return None,'missing_candidacy'
    if len(cs)!=1:raise ValueError('Ambiguous party candidature')
    return cs[0],None


def build():
    hashes={}
    def read(path):
        raw=(ROOT/path).read_bytes();hashes[path]=hashlib.sha256(raw).hexdigest();return raw
    selection=json.loads(read('data/processed/models/party-vote-transform/selection.json'))
    if selection['selectionStatus']!='unresolved_between_methods' or selection['retainedCandidateSet']!=['additive','proportional','log_odds']:raise ValueError('Changed Stage5 selection')
    base=json.loads(read('data/processed/models/party-vote-transform/backtest-records.json'))['records']
    base=[r for r in base if r['primary'] and r['canonicalPartyId'] in PARTIES]
    snapshot=json.loads(read('data/source-plans/stage6-7-supporting-candidate-sources.json'))
    registry=json.loads((ROOT/'data/sources.json').read_bytes())
    supporting=validated_supporting_sources(snapshot,registry,read)
    elections={}
    for y in [2008,2011,2014,2017,2020,2023]:
        d=json.loads(read(f'data/processed/elections/{y}.json'));rs={key(e['name']):e for e in d['electorates']}
        plan=json.loads(read(f'data/source-plans/historical-{y}.json'))
        entries=[r for r in plan['resources'] if ('support' in r['role'].lower()) and ('cand_' in r['url'] or 'candidate-votes-by-voting-place' in r['url'])]
        if len(entries)!=7:raise ValueError('Supporting Maori inventory')
        names=[r['electorateName'] for r in base if r['sourceYear']==y or r['targetYear']==y]
        for entry in entries:
            if entry['url'] not in supporting:raise ValueError('Unpinned supporting candidate source')
            raw=supporting[entry['url']]['raw']
            c=legacy(raw) if y<=2014 else modern(raw,names)
            name=re.sub(r'\s+\d+$','',c['sourceElectorateLabel'])
            rs[key(name)]={'name':name,'validCandidateVotes':c['validVotes'],'candidates':c['candidates'],'candidateContestStatus':'held'}
        elections[y]=rs
    records=[];excluded=[]
    for r in base:
        s,t=r['sourceYear'],r['targetYear'];party=r['canonicalPartyId']
        if s not in TRANSITIONS or TRANSITIONS[s]!=(t,r['boundaryRegime']):raise ValueError('Changed-boundary or future transition')
        if r['boundarySourceClass']!='observed':raise ValueError('Synthetic candidate change forbidden')
        a,reason0=extract(elections[s][key(r['electorateName'])],party);b,reason1=extract(elections[t][key(r['electorateName'])],party)
        if a is None or b is None:
            excluded.append({'id':r['id'],'party':party,'scope':r['electorateType'],'electorate':r['electorateName'],'sourceYear':s,'targetYear':t,'sourceReason':reason0,'targetReason':reason1});continue
        p0,p1=r['sourceLocalShare'],r['actualTargetShare']
        if not all(0<=v<=1 for v in [p0,p1,a['share'],b['share']]):raise ValueError('Invalid share')
        records.append({'id':r['id'],'party':party,'scope':r['electorateType'],'sourceYear':s,'targetYear':t,'boundaryRegime':r['boundaryRegime'],'electorateId':r['electorateId'],'electorateName':r['electorateName'],
            'sourceCandidateName':a['name'],'targetCandidateName':b['name'],'sourceAffiliation':a['party'],'targetAffiliation':b['party'],'personIdentityInferred':False,
            'sourceCandidateShare':a['share'],'targetCandidateShare':b['share'],'sourcePartyShare':p0,'targetPartyShare':p1,
            'deltaParty':p1-p0,'deltaCandidate':b['share']-a['share'],
            'stage5PredictedTargetParty':{m:r['predictions'][m]['point'] for m in selection['retainedCandidateSet']}})
    return {'schemaVersion':1,'records':records,'excluded':excluded,'inputHashes':hashes}
