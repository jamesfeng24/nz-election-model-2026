"""Independent Decimal/count arithmetic; no model fitting or forecast scoring."""
import hashlib
import json
import re
from collections import Counter
from datetime import date,timedelta
from decimal import Decimal
from fractions import Fraction
from .run import ROOT,RAW,OUT,save


def run(check=False):
    polls=json.loads((OUT/'polls.json').read_text())['records']
    ledger=json.loads((RAW/'acquisition-ledger.json').read_text())
    sources={r['id']:r for r in ledger['resources']}
    tested=0
    for r in polls:
        for p,obs in r['estimates'].items():
            if obs['status'] not in ('rounded','rounded_zero'):continue
            raw=Decimal(obs['published']);unit=Decimal(10)**raw.as_tuple().exponent/100
            lo=max(Decimal(0),raw/100-unit/2);hi=min(Decimal(1),raw/100+unit/2)
            if obs['bounds']!=[float(lo),float(hi)]:raise ValueError('Independent rounding '+r['id'])
            tested+=1
        for provenance in r['provenance']:
            if provenance['sourceId'] not in sources:raise ValueError('Dangling source')
    anchored=json.loads((OUT/'official-results-isolated.json').read_text())['records']
    cells=0
    for r in anchored:
        data=json.loads((ROOT/f"data/processed/elections/{r['year']}.json").read_text())
        total=sum(p['partyVotes'] for p in data['nationalControls']['parties'] if p['partyVotes'] is not None)
        if total!=r['validPartyVotes']:raise ValueError('Independent full national total')
        for key,value in r['shares'].items():
            count=sum(x['count'] for x in r['categoryEvidence'] if x['modelCategory']==key)
            if abs(float(Fraction(count,total))-value)>1e-15:raise ValueError('Independent anchor ratio')
            cells+=1
    # Verify finite horizon dates independently, without party/candidate outcomes.
    horizons=json.loads((OUT/'coverage.json').read_text())['horizons']
    for h in horizons:
        e=next(r for r in anchored if r['year']==h['election'])
        expected=date.fromisoformat(e['electionAt'][:10])-timedelta(days=h['horizonDays'])
        if h['cutoff'][:10]!=expected.isoformat():raise ValueError('Independent horizon')
    save('independent-verification.json',{'roundedCellsChecked':tested,'officialCategoryRatiosChecked':cells,
         'horizonManifestsChecked':len(horizons),'polls':len(polls),
         'sourceReferencesChecked':sum(len(r['provenance']) for r in polls),
         'method':'Decimal printed-precision bounds; Fraction official counts; date subtraction; no fits or scores'},check)
    print(tested,'rounding cells;',cells,'national ratios;',len(horizons),'horizon manifests independently checked')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
