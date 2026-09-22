"""Pinned historical party-only evidence; no current political inputs."""
import hashlib
import json
from scripts.boundaries.census_2013 import ROOT
from scripts.transform.historical import key,read_csv,count,turnout_table
from scripts.transform.modern_tables import party_table
from scripts.transform.modern_config import election_config
from scripts.transform.panel_config import canonical,YEARS

DEST=ROOT/'data/processed/models/party-vote-transform'


def allowed(path):
    permitted={f'data/processed/elections/{y}.json' for y in YEARS}
    permitted|={f'data/raw/elections/{y}/e9/csv/{f}' for y in YEARS[:3] for f in ['e9_part4.csv','e9_part9_1.csv']}
    permitted|={f'data/raw/elections/{y}/statistics/csv/votes-for-registered-parties-by-electorate.csv' for y in YEARS[3:]}
    permitted|={f'data/processed/boundaries/{t}/{f}' for t in ['2011-2014','2017-2020'] for f in ['party-votes.json','crosswalk.json']}
    permitted|={'data/processed/boundaries/backtesting-readiness.json','data/processed/historical/2008-2023/party-votes.json','data/processed/historical/2008-2023/manifest.json'}
    if path not in permitted:raise ValueError('Unapproved Stage5 input: '+path)


class Inputs:
    def __init__(self):self.hashes={}
    def raw(self,path):
        allowed(path);raw=(ROOT/path).read_bytes();self.hashes[path]=hashlib.sha256(raw).hexdigest();return raw
    def json(self,path):return json.loads(self.raw(path))
    def elections(self):
        panel=self.json('data/processed/historical/2008-2023/party-votes.json')['records']
        self.json('data/processed/historical/2008-2023/manifest.json')
        identity={(r['year'],r['partyKey']):r['canonicalPartyId'] for r in panel}
        result={}
        for year in YEARS:
            e=self.json(f'data/processed/elections/{year}.json');general={key(r['name']):r for r in e['electorates']}
            base=f'data/raw/elections/{year}/'
            if year<=2014:
                rows,_=read_csv(self.raw(base+'e9/csv/e9_part4.csv'));header=rows[1];end=header.index('Total Valid Party Votes')
                definitions={p['sourceHeader']:p for p in e['electorates'][0]['parties']}
                ballots,_=turnout_table(self.raw(base+'e9/csv/e9_part9_1.csv'))
                by_name={key(r[0]):r for r in rows[3:] if len(r)>end}
                records={}
                for ballot in ballots:
                    row=by_name[key(ballot['name'])]
                    records[key(ballot['name'])]={'name':ballot['name'],'validVotes':count(row[end]),'parties':[{'partyKey':definitions[h]['partyKey'],'partyName':definitions[h]['partyName'],'votes':count(row[i])} for i,h in enumerate(header[1:end],1)]}
            else:records=party_table(self.raw(base+'statistics/csv/votes-for-registered-parties-by-electorate.csv'),election_config(year).party_label_aliases)['records']
            scopes={'general':{},'maori':{}};parties={}
            for name,r in records.items():
                kind='general' if name in general else 'maori'
                if kind=='general':
                    observed=general[name]
                    if observed['validPartyVotes']!=r['validVotes'] or {p['partyKey']:p['votes'] for p in observed['parties']}!={p['partyKey']:p['votes'] for p in r['parties']}:raise ValueError('Observed mismatch')
                if r['validVotes']<=0 or sum(p['votes'] for p in r['parties'])!=r['validVotes']:raise ValueError('Denominator mismatch')
                ps={}
                for p in r['parties']:
                    if type(p['votes']) is not int or p['votes']<0:raise ValueError('Invalid votes')
                    cid=identity[year,p['partyKey']]
                    if cid!=canonical(p['partyKey']) or cid in ps:raise ValueError('Ambiguous canonical identity')
                    ps[cid]={**p,'share':p['votes']/r['validVotes']}
                    parties.setdefault(cid,{'sourceKey':p['partyKey'],'label':p['partyName'],'votes':0})['votes']+=p['votes']
                scopes[kind][name]={'id':general[name]['id'] if kind=='general' else f'nz-general-{year}-maori-source-{name}', 'name':r['name'],'validVotes':r['validVotes'],'parties':ps}
            for kind,rs in scopes.items():
                if sum(r['validVotes'] for r in rs.values())!=e['nationalControls']['party'][kind]['validVotes']:raise ValueError('Scope totals')
            if len(scopes['maori'])!=7:raise ValueError('Maori inventory')
            national=e['nationalControls']['party']['national']['validVotes']
            controls={canonical(key(p['name'])):p['partyVotes'] for p in e['nationalControls']['parties'] if p['partyVotes'] is not None}
            for cid,p in parties.items():
                if p['votes']!=controls[cid]:raise ValueError('National party total')
                p['share']=p['votes']/national
            result[year]={'scopes':scopes,'parties':parties,'nationalValidVotes':national}
        return result


def continuity(elections,transitions):
    rows=[]
    for t in transitions:
        s,d=t['sourceYear'],t['targetYear'];a,b=elections[s]['parties'],elections[d]['parties']
        for cid in sorted(set(a)|set(b)):
            status='eligible' if cid in a and cid in b else ('entrant' if cid in b else 'exit')
            if status=='eligible' and not (0<a[cid]['share']<1 and 0<b[cid]['share']<1):status='excluded_national_domain'
            rows.append({'sourceYear':s,'targetYear':d,'canonicalPartyId':cid,'status':status,'source':a.get(cid),'target':b.get(cid),'identityEvidence':'existing historical panel canonicalPartyId; D017/D022 only; report groupings excluded'})
    return rows
