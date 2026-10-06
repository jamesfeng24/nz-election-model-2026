"""Deterministic National/Labour incumbent-seat universe for adjacent elections 2008-2023.

Evidence acquisition only: names and geography are read from preserved Stage7/Stage25/Stage26
artifacts; no residual, coefficient or forecast is computed or used.
"""
from collections import defaultdict
from fractions import Fraction

from scripts.evidence.practical_candidate_linkage.names import alias_pairs, name_match, parse_name

OCCURRENCES = 'data/processed/models/candidate-overperformance/occurrences.json'
GEOGRAPHY = 'data/processed/checkpoints/stage25-historical-geography/geography.json'
ALIASES = 'data/processed/evidence/practical-candidate-linkage/aliases.json'
CANDIDATE_VOTES = 'data/processed/historical/2008-2023/candidate-votes.json'
MAORI_OVERLAY = 'data/processed/models/replacement-candidate/maori-winner-overlay.json'
INPUTS = (OCCURRENCES, GEOGRAPHY, ALIASES, CANDIDATE_VOTES, MAORI_OVERLAY)
PARTIES = {'nationalparty': 'NAT', 'labourparty': 'LAB'}
PAIRS = ((2008, 2011), (2011, 2014), (2014, 2017), (2017, 2020), (2020, 2023))


def fraction(value):
    return None if not value['denominator'] else float(Fraction(value['numerator'], value['denominator']))


def seat_winners(occurrences):
    """Highest published candidate vote among held candidatures; ties fail."""
    by_seat = defaultdict(list)
    for row in occurrences:
        if row['candidateContestStatus'] == 'held' and row['sourcePublishedCandidateVotes'] is not None:
            by_seat[row['electorateId']].append(row)
    winners = {}
    for seat, rows in by_seat.items():
        top = max(r['sourcePublishedCandidateVotes'] for r in rows)
        leaders = [r for r in rows if r['sourcePublishedCandidateVotes'] == top]
        if len(leaders) != 1:
            raise ValueError(f'Tied seat winner {seat}')
        winners[seat] = leaders[0]
    return winners


def verify_winners(winners, candidate_votes, overlay):
    """General winners must equal the published elected flag; Maori winners the Stage10 overlay."""
    elected = {r['id'] for r in candidate_votes['records'] if r['elected']}
    for seat, row in winners.items():
        if row['electorateType'] == 'general' and row['year'] != 2023:
            if row['candidateOccurrenceId'] not in elected:
                raise ValueError(f'Winner disagrees with elected flag {seat}')
    maori = {r['winnerOccurrenceId'] for r in overlay['records']}
    seen = {r['candidateOccurrenceId'] for r in winners.values() if r['electorateType'] == 'maori'
            and r['year'] in (2008, 2014, 2020)}
    if not maori <= seen:
        raise ValueError('Maori winner disagrees with Stage10 official overlay')


def successor_seats(geography):
    """Source electorate id -> target geography records in which it is a predecessor."""
    result = defaultdict(list)
    for record in geography:
        for predecessor in record['predecessors']:
            result[predecessor['sourceElectorateId']].append((record, predecessor))
    return result


def candidate_summary(row):
    return {'occurrenceId': row['candidateOccurrenceId'], 'name': row['sourceCandidateName'],
            'party': row['partyKey'], 'seat': row['electorateName'], 'seatId': row['electorateId'],
            'contestStatus': row['candidateContestStatus']}


def build_rows(occurrences, geography, aliases, winners):
    aliases = alias_pairs(aliases)
    by_year = defaultdict(list)
    for row in occurrences:
        by_year[row['year']].append(row)
    successors = successor_seats(geography)
    rows = []
    for pair in PAIRS:
        source_year, target_year = pair
        for seat_id, winner in sorted(winners.items(), key=lambda kv: kv[0]):
            if winner['year'] != source_year or winner['partyKey'] not in PARTIES:
                continue
            links = successors.get(seat_id, [])
            if not links:
                raise ValueError(f'No successor geography for {seat_id}')
            dominant = [(g, p) for g, p in links if g['dominantPredecessorId'] == seat_id]
            rule = 'dominant_predecessor'
            if not dominant:
                best = max(links, key=lambda gp: (fraction(gp[1]['sourceRetentionLower']) or 0, gp[0]['targetElectorateId']))
                dominant, rule = [best], 'greatest_source_retention_no_dominant_successor'
            successor_ids = {g['targetElectorateId'] for g, _ in dominant}
            parsed = parse_name(winner['sourceCandidateName'])
            candidates = []
            for row in by_year[target_year]:
                if row['electorateId'] in successor_ids and row['partyKey'] == winner['partyKey']:
                    match = name_match(parsed, parse_name(row['sourceCandidateName']), aliases)
                    candidates.append({**candidate_summary(row), 'nameMatch': match})
            leads = []
            for row in by_year[target_year]:
                if row['electorateId'] in successor_ids and row['partyKey'] == winner['partyKey']:
                    continue
                match = name_match(parsed, parse_name(row['sourceCandidateName']), aliases)
                if match['compatible']:
                    leads.append({**candidate_summary(row), 'nameMatch': match})
            if any(c['nameMatch']['compatible'] for c in candidates):
                auto = 'compatible_name_same_party_successor_seat'
            elif candidates:
                auto = 'different_or_unresolved_name_same_party_successor_seat'
            else:
                auto = 'no_same_party_candidate_in_successor_seat'
            key = f"{source_year}-{target_year}|{PARTIES[winner['partyKey']]}|{winner['electorateName']}"
            rows.append({
                'key': key, 'sourceYear': source_year, 'targetYear': target_year,
                'scope': winner['electorateType'], 'party': PARTIES[winner['partyKey']],
                'sourceElectorate': {'id': seat_id, 'name': winner['electorateName']},
                'sourceWinner': candidate_summary(winner) | {'votes': winner['sourcePublishedCandidateVotes']},
                'successorRule': rule,
                'successorSeats': [{'id': g['targetElectorateId'], 'name': g['targetElectorateName'],
                                    'geographyTier': g['exclusiveTier'],
                                    'sourceRetentionLower': fraction(p['sourceRetentionLower']),
                                    'sourceRetentionUpper': fraction(p['sourceRetentionUpper']),
                                    'targetInheritanceLower': fraction(p['targetInheritanceLower']),
                                    'targetInheritanceUpper': fraction(p['targetInheritanceUpper'])}
                                   for g, p in sorted(dominant, key=lambda gp: gp[0]['targetElectorateId'])],
                'targetCandidates': candidates, 'automaticRelation': auto,
                'sourceWinnerNameCompatibleElsewhere': leads})
    return rows
