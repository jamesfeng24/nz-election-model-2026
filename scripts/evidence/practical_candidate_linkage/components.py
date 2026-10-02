"""Check complete proposed components before reversible research grouping."""
from collections import defaultdict
from hashlib import sha256
from itertools import combinations

from .names import name_match, strict_member

SAME = ('documentary_same_person', 'accepted_algorithmic_same_person')


def connected(edges):
    neighbors = defaultdict(set)
    for edge in edges:
        a, b = edge['sourceOccurrenceId'], edge['targetOccurrenceId']
        neighbors[a].add(b)
        neighbors[b].add(a)
    pending, groups = set(neighbors), []
    while pending:
        todo, members = [min(pending)], set()
        while todo:
            node = todo.pop()
            if node in members:
                continue
            members.add(node)
            todo.extend(neighbors[node]-members)
        pending -= members
        groups.append(sorted(members))
    return sorted(groups)


def validate_components(edges, rows, aliases):
    by_id = {r['candidateOccurrenceId']: r for r in rows}
    by_pair = {frozenset((e['sourceOccurrenceId'], e['targetOccurrenceId'])): e for e in edges}
    groups = connected([e for e in edges if e['label'] in SAME])
    audits = []
    for ids in groups:
        members, conflicts = set(ids), []
        for a, b in combinations(ids, 2):
            source, target = by_id[a], by_id[b]
            direct = by_pair.get(frozenset((a,b)))
            if source['year'] == target['year']:
                conflicts.append({'reason': 'simultaneous_occurrences', 'occurrenceIds': [a,b]})
            if direct and direct['label'] not in SAME:
                conflicts.append({'reason': 'rejected_internal_edge', 'edgeId': direct['edgeId']})
            explicit_bridge = direct and direct['label'] == 'documentary_same_person'
            if not explicit_bridge and not name_match(source['parsedName'], target['parsedName'], aliases)['compatible']:
                conflicts.append({'reason': 'incompatible_component_names', 'occurrenceIds': [a,b]})
        internal = [e for e in edges if e['sourceOccurrenceId'] in members and e['targetOccurrenceId'] in members]
        for edge in internal:
            if edge['label'] in SAME and edge['competingOccurrenceIds']:
                conflicts.append({'reason': 'unresolved_electionwide_competitor', 'edgeId': edge['edgeId']})
        if conflicts:
            for edge in internal:
                if edge['label'] in SAME:
                    edge['preComponentLabel'] = edge['label']
                    edge['label'] = 'unresolved_ambiguous'
                    edge['ambiguityType'] = 'component_conflict'
                    edge['componentConflicts'] = conflicts
        audits.append({'occurrenceIds': ids, 'conflicts': conflicts,
                       'status': 'quarantined' if conflicts else 'compatible_all_members_checked'})
    return audits


def person_groups(edges, rows, strict=False):
    accepted = [e for e in edges if e['label'] in SAME and (not strict or strict_member(e))]
    by_id = {r['candidateOccurrenceId']: r for r in rows}
    records = []
    for ids in connected(accepted):
        members = set(ids)
        records.append({'provisionalGroupId': 'research-group:stage26:'+sha256('\n'.join(ids).encode()).hexdigest()[:20],
                        'candidateOccurrenceIds': ids,
                        'sourceNameAliases': sorted({by_id[i]['sourceCandidateName'] for i in ids}),
                        'supportingEdgeIds': [e['edgeId'] for e in accepted
                                              if e['sourceOccurrenceId'] in members and e['targetOccurrenceId'] in members],
                        'historicalPersonIdsOverwritten': False,
                        'careerHistoryCompleteness': 'not_established',
                        'availabilityBeforeHistoricalCutoff': 'unknown'})
    return records
