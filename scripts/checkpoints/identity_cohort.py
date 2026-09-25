"""Deterministic, outcome-blind seat-cluster identity evidence cohort."""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import unicodedata


ROOT = Path(__file__).resolve().parents[2]
OCCURRENCES = Path('data/processed/models/candidate-overperformance/occurrences.json')
READINESS = Path('data/processed/boundaries/backtesting-readiness.json')
OUTPUT = Path('data/processed/checkpoints/evidence-repair/cohort-inventory.json')
SEED = 'nz-election-model-2026-evidence-repair-v1'
TRANSITIONS = ((2008, 2011, '2007'), (2014, 2017, '2014'), (2020, 2023, '2020'))
QUOTAS = {'general': 8, 'maori': 2}


def _label_key(label):
    decomposed = unicodedata.normalize('NFKD', label)
    return ''.join(character for character in decomposed if not unicodedata.combining(character)).casefold()


def _seat_index(occurrences):
    seats = defaultdict(list)
    seen = set()
    for row in occurrences:
        occurrence_id = row['candidateOccurrenceId']
        if occurrence_id in seen:
            raise ValueError(f'Duplicate candidate occurrence: {occurrence_id}')
        seen.add(occurrence_id)
        key = (row['year'], row['electorateType'], row['sourceElectorateNumber'])
        seats[key].append(row)
    return seats


def build_inventory(occurrences, readiness, input_hashes):
    """Select fixed seat clusters without consulting votes, winners or identity links."""
    validated = {(item['sourceYear'], item['targetYear']): item
                 for item in readiness['comparisons']
                 if item['status'] == 'same_boundary_inventory_validated'
                 and item['leftClass'] == item['rightClass'] == 'observed'}
    seats = _seat_index(occurrences)
    frame = []
    summary = []
    for source_year, target_year, regime in TRANSITIONS:
        comparison = validated.get((source_year, target_year))
        if comparison is None or comparison['boundaryRegime'] != regime:
            raise ValueError(f'Unvalidated geography: {source_year}->{target_year}')
        for scope, quota in QUOTAS.items():
            source_codes = {code for year, kind, code in seats if year == source_year and kind == scope}
            target_codes = {code for year, kind, code in seats if year == target_year and kind == scope}
            if source_codes != target_codes:
                raise ValueError(f'Missing seat in {source_year}->{target_year} {scope}')
            if scope == 'general' and len(source_codes) != comparison['generalElectorates']:
                raise ValueError('General seat count differs from validated boundary inventory')
            if scope == 'maori' and len(source_codes) != 7:
                raise ValueError('Unexpected Māori seat count')
            ranking = sorted(source_codes, key=lambda code: (
                sha256(f'{SEED}|{source_year}|{target_year}|{scope}|{code:02d}'.encode()).hexdigest(), code))
            selected = set(ranking[:quota])
            selected_occurrences = 0
            held_occurrences = 0
            for code in sorted(source_codes):
                source = seats[source_year, scope, code]
                target = seats[target_year, scope, code]
                source_labels = {row['electorateName'] for row in source}
                target_labels = {row['electorateName'] for row in target}
                if len(source_labels) != 1 or len(target_labels) != 1:
                    raise ValueError('Ambiguous election-local seat label')
                source_label = next(iter(source_labels))
                target_label = next(iter(target_labels))
                if _label_key(source_label) != _label_key(target_label):
                    raise ValueError(f'Seat code/name conflict: {source_year}->{target_year} {scope} {code}')
                if {row['boundaryRegime'] for row in source + target} != {regime}:
                    raise ValueError('Seat regime differs from validated comparison')
                ids = [row['candidateOccurrenceId'] for row in source + target]
                held = all(row['candidateContestStatus'] == 'held' for row in source + target)
                if code in selected:
                    selected_occurrences += len(ids)
                    held_occurrences += len(ids) if held else 0
                frame.append({
                    'sourceYear': source_year, 'targetYear': target_year,
                    'scope': scope, 'sourceElectorateNumber': code,
                    'sourceSeatLabel': source_label, 'targetSeatLabel': target_label,
                    'boundaryRegime': regime, 'selected': code in selected,
                    'contestStatus': 'held_both' if held else 'cancelled_or_unheld',
                    'sourceOccurrenceIds': sorted(row['candidateOccurrenceId'] for row in source),
                    'targetOccurrenceIds': sorted(row['candidateOccurrenceId'] for row in target),
                })
            summary.append({'sourceYear': source_year, 'targetYear': target_year,
                            'scope': scope, 'frameSeats': len(source_codes),
                            'selectedSeats': len(selected),
                            'selectedOccurrences': selected_occurrences,
                            'selectedHeldOccurrences': held_occurrences})
    return {'schemaVersion': 1, 'checkpoint': 'evidence-repair-design',
            'selectionRule': {'unit': 'complete seat-transition cluster',
                              'seed': SEED, 'ranking': 'ascending SHA-256 of seed|sourceYear|targetYear|scope|two-digit election-local seat number',
                              'quotasPerTransition': QUOTAS,
                              'identityAdjudication': 'none', 'outcomeFieldsUsed': []},
            'inputHashes': input_hashes, 'summary': summary, 'frame': frame}


def _read_with_hash(path):
    raw = (ROOT / path).read_bytes()
    return json.loads(raw), sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    occurrences, occurrence_hash = _read_with_hash(OCCURRENCES)
    readiness, readiness_hash = _read_with_hash(READINESS)
    inventory = build_inventory(occurrences['records'], readiness, {
        str(OCCURRENCES): occurrence_hash, str(READINESS): readiness_hash})
    encoded = (json.dumps(inventory, indent=2, ensure_ascii=False) + '\n').encode()
    destination = ROOT / OUTPUT
    if args.check:
        if not destination.is_file() or destination.read_bytes() != encoded:
            raise SystemExit('Cohort inventory differs from preserved inputs or selection rule')
        print('Cohort inventory and pinned inputs match')
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(encoded)


if __name__ == '__main__':
    main()
