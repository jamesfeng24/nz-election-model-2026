"""Pure parsers for the modern Electoral Commission statistics CSV layout."""
from decimal import Decimal, InvalidOperation

from .historical import read_csv, count, key, ratio, require


def percent(value):
    """Read a bounded published percentage; missing is an error."""
    try:
        result = Decimal(value.removesuffix('%'))
    except InvalidOperation as exc:
        raise ValueError('Missing or invalid percentage: ' + repr(value)) from exc
    require(result.is_finite() and 0 <= result <= 100, 'Invalid percentage')
    return float(result)


def check_percent(votes, total, reported, context):
    require(total > 0 and abs(votes / total * 100 - reported) <= .00501,
            'Published percentage: ' + context)


def unique(records, field):
    result = {}
    for record in records:
        identity = key(record[field])
        require(identity not in result, 'Duplicate or ambiguous ' + field)
        result[identity] = record
    return result


def turnout_table(data):
    """Return electorate ballot controls and general/Māori/national controls."""
    rows, _ = read_csv(data)
    start = next(i for i, row in enumerate(rows) if row[0] == 'Electoral District') + 2
    fields = ('ordinaryValid', 'specialValid', 'validVotes', 'ordinaryInformal',
              'specialInformal', 'informalVotes', 'ordinaryDisallowed',
              'specialDisallowed', 'votesCast', 'enrolled', 'electoralPopulation')
    records, totals, scope = [], {}, 'general'
    scopes = {'General Electorate Totals': 'general', 'Māori Electorate Totals': 'maori',
              'Combined Totals': 'national'}
    for row in rows[start:]:
        require(len(row) == len(rows[start - 2]), 'Ragged turnout row')
        record = {'name': row[0], 'scope': scopes.get(row[0], scope),
                  **dict(zip(fields, map(count, row[1:12]))),
                  'reportedTurnoutPercent': percent(row[12]),
                  'reportedInformalPercent': percent(row[-1])}
        if len(row) == 15:
            record['reportedWinnerPercentOfVotesCast'] = percent(row[13]) if row[13] else None
        require(record['ordinaryValid'] + record['specialValid'] == record['validVotes'], 'Valid vote components')
        require(record['ordinaryInformal'] + record['specialInformal'] == record['informalVotes'], 'Informal vote components')
        require(sum(record[f] for f in ('validVotes', 'informalVotes', 'ordinaryDisallowed', 'specialDisallowed')) == record['votesCast'], 'Votes cast components')
        check_percent(record['votesCast'], record['enrolled'], record['reportedTurnoutPercent'], row[0])
        check_percent(record['informalVotes'], record['validVotes'] + record['informalVotes'], record['reportedInformalPercent'], row[0])
        if row[0] in scopes:
            require(record['scope'] not in totals, 'Duplicate turnout control')
            totals[record['scope']] = record
            scope = 'maori'
        else:
            records.append(record)
    unique(records, 'name')
    require(set(totals) == {'general', 'maori', 'national'}, 'Missing turnout controls')
    for scope in totals:
        selected = records if scope == 'national' else [r for r in records if r['scope'] == scope]
        for field in fields:
            require(sum(r[field] for r in selected) == totals[scope][field], 'Turnout aggregate: ' + field)
    return records, totals


def candidate_table(data, electorate_names=()):
    """Reconcile footer candidates with every voting-place row and column."""
    rows, encoding = read_csv(data)
    start = next(i for i, row in enumerate(rows) if row[0] == 'Electorate Candidate Valid Votes')
    headers = rows[2][2:-2]
    require(len(headers) == len(set(headers)), 'Duplicate candidate column')
    winner_text = next(cell for cell in rows[start] if ' - majority ' in cell)
    winner, majority = winner_text.rsplit(' - majority ', 1)
    candidates = []
    for row in rows[start + 1:]:
        require(len(row) == 4, 'Ragged candidate footer')
        require(bool(row[0]) and bool(row[1]), 'Missing candidate name or affiliation')
        reported = percent(row[3])
        candidates.append({'name': row[0], 'party': row[1], 'votes': count(row[2]),
                           'sourceShare': reported / 100, 'reportedPercent': reported})
    unique(candidates, 'name')
    require(headers == [c['name'] for c in candidates], 'Candidate header/footer identity')
    total_rows = [i for i, row in enumerate(rows[:start]) if len(row) == len(rows[2]) and row[1].endswith(' Total')]
    require(len(total_rows) == 1, 'Ambiguous candidate totals')
    total_index = total_rows[0]
    totals = list(map(count, rows[total_index][2:]))
    details = []
    disclosure_notes = []
    section_labels = []
    for row in rows[3:total_index]:
        if row == ['', 'Voting places where less than 6 votes were taken']:
            disclosure_notes.append(row[1])
            continue
        if len(row) == 1:
            require(row[0] in ('Advance Voting Places', 'Voting Places') or row[0] in electorate_names, 'Unknown voting-place section')
            section_labels.append(row[0])
            continue
        require(len(row) == len(rows[2]), 'Ragged voting-place row')
        values = list(map(count, row[2:]))
        require(sum(values[:-2]) == values[-2], 'Voting-place valid total')
        details.append(values)
    require([sum(column) for column in zip(*details)] == totals, 'Voting-place column totals')
    require([c['votes'] for c in candidates] == totals[:-2], 'Candidate footer/polling-place totals')
    total = sum(c['votes'] for c in candidates)
    require(total == totals[-2], 'Candidate valid total')
    combined = rows[total_index + 1]
    require(combined[1] == 'Valid Candidate Votes plus Informal Candidate Votes' and count(combined[-1]) == sum(totals[-2:]), 'Candidate counted ballot total')
    for candidate in candidates:
        candidate['share'] = ratio(candidate['votes'], total)
        check_percent(candidate['votes'], total, candidate['reportedPercent'], candidate['name'])
    ranked = sorted(candidates, key=lambda c: c['votes'], reverse=True)
    require(len(ranked) >= 2 and ranked[0]['name'] == winner and ranked[0]['votes'] - ranked[1]['votes'] == count(majority), 'Candidate winner or majority')
    return {'sourceElectorateLabel': rows[1][0], 'candidates': candidates, 'validVotes': total,
            'informalVotes': totals[-1], 'winnerName': winner, 'majority': count(majority),
            'sourceEncoding': encoding, 'votingPlaceRowsValidated': len(details), 'sourceDisclosureNotes': disclosure_notes, 'sourceSectionLabels': section_labels}


