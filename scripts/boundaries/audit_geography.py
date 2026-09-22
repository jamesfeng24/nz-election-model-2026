"""Deterministic geographic acquisition audit, not a population crosswalk."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.boundaries.geometry import decode_layer

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'data/processed/boundaries/2020-2025/geography-validation.json'


def build():
    plan = json.loads((ROOT / 'data/source-plans/boundary-2023-2026.json').read_bytes())
    control_path = ROOT / 'data/controls/boundaries/2025-change-controls.json'
    controls = json.loads(control_path.read_bytes())
    registry = {s['id']: s for s in json.loads((ROOT / 'data/sources.json').read_bytes())['sources']}
    layers, inputs, inventories = {}, {}, []
    for entry in plan['resources']:
        if 'expectedFeatureCount' not in entry:
            continue
        raw = (ROOT / entry['rawPath']).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != registry[entry['id']]['sha256']:
            raise ValueError('Source checksum changed: ' + entry['id'])
        layer = decode_layer(json.loads(raw), entry['codeField'], entry['nameField'],
                             entry['expectedFeatureCount'], entry['expectedCrs'])
        layers[entry['boundaryYear'], entry['electorateType']] = {
            a[entry['nameField']]: (code, shape) for code, (a, shape) in layer.items()
        }
        inputs[entry['rawPath']] = digest
        inventories.append({'sourceId': entry['id'], 'boundaryYear': entry['boundaryYear'],
                            'electorateType': entry['electorateType'], 'count': len(layer),
                            'crs': entry['expectedCrs'], 'allPolygonsValidWithoutRepair': True})
    inputs[str(control_path.relative_to(ROOT))] = hashlib.sha256(control_path.read_bytes()).hexdigest()
    official = registry[controls['sourceId']]
    raw = (ROOT / official['rawPath']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != official['sha256']:
        raise ValueError('Official change schedule checksum mismatch')
    inputs[official['rawPath']] = official['sha256']
    comparisons = []
    for kind, control in [('general', 'unchangedGeneral'), ('maori', 'unchangedMaori')]:
        for target in controls[control]:
            source = controls['unchangedRename'].get(target, target)
            source_code, old = layers[2020, kind][source]
            target_code, new = layers[2025, kind][target]
            comparisons.append({'electorateType': kind, 'sourceCode': source_code,
                'sourceName': source, 'targetCode': target_code, 'targetName': target,
                'officialStatus': 'unchanged', 'renamed': source != target,
                'geometryExactlyEqual': old.equals(new),
                'symmetricDifferenceSquareMetres': old.symmetric_difference(new).area,
                'populationMovement': None,
                'populationReconciliationStatus': 'pending_meshblock_source_membership'})
    return {'schemaVersion': 1, 'status': 'incomplete_population_and_change_reconciliation',
            'isVoteTransferOutput': False, 'inputSha256': inputs, 'layers': inventories,
            'officialUnchangedGeometryComparisons': comparisons,
            'limitations': [
                'Area differences are geometric diagnostics, never population transfer weights.',
                'Published layer versions differ even for officially unchanged electorates.',
                'Meshblock source membership and Schedule C population controls remain pending.',
                'No synthetic votes or crosswalk weights have been generated.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = (json.dumps(build(), ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != raw:
            raise ValueError('Geographic audit output missing or stale')
        print('Geographic acquisition audit deterministic check passed (population reconciliation pending).')
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(raw)
        print('Wrote incomplete geographic acquisition audit; no crosswalk weights.')


if __name__ == '__main__':
    main()
