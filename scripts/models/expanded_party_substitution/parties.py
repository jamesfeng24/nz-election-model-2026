"""Reuse the unchanged Stage23 whole-roster composition on certified exact IDs."""
from scripts.models.complete_party_vector.construction import construct_vector,validate_simplex
from .common import read,S23,keyed


def one(row,categories):
    scenario={c['categoryId']:c['suppliedTargetNationalShare'] for c in categories if c['relationship']!='exit'}
    keys={c['categoryId']:c['targetPartyKey'] for c in categories if c['relationship']!='exit'}
    if len(set(keys.values()))!=len(keys):raise ValueError('Duplicate party ballot group')
    vector,status=construct_vector(categories,keyed(row['sourceCategories'],'categoryId'),scenario)
    return {'geographyId':row['geographyId'],'sourceYear':row['sourceYear'],'targetYear':row['targetYear'],
            'sourceElectorateId':row['sourceElectorateId'],'targetElectorateId':row['targetElectorateId'],
            'contestStatus':row['contestStatus'],'originalFrame':row['originalFrame'],'scope':row['scope'],
            'applicability':'constructed','localPartyShares':vector,'targetPartyGroupKeys':keys,
            'suppliedNationalScenario':scenario,'sourceAffinityStatus':status,
            'nationalReconciliation':'not_imposed; no_target_local_controls_used'}


def build(inventory):
    categories={(r['sourceYear'],r['targetYear']):r['categories'] for r in inventory['categoryRelationships']}
    old=keyed(read(S23+'construction.json')['records'],'targetElectorateId')
    available=[r for r in inventory['partyFrame'] if r['partyInputStatus']=='available']
    results={};checks=[]
    # Matching vectors must reproduce before constructing newly admitted years.
    for matching in (True,False):
        for row in available:
            cid=row['targetElectorateId']
            if (cid in old)!=matching:continue
            result=one(row,categories[(row['sourceYear'],row['targetYear'])])
            if matching:
                reference=old[cid]
                if set(result['localPartyShares'])!=set(reference['localPartyShares']) or result['targetPartyGroupKeys']!=reference['targetPartyGroupKeys']:
                    raise ValueError('Stage23 reference categories/group mapping changed')
                gap=max(abs(v-reference['localPartyShares'][c]) for c,v in result['localPartyShares'].items())
                if gap>1e-12:raise ValueError('Stage23 vector reproduction failed')
                checks.append({'targetElectorateId':cid,'maximumAbsoluteShareDifference':gap,'tolerance':1e-12})
            results[cid]=result
    coverage=[{k:r[k] for k in ('geographyId','targetElectorateId','sourceYear','targetYear','scope','contestStatus','partyInputStatus','reason')}
              for r in inventory['partyFrame']]
    return {'stage':31,'records':[results[r['targetElectorateId']] for r in available],
            'fullFrameCoverage':coverage,'stage23Reproduction':checks,
            'sourceNationalPopulationDenominatorsFromFullOfficialPopulation':True,'operationalSelection':None}


def ballot_vector(row):
    shares=row['localPartyShares'];groups=row['targetPartyGroupKeys']
    if set(shares)!=set(groups) or len(set(groups.values()))!=len(groups):raise ValueError('Incomplete or duplicate ballot-group vector')
    validate_simplex(list(shares.values()))
    return {groups[c]:v for c,v in shares.items()}
