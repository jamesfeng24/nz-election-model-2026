"""One feasible population scenario, with exactly conserved source party mass.

The chosen vertex is an assumption. It is neither a reconstruction of candidate
votes nor an estimate of the expectation of the feasible population set.
"""
import argparse
from fractions import Fraction

import numpy as np
from scipy.optimize import linprog

from scripts.boundaries.contract import TRANSITIONS, system
from scripts.transport.common import digest, read, save, verify_inputs


def rational(value):
    value = Fraction(value)
    return {'numerator': value.numerator, 'denominator': value.denominator}


def lexicographic_witness(population):
    """Sequential LP minimization, followed by exact integral certification."""
    bounds = [(0, None) for _ in population.variables]
    order = sorted(range(population.n), key=lambda i: population.variables[i])
    witness = None
    for index in order:
        objective = np.zeros(population.n)
        objective[index] = 1
        result = linprog(objective, A_ub=population.A, b_ub=population.b,
                         A_eq=population.E, b_eq=population.c, bounds=bounds,
                         method='highs-ds', options={
                             'primal_feasibility_tolerance': 1e-9,
                             'dual_feasibility_tolerance': 1e-9})
        if not result.success:
            raise ValueError('Unresolved lexicographic population allocation: '+result.message)
        rounded = np.rint(result.x)
        if not np.all(np.isfinite(result.x)) or max(abs(rounded-result.x)) > 1e-5:
            raise ValueError('Unexpected nonintegral lexicographic optimum')
        witness = [int(v) for v in rounded]
        certify_witness(population, witness)
        value = witness[index]
        bounds[index] = (value, value)
    if witness is None:
        raise ValueError('Empty population allocation')
    return witness


def certify_witness(population, witness):
    """Check original group bounds and controls in integer arithmetic."""
    if len(witness) != population.n or any(type(v) is not int or v < 0 for v in witness):
        raise ValueError('Invalid integral population witness')
    grouped = {g['id']: 0 for g in population.groups}
    incoming = {target: 0 for target in population.controls}
    for (group, _, target), value in zip(population.variables, witness):
        grouped[group] += value
        incoming[target] += value
    for group in population.groups:
        if not group['lower'] <= grouped[group['id']] <= group['upper']:
            raise ValueError('Population witness violates original group interval')
    if incoming != population.controls:
        raise ValueError('Population witness violates destination controls')
    return grouped


def source_party_records(sources, expected_sources):
    """Require complete identical rosters; nonreporting never becomes zero."""
    if set(sources) != set(expected_sources):
        raise ValueError('Incomplete source party electorate inventory')
    records, roster = {}, None
    for code, source in sorted(sources.items()):
        parties = source['parties']
        values = {p['partyKey']: p['votes'] for p in parties}
        if len(values) != len(parties) or not values:
            raise ValueError('Duplicate or empty source party categories')
        if roster is None:
            roster = set(values)
        if set(values) != roster:
            raise ValueError('Missing source party category; not an observed zero')
        denominator = source['validVotes']
        if type(denominator) is not int or denominator <= 0:
            raise ValueError('Missing/invalid source valid-party denominator')
        if any(type(v) is not int or v < 0 for v in values.values()):
            raise ValueError('Missing/invalid source party votes')
        if sum(values.values()) != denominator:
            raise ValueError('Source party mass does not equal valid-party denominator')
        records[code] = (denominator, values)
    return records, sorted(roster)


