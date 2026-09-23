"""Project pinned Parliament member indexes onto observed election winners."""

from collections import defaultdict
from datetime import datetime
from html import unescape
import re


BASE_URL = 'https://www3.parliament.nz'
ROW = re.compile(r'<tr class="list__row hot js-hot">(.*?)</tr>', re.S)
MEMBER = re.compile(
    r'<a href="(?P<url>/en/mps-and-electorates/(?:former-members-of-parliament|members-of-parliament)/[^\"]+)"'
    r' class="list__cell-heading theme__link" title="(?P<name>[^\"]+)">', re.S)
SERVICE = re.compile(r'<p class="list__cell-abstract">(.*?)</p>', re.S)
SERVICE_DATES = re.compile(r'(\d{1,2} [A-Za-z]+ \d{4})\s*-\s*(\d{1,2} [A-Za-z]+ \d{4})')
ELECTION_DATES = {2008: '8 November 2008', 2011: '26 November 2011',
                  2014: '20 September 2014', 2017: '23 September 2017',
                  2020: '17 October 2020', 2023: '14 October 2023'}


def _name_key(name):
    parts = name.split(',', 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None
    return parts[0].strip().casefold(), parts[1].strip().split()[0].casefold()


def _date(value):
    return datetime.strptime(value, '%d %B %Y').date()


def _service_intervals(text):
    return [(_date(start), _date(end)) for start, end in SERVICE_DATES.findall(text or '')]


def parse_members(raw):
    """Read unique official profile links and retained published service text."""
    records = {}
    for row in ROW.findall(raw.decode('utf-8')):
        found = MEMBER.search(row)
        if not found:
            continue
        url = BASE_URL + unescape(found['url'])
        service = SERVICE.search(row)
        record = {'name': unescape(found['name']), 'sourceUrl': url,
                  'serviceText': unescape(re.sub(r'<[^>]+>', '', service[1])).strip() if service else None}
        if url in records and records[url] != record:
            raise ValueError(f'Conflicting official profile: {url}')
        records[url] = record
    if len(records) < 100:
        raise ValueError('Incomplete Parliament member index')
    return sorted(records.values(), key=lambda value: value['sourceUrl'])


def project_members(occurrences, members, elected_ids, source_metadata=None):
    """Anchor observed winners and retain probable links in their exact chains.

    A parliamentary page supplies an independent person profile. The official
    election winner and exact original full-name/party/seat chain connect it to
    a specific occurrence. Omitted middle names remain explicit aliases.
    """
    source_metadata = source_metadata or {}
    by_key = defaultdict(list)
    for member in members:
        key = _name_key(member['name'])
        if key:
            by_key[key].append(member)
    by_chain = defaultdict(list)
    for row in occurrences:
        key = (row['sourceCandidateName'], row['candidateAffiliationKey'],
               row['electorateName'], row['electorateType'])
        by_chain[key].append(row)
    official = []
    for chain, rows in sorted(by_chain.items()):
        key = _name_key(chain[0])
        matches = by_key.get(key, [])
        if len({m['sourceUrl'] for m in matches}) != 1:
            continue
        member = matches[0]
        intervals = _service_intervals(member['serviceText'])
        winner_ids = sorted(row['candidateOccurrenceId'] for row in rows
                            if row['candidateOccurrenceId'] in elected_ids and
                            ((intervals and any(start <= _date(ELECTION_DATES[row['year']]) <= end
                                                for start, end in intervals)) or
                             (member['serviceText'] is None and row['year'] == 2023)))
        if not winner_ids or len({row['year'] for row in rows}) != len(rows):
            continue
        source_id = ('parliament-former-mp-index-2026-09-23' if
                     '/former-members-of-parliament/' in member['sourceUrl'] else
                     'parliament-current-mp-index-2026-09-23')
        anchors = [{'candidateOccurrenceId': candidate_id,
                    'year': next(row['year'] for row in rows if row['candidateOccurrenceId'] == candidate_id),
                    'electionDate': ELECTION_DATES[next(row['year'] for row in rows
                                                        if row['candidateOccurrenceId'] == candidate_id)]}
                   for candidate_id in winner_ids]
        for row in rows:
            source_name = row['sourceCandidateName']
            evidence = {
                'candidateOccurrenceId': row['candidateOccurrenceId'],
                'personId': 'parliament:' + member['sourceUrl'].rsplit('/', 2)[-2],
                'sourceUrl': member['sourceUrl'],
                'sourceId': source_id,
                'sourceName': member['name'],
                'winnerOccurrenceIds': winner_ids,
                'anchorOccurrences': anchors,
                'directOccurrenceEvidence': row['candidateOccurrenceId'] in winner_ids,
                'evidenceRetrievedAt': source_metadata.get(source_id, {}).get('retrievedAt'),
                'evidencePublishedAt': None,
                'serviceText': member['serviceText'],
            }
            if member['name'] != source_name:
                evidence['aliasEvidence'] = (
                    'Official profile display and preserved election source differ in case or middle names. '
                    'Unique surname/first-name profile plus observed winner in exact full-name/affiliation/seat chain.'
                )
            prior_winners = [earlier for earlier in rows if earlier['year'] < row['year'] and
                             earlier['candidateOccurrenceId'] in elected_ids]
            if prior_winners:
                latest = max(prior_winners, key=lambda earlier: earlier['year'])
                uninterrupted = any(start <= _date(ELECTION_DATES[latest['year']]) and
                                    end >= _date(ELECTION_DATES[row['year']])
                                    for start, end in intervals)
                if uninterrupted:
                    first_start = min(start for start, _ in intervals)
                    evidence['status'] = ('first_term_incumbent' if first_start >= _date(ELECTION_DATES[latest['year']])
                                          else 'continuing_incumbent')
                    evidence['priorServiceEvidence'] = (
                        f"{latest['candidateOccurrenceId']} observed elected; "
                        f"{member['sourceUrl']} published continuous service interval")
                    evidence['priorParliamentaryTenure'] = 'documented_continuous_service'
            official.append(evidence)
    return sorted(official, key=lambda value: value['candidateOccurrenceId'])
