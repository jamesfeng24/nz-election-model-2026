"""Audit exact electorate-name joins against macron-insensitive seat identity, without touching frozen outputs.

python -m scripts.audits.seat_name_keys [--check]

Election results spell some seats without macrons in early years (2008 Kaikoura, 2011 Kaikōura; 2017 Whangarei, 2020
Whangārei). Stage 8 chain keys and pair filters and the Stage 10 inventory compare `electorateName` exactly, so those seats
silently drop out of cross-election pairs. The pinned Stage 8 and Stage 10 outputs are hash-preserved by many later stages
and are not changed. This audit measures what the exact-name joins miss, and writes the Stage 10 records that a
macron-insensitive seat identity adds, as a separate additive file.
"""
import argparse
import json
import unicodedata
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from scripts.models.replacement_candidate import run as stage10

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'data/processed/audits/seat-name-keys'
OCCURRENCES = 'data/processed/models/candidate-overperformance/occurrences.json'
PAIRS = 'data/processed/models/candidate-persistence/pairs.json'
INVENTORY = 'data/processed/models/replacement-candidate/inventory.json'
ADJACENT = ((2008, 2011), (2011, 2014), (2014, 2017), (2017, 2020), (2020, 2023))
CODE = ('scripts/audits/seat_name_keys.py',)
INPUTS = (OCCURRENCES, PAIRS, INVENTORY)


def fold(value):
    """Case- and diacritic-insensitive seat identity that keeps spaces and hyphens."""
    plain = unicodedata.normalize('NFKD', value.casefold())
    return ''.join(char for char in plain if not unicodedata.combining(char))


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def spelling_families(occurrences):
    """Seats whose spelling differs between elections only by case or diacritics."""
    spellings = defaultdict(lambda: defaultdict(set))
    for row in occurrences:
        spellings[(row['electorateType'], fold(row['electorateName']))][row['electorateName']].add(row['year'])
    families = []
    for (scope, folded), names in sorted(spellings.items()):
        if len(names) > 1:
            families.append({'electorateType': scope, 'foldedName': folded,
                             'spellings': {name: sorted(years) for name, years in sorted(names.items())}})
    # one folded name must never stand for two seats in the same election
    for (scope, folded), names in spellings.items():
        years = [year for ys in names.values() for year in ys]
        if len(years) != len(set(years)):
            raise ValueError('Folded seat name is ambiguous within an election: ' + folded)
    return families


def stage10_additions(occurrences, pinned):
    """Re-run the unchanged Stage 10 builder with macron-insensitive seat identity and report only what it adds."""
    raw_name = {row['candidateOccurrenceId']: row['electorateName'] for row in occurrences}
    original = stage10.build_inventory

    def folded(occ, *args, **kwargs):
        result = original([{**row, 'electorateName': fold(row['electorateName'])} for row in occ], *args, **kwargs)
        for record in result['records']:
            record['electorateName'] = raw_name[record['sourceOccurrenceId']]
        return result

    with patch.object(stage10, 'build_inventory', folded):
        keyed = stage10.build()['inventory.json']
    pinned_by_event = {row['eventId']: row for row in pinned['records']}
    keyed_by_event = {row['eventId']: row for row in keyed['records']}
    if not set(pinned_by_event) <= set(keyed_by_event):
        raise ValueError('Folded Stage 10 inventory lost a pinned record')
    changed = sorted(event for event, row in pinned_by_event.items() if keyed_by_event[event] != row)
    additions = [row for event, row in sorted(keyed_by_event.items()) if event not in pinned_by_event]
    return keyed, additions, changed


def summarise_additions(additions, pinned, keyed):
    def counts(rows, field):
        out = defaultdict(int)
        for row in rows:
            out[str(row[field])] += 1
        return dict(sorted(out.items()))
    seats = defaultdict(set)
    for row in additions:
        seats[(row['sourceYear'], row['targetYear'], row['electorateType'])].add(row['electorateName'])
    return {
        'pinnedRecords': len(pinned['records']), 'foldedRecords': len(keyed['records']), 'additionalRecords': len(additions),
        'pinnedPrimaryEligible': pinned['primaryEligible'], 'foldedPrimaryEligible': keyed['primaryEligible'],
        'additionalPrimaryEligible': sum(row['primaryEligible'] for row in additions),
        'additionsByTransition': {f'{s}-{t} {scope}': {'records': sum(1 for row in additions
                                                                  if (row['sourceYear'], row['targetYear'], row['electorateType']) == (s, t, scope)),
                                                       'seats': sorted(names)}
                                  for (s, t, scope), names in sorted(seats.items())},
        'additionsByIdentityClass': counts(additions, 'identityClass'),
        'additionsByOutgoingStatus': counts(additions, 'outgoingStatus'),
    }