def transport_votes(population, witness, sources, target_names=None):
    """Transport all categories and their denominator using the same weights."""
    certify_witness(population, witness)
    source_codes = {source for _, source, _ in population.variables}
    records, categories = source_party_records(sources, source_codes)
    flows = {edge: 0 for edge in population.edge_inventory()}
    for (_, source, target), value in zip(population.variables, witness):
        flows[source, target] += value
    outgoing = {source: sum(v for (s, _), v in flows.items() if s == source)
                for source in source_codes}
    if any(v <= 0 for v in outgoing.values()):
        raise ValueError('Source population vanishes; allocation weight undefined')
    weights = {edge: Fraction(value, outgoing[edge[0]]) for edge, value in flows.items()}
    targets = []
    target_masses = {party: Fraction(0) for party in categories}
    total_target = Fraction(0)
    for target in sorted(population.controls):
        denominator = sum((records[s][0]*w for (s, t), w in weights.items() if t == target), Fraction(0))
        values = {party: sum((records[s][1][party]*w for (s, t), w in weights.items() if t == target), Fraction(0))
                  for party in categories}
        if denominator <= 0 or sum(values.values()) != denominator:
            raise ValueError('Incomplete/zero transported target valid-party mass')
        targets.append({'targetCode': target, 'targetName': (target_names or {}).get(target),
                        'validPartyVotes': float(denominator), 'validPartyVotesExact': rational(denominator),
                        'parties': [{'partyKey': p, 'votes': float(values[p]), 'votesExact': rational(values[p]),
                                     'share': float(values[p]/denominator), 'shareExact': rational(values[p]/denominator)}
                                    for p in categories]})
        total_target += denominator
        for party, value in values.items():
            target_masses[party] += value
    source_masses = {p: sum(values[p] for _, values in records.values()) for p in categories}
    total_source = sum(denominator for denominator, _ in records.values())
    if total_target != total_source or target_masses != source_masses:
        raise ValueError('Transport lost source party mass')
    edges = [{'sourceCode': s, 'targetCode': t, 'population': flows[s, t],
              'sourceOutgoingPopulation': outgoing[s], 'weight': rational(weights[s, t])}
             for s, t in sorted(flows)]
    return {'partyCategories': categories, 'aggregatedEdges': edges, 'targetPartyVectors': targets,
            'sourceValidPartyVotes': total_source, 'targetValidPartyVotesExact': rational(total_target),
            'sourcePartyMass': source_masses,
            'targetPartyMassExact': {p: rational(v) for p, v in target_masses.items()},
            'nationalSourceShares': {p: float(Fraction(v, total_source)) for p, v in source_masses.items()},
            'nationalSourceSharesExact': {p: rational(Fraction(v, total_source)) for p, v in source_masses.items()},
            'nationalSourceSharesPopulation': 'ALL source electorates in this complete scope, never selected exact/overlap seats',
            'conservation': 'exact rational source party and valid-vote mass conserved'}


def build_scope(scope, party_sources):
    population = system(scope)
    witness = lexicographic_witness(population)
    grouped = certify_witness(population, witness)
    result = transport_votes(population, witness, party_sources,
                             {row['code']: row['name'] for row in scope['targets']})
    result.update({'status': 'constructed',
                   'witnessVariables': [{'groupId': g, 'sourceCode': s, 'targetCode': t, 'population': witness[i]}
                                        for i, (g, s, t) in sorted(enumerate(population.variables), key=lambda item: item[1])],
                   'groupWitnessTotals': grouped,
                   'targetPopulationControls': population.controls,
                   'solver': {'method': 'highs-ds', 'primalTolerance': 1e-9, 'dualTolerance': 1e-9,
                              'sequentialMinimizations': population.n, 'integerCertificationTolerance': 1e-5,
                              'constraintCertification': 'exact integer arithmetic',
                              'ordering': 'groupId, sourceCode, targetCode'}})
    return result


def combined_source_shares(scopes):
    """National source denominator includes both full scopes, not general only."""
    constructed = list(scopes.values())
    if any(s['status'] != 'constructed' for s in constructed):
        return {'status': 'unavailable', 'reason': 'A complete source scope abstained'}
    categories = constructed[0]['partyCategories']
    if any(s['partyCategories'] != categories for s in constructed):
        raise ValueError('Incompatible complete-scope party categories')
    denominator = sum(s['sourceValidPartyVotes'] for s in constructed)
    votes = {p: sum(s['sourcePartyMass'][p] for s in constructed) for p in categories}
    return {'status': 'available', 'sourceValidPartyVotes': denominator, 'sourcePartyMass': votes,
            'shares': {p: float(Fraction(v, denominator)) for p, v in votes.items()},
            'sharesExact': {p: rational(Fraction(v, denominator)) for p, v in votes.items()},
            'population': 'ALL preserved general AND Māori source party electorates'}


def build():
    verify_inputs()
    transitions = {}
    for transition in TRANSITIONS:
        prefix = 'data/processed/boundaries/'+transition+'/'
        crosswalk, party = read(prefix+'crosswalk.json'), read(prefix+'party-votes.json')
        scopes = {}
        for name, scope in sorted(crosswalk['scopes'].items()):
            try:
                scopes[name] = build_scope(scope, party['scopes'][name]['sources'])
            except ValueError as error:
                scopes[name] = {'status': 'abstained', 'reason': str(error)}
        transitions[transition] = {'scopes': scopes, 'nationalSourceShares': combined_source_shares(scopes),
                                   'inputHashes': {prefix+f: digest(prefix+f) for f in ('crosswalk.json', 'party-votes.json')}}
    return {'stage': 41, 'schemaVersion': 1, 'role': 'chosen feasible source-party geography scenario',
            'assumption': 'uniform source party voting over chosen source outgoing population; lexicographic vertex is not an expectation',
            'nationalReconciliation': 'not imposed against supplied future national shares',
            'candidateVoteReconstruction': False, 'transitions': transitions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    value = build()
    save('party-construction.json', value, args.check)
    statuses = [s['status'] for t in value['transitions'].values() for s in t['scopes'].values()]
    print('Stage41 party scopes: '+str({status: statuses.count(status) for status in sorted(set(statuses))}))


if __name__ == '__main__':
    main()
