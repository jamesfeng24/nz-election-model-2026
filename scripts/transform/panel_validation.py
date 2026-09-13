"""Structural and lossless audit of a processed-input historical panel."""
from collections import defaultdict
import hashlib
import json
from .panel_config import YEARS, COUNTS, CONTRACT, canonical


def require(ok, message):
    if not ok:
        raise ValueError(message)


def status(electorate):
    return electorate.get('candidateContestStatus', 'held')


def unique(records, field, label):
    result = {r[field]: r for r in records}
    require(len(result) == len(records), 'Duplicate '+label)
    return result


def read_inputs(root):
    contract = json.loads((root/CONTRACT).read_bytes())
    loaded = {y:{} for y in YEARS}
    for path,digest in contract['inputSha256'].items():
        raw=(root/path).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==digest, 'Altered per-election input: '+path)
        value=json.loads(raw)
        kind='split' if '/split-votes/' in path else 'validation' if '-validation.' in path else 'elections'
        loaded[value['year']][kind]=value
    return loaded


def validate_electorates(panel):
    electorates=unique(panel['electorates'],'id','electorate')
    require({e['year'] for e in electorates.values()}==set(YEARS),'Unexpected years')
    for y,expected in COUNTS.items():
        actual=tuple(sum(r['year']==y for r in panel[k]) for k in ('electorates','party-votes','candidate-votes'))
        require(actual==expected,'Record counts: '+str(y))
    cancelled=[]
    for e in electorates.values():
        require(e['kind']=='general','Supporting electorate in primary panel')
        require(e['electionId']==f"nz-general-{e['year']}",'Election identity')
        require(e['id']==f"{e['electionId']}-electorate-{e['sourceElectorateNumber']:02}",'Electorate identity')
        require(e['boundaryVersionId']==f"historical-election-{e['year']}-as-published",'Boundary harmonization')
        require(status(e) in ('held','cancelled'),'Unknown contest status')
        if status(e)=='cancelled':
            cancelled.append((e['year'],e['name'],e['sourceElectorateNumber']))
            require(e['winnerCandidateId'] is None and e['majority'] is None and e['validCandidateVotes']==0,'Cancelled outcome')
    require(cancelled==[(2023,'Port Waikato',39)],'Unexpected cancellation coverage')
    return electorates


def validate_votes(panel,electorates):
    for kind,ballot in [('party-votes','Party'),('candidate-votes','Candidate')]:
        local=defaultdict(list)
        seen=set()
        for r in panel[kind]:
            require(r['electorateId'] in electorates,'Missing electorate reference')
            e=electorates[r['electorateId']]
            require(r['year']==e['year'] and r['electionId']==e['electionId'],'Foreign key year')
            identity=r['id'] if ballot=='Candidate' else (r['electorateId'],r['partyKey'])
            require(identity not in seen,'Duplicate '+kind);seen.add(identity)
            require(type(r['votes']) is int and r['votes']>=0,'Invalid votes')
            require(r['canonicalPartyId']==canonical(r['partyKey']),'Canonical party mismatch')
            denominator=e['valid'+ballot+'Votes']
            if ballot=='Candidate':
                require(r['id'].startswith(e['id']+'-candidate-'),'Candidate occurrence scope')
                require(r['personId'] is None,'Unreviewed person identity')
            if ballot=='Candidate' and status(e)=='cancelled':
                require(r['votes']==0 and r['share'] is None and r['sourceShare'] is None and r['elected'] is None,'Cancelled candidate outcome')
            else:
                require(denominator>0 and isinstance(r['share'],(float,int)) and 0<=r['share']<=1 and abs(r['share']-r['votes']/denominator)<1e-12,'Invalid share')
                if ballot=='Candidate':require(type(r['elected']) is bool,'Invalid held elected status')
            local[e['id']].append(r)
        for e in electorates.values():
            records=local[e['id']]
            require(sum(r['votes'] for r in records)==e['valid'+ballot+'Votes'],'Denominator reconciliation')
            if ballot=='Candidate' and status(e)=='held':
                ranked=sorted(records,key=lambda r:r['votes'],reverse=True)
                winners=[r for r in records if r['elected']]
                require(len(winners)==1 and winners[0]['id']==e['winnerCandidateId']==ranked[0]['id'],'Winner mismatch')
                require(ranked[0]['votes']-ranked[1]['votes']==e['majority'],'Margin mismatch')


