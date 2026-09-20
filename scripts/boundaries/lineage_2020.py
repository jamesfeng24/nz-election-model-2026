"""Audit final-2020 population membership through official vintage lineage."""
import argparse
import csv
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path
from scripts.boundaries.membership import index_rows, read_csv_zip
from scripts.boundaries.population import population_interval

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'data/processed/boundaries/2017-2020/membership-validation.json'


def reconcile(population, source, lineage):
    """Use one population row per final meshblock; never expand parent totals."""
    descendants = defaultdict(list)
    names = {kind: {'source': {}, 'target': {}} for kind in ('general', 'maori')}
    cells = {'general': [], 'maori': []}
    for code, row in sorted(population.items()):
        if code not in lineage:
            raise ValueError('Missing official lineage: ' + code)
        link = lineage[code]
        parent = link['MB2020_code']
        if parent not in source:
            raise ValueError('Missing official predecessor: ' + code)
        descendants[parent].append(code)
        for kind, prefix, field in [('general', 'GED', 'General_Electoral_Population'),
                                    ('maori', 'MED', 'Maori_Electoral_Population')]:
            target = row[prefix + '2020_V1_00']
            target_name = row[prefix + '2020_V1_00_NAME']
            if (target != link[prefix + '2020_code'] or
                    target_name != link[prefix + '2020_name']):
                raise ValueError('Lineage target mismatch: ' + code)
            previous = source[parent]
            src, src_name = previous[prefix + '2014_code'], previous[prefix + '2014_name']
            for side, key, label in [('source', src, src_name), ('target', target, target_name)]:
                if key in names[kind][side] and names[kind][side][key] != label:
                    raise ValueError('Non-unique electorate name')
                names[kind][side][key] = label
            cells[kind].append({'meshblockId': code, 'source': src, 'target': target,
                                'sourceConcordanceMeshblockId': parent,
                                'population': population_interval(row[field])})
    splits = []
    for parent, children in sorted(descendants.items()):
        if len(children) > 1:
            if parent in population:
                raise ValueError('Retired parent population would be counted with descendants')
            splits.append({'predecessor': parent, 'descendants': children,
                           'relationship': 'official_one_to_many_lineage'})
    outside = []
    for code in sorted(set(source) - set(descendants)):
        row = source[code]
        if not all(row[p + '2014_name'].startswith('Area Outside ') for p in ('GED', 'MED')):
            raise ValueError('Unrepresented source electorate meshblock: ' + code)
        outside.append(code)
    return cells, names, splits, outside


def load_memberships():
    registry = json.loads((ROOT / 'data/sources.json').read_bytes())['sources']
    hashes = {}

    def read(name):
        path = 'data/raw/boundaries/2014-2020/' + name
        raw = (ROOT / path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        records = [s for s in registry if s['rawPath'] == path]
        if len(records) != 1 or records[0]['sha256'] != digest:
            raise ValueError('Unregistered or altered lineage input: ' + path)
        hashes[path] = digest
        return raw

    pop = index_rows(csv.DictReader(io.StringIO(read('population-2020.csv').decode('utf-8-sig'))), 'MB2020_V2_00')
    source = read_csv_zip(read('geographic-areas-file-2020.zip'), 'geographic-areas-file-2020.csv', 'MB2020_code')
    lineage = read_csv_zip(read('geographic-areas-table-2021.zip'), 'geographic-areas-table-2021.csv', 'MB2021_code')
    cells, names, splits, outside = reconcile(pop, source, lineage)
    if len(pop) != 53582 or [(len(names[k]['source']), len(names[k]['target'])) for k in cells] != [(64, 65), (7, 7)]:
        raise ValueError('Unexpected 2014/2020 membership coverage')
    return cells, names, splits, outside, hashes, pop, lineage


def build():
    cells, names, splits, outside, hashes, pop, lineage = load_memberships()
    return {'schemaVersion': 1, 'transition': '2017-2020', 'status': 'membership_complete_controls_pending',
            'inputHashes': hashes, 'populationMeshblocks': len(pop),
            'directLineageCount': sum(c == lineage[c]['MB2020_code'] for c in pop),
            'splitLineage': splits, 'outsideElectorateSourceRecords': outside,
            'electorates': names,
            'populationBounds': {k: {'lower': sum(c['population']['lower'] for c in v),
                                     'upper': sum(c['population']['upper'] for c in v),
                                     'suppressed': sum(c['population']['status'] == 'suppressed' for c in v)} for k, v in cells.items()},
            'limitations': ['Membership audit only; target population controls and unchanged-boundary checks remain pending.',
                            'Each final population row is allocated once. Historical parent codes are joins, not extra population observations.',
                            'Suppression and random rounding bounds are retained; no nominal transfer weights or votes generated.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = (json.dumps(build(), ensure_ascii=False, indent=2) + '\n').encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != raw:
            raise ValueError('Stale 2020 membership audit')
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(raw)
    print('2020 membership audit passed: 53,582 unique population rows; controls pending.')


if __name__ == '__main__':
    main()