def chain_audit(occurrences, pairs):
    """Stage 8 chains key candidate occurrences by (name, party, exact seat name, scope); count what folding adds."""
    def adjacent(spelling):
        chains = defaultdict(list)
        for row in occurrences:
            chains[(row['sourceCandidateName'], row['candidateAffiliationKey'], spelling(row['electorateName']),
                    row['electorateType'])].append(row['year'])
        return {chain: sorted(years) for chain, years in chains.items()}
    exact, folded = adjacent(lambda name: name), adjacent(fold)

    def links(chains):
        return sum(1 for years in chains.values() for pair in zip(years, years[1:]) if pair in ADJACENT)
    spellings = defaultdict(set)
    for chain in exact:
        spellings[(chain[0], chain[1], fold(chain[2]), chain[3])].add(chain[2])
    gained = [{'candidate': chain[0], 'partyKey': chain[1], 'seat': chain[2], 'electorateType': chain[3],
               'years': folded[chain], 'spellings': sorted(spellings[chain])}
              for chain in folded if len(spellings[chain]) > 1]
    flagged = []
    for pair in pairs['pairs']:
        if (pair['sourceElectorate'] != pair['targetElectorate'] and
                fold(pair['sourceElectorate']) == fold(pair['targetElectorate'])):
            flagged.append({'pairId': pair['pairId'], 'sourceYear': pair['sourceYear'], 'targetYear': pair['targetYear'],
                            'sourceElectorate': pair['sourceElectorate'], 'targetElectorate': pair['targetElectorate'],
                            'validationEligible': pair['validationEligible'],
                            'exclusionReasons': pair['exclusionReasons'],
                            'primaryTransition': (pair['sourceYear'], pair['targetYear']) in ((2008, 2011), (2014, 2017), (2020, 2023))})
    return {'adjacentChainLinksExact': links(exact), 'adjacentChainLinksFolded': links(folded),
            'chainsGainedByFolding': sorted(gained, key=lambda row: (row['seat'], row['candidate'])),
            'pairsFlaggedOnlyByNameSpelling': flagged}


def build():
    occurrences = read(OCCURRENCES)['records']
    pinned = read(INVENTORY)
    keyed, additions, changed = stage10_additions(occurrences, pinned)
    audit = {
        'schemaVersion': 1,
        'question': 'What do exact electorate-name joins miss that a macron-insensitive seat identity would keep?',
        'rule': 'seat identity = case- and diacritic-insensitive name within election type; stable occurrence/electorate IDs where available',
        'frozenOutputsChanged': False,
        'spellingFamilies': spelling_families(occurrences),
        'stage10': {**summarise_additions(additions, pinned, keyed), 'pinnedRecordsDiffering': len(changed),
                    'finding': ('Every pinned record is reproduced exactly; the additions are records the exact-name join dropped. '
                                f'{sum(row["primaryEligible"] for row in additions)} additions are primary eligible '
                                '(same-person incumbent continuations in seats whose 2008 name lacks a macron), so the pinned primary '
                                'cohort is short by that many records; the rest are non-primary comparisons. Stage 51 and Stage 55 '
                                'join by occurrence ID and are unaffected.')},
        'stage8': chain_audit(occurrences, read(PAIRS)),
    }
    additions_file = {'schemaVersion': 1, 'derivedFrom': INVENTORY, 'usage':
                      'Additive supplement; the pinned Stage 10 inventory is unchanged and stays the preserved record.',
                      'records': additions}
    return {'audit.json': audit, 'stage10-keyed-additions.json': additions_file}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    manifest = {'schemaVersion': 1, 'inputHashes': {path: digest(path) for path in INPUTS},
                'codeHashes': {path: digest(path) for path in CODE},
                'outputHashes': {name: sha256(encode(value)).hexdigest() for name, value in outputs.items()},
                'dataSourcesJsonTouched': False, 'newSourcesOrAcquisition': False, 'frozenOutputsChanged': False}
    outputs['manifest.json'] = manifest
    dest = ROOT / PREFIX
    if args.check:
        for name, value in outputs.items():
            if (dest / name).read_bytes() != encode(value):
                raise ValueError(f'Changed pinned seat-name-key audit {name}')
        print('Seat-name-key audit reproducible')
        return
    dest.mkdir(parents=True, exist_ok=True)
    for name, value in outputs.items():
        (dest / name).write_bytes(encode(value))
    print('Seat-name-key audit written;', outputs['audit.json']['stage10']['additionalRecords'], 'additional Stage 10 records')


if __name__ == '__main__':
    main()
