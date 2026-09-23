"""Observed candidate inventory and conservative election-local counterpart joins."""
import hashlib
import json
import re

from scripts.models.party_vote_transform.inputs import Inputs as PartyInputs
from scripts.transform.historical import candidate_table as legacy, key
from scripts.transform.modern_tables import candidate_table as modern
from scripts.transform.panel_config import YEARS, COUNTS
from scripts.boundaries.census_2013 import ROOT

DEST = ROOT / 'data/processed/models/candidate-overperformance'
BASE = 'a28044a795e18a1ebc07bc3ea7c16fd23d6c8c14'
REGIMES = {2008: '2007', 2011: '2007', 2014: '2014', 2017: '2014', 2020: '2020', 2023: '2020'}


def counterpart(candidate, parties):
    """Exact normalized affiliation only; no alliance or cross-year alias joins."""
    affiliation = key(candidate['party'])
    if affiliation == 'independent':
        return None, 'independent_no_party_vote_counterpart'
    matches = [p for p in parties.values() if p['partyKey'] == affiliation]
    if len(matches) > 1:
        raise ValueError('Ambiguous within-election party counterpart')
    return (matches[0], None) if matches else (None, 'no_exact_party_vote_counterpart')


def validate_contest(e, year):
    status = e.get('candidateContestStatus', 'held')
    cancelled = year == 2023 and key(e['name']) == 'portwaikato'
    if (status == 'cancelled') != cancelled or status not in ('held', 'cancelled'):
        raise ValueError('Unexpected contest status')
    total = e['validCandidateVotes']
    if type(total) is not int or total < 0 or (not cancelled and total == 0):
        raise ValueError('Candidate denominator')
    if sum(c['votes'] for c in e['candidates']) != total:
        raise ValueError('Candidate count sum')
    for c in e['candidates']:
        if c.get('personId') is not None:
            raise ValueError('Person identity outside Stage7')
        if type(c['votes']) is not int or c['votes'] < 0:
            raise ValueError('Malformed candidate votes')
        if cancelled:
            if total != 0 or c['share'] is not None or c.get('elected') is not None:
                raise ValueError('Fabricated cancelled candidate result')
        elif c['share'] is None or abs(c['share'] - c['votes'] / total) > 1e-10:
            raise ValueError('Candidate share/denominator mismatch')
    return status


def make_occurrences(year, e, scope, party_seat, provenance):
    status = validate_contest(e, year)
    if key(e['name']) != key(party_seat['name']):
        raise ValueError('Candidate/party electorate mismatch')
    party_path = (f'data/raw/elections/{year}/e9/csv/e9_part4.csv' if year <= 2014 else
                  f'data/raw/elections/{year}/statistics/csv/votes-for-registered-parties-by-electorate.csv')
    provenance = {**provenance, 'partyInputPath': party_path}
    rows = []
    for ordinal, c in enumerate(e['candidates'], 1):
        p, reason = counterpart(c, party_seat['parties'])
        if status == 'cancelled':
            reason = 'cancelled_candidate_contest'
        eligible = reason is None
        cid = c.get('id', f"nz-general-{year}-electorate-{e['sourceElectorateNumber']:02d}-candidate-{ordinal:02d}")
        rows.append({
            'candidateOccurrenceId': cid, 'year': year, 'electionId': f'nz-general-{year}',
            'boundaryRegime': REGIMES[year], 'boundaryVersionId': f'historical-election-{year}-as-published',
            'inputClass': 'observed', 'electorateId': e['id'], 'electorateName': e['name'],
            'sourceElectorateNumber': e['sourceElectorateNumber'], 'electorateType': scope,
            'sourceCandidateName': c['name'], 'sourceAffiliation': c['party'], 'candidateAffiliationKey': key(c['party']),
            'personId': None, 'candidateContestStatus': status, 'sourcePublishedCandidateVotes': c['votes'],
            'validCandidateVotes': e['validCandidateVotes'], 'candidateShare': c['share'],
            'partyKey': p['partyKey'] if p else None, 'sourcePartyLabel': p['partyName'] if p else None,
            'sourcePartyHeader': p.get('sourceHeader', p['partyName']) if p else None,
            'localPartyVotes': p['votes'] if p else None, 'validPartyVotes': party_seat['validVotes'],
            'localPartyShare': p['share'] if p else None,
            'counterpartEvidence': 'exact normalized within-election affiliation/party key; upstream source-header aliases preserved' if p else None,
            'eligible': eligible, 'exclusionReason': reason,
            'rawPremium': c['share'] - p['share'] if eligible else None,
            'provenance': provenance,
        })
    return rows


