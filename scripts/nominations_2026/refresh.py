"""Stage50 refresh: official nominations -> dated roster snapshot -> 2026 candidate features -> recentred features.

python -m scripts.nominations_2026.refresh --acquisition ACQUISITION.json [--check] [--apply-config]

ACQUISITION.json (written when the publication is preserved) names the dated snapshot and the official sources:
{"schemaVersion": 1, "snapshotDateNZ": "2026-10-08", "acquisitionCutoffUTC": "...Z",
 "sourceRegistryPath": "data/processed/nominations-2026/source-registry.json",
 "tables": [{"sourceKey": "...", "path": "data/processed/nominations-2026/<date>/official-table.json"}]}
Every official source must be in the standalone registry with verified bytes. The Stage40 builder runs unchanged with
only the official claims (no retained party announcements), so every seat is an official complete slate. Outputs:
the Stage40 snapshot directory `data/processed/forecast-readiness/snapshots/<date>/`, and under
`data/processed/nominations-2026/<date>/`: the reconciliation against the 2026-10-05 announcements, the refreshed
Stage42 features (`features-raw.json`) and their Stage75 recentring (`features-centred.json`).
"""
import argparse
import json
from collections import Counter
from scripts.balance_scale.common import equivalent
from scripts.candidate_fit_2026 import run as stage75
from scripts.candidate_fit_2026.common import FIT
from scripts.readiness import run as stage40
from scripts.transport.continuous import readiness as stage42
from scripts.validate.source_files import verify_source_files
from scripts.uncertainty_revision.common import ROOT, read, encode
from . import official

PREVIOUS = 'data/processed/forecast-readiness/snapshots/2026-10-05/'
STAGE40_MANIFEST = 'data/processed/forecast-readiness/acquisition-manifest.json'
CONFIG = 'config/nowcast-2026.json'


def snapshot_dir(acquisition):
    return f"data/processed/forecast-readiness/snapshots/{acquisition['snapshotDateNZ']}/"


def output_dir(acquisition):
    return f"data/processed/nominations-2026/{acquisition['snapshotDateNZ']}/"


def manifest(acquisition, registry):
    """A Stage40-shaped manifest: the preserved Schedule C and register (unchanged) first, then official sources."""
    previous = {s['key']: s for s in read(STAGE40_MANIFEST)['sources']}
    sources = [previous['schedule-c'], previous['party-register']]
    for record in registry['sources']:
        sources.append({'id': record['id'], 'key': record['resource'], 'url': record['url'], 'retrievedAt': record['retrievedAt'],
                        'rawPath': record['rawPath'], 'sha256': record['sha256'], 'contentStatus': record.get('contentStatus', 'original'),
                        'availability': 'official publication after nomination close'})
    if any(s['retrievedAt'] > acquisition['acquisitionCutoffUTC'] for s in sources):
        raise ValueError('Source retrieved after the acquisition cutoff')
    return {'schemaVersion': 1, 'stage': 50, 'snapshotDateNZ': acquisition['snapshotDateNZ'],
            'acquisitionCutoffUTC': acquisition['acquisitionCutoffUTC'], 'resourceCap': len(sources), 'queries': [], 'queryCap': 0,
            'sources': sources, 'unresolved': [], 'sourceRegistryPath': acquisition['sourceRegistryPath']}


