"""Generic controlled population crosswalk; observed elections are never edited."""
import argparse
import hashlib
import json
from fractions import Fraction
from scripts.boundaries.current_inputs import ROOT
from scripts.boundaries.feasible import tighten_destinations, outgoing_weight_bounds, fraction_json
from scripts.boundaries.composition import summarize


def build_scope(cells, controls, source_names, target_names, unchanged, renames, source_label_aliases=None):
    from scripts.boundaries.feasible import aggregate
    source_label_aliases = source_label_aliases or {}
    if set(controls) != set(target_names):
        raise ValueError('Incomplete target control/name coverage')
    if {c['source'] for c in cells} != source_names.keys():
        raise ValueError('Incomplete source coverage')
    if {c['target'] for c in cells} != target_names.keys():
        raise ValueError('Incomplete target coverage')
    if len({c['meshblockId'] for c in cells}) != len(cells):
        raise ValueError('Duplicate meshblock in electorate universe')
    original = aggregate(cells)
    edges = outgoing_weight_bounds(tighten_destinations(original, controls))
    targets = []
    for code, name in sorted(target_names.items()):
        incoming = [e for e in edges if e['target'] == code]
        metrics = summarize(incoming, controls[code])
        expected_source = renames.get(name, name)
        foreign = [e for e in incoming if source_label_aliases.get(source_names[e['source']], source_names[e['source']]) != expected_source]
        official_status = 'unchanged' if name in unchanged else 'changed'
        if official_status == 'unchanged' and any(e['lower'] > 0 for e in foreign):
            raise ValueError('Positive identified transfer into officially unchanged electorate')
        targets.append({'code': code, 'name': name, 'populationControl': controls[code],
                        'officialChangeStatus': official_status,
                        'officialRename': name in renames,
                        'unchangedMembershipStatus': ('identity' if not foreign else 'suppressed_technical_uncertainty') if official_status=='unchanged' else None,
                        'sourceMembershipPublications': len(incoming), **metrics,
                        'composition': [{'source':e['source'], 'shareLower':fraction_json(Fraction(e['lower'],controls[code])),
                                         'shareUpper':fraction_json(Fraction(e['upper'],controls[code]))} for e in incoming]})
    sources = []
    for code,name in sorted(source_names.items()):
        outgoing = [e for e in edges if e['source']==code]
        sources.append({'code':code,'name':name,
                        'populationLower':sum(e['lower'] for e in outgoing),
                        'populationUpper':sum(e['upper'] for e in outgoing),
                        'outgoingWeightSum':1, 'sumInterpretation':'exact for every feasible joint allocation, not sum of independent marginal endpoints',
                        'successorCount':len(outgoing)})
    for edge in edges:
        edge['populationPointEstimate'] = edge['lower'] if edge['lower']==edge['upper'] else None
    return {'meshblockCount':len(cells), 'sources':sources, 'targets':targets,'edges':edges,
            'constraints': {'populationVariables': 'x[source,target]',
                            'variableBounds': 'edge lower <= x <= edge upper; integer',
                            'destinationEquations': [{'target':k,'sumIncomingPopulation':v} for k,v in sorted(controls.items())],
                            'sourcePopulation': 'P[source] = sum_target x[source,target]',
                            'outgoingWeights': 'w[source,target] = x[source,target] / P[source]',
                            'conservation': 'sum_target w[source,target] = 1; all source population retained',
                            'jointConstraintWarning':'Marginal endpoints are sharp individually, not an independently selectable matrix.'}}


def build(config):
    from scripts.boundaries import current_inputs, inputs_2020
    adapters = {'current_inputs': current_inputs, 'inputs_2020': inputs_2020}
    if config['adapter'] not in adapters:
        raise ValueError('No reviewed adapter for transition')
    inputs = adapters[config['adapter']].load()
    scopes = {}
    for kind,key in [('general','unchangedGeneral'),('maori','unchangedMaori')]:
        if len(inputs['sourceNames'][kind])!=config['expectedSourceCounts'][kind] or len(inputs['targetNames'][kind])!=config['expectedTargetCounts'][kind]:
            raise ValueError('Unexpected electorate inventory')
        scopes[kind] = build_scope(inputs['cells'][kind],inputs['controls'][kind],
                                   inputs['sourceNames'][kind],inputs['targetNames'][kind],
                                   inputs['changes'][key],inputs['changes']['unchangedRename'],
                                   inputs['changes'].get('sourceLabelAliases'))
    return {'schemaVersion':1,'transition':config,'status':'validated_feasible_crosswalk',
            'dataClass':'synthetic_reconstruction_constraints_not_observed_votes',
            'inputHashes':inputs['inputHashes'],'scopes':scopes,
            'nominalAllocation':None,
            'limitations':['Disclosure bounds are conditional on published target totals and do not identify every population or weight.',
                           'No whole-electorate area weighting, geometry membership inference or point imputation.',
                           'Population weighting does not observe geographic party-vote heterogeneity; later notional votes require that explicit assumption.',
                           'Non-dominant population share describes predecessor mixing, not proven individual residential movement.',
                           'No candidate-person linking, model fitting or constant-geography historical panel.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transition',default='2023-2026')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    config_path=ROOT / f'data/controls/boundaries/transitions/{args.transition}.json'
    config=json.loads(config_path.read_bytes())
    result=build(config)
    raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    folder=ROOT / f'data/processed/boundaries/{args.transition}'
    output=folder/'crosswalk.json'
    code_paths=['scripts/boundaries/'+name+'.py' for name in ['transition','composition','feasible','current_inputs','membership','population']]
    if config['adapter'] == 'inputs_2020':
        code_paths += ['scripts/boundaries/inputs_2020.py', 'scripts/boundaries/lineage_2020.py']
    manifest={'schemaVersion':1,'transitionId':config['id'],
              'inputHashes':{**result['inputHashes'],str(config_path.relative_to(ROOT)):hashlib.sha256(config_path.read_bytes()).hexdigest()},
              'codeHashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in code_paths},
              'outputSha256':hashlib.sha256(raw).hexdigest(),
              'scopes':{k:{'sources':len(v['sources']),'targets':len(v['targets']),'edges':len(v['edges'])} for k,v in result['scopes'].items()}}
    files={output:raw,folder/'manifest.json':(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()}
    for path,content in files.items():
        if args.check:
            if not path.exists() or path.read_bytes()!=content:
                raise SystemExit('Stale crosswalk or manifest: '+str(path))
        else:
            folder.mkdir(parents=True,exist_ok=True)
            path.write_bytes(content)
    print(json.dumps(manifest['scopes']))


if __name__=='__main__':
    main()
