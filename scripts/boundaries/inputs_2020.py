"""2014→2020 adapter: official final meshblock lineage and 2018 populations."""
import hashlib
import json
from scripts.boundaries.lineage_2020 import ROOT, load_memberships


def load():
    cells, names, _, _, hashes, _, _ = load_memberships()
    registry = json.loads((ROOT / 'data/sources.json').read_bytes())['sources']

    def read(path, registered=False):
        raw = (ROOT / path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if registered:
            matches = [s for s in registry if s['rawPath'] == path]
            if len(matches) != 1 or matches[0]['sha256'] != digest:
                raise ValueError('Unregistered or altered official control: ' + path)
        hashes[path] = digest
        return raw

    read('data/raw/boundaries/2014-2020/schedule-c.pdf', True)
    read('data/raw/boundaries/2014-2020/schedule-b.pdf', True)
    controls = json.loads(read('data/controls/boundaries/2020-population-controls.json'))
    changes = json.loads(read('data/controls/boundaries/2020-change-controls.json'))
    totals = {'general': {}, 'maori': {}}
    typography = {'Rangitῑkei': 'Rangitīkei'}
    for row in controls['electorates']:
        kind, code = row['electorateType'], row['sourceCode']
        if code in totals[kind] or names[kind]['target'].get(code) != typography.get(row['name'], row['name']):
            raise ValueError('Invalid official target population identity')
        totals[kind][code] = row['electoralPopulation']
    return {'cells': cells, 'controls': totals,
            'sourceNames': {k: v['source'] for k, v in names.items()},
            'targetNames': {k: v['target'] for k, v in names.items()},
            'changes': changes, 'inputHashes': hashes}
