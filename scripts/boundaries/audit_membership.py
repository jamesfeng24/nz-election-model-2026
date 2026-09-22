"""Deterministic exact-membership coverage audit, not a transition matrix."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from scripts.boundaries.membership import index_rows, read_csv_zip, join_memberships

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'data/processed/boundaries/2020-2025/membership-validation.json'


def build():
    sources = {s['id']: s for s in json.loads((ROOT / 'data/sources.json').read_bytes())['sources']}
    hashes = {}

    def read(path):
        raw = (ROOT / path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        matches = [s for s in sources.values() if s['rawPath'] == path]
        if len(matches) != 1 or matches[0]['sha256'] != digest:
            raise ValueError('Missing registration or changed checksum: ' + path)
        hashes[path] = digest
        return raw

    folder = 'data/raw/boundaries/2020-2025/'
    population = index_rows(csv.DictReader(io.StringIO(read(folder + 'population-2025.csv').decode('utf-8-sig'))), 'MB2025_V2_00')
    concordance = read_csv_zip(read(folder + 'geographic-areas-table-2025.zip'),
                              'geographic-areas-table-2025.csv', 'MB2025_code')
    controls = {}
    for kind, prefix in [('general', 'GED'), ('maori', 'MED')]:
        features = json.loads(read(folder + kind + '-2020-geometry.json'))['features']
        controls[kind] = {f['attributes'][prefix + '2020_V1_00']: f['attributes'][prefix + '2020_V1_00_NAME'] for f in features}
    lineage = read_csv_zip(read(folder + 'geographic-areas-table-2026.zip'),
                           'geographic-areas-table-2026.csv', 'MB2026_code')
    records = join_memberships(population, concordance, controls, lineage)
    unresolved = [r for r in records if r['membershipStatus'] == 'unresolved']
    return {'schemaVersion': 1, 'status': 'incomplete_source_membership' if unresolved else 'membership_complete',
            'isVoteTransferOutput': False, 'inputHashes': hashes,
            'finalMeshblockCount': len(population), 'concordanceMeshblockCount': len(concordance),
            'exactOfficialMembershipCount': sum(r['membershipStatus'] == 'official_exact_code' for r in records),
            'officialLineageMembershipCount': sum(r['membershipStatus'] == 'official_historical_code' for r in records),
            'officialLineageJoins': [r for r in records if r['membershipStatus'] == 'official_historical_code'],
            'unresolvedMeshblocks': unresolved,
            'concordanceOnlyMeshblocks': sorted(concordance.keys() - population.keys()),
            'limitations': ['Official exact-code and explicit historical-code joins only; no geometry allocation.',
                            'Suppressed population is not zero. No population weights or synthetic votes produced.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build()
    raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != raw:
            raise SystemExit('Stale membership audit')
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(raw)
    print(f"Exact memberships: {result['exactOfficialMembershipCount']}; unresolved: {len(result['unresolvedMeshblocks'])}")


if __name__ == '__main__':
    main()
