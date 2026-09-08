"""Offline, lossless integration of validated historical JSON; no person linking."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

YEARS = (2008, 2011, 2014)
COUNTS = {2008: (63, 1197, 499), 2011: (63, 819, 423), 2014: (64, 960, 451)}
DEST = 'data/processed/historical/2008-2014'
# Electoral Commission report on the 2014 election, party registration section.
ALIASES = {'conservativeparty': 'conservative', 'mana': 'manamovement'}
ALIAS_SOURCE = 'https://elections.nz/assets/2014-general-election/report-of-the-electoral-commission-on-the-2014-general-election.pdf'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(key):
    return None if key == 'independent' else ALIASES.get(key, key)


def build_panel(root):
    panel = {k: [] for k in ('electorates', 'party-votes', 'candidate-votes', 'split-votes', 'election-controls')}
    inputs = {}
    registry = json.loads((root / 'data/sources.json').read_bytes())
    source_ids = {r['id'] for r in registry['sources']}
    for year in YEARS:
        loaded = {}
        for kind, relative in [('elections', f'data/processed/elections/{year}.json'), ('split', f'data/processed/split-votes/{year}.json'), ('validation', f'data/processed/elections/{year}-validation.json')]:
            raw = (root / relative).read_bytes()
            inputs[relative] = hashlib.sha256(raw).hexdigest()
            loaded[kind] = json.loads(raw)
            require(loaded[kind]['year'] == year and loaded[kind]['schemaVersion'] == 1, 'Unsupported input year/schema')
        election, split, report = (loaded[k] for k in ('elections', 'split', 'validation'))
        require(set(election['sourceIds']) <= source_ids, 'Unknown provenance source')
        require(not report['discrepancies'], f'Unresolved per-year discrepancies: {year}')
        for electorate in election['electorates']:
            metadata = {k: copy.deepcopy(v) for k, v in electorate.items() if k not in ('parties', 'candidates')}
            panel['electorates'].append(metadata)
            for kind, field in [('party-votes', 'parties'), ('candidate-votes', 'candidates')]:
                for record in electorate[field]:
                    panel[kind].append({**copy.deepcopy(record), 'year': year, 'electionId': electorate['electionId'], 'electorateId': electorate['id'], 'sourceIds': electorate['sourceIds'][:], 'canonicalPartyId': canonical(record['partyKey'])})
        panel['split-votes'].extend(copy.deepcopy(split['matrices']))
        panel['election-controls'].append({'year': year, 'nationalControls': election['nationalControls'], 'sourceIds': election['sourceIds'], 'perYearValidation': report, 'aggregateSplitAvailability': 'not-collected' if year == 2008 else 'preserved', 'aggregateMatrices': split.get('aggregateMatrices'), 'officialSplitSummary': split.get('officialSplitSummary'), 'partyGrouping': split.get('partyGrouping')})
    validate_panel(panel)
    outputs = {f'{k}.json': {'schemaVersion': 1, 'years': list(YEARS), 'records': v} for k, v in panel.items()}
    outputs['manifest.json'] = {'schemaVersion': 1, 'years': list(YEARS), 'inputSha256': inputs, 'outputSha256': {k: hashlib.sha256(encode(v)).hexdigest() for k, v in outputs.items()}, 'recordCounts': {k: len(v) for k, v in panel.items()}, 'canonicalPartyAliases': ALIASES, 'canonicalPartyAliasSource': ALIAS_SOURCE, 'independentCanonicalPartyId': None, 'candidateIdentityScope': 'election-local occurrence; personId remains null', 'discrepancies': []}
    return outputs


def validate_panel(panel):
    electorates = {e['id']: e for e in panel['electorates']}
    require(len(electorates) == len(panel['electorates']), 'Duplicate electorate')
    require({e['year'] for e in electorates.values()} == set(YEARS), 'Unexpected years')
    for year, expected in COUNTS.items():
        actual = tuple(sum(r['year'] == year for r in panel[k]) for k in ('electorates', 'party-votes', 'candidate-votes'))
        require(actual == expected, f'Record counts: {year}')
    for kind, identity in [('party-votes', lambda r: (r['year'], r['electorateId'], r['partyKey'])), ('candidate-votes', lambda r: (r['year'], r['id']))]:
        records = panel[kind]
        require(len({identity(r) for r in records}) == len(records), 'Duplicate ' + kind)
        for r in records:
            e = electorates[r['electorateId']]
            require(r['year'] == e['year'] and r['electionId'] == e['electionId'], 'Foreign key year')
            denominator = e['validPartyVotes' if kind == 'party-votes' else 'validCandidateVotes']
            require(type(r['votes']) is int and r['votes'] >= 0, 'Invalid votes')
            require(0 <= r['share'] <= 1 and abs(r['share'] - r['votes'] / denominator) < 1e-12, 'Invalid share')
            require(r['canonicalPartyId'] == canonical(r['partyKey']), 'Canonical party mismatch')
            if kind == 'candidate-votes':
                require(r['personId'] is None, 'Unreviewed person identity')
        for e in electorates.values():
            local = [r for r in records if r['electorateId'] == e['id']]
            require(e['kind'] == 'general', 'Unexpected supporting electorate')
            require(sum(r['votes'] for r in local) == e['validPartyVotes' if kind == 'party-votes' else 'validCandidateVotes'], 'Denominator reconciliation')
            if kind == 'candidate-votes':
                winners = [r for r in local if r['elected']]
                ranked = sorted(local, key=lambda r: r['votes'], reverse=True)
                require(len(winners) == 1 and winners[0]['id'] == e['winnerCandidateId'] == ranked[0]['id'], 'Winner mismatch')
                require(ranked[0]['votes'] - ranked[1]['votes'] == e['majority'], 'Margin mismatch')
    matrices = panel['split-votes']
    require(len(matrices) == len(electorates) and {m['electorateId'] for m in matrices} == set(electorates), 'Split coverage')
    for m in matrices:
        require(m['year'] == electorates[m['electorateId']]['year'], 'Split year')
        require(m['countAvailability'] == 'unavailable: source publishes rounded percentages, not joint counts', 'Split precision')
        candidates = {c['id'] for c in panel['candidate-votes'] if c['electorateId'] == m['electorateId']}
        for row in m['rows']:
            for cell in row['cells']:
                require(cell['count'] is None, 'Invented joint count')
                require(cell['reportedPercent'] is None or 0 <= cell['reportedPercent'] <= 100, 'Split percentage')
                require(cell['candidateId'] is None or cell['candidateId'] in candidates, 'Split candidate reference')
    require([r['year'] for r in panel['election-controls']] == list(YEARS), 'Control years')
    for control in panel['election-controls']:
        year = control['year']
        local = [e for e in electorates.values() if e['year'] == year]
        for ballot in ('party', 'candidate'):
            totals = control['nationalControls'][ballot]
            for field in ('validVotes', 'informalVotes', 'votesCast', 'enrolled'):
                require(sum(e[ballot + 'Ballot'][field] for e in local) == totals['general'][field], 'Panel general control')
                require(totals['general'][field] + totals['maori'][field] == totals['national'][field], 'Panel national control')



def verify_years(root):
    """Regenerate in memory from preserved raw files; never write per-year inputs."""
    from .historical import build_year
    for year in YEARS:
        rebuilt = build_year(root, year)
        for kind, relative in [('elections', f'data/processed/elections/{year}.json'), ('split', f'data/processed/split-votes/{year}.json'), ('validation', f'data/processed/elections/{year}-validation.json')]:
            require((root / relative).read_bytes() == encode(rebuilt[kind]), 'Per-year regression: ' + relative)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--verify-years', action='store_true', help='Also regenerate all three years in memory and require byte-identical inputs')
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
    print('Historical panel validated: 190 electorate-years, 2976 party records, 1373 candidate records, 190 split matrices.')


if __name__ == '__main__':
    main()
