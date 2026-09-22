"""Offline Stage5 generation, strictly pinned historical inputs only."""
import argparse
import hashlib
import json
from scripts.models.party_vote_transform.inputs import Inputs,DEST,ROOT,continuity
from scripts.models.party_vote_transform.records import build_records
from scripts.models.party_vote_transform.scoring import build_scores


def encode(x):return (json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()


def build():
    contract=json.loads((DEST/'input-contract.json').read_bytes())['inputHashes']
    from scripts.models.party_vote_transform.inputs import allowed
    for path,h in contract.items():
        allowed(path)
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('Changed historical input: '+path)
    inputs=Inputs();elections=inputs.elections();spec=json.loads((DEST/'specification.json').read_bytes())
    if [(r['sourceYear'],r['targetYear'],r['primary']) for r in spec['transitions']]!=[(2008,2011,True),(2011,2014,False),(2014,2017,True),(2017,2020,False),(2020,2023,True)]:raise ValueError('Unexpected scored transition')
    ids=continuity(elections,spec['transitions']);records,vectors=build_records(inputs,elections,ids,spec)
    if any(contract.get(p)!=h for p,h in inputs.hashes.items()):raise ValueError('Unpinned evidence')
    outputs={'party-continuity.json':{'schemaVersion':1,'records':ids},'backtest-records.json':{'schemaVersion':1,'records':records,'errorBoundsMeaning':'Marginal/conservative, not jointly attainable; no 2026 outcome'},
        'vector-diagnostics.json':{'schemaVersion':1,'records':vectors,'renormalizationApplied':False},'scores.json':{'schemaVersion':1,'units':'percentage points except clipping fraction','reports':build_scores(records)}}
    manifest={'schemaVersion':1,'inputHashes':contract,'specificationSha256':hashlib.sha256((DEST/'specification.json').read_bytes()).hexdigest(),
        'codeHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'scripts/models/party_vote_transform').glob('*.py'))},
        'outputHashes':{p:hashlib.sha256(encode(d)).hexdigest() for p,d in outputs.items()},'recordCount':len(records),'scoredYears':[2008,2011,2014,2017,2020,2023]}
    outputs['manifest.json']=manifest
    return outputs


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args();outputs=build()
    for name,d in outputs.items():
        path=DEST/name;raw=encode(d)
        if args.check:
            if not path.exists() or path.read_bytes()!=raw:raise ValueError('Stale '+name)
        else:path.write_bytes(raw)
    print('Stage5 records:',outputs['manifest.json']['recordCount'])

if __name__=='__main__':main()