def party_table(data):
    """Return all party rows, retaining official labels and explicit totals."""
    rows, _ = read_csv(data)
    labels = rows[1][1:-3]
    require(len(set(map(key, labels))) == len(labels), 'Ambiguous party header')
    records, totals = [], {}
    scopes = {'General Electorate Totals': 'general', 'Māori Electorate Totals': 'maori', 'Combined Totals': 'national'}
    for row in rows[2:]:
        require(len(row) == len(rows[1]), 'Ragged party row')
        valid, informal, counted = map(count, row[-3:])
        parties = [{'partyName': label, 'partyKey': key(label), 'sourceHeader': label,
                    'votes': count(value), 'share': ratio(count(value), valid)}
                   for label, value in zip(labels, row[1:-3])]
        require(sum(p['votes'] for p in parties) == valid and valid + informal == counted, 'Party row totals')
        record = {'name': row[0], 'parties': parties, 'validVotes': valid, 'informalVotes': informal, 'votesCounted': counted}
        if row[0] in scopes:
            require(scopes[row[0]] not in totals, 'Duplicate party control')
            totals[scopes[row[0]]] = record
        else:
            records.append(record)
    return {'partyLabels': labels, 'records': unique(records, 'name'), 'totals': totals}


def winners_table(data):
    """Return official winner rows keyed by an election-local electorate label."""
    rows, _ = read_csv(data)
    records = []
    for row in rows[2:]:
        require(len(row) == 7, 'Ragged winner row')
        records.append({'name': row[0], 'candidateName': row[1], 'party': row[2],
                        'votes': count(row[3]), 'majority': count(row[4]),
                        'reportedPercent': percent(row[5]), 'onPartyList': row[6]})
    return unique(records, 'name')


def overall_table(data):
    """Preserve candidate-only affiliations and their explicitly published zeros."""
    rows, _ = read_csv(data)
    parties, group = [], None
    groups = ('Registered Parties with List', 'Registered Parties, no List', 'Unregistered Parties')
    end = next(i for i, row in enumerate(rows) if row[0] == 'State of the Parties')
    for row in rows[:end]:
        if row[0] in groups:
            group = row[0]
        elif group and row[0]:
            require(len(row) == 9, 'Ragged overall party row')
            parties.append({'name': row[0], 'partyKey': key(row[0]), 'sourceGroup': group,
                            'partyVotes': count(row[2]), 'candidateVotes': count(row[6]),
                            'reportedPartyPercent': percent(row[3]), 'reportedCandidatePercent': percent(row[7]),
                            'candidateNominations': count(row[8])})
    unique(parties, 'name')
    valid, informal = rows[end - 2], rows[end - 1]
    controls = {'validPartyVotes': count(valid[3]), 'validCandidateVotes': count(valid[7]),
                'informalPartyVotes': count(informal[3]), 'informalCandidateVotes': count(informal[7])}
    for ballot in ('Party', 'Candidate'):
        require(sum(p[ballot.lower() + 'Votes'] for p in parties) == controls['valid' + ballot + 'Votes'], 'Overall vote sum')
        for party in parties:
            check_percent(party[ballot.lower() + 'Votes'], controls['valid' + ballot + 'Votes'], party['reported' + ballot + 'Percent'], party['name'])
    return {'parties': parties, **controls}