def build(acquisition, registry=None, tables=None):
    registry = read(acquisition['sourceRegistryPath']) if registry is None else registry
    tables = [(t['sourceKey'], read(t['path'])) for t in acquisition['tables']] if tables is None else tables
    m = manifest(acquisition, registry)
    claims = [c for key, table in tables for c in official.claims(table, key)]
    frame = read(PREVIOUS + 'target-frame.json')['records']
    declarations = [d for _, table in tables for d in official.completeness(table, frame)]
    seats = Counter(d['targetElectorateId'] for d in declarations)
    if any(n > 1 for n in seats.values()):
        raise official.OfficialTableError('An electorate appears in more than one official table')
    evidence = {'claims': claims, 'context': [], 'gaps': [], 'sourceCounts': {key: len(t['rows']) for key, t in tables}}
    results = stage40.build(m, evidence=evidence, previous=None, completeness=declarations)
    snapshot = results['snapshot.json']
    if len(snapshot['completeSlateDeclarations']) != len(frame):
        raise ValueError('Not every electorate is an official complete slate')
    if snapshot['unmatchedClaims']:
        raise ValueError(f"{len(snapshot['unmatchedClaims'])} official claims did not resolve")
    features = stage42.build(frame=results['target-frame.json']['records'], snapshot=snapshot,
                             links=results['identity-links.json']['records'], relations=results['party-relationships.json']['records'])
    features['sourceSnapshot'] = snapshot_dir(acquisition)
    centred = stage75.recentre(read(FIT), readiness=features, source=output_dir(acquisition) + 'features-raw.json')
    outputs = {snapshot_dir(acquisition) + name: value for name, value in results.items()}
    outputs[output_dir(acquisition) + 'reconciliation.json'] = reconciliation(snapshot)
    outputs[output_dir(acquisition) + 'features-raw.json'] = features
    outputs[output_dir(acquisition) + 'features-centred.json'] = centred
    return outputs


def reconciliation(snapshot):
    """Official list against the 2026-10-05 party announcements, by seat, party and normalised name."""
    from scripts.evidence.practical_candidate_linkage.names import normalize
    announced = read(PREVIOUS + 'snapshot.json')['occurrences']
    key = lambda o: (o['targetElectorateId'], o['originalAffiliation'], normalize(o['displayedName']))
    nominated = {key(o): o for o in snapshot['occurrences']}
    prior = {key(o): o for o in announced}
    matched = sorted(set(nominated) & set(prior))
    by_seat_party = {(o['targetElectorateId'], o['originalAffiliation']) for o in snapshot['occurrences']}
    not_nominated = [prior[k] for k in sorted(set(prior) - set(nominated))]
    return {'stage': 50, 'rule': 'the official list replaces party announcements in the live roster (James, 2026-10-07)',
            'officialCandidates': len(nominated), 'announcedCandidates': len(prior), 'matched': len(matched),
            'newInOfficialList': len(set(nominated) - set(prior)),
            'announcedNotNominatedAsSamePerson': [{'targetElectorateId': o['targetElectorateId'], 'party': o['originalAffiliation'],
                                                   'displayedName': o['displayedName'],
                                                   'partyStandsAnotherCandidate': (o['targetElectorateId'], o['originalAffiliation']) in by_seat_party}
                                                  for o in not_nominated],
            'officialByParty': dict(sorted(Counter(o['originalAffiliation'] for o in snapshot['occurrences']).items())),
            'unmappedBallotGroups': sorted({o['originalAffiliation'] for o in snapshot['occurrences'] if o['ballotGroupKey'] is None})}


def apply_config(acquisition, outputs):
    """Point the live config at the official roster; the pending roster field is filled with the snapshot id."""
    config = read(CONFIG)
    config['roster']['snapshotId'] = 'nz-2026-official-nominations-' + acquisition['snapshotDateNZ']
    config['candidate']['features'] = output_dir(acquisition) + 'features-raw.json'
    config['candidate']['centredFeatures'] = output_dir(acquisition) + 'features-centred.json'
    config['partyRelationships'] = snapshot_dir(acquisition) + 'party-relationships.json'
    config['pending'].pop('roster.snapshotId', None)
    (ROOT / CONFIG).write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--acquisition', required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--apply-config', action='store_true')
    args = parser.parse_args()
    acquisition = read(args.acquisition)
    registry = read(acquisition['sourceRegistryPath'])
    verify_source_files(ROOT, registry)
    outputs = build(acquisition, registry)
    for path, value in outputs.items():
        if args.check:
            if not equivalent(read(path), value, 1e-9):
                raise SystemExit('Stale ' + path)
        else:
            (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
            (ROOT / path).write_bytes(encode(value))
    if args.apply_config and not args.check:
        apply_config(acquisition, outputs)
    print('Stage50', 'reproduced' if args.check else 'written', outputs[output_dir(acquisition) + 'reconciliation.json']['officialCandidates'], 'official candidates')


if __name__ == '__main__':
    main()
