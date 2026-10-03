"""Outcome-free Stage31 construction entry point; never invokes fitting."""
import argparse
from .common import local,save,phase,verify_inputs,SCENARIOS
from . import parties,candidates


def build(inventory=None):
    inventory=local('input-inventory.json') if inventory is None else inventory
    party=parties.build(inventory);candidate=candidates.build(inventory,party)
    compat=candidates.compatibility(inventory,party)
    return party,candidate,{'checks':compat,'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify_inputs()
    party,candidate,compat=build()
    for name,value in [('party-vectors.json',party),('candidate-predictions.json',candidate),('compatibility.json',compat)]:save(name,value,a.check)
    phase('construction',['party-vectors.json','candidate-predictions.json','compatibility.json'],
          ['scripts/models/expanded_party_substitution/'+n+'.py' for n in ('parties','candidates','construction')],a.check)
    print('Party vectors',len(party['records']),'matching Stage23',len(party['stage23Reproduction']),
          'fitted fold/scenarios',sum(f['scenarios'][s]['status']=='constructed' for f in candidate['folds'] for s in SCENARIOS),
          'compatibility checks',len(compat['checks']))


if __name__=='__main__':main()
