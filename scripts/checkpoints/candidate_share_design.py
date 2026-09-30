"""Pure synthetic feasibility kernel for the proposed direct candidate-share baseline.

This module has no historical runner and does not fit the support floor. It
accepts a supplied target-boundary party scenario and a positive floor so all
standing candidates can receive candidate-share mass without person links.
``partyKey=None`` requires ``noRegisteredPartyGroup=True`` from an independent
classification; it cannot stand for a failed or ambiguous party mapping.
"""

from math import isfinite


def candidate_shares(slate, party_support, support_floor):
    """Return one coherent valid-candidate-vote share vector for a scenario."""
    if not slate or not isfinite(support_floor) or support_floor <= 0:
        raise ValueError('Standing slate and positive support floor required')
    if (not party_support or any(not isfinite(value) or value < 0 or value > 1
                                 for value in party_support.values()) or
            abs(sum(party_support.values()) - 1) > 1e-9):
        raise ValueError('Complete normalized target party scenario required')
    ids = [candidate['candidateId'] for candidate in slate]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate candidate destination')
    party_keys = [candidate.get('partyKey') for candidate in slate]
    if any(party is None and candidate.get('noRegisteredPartyGroup') is not True
           for party, candidate in zip(party_keys, slate)):
        raise ValueError('Unmapped candidate party category is unknown')
    if any(party is not None and candidate.get('noRegisteredPartyGroup') is True
           for party, candidate in zip(party_keys, slate)):
        raise ValueError('Conflicting candidate party classification')
    if len([party for party in party_keys if party is not None]) != len(
            {party for party in party_keys if party is not None}):
        raise ValueError('Ambiguous multiple candidates of one party')
    if any(party is not None and party not in party_support for party in party_keys):
        raise ValueError('Missing party category support is unknown, not zero')
    weights = [party_support[party] + support_floor if party is not None
               else support_floor for party in party_keys]
    total = sum(weights)
    shares = [weight / total for weight in weights]
    return {'candidateShares': dict(zip(ids, shares)),
            'validCandidateShareSum': sum(shares),
            'rule': 'conditional_party_anchored_positive_floor_no_person_adjustment'}


def candidate_counts(shares, candidate_ballots):
    """Convert shares to expected counts only with distinct candidate controls."""
    required = ('votesCast', 'validCandidateVotes', 'informalCandidateVotes',
                'disallowedCandidateVotes')
    if any(field not in candidate_ballots for field in required):
        raise ValueError('Incomplete candidate-ballot count scenario')
    values = [candidate_ballots[field] for field in required]
    if any(not isinstance(value, int) or value < 0 for value in values):
        raise ValueError('Candidate-ballot controls must be nonnegative counts')
    cast, valid, informal, disallowed = values
    if valid <= 0 or valid + informal + disallowed != cast:
        raise ValueError('Incompatible or zero-valid candidate-ballot population')
    vector = shares['candidateShares']
    if abs(sum(vector.values()) - 1) > 1e-9:
        raise ValueError('Candidate shares must conserve valid votes')
    return {'expectedCandidateVotes': {key: share * valid for key, share in vector.items()},
            'validCandidateVotesScenario': valid,
            'informalCandidateVotesScenario': informal,
            'disallowedCandidateVotesScenario': disallowed,
            'votesCastScenario': cast}
