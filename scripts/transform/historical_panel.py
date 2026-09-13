"""Offline, lossless integration of validated historical JSON; no person linking."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from .panel_config import YEARS, COUNTS, DEST, CONTRACT, ALIASES, LEGACY_ALIASES, ALIAS_SOURCE, ALIAS_EVIDENCE, canonical


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_panel(root):
    panel = {k: [] for k in ('electorates', 'party-votes', 'candidate-votes', 'split-votes', 'election-controls')}
    inputs = {}
    contract = json.loads((root / CONTRACT).read_bytes())
    require(contract['years'] == list(YEARS), 'Input contract years')
    loaded_years = {}
    registry = json.loads((root / 'data/sources.json').read_bytes())
    source_ids = {r['id'] for r in registry['sources']}
    for year in YEARS:
        loaded = {}
        for kind, relative in [('elections', f'data/processed/elections/{year}.json'), ('split', f'data/processed/split-votes/{year}.json'), ('validation', f'data/processed/elections/{year}-validation.json')]:
            raw = (root / relative).read_bytes()
            inputs[relative] = hashlib.sha256(raw).hexdigest()
            require(inputs[relative] == contract['inputSha256'][relative], 'Altered per-election input: '+relative)
            loaded[kind] = json.loads(raw)
            require(loaded[kind]['year'] == year and loaded[kind]['schemaVersion'] == 1, 'Unsupported input year/schema')
        election, split, report = (loaded[k] for k in ('elections', 'split', 'validation'))
        require(set(election['sourceIds']) <= source_ids, 'Unknown provenance source')
        loaded_years[year] = loaded
        if report['discrepancies']:
            require(year == 2023 and report['splitStatus'] == 'validated-with-source-discrepancies' and report['discrepancies'] == split['sourceDiscrepancies'], 'New source discrepancy')
        for electorate in election['electorates']:
            metadata = {k: copy.deepcopy(v) for k, v in electorate.items() if k not in ('parties', 'candidates')}
            panel['electorates'].append(metadata)
            for kind, field in [('party-votes', 'parties'), ('candidate-votes', 'candidates')]:
                for record in electorate[field]:
                    panel[kind].append({**copy.deepcopy(record), 'year': year, 'electionId': electorate['electionId'], 'electorateId': electorate['id'], 'sourceIds': electorate['sourceIds'][:], 'canonicalPartyId': canonical(record['partyKey'])})
        panel['split-votes'].extend(copy.deepcopy(split['matrices']))
        panel['election-controls'].append({'year': year, 'nationalControls': election['nationalControls'], 'sourceIds': election['sourceIds'], 'perYearValidation': report, 'aggregateSplitAvailability': 'not-collected' if year == 2008 else 'preserved', 'aggregateMatrices': split.get('aggregateMatrices'), 'officialSplitSummary': split.get('officialSplitSummary'), 'partyGrouping': split.get('partyGrouping')})
        # Preserve every additional split evidence layer without inventing absent controls.
        for field, value in split.items():
            if field not in ('schemaVersion', 'year', 'matrices', 'aggregateMatrices', 'officialSplitSummary', 'partyGrouping'):
                panel['election-controls'][-1][field] = copy.deepcopy(value)
    validate_panel(panel, root, loaded_years)
    outputs = {f'{k}.json': {'schemaVersion': 1, 'years': list(YEARS), 'records': v} for k, v in panel.items()}
    outputs['manifest.json'] = {'schemaVersion': 1, 'years': list(YEARS), 'inputSha256': inputs, 'outputSha256': {k: hashlib.sha256(encode(v)).hexdigest() for k, v in outputs.items()}, 'recordCounts': {k: len(v) for k, v in panel.items()}, 'canonicalPartyAliases': ALIASES, 'canonicalPartyAliasSource': ALIAS_SOURCE, 'independentCanonicalPartyId': None, 'candidateIdentityScope': 'election-local occurrence; personId remains null', 'discrepancies': []}
    outputs['manifest.json'].update(canonicalPartyAliasEvidence=ALIAS_EVIDENCE, perYearRecordCounts={str(y): dict(zip(('electorates','party-votes','candidate-votes'), COUNTS[y])) for y in YEARS}, splitPublicationCounts={'ordinary':383,'cancelled':1}, geographyScope='election-specific geography as published; not boundary harmonized', knownSourceDiscrepancies=copy.deepcopy(loaded_years[2023]['validation']['discrepancies']), integrationCodeSha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'scripts/transform').glob('panel_*.py'))}, inputContractSha256=hashlib.sha256((root/CONTRACT).read_bytes()).hexdigest())
    outputs['manifest.json']['integrationCodeSha256']['scripts/transform/historical_panel.py'] = hashlib.sha256((root/'scripts/transform/historical_panel.py').read_bytes()).hexdigest()
    outputs['manifest.json']['discrepancies'] = copy.deepcopy(loaded_years[2023]['validation']['discrepancies'])
    outputs['manifest.json']['legacySliceCompatibility'] = verify_legacy_slice(outputs, contract)
    return outputs


def validate_panel(panel, root=None, loaded_years=None):
    from .panel_validation import validate
    validate(panel, root or Path(__file__).resolve().parents[2], loaded_years)


def verify_legacy_slice(outputs, contract):
    hashes = {}
    for name, output in outputs.items():
        if name == 'manifest.json':
            continue
        subset = {'schemaVersion': 1, 'years': [2008,2011,2014], 'records': [r for r in output['records'] if r['year'] <= 2014]}
        digest = hashlib.sha256(encode(subset)).hexdigest()
        require(digest == contract['legacyPanel'][name]['sha256'], 'Legacy slice changed: '+name)
        hashes[name] = digest
    legacy_manifest = {'schemaVersion': 1, 'years': [2008,2011,2014],
        'inputSha256': {p:h for p,h in outputs['manifest.json']['inputSha256'].items() if any(str(y) in p for y in (2008,2011,2014))},
        'outputSha256': hashes.copy(),
        'recordCounts': {name[:-5]: len([r for r in outputs[name]['records'] if r['year'] <= 2014]) for name in hashes},
        'canonicalPartyAliases': LEGACY_ALIASES, 'canonicalPartyAliasSource': ALIAS_SOURCE,
        'independentCanonicalPartyId': None, 'candidateIdentityScope': 'election-local occurrence; personId remains null', 'discrepancies': []}
    digest = hashlib.sha256(encode(legacy_manifest)).hexdigest()
    require(digest == contract['legacyPanel']['manifest.json']['sha256'], 'Legacy manifest projection changed')
    hashes['manifest.json'] = digest
    return {'years': [2008,2011,2014], 'status': 'byte-identical serialized subsets', 'outputSha256': hashes, 'baselineCommit': contract['baseCommit']}


def verify_years(root):
    """Regenerate in memory from preserved raw files; never write per-year inputs."""
    from .historical import build_year as legacy
    from .modern_election import build_year as modern
    for year in YEARS:
        rebuilt = (legacy if year <= 2014 else modern)(root, year)
        for kind, relative in [('elections', f'data/processed/elections/{year}.json'), ('split', f'data/processed/split-votes/{year}.json'), ('validation', f'data/processed/elections/{year}-validation.json')]:
            require((root / relative).read_bytes() == encode(rebuilt[kind]), 'Per-year regression: ' + relative)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--verify-years', action='store_true', help='Also regenerate all six years in memory and require byte-identical inputs')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.verify_years:
        verify_years(root)
    for name, value in build_panel(root).items():
        path = root / DEST / name
        data = encode(value)
        if args.check:
            require(path.read_bytes() == data, 'Stale panel: ' + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print('Historical panel validated: 384 electorate-years, 6210 party records, 2833 candidate records, 383 ordinary + 1 cancelled split publications; 21 known source discrepancies retained.')


if __name__ == '__main__':
    main()
