"""Project public 2013 constraints onto population flows, without a local roll ratio."""
from collections import defaultdict
import hashlib
import json
from scripts.boundaries.census_2013 import ROOT, load_census, registered_bytes
from scripts.boundaries.membership import read_csv_zip


def load():
    hashes = {}
    folder = 'data/raw/boundaries/2007-2014/'
    for name in ['electoral-population-methodology-2013.pdf',
                 'descent-imputation-methodology.pdf','electoral-mathematics-2000.pdf']:
        registered_bytes(folder+name,hashes)
    source = read_csv_zip(registered_bytes(folder + 'geographic-areas-file-2013.zip', hashes),
                          'geographic-areas-file-2013.csv', 'MB2013_code')
    target = read_csv_zip(registered_bytes(folder + 'geographic-areas-file-2016.zip', hashes),
                          'geographic-areas-file-2016.csv', 'MB2016_code')
    census = load_census(hashes)
    controls_path = 'data/controls/boundaries/2014-population-controls.json'
    raw = (ROOT / controls_path).read_bytes()
    hashes[controls_path] = hashlib.sha256(raw).hexdigest()
    controls = json.loads(raw)
    registered_bytes(folder + 'schedule-c.pdf', hashes)
    if controls['sourceSha256'] != hashes[folder + 'schedule-c.pdf']:
        raise ValueError('Control transcription source hash mismatch')
    descendants = defaultdict(list)
    for code, row in sorted(target.items()):
        parent = row['MB2013_code']
        if parent not in source:
            raise ValueError('Unknown official lineage parent')
        descendants[parent].append((code, row))
    if descendants.keys() != source.keys() or census.keys() - source.keys():
        raise ValueError('Incomplete source lineage/Census coverage')
    outside = []
    for code in source.keys() - census.keys():
        if not all(source[code][p+'2007_label'].startswith('Area Outside ') for p in ['GED', 'MED']):
            raise ValueError('Missing Census population inside electorate')
        outside.append(code)
    scopes, split_evidence, outside_target = {}, {}, []
    for kind, prefix in [('general', 'GED'), ('maori', 'MED')]:
        names = {'source': {}, 'target': {}}
        groups = []
        fixed_edges = {}
        for code, population in sorted(census.items()):
            src = source[code][prefix+'2007_code']
            src_name = source[code][prefix+'2007_label']
            children = descendants[code]
            targets = sorted({r[prefix+'2014_code'] for _, r in children})
            if src_name.startswith('Area Outside '):
                if any(not r[prefix+'2014_label'].startswith('Area Outside ') for _, r in children):
                    raise ValueError('Outside source has an electoral descendant')
                continue
            if all(r[prefix+'2014_label'].startswith('Area Outside ') for _,r in children):
                outside_target.append({'scope':kind,'predecessor':code,'source':src,
                    'descendants':[c for c,_ in children], 'populationEvidence':population,
                    'status':'outside_final_electoral_universe_not_an_electorate_transfer'})
                continue
            names['source'][src] = src_name
            for _, row in children:
                dst, label = row[prefix+'2014_code'], row[prefix+'2014_label']
                if label.startswith('Area Outside '):
                    raise ValueError('Electoral source loses population outside target')
                if dst in names['target'] and names['target'][dst] != label:
                    raise ValueError('Inconsistent target label')
                names['target'][dst] = label
            lo = population['nonMaoriDescentLower'] if kind == 'general' else 0
            hi = population['residentUpper'] if kind == 'general' else population['electoralDescentUpper']
            if len(targets) == 1:
                edge = fixed_edges.setdefault((src, targets[0]), {'lower': 0, 'upper': 0, 'meshblockCount': 0})
                edge['lower'] += lo
                edge['upper'] += hi
                edge['meshblockCount'] += 1
            else:
                groups.append({'id': 'split-'+code, 'source': src, 'targets': targets,
                               'lower': lo, 'upper': hi, 'meshblockCount': 1})
                split_evidence[code] = {
                    'predecessor': code, 'sourceGeneral': source[code]['GED2007_code'],
                    'sourceMaori': source[code]['MED2007_code'], **population,
                    'descendants': [{'meshblockId': c, 'targetGeneral': r['GED2014_code'],
                                     'targetMaori': r['MED2014_code']} for c, r in children],
                    'allocation': 'unknown; sum of descendant contributions equals one parent quantity',
                    'quality': 'no contemporaneous descendant population; coupled feasible allocation'}
        for (src, dst), values in sorted(fixed_edges.items()):
            groups.append({'id': 'fixed-'+src+'-'+dst, 'source': src, 'targets': [dst], **values})
        totals = {}
        for row in controls['records']:
            if row['kind'] != kind:
                continue
            code = row['sourceCode'] if kind == 'general' else str(int(row['sourceCode'])-64)
            if code in totals or row['electoralPopulation'] - row['quota'] not in range(-4000,4001):
                raise ValueError('Invalid target control')
            totals[code] = row['electoralPopulation']
        if totals.keys() != names['target'].keys():
            raise ValueError('Target control inventory mismatch')
        if (len(names['source']),len(names['target'])) != ((63,64) if kind=='general' else (7,7)):
            raise ValueError('Wrong electorate inventory')
        scopes[kind] = {'names': names, 'groups': sorted(groups,key=lambda g:g['id']), 'controls': totals}
    return {'scopes': scopes, 'splitEvidence': [split_evidence[k] for k in sorted(split_evidence)],
            'inputHashes': hashes, 'censusMeshblocks': len(census),
            'outsideWithoutCensus': sorted(outside),
            'outsideTargetRecords': outside_target,
            'splitPublishedResidentTotal': sum(c['publishedResident'] for c in split_evidence.values())}