def validate_splits(panel,electorates):
    matrices=panel['split-votes']
    unique(matrices,'id','split matrix')
    require(len(matrices)==384 and {m['electorateId'] for m in matrices}==set(electorates),'Split coverage')
    candidates=defaultdict(set)
    for c in panel['candidate-votes']:candidates[c['electorateId']].add(c['id'])
    for m in matrices:
        e=electorates[m['electorateId']]
        require(m['year']==e['year'],'Split year')
        require(m['countAvailability']=='unavailable: source publishes rounded percentages, not joint counts','Split precision')
        if status(e)=='cancelled':
            require(m.get('candidateContestStatus')=='cancelled' and m.get('behaviouralEvidence') is False and m['unallocatedPartyVotes']==e['validPartyVotes']+e['partyBallot']['informalVotes'],'Cancelled split semantics')
        else:
            require(m.get('behaviouralEvidence',True) is True and m.get('candidateContestStatus','held')=='held','Unexpected non-behavioural matrix')
        for row in m['rows']:
            for cell in row['cells']:
                require(cell['count'] is None,'Invented joint count')
                require(cell['reportedPercent'] is None or 0<=cell['reportedPercent']<=100,'Split percentage')
                require(cell['candidateId'] is None or cell['candidateId'] in candidates[e['id']],'Split candidate reference')


def validate_controls(panel,electorates):
    require([r['year'] for r in panel['election-controls']]==list(YEARS),'Control years')
    for c in panel['election-controls']:
        local=[e for e in electorates.values() if e['year']==c['year']]
        for ballot in ('party','candidate'):
            t=c['nationalControls'][ballot]
            for field in ('validVotes','informalVotes','votesCast','enrolled'):
                require(sum(e[ballot+'Ballot'][field] for e in local)==t['general'][field],'Panel general control')
                require(t['general'][field]+t['maori'][field]==t['national'][field],'Panel national control')
        if c['year']==2008:
            require(c['aggregateSplitAvailability']=='not-collected' and c['aggregateMatrices'] is None and c['officialSplitSummary'] is None,'Missing aggregate evidence changed')


def validate_projection(panel,loaded):
    """Reconstruct source objects from panel fields; no raw parsing or inference."""
    meta={e['id']:e for e in panel['electorates']}
    grouped={kind:defaultdict(list) for kind in ('party-votes','candidate-votes')}
    added={'year','electionId','electorateId','sourceIds','canonicalPartyId'}
    for kind in grouped:
        for r in panel[kind]:grouped[kind][r['electorateId']].append({k:v for k,v in r.items() if k not in added})
    for y,inputs in loaded.items():
        for original in inputs['elections']['electorates']:
            reconstructed={**meta[original['id']], 'parties':grouped['party-votes'][original['id']], 'candidates':grouped['candidate-votes'][original['id']]}
            require(reconstructed==original,'Lossy electorate projection')
        split=inputs['split']
        require([m for m in panel['split-votes'] if m['year']==y]==split['matrices'],'Lossy split projection')
        control=next(c for c in panel['election-controls'] if c['year']==y)
        require(control['perYearValidation']==inputs['validation'],'New or altered per-year discrepancy/validation')
        require(control['nationalControls']==inputs['elections']['nationalControls'],'Lossy national controls')
        require(control['sourceIds']==inputs['elections']['sourceIds'],'Control provenance changed')
        for field in ('aggregateMatrices','officialSplitSummary','partyGrouping'):
            require(control[field]==split.get(field),'Missing or altered aggregate evidence')
        for field,value in split.items():
            if field not in ('schemaVersion','year','matrices'):
                require(control.get(field)==value,'Lost source convention: '+field)


def validate(panel,root,loaded=None):
    electorates=validate_electorates(panel)
    validate_votes(panel,electorates)
    validate_splits(panel,electorates)
    validate_controls(panel,electorates)
    validate_projection(panel,loaded or read_inputs(root))
    source_ids={r['id'] for r in json.loads((root/'data/sources.json').read_bytes())['sources']}
    for records in panel.values():
        for r in records:
            require(bool(r['sourceIds']) and set(r['sourceIds'])<=source_ids,'Unknown provenance source')
            if 'electorateId' in r and 'canonicalPartyId' in r:
                require(r['sourceIds']==electorates[r['electorateId']]['sourceIds'],'Vote provenance changed')
