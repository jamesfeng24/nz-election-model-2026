"""Observed general JSON plus preserved supporting Māori party tables, read only."""
import hashlib
import json
from scripts.boundaries.census_2013 import ROOT, registered_bytes
from scripts.transform.historical import key, read_csv, count, turnout_table
from scripts.transform.modern_tables import party_table
from scripts.transform.modern_config import election_config


def load(year, crosswalk):
    hashes={}
    path=f'data/processed/elections/{year}.json'
    raw=(ROOT/path).read_bytes();hashes[path]=hashlib.sha256(raw).hexdigest();election=json.loads(raw)
    base=f'data/raw/elections/{year}/'
    if year==2011:
        data=registered_bytes(base+'e9/csv/e9_part4.csv',hashes)
        rows,_=read_csv(data);header=rows[1]
        valid_index=header.index('Total Valid Party Votes')
        definitions={p['sourceHeader']:p for p in election['electorates'][0]['parties']}
        if set(header[1:valid_index])!=set(definitions):raise ValueError('Legacy party header mismatch')
        ballots,_=turnout_table(registered_bytes(base+'e9/csv/e9_part9_1.csv',hashes))
        by_name={key(r[0]):r for r in rows[3:] if len(r)>valid_index}
        records={}
        for b in ballots:
            row=by_name[key(b['name'])]
            parties=[{'partyKey':definitions[h]['partyKey'],'partyName':definitions[h]['partyName'],
                      'sourceHeader':h,'votes':count(row[i])} for i,h in enumerate(header[1:valid_index],1)]
            if sum(p['votes'] for p in parties)!=b['validVotes'] or count(row[valid_index])!=b['validVotes']:
                raise ValueError('Supporting party denominator')
            records[key(b['name'])]={'name':b['name'],'validVotes':b['validVotes'],'parties':parties}
    else:
        config=election_config(year)
        data=registered_bytes(base+'statistics/csv/votes-for-registered-parties-by-electorate.csv',hashes)
        records=party_table(data,config.party_label_aliases)['records']
    general={key(e['name']):e for e in election['electorates']}
    result={}
    used=set()
    for kind,scope in crosswalk['scopes'].items():
        result[kind]={}
        for src in scope['sources']:
            name_key=key(src['name'])
            if name_key in used or name_key not in records:raise ValueError('Ambiguous/missing source electorate join')
            used.add(name_key);r=records[name_key]
            if kind=='general':
                e=general[name_key]
                if e['validPartyVotes']!=r['validVotes'] or {p['partyKey']:p['votes'] for p in e['parties']}!={p['partyKey']:p['votes'] for p in r['parties']}:
                    raise ValueError('Supporting table disagrees with preserved general observations')
                r={'name':e['name'],'validVotes':e['validPartyVotes'],'parties':e['parties'],'observedElectorateId':e['id']}
            result[kind][src['code']]={**r,'boundarySourceName':src['name'],
                                      'join':'unique within-election normalized label; no person/party continuity inference'}
    if used!=set(records):raise ValueError('Dropped observed electorate party record')
    for kind,scope in result.items():
        if sum(r['validVotes'] for r in scope.values())!=election['nationalControls']['party'][kind]['validVotes']:
            raise ValueError('Scope party control mismatch')
    for p in election['nationalControls']['parties']:
        if p['partyVotes'] is None:continue
        total=sum(q['votes'] for scope in result.values() for r in scope.values() for q in r['parties'] if q['partyKey']==key(p['name']))
        if total!=p['partyVotes']:raise ValueError('National party control: '+p['name'])
    return result,hashes
