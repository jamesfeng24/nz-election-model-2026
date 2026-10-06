"""Build the sourced National/Labour incumbent-to-successor transition ledger (evidence only).

python -m scripts.evidence.candidate_transitions.run [--check]

No replacement effect, residual, coefficient or forecast is estimated here.
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path

from scripts.evidence.practical_candidate_linkage.names import alias_pairs, name_match, parse_name
from .universe import (ALIASES, CANDIDATE_VOTES, GEOGRAPHY, INPUTS, MAORI_OVERLAY, OCCURRENCES, PAIRS,
                       build_rows, seat_winners, verify_winners)

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'data/processed/evidence/candidate-transitions'
CURATION = 'data/source-plans/candidate-transition-curation.json'
REGISTRY = 'data/processed/evidence/candidate-transitions/source-registry.json'
STAGE10_INVENTORY = 'data/processed/models/replacement-candidate/inventory.json'
DATE = re.compile(r'^\d{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?)?$')
DATE_KINDS = {'announcement', 'event', 'selection', 'publication', 'list_membership', 'retrieval', 'listing'}
READINGS = {'direct', 'listing', 'low_reliability'}
CHANGE_TYPES = {'retirement', 'resignation_before_election', 'by_election_succession', 'by_election_party_change',
                'deselection', 'party_change', 'boundary_complication', 'death_or_illness_withdrawal'}
CONFIDENCE = {'high', 'medium', 'low'}


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def verify_registry(registry):
    ids = [s['id'] for s in registry['sources']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate registry source id')
    for source in registry['sources']:
        if digest(source['rawPath']) != source['sha256']:
            raise ValueError(f"Changed raw evidence extract: {source['rawPath']}")
    return set(ids)


def verify_evidence(items, source_ids, where):
    if not items:
        raise ValueError(f'No evidence: {where}')
    for item in items:
        if item['source'] not in source_ids:
            raise ValueError(f'Unregistered evidence source {item["source"]} in {where}')
        if item['date'] is not None and not DATE.match(item['date']):
            raise ValueError(f'Bad evidence date in {where}')
        if item['dateKind'] not in DATE_KINDS or item['reading'] not in READINGS or not item['claim']:
            raise ValueError(f'Bad evidence item in {where}')


def primary_candidate(row):
    compatible = [c for c in row['targetCandidates'] if c['nameMatch']['compatible']]
    if compatible:
        return compatible[0]
    seat_rank = {s['id']: (s['sourceRetentionLower'] or 0) for s in row['successorSeats']}
    ranked = sorted(row['targetCandidates'], key=lambda c: (-seat_rank.get(c['seatId'], 0), c['occurrenceId']))
    return ranked[0] if ranked else None


def classify(rows, curation, source_ids, by_year, aliases):
    transitions, judgements, notes = curation['transitions'], curation['identityJudgements'], curation['continuationNotes']
    used = Counter()
    out = []
    for row in rows:
        row = dict(row)
        key = row['key']
        row['primaryTargetCandidate'] = primary_candidate(row)
        compatible = row['automaticRelation'] == 'compatible_name_same_party_successor_seat'
        if key in transitions:
            if compatible or key in judgements:
                raise ValueError(f'Curated change conflicts with a same-person finding: {key}')
            entry = transitions[key]
            if entry['transitionType'] not in CHANGE_TYPES or entry['confidence'] not in CONFIDENCE:
                raise ValueError(f'Bad curated transition: {key}')
            verify_evidence(entry['evidence'], source_ids, key)
            row['relation'] = 'candidate_change'
            row['transition'] = entry
            used['transitions'] += 1
            effective = entry['effectiveIncumbentAtTarget']
            if effective:
                hits = [o for o in by_year[row['targetYear']] if name_match(parse_name(effective['name']),
                        parse_name(o['sourceCandidateName']), aliases)['compatible']]
                if not hits:
                    raise ValueError(f'Effective incumbent not found among target candidates: {key}')
                if entry['effectiveIncumbentRecontests']:
                    if not (row['primaryTargetCandidate'] and name_match(parse_name(effective['name']),
                            parse_name(row['primaryTargetCandidate']['name']), aliases)['compatible']):
                        raise ValueError(f'By-election incumbent is not the target candidate: {key}')
                row['effectiveIncumbentTargetOccurrences'] = [candidate_ref(o) for o in hits]
        elif key in judgements:
            if compatible:
                raise ValueError(f'Redundant identity judgement: {key}')
            entry = judgements[key]
            verify_evidence(entry['evidence'], source_ids, key)
            row['relation'] = 'continuation'
            row['continuationBasis'] = 'curated_identity_judgement'
            row['identityJudgement'] = entry
            used['judgements'] += 1
        elif compatible:
            row['relation'] = 'continuation'
            row['continuationBasis'] = 'automatic_name_match_same_party_successor_seat'
            row['automaticFlags'] = row['primaryTargetCandidate']['nameMatch']['flags']
        else:
            raise ValueError(f'Unclassified candidate difference: {key}')
        if key in notes:
            if row['relation'] != 'continuation':
                raise ValueError(f'Continuation note on a change: {key}')
            verify_evidence(notes[key]['evidence'], source_ids, key)
            row['continuationNote'] = notes[key]
            used['notes'] += 1
        out.append(row)
    unused = (set(transitions) | set(judgements) | set(notes)) - {r['key'] for r in out}
    if unused:
        raise ValueError(f'Curation keys with no ledger row: {sorted(unused)}')
    for gain in curation['supplementarySeatGains']:
        verify_evidence(gain['evidence'], source_ids, gain['key'])
    return out


def candidate_ref(row):
    return {'occurrenceId': row['candidateOccurrenceId'], 'name': row['sourceCandidateName'],
            'party': row['partyKey'], 'seat': row['electorateName'], 'contestStatus': row['candidateContestStatus']}


def supplementary(curation, by_year, aliases):
    result = []
    for gain in curation['supplementarySeatGains']:
        hits = [o for o in by_year[gain['targetYear']] if o['partyKey'] == 'nationalparty' and o['electorateName'] == gain['seat']
                and name_match(parse_name(gain['effectiveIncumbent']), parse_name(o['sourceCandidateName']), aliases)['compatible']]
        if len(hits) != 1:
            raise ValueError('Supplementary seat gain candidate not found uniquely')
        result.append({**gain, 'targetOccurrence': candidate_ref(hits[0])})
    return result


def summary(rows, inventory):
    changes = [r for r in rows if r['relation'] == 'candidate_change']
    by_pair = {}
    for pair in PAIRS:
        label = f'{pair[0]}-{pair[1]}'
        rs = [r for r in rows if (r['sourceYear'], r['targetYear']) == pair]
        cs = [r for r in rs if r['relation'] == 'candidate_change']
        by_pair[label] = {
            'incumbentSeats': len(rs), 'byParty': dict(sorted(Counter(r['party'] for r in rs).items())),
            'continuations': len(rs) - len(cs), 'candidateChanges': len(cs),
            'changesByType': dict(sorted(Counter(r['transition']['transitionType'] for r in cs).items())),
            'changesByParty': dict(sorted(Counter(r['party'] for r in cs).items())),
            'electionTimeIncumbentExits': sum(1 for r in cs if not r['transition']['effectiveIncumbentRecontests']
                                              and r['transition']['transitionType'] not in ('by_election_party_change', 'party_change', 'boundary_complication')),
            'generalAndMaori': dict(sorted(Counter(r['scope'] for r in cs).items()))}
    return {
        'incumbentSeats': len(rows), 'continuations': len(rows) - len(changes), 'candidateChanges': len(changes),
        'changesByType': dict(sorted(Counter(r['transition']['transitionType'] for r in changes).items())),
        'changesByConfidence': dict(sorted(Counter(r['transition']['confidence'] for r in changes).items())),
        'continuationBasis': dict(sorted(Counter(r['continuationBasis'] for r in rows if r['relation'] == 'continuation').items())),
        'automaticContinuationFlags': dict(sorted(Counter(f for r in rows if r.get('automaticFlags') for f in r['automaticFlags']).items())),
        'tags': dict(sorted(Counter(t for r in changes for t in r['transition']['tags']).items())),
        'byPair': by_pair, 'exactNameDifferencesByPair': exact_name_differences(rows),
        'stage10Reconciliation': reconcile_stage10(rows, inventory),
        'definitions': {
            'electionTimeIncumbentExits': 'Changes in which the party seat holder at the target election did not recontest and the departure is neither a party switch nor a boundary move: the cleanest incumbent-to-newcomer set.',
            'by_election_succession': 'Not newcomers at the election: the by-election winner is the effective incumbent.'}}


def reconcile_stage10(rows, inventory):
    """Stage10 counted exact-name contrasts among general source winners; resolve each against this ledger."""
    by_source = {r['sourceWinner']['occurrenceId']: r for r in rows}
    resolved = defaultdict(Counter)
    listed = set()
    for event in inventory:
        if not (event['electorateType'] == 'general' and event['outgoingStatus'] == 'source_winner' and event['nameContrast']
                and (event['sourceYear'], event['targetYear']) in ((2008, 2011), (2014, 2017), (2020, 2023))):
            continue
        label = f"{event['sourceYear']}-{event['targetYear']}"
        row = by_source.get(event['sourceOccurrenceId'])
        listed.add(event['sourceOccurrenceId'])
        if row is None:
            resolved[label]['other_party_winner_outside_ledger'] += 1
        elif row['relation'] == 'candidate_change':
            resolved[label]['candidate_change'] += 1
        else:
            resolved[label][row['continuationBasis'] + '_same_person'] += 1
    extra = sorted(r['key'] for r in rows if r['sourceYear'] in (2008, 2014, 2020) and r['scope'] == 'general'
                   and r['relation'] == 'candidate_change' and r['sourceWinner']['occurrenceId'] not in listed)
    return {'stage10NameContrastSourceWinners': {k: dict(sorted(v.items())) for k, v in sorted(resolved.items())},
            'stage10Total': sum(sum(v.values()) for v in resolved.values()),
            'ledgerChangesAbsentFromStage10List': extra,
            'note': 'Stage10 listed exact-name contrasts (13/21/27 incl. ACT and United Future, 61 total). Same-person variants and by-election successions are not election-time replacements; three further National/Labour changes are in seats absent from the Stage10 inventory (cause not investigated; Stage10 outputs unchanged).'}


def exact_name_differences(rows):
    result = {}
    for pair in PAIRS:
        rs = [r for r in rows if (r['sourceYear'], r['targetYear']) == pair]
        different = [r for r in rs if not r['primaryTargetCandidate'] or r['primaryTargetCandidate']['name'] != r['sourceWinner']['name']]
        result[f'{pair[0]}-{pair[1]}'] = {
            'incumbentSeats': len(rs), 'exactStringDifferences': len(different),
            'resolvedSamePersonAutomatic': sum(1 for r in different if r['relation'] == 'continuation' and r['continuationBasis'].startswith('automatic')),
            'resolvedSamePersonCurated': sum(1 for r in different if r['relation'] == 'continuation' and r['continuationBasis'].startswith('curated')),
            'candidateChanges': sum(1 for r in different if r['relation'] == 'candidate_change')}
    return result


def table(rows):
    lines = ['# Candidate-change transition table (National and Labour incumbent seats, 2008-2023)', '',
             'Generated deterministically from `incumbent-seat-ledger.json`. Evidence only: no effect is estimated. '
             '"Effective incumbent" is the party holder at the target election after any by-election. See `docs/candidate-transition-evidence.md`.', '']
    for pair in PAIRS:
        label = f'{pair[0]}-{pair[1]}'
        changes = [r for r in rows if (r['sourceYear'], r['targetYear']) == pair and r['relation'] == 'candidate_change']
        lines += [f'## {pair[0]} to {pair[1]} ({len(changes)} changes)', '',
                  '| Seat | Party | Outgoing (source winner) | Incoming candidate | Type | Tags | Key dated evidence | Conf. |',
                  '|---|---|---|---|---|---|---|---|']
        for r in sorted(changes, key=lambda r: (r['scope'], r['sourceElectorate']['name'], r['party'])):
            t = r['transition']
            dated = next((e for e in t['evidence'] if e['date'] and e['dateKind'] in ('announcement', 'event', 'selection', 'publication')), t['evidence'][0])
            incoming = r['primaryTargetCandidate']['name'] if r['primaryTargetCandidate'] else 'none'
            lines.append(f"| {r['sourceElectorate']['name']}{' (Māori)' if r['scope'] == 'maori' else ''} | {r['party']} | {r['sourceWinner']['name']} | {incoming} | "
                         f"{t['transitionType']} | {', '.join(t['tags']) or '-'} | {dated['date'] or 'undated'}: {dated['claim'][:110]} | {t['confidence']} |")
        lines.append('')
    return ('\n'.join(lines)).encode()


def construct():
    registry = read(REGISTRY)
    source_ids = verify_registry(registry)
    curation = read(CURATION)
    occurrences = read(OCCURRENCES)['records']
    geography = read(GEOGRAPHY)['records']
    aliases = read(ALIASES)
    winners = seat_winners(occurrences)
    verify_winners(winners, read(CANDIDATE_VOTES), read(MAORI_OVERLAY))
    rows = build_rows(occurrences, geography, aliases, winners)
    by_year = defaultdict(list)
    for o in occurrences:
        by_year[o['year']].append(o)
    pairs = alias_pairs(aliases)
    ledger = classify(rows, curation, source_ids, by_year, pairs)
    changes = [r for r in ledger if r['relation'] == 'candidate_change']
    judgements = [{'key': k, **v} for k, v in sorted(curation['identityJudgements'].items())]
    return {
        'incumbent-seat-ledger.json': {'records': ledger, 'supplementarySeatGains': supplementary(curation, by_year, pairs),
            'universe': 'Every National or Labour electorate winner (general and Maori) at the 2008, 2011, 2014, 2017 and 2020 elections, joined to the same party candidate in the dominant Stage25 successor seat at the next election.'},
        'transition-table.json': {'records': changes},
        'identity-judgements.json': {'records': judgements, 'continuationNotes': curation['continuationNotes'],
            'policy': curation['policy'],
            'automaticAcceptance': 'Stage26 name_match flags on same-party successor-seat candidates; see summary.json automaticContinuationFlags.'},
        'summary.json': summary(ledger, read(STAGE10_INVENTORY)['records']),
        'transition-table.md': table(ledger)}


def save(name, value, check):
    raw = value if isinstance(value, bytes) else encode({'schemaVersion': 1, **value})
    path = DEST / name
    if check:
        if path.read_bytes() != raw:
            raise ValueError(f'Changed deterministic artifact: {name}')
    else:
        path.write_bytes(raw)
    return sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = construct()
    hashes = {name: save(name, value, args.check) for name, value in outputs.items()}
    scripts = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'scripts/evidence/candidate_transitions').glob('*.py'))
    manifest = {'inputSha256': {p: digest(p) for p in (*INPUTS, STAGE10_INVENTORY, CURATION, REGISTRY)},
                'generatorSha256': {p: digest(p) for p in scripts}, 'outputSha256': hashes}
    save('manifest.json', manifest, args.check)
    s = outputs['summary.json']
    print({'incumbentSeats': s['incumbentSeats'], 'candidateChanges': s['candidateChanges'], 'continuations': s['continuations']})


if __name__ == '__main__':
    main()