def build():
    inputs = PartyInputs()
    parties = inputs.elections()
    hashes = dict(inputs.hashes)

    def read(path):
        raw = (ROOT / path).read_bytes()
        hashes[path] = hashlib.sha256(raw).hexdigest()
        return raw

    registry = json.loads(read('data/sources.json'))['sources']
    by_url = {r['url']: r for r in registry}
    rows = []
    for year in YEARS:
        path = f'data/processed/elections/{year}.json'
        observed = json.loads(read(path))
        headers = {p['partyKey']: p['sourceHeader'] for p in observed['electorates'][0]['parties']}
        for scope in parties[year]['scopes'].values():
            for seat in scope.values():
                for party in seat['parties'].values():
                    party['sourceHeader'] = headers[party['partyKey']]
        for e in observed['electorates']:
            rows.extend(make_occurrences(year, e, 'general', parties[year]['scopes']['general'][key(e['name'])],
                                         {'inputPath': path, 'sourceIds': e['sourceIds']}))
        plan = json.loads(read(f'data/source-plans/historical-{year}.json'))
        entries = [r for r in plan['resources'] if 'support' in r['role'].lower()
                   and ('cand_' in r['url'] or 'candidate-votes-by-voting-place' in r['url'])]
        if len(entries) != 7:
            raise ValueError('Supporting Maori candidate inventory')
        names = [e['name'] for scope in parties[year]['scopes'].values() for e in scope.values()]
        for entry in entries:
            source = by_url[entry['url']]
            raw = read(source['rawPath'])
            if hashes[source['rawPath']] != source['sha256']:
                raise ValueError('Source checksum changed')
            c = legacy(raw) if year <= 2014 else modern(raw, names)
            label = c['sourceElectorateLabel']
            name = re.sub(r'\s+\d+$', '', label)
            number = int(re.search(r'\s+(\d+)$', label).group(1))
            if entry.get('sourceElectorateNumber', number) != number:
                raise ValueError('Official electorate number mismatch')
            e = {'id': f'nz-general-{year}-electorate-{number:02d}', 'name': name,
                 'sourceElectorateNumber': number, 'validCandidateVotes': c['validVotes'], 'candidates': c['candidates']}
            rows.extend(make_occurrences(year, e, 'maori', parties[year]['scopes']['maori'][key(name)],
                                         {'inputPath': source['rawPath'], 'sourceIds': [source['id']],
                                          'occurrenceIdBasis': 'official election/number and source candidate order; supporting observed record, not person identity'}))
        for scope, expected_count in [('general', COUNTS[year][0]), ('maori', 7)]:
            seats = {r['electorateId']: r['validCandidateVotes'] for r in rows if r['year'] == year and r['electorateType'] == scope}
            if len(seats) != expected_count or sum(seats.values()) != observed['nationalControls']['candidate'][scope]['validVotes']:
                raise ValueError('Observed candidate scope control mismatch')
    rows.sort(key=lambda r: (r['year'], r['sourceElectorateNumber'], r['candidateOccurrenceId']))
    if len({r['candidateOccurrenceId'] for r in rows}) != len(rows):
        raise ValueError('Duplicate occurrence ID')
    for y in YEARS:
        general = [r for r in rows if r['year'] == y and r['electorateType'] == 'general']
        if len(general) != COUNTS[y][2]:
            raise ValueError('Prior general candidate coverage changed')
    return rows, dict(sorted(hashes.items())), {y: COUNTS[y][0] + 7 for y in YEARS}
