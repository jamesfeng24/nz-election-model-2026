"""Shared controls for the compatible 2011/2014 split publications."""
from collections import defaultdict
from .historical import count, key, read_csv, require, split_rows, split_party_key


def validate_split_controls(source, electorates, matrices, *, year):
    expected_general = {2011: 63, 2014: 64}[year]
    expected_all = expected_general + 7
    require(len(electorates) == expected_all, f'{year} supporting electorate count')
    general = [e for e in electorates if e['kind'] == 'general']
    require(len(general) == expected_general and len(matrices) == expected_general, f'{year} general electorate/matrix count')
    for field in ('id', 'name', 'sourceElectorateNumber'):
        require(len({e[field] for e in electorates}) == expected_all, 'Duplicate electorate ' + field)
    require({m['electorateId'] for m in matrices} == {e['id'] for e in general}, 'Split coverage mismatch')
    ids = [c['id'] for e in electorates for c in e['candidates']]
    require(len(set(ids)) == len(ids), 'Duplicate candidate occurrence')
    for e, m in zip(general, matrices):
        require(m['sourceElectorateLabel'] == f"{e['sourceElectorateNumber']:02d} {e['name']}", 'Split source electorate label mismatch')
        require(len({r['partyLabel'] for r in m['rows']}) == len(m['rows']), 'Duplicate split row')
        require(len(m['rows']) == len(e['parties']) + 2, 'Missing split party rows')
        cells = m['rows'][0]['cells']
        require(len({c['candidateLabel'] for c in cells}) == len(cells), 'Duplicate split column')
        require({c['candidateId'] for c in cells if c['category'] == 'candidate'} == {c['id'] for c in e['candidates']}, 'Missing candidate split columns')
        for r in m['rows']:
            require(r['reportedTotalPercent'] == 100, 'Unexpected split total percentage')
            for c in r['cells']:
                require(c['count'] is None, 'Percentage source must not invent counts')

    # Aggregate destination columns refer to parties, unlike local candidate columns.
    aggregates = {}
    for title, scope in [('General', 'general'), ('Maori', 'maori'), ('Overall', 'national')]:
        raw, sid = source(f'elect-splitvote-{title}.csv')
        table = split_rows(raw)
        table['sourceIds'] = [sid]
        selected = electorates if scope == 'national' else [e for e in electorates if e['kind'] == scope]
        party = defaultdict(int)
        candidate = defaultdict(int)
        for e in selected:
            for p in e['parties']:
                party[p['partyKey']] += p['votes']
            for c in e['candidates']:
                candidate[split_party_key(c['partyKey'], year)] += c['votes']
        informal = sum(e['partyBallot']['informalVotes'] for e in selected)
        total = sum(party.values()) + informal
        require(table['rows'][-1]['totalPartyVotes'] == total, 'Aggregate split total: ' + title)
        require(sum(r['totalPartyVotes'] for r in table['rows'][:-1]) == total, 'Aggregate row sum: ' + title)
        for row in table['rows'][:-1]:
            expected = informal if row['partyLabel'] == 'Party Informals' else party[key(row['partyLabel'])]
            require(row['totalPartyVotes'] == expected, 'Aggregate party row: ' + title + '/' + row['partyLabel'])
        for row in table['rows']:
            values = [c['reportedPercent'] for c in row['cells']]
            require(all(v is not None for v in values), 'Missing aggregate percentage')
            require(abs(sum(values)-100) <= .005*len(values)+1e-8, 'Aggregate row rounding')
        for j, cell in enumerate(table['rows'][-1]['cells']):
            label = cell['candidateLabel']
            if label == 'Candidate Informals':
                expected = sum(e['candidateBallot']['informalVotes'] for e in selected)
            elif label == 'Party Vote Only':
                expected = total-sum(e['validCandidateVotes']+e['candidateBallot']['informalVotes'] for e in selected)
            elif label == 'Independents & parties with no list candidates':
                expected = sum(v for k, v in candidate.items() if k not in party)
            else:
                expected = candidate[key(label)]
            require(abs(expected/total*100-cell['reportedPercent']) <= .00501, 'Aggregate overall column: ' + title + '/' + label)
            midpoint = sum(r['totalPartyVotes']*r['cells'][j]['reportedPercent']/100 for r in table['rows'][:-1])
            require(abs(midpoint-expected) <= total*.00005+1e-8, 'Aggregate weighted column: ' + title + '/' + label)
        aggregates[scope] = table

    # Compare every general aggregate cell with the sum of corresponding local
    # percentage intervals. These are interval checks, never reconstructed counts.
    candidates = {c['id']: c for e in general for c in e['candidates']}
    listed = {p['partyKey'] for p in general[0]['parties']}
    grouped = defaultdict(lambda: [0.0, 0.0])
    for matrix in matrices:
        for row in matrix['rows'][:-1]:
            pk = 'partyinformals' if row['partyLabel'] == 'Informal Party Votes' else key(row['partyLabel'])
            for cell in row['cells']:
                if cell['category'] == 'candidate':
                    dest = split_party_key(candidates[cell['candidateId']]['partyKey'], year)
                    if dest not in listed:
                        dest = key('Independents & parties with no list candidates')
                else:
                    dest = key('Candidate Informals' if cell['category'] == 'informal' else 'Party Vote Only')
                n = row['totalPartyVotes']
                value = cell['reportedPercent']
                require(value is not None or n == 0, 'Missing nonzero local split cell')
                grouped[pk, dest][0] += n*(value or 0)/100
                grouped[pk, dest][1] += n*.00005
    for row in aggregates['general']['rows'][:-1]:
        for cell in row['cells']:
            midpoint, bound = grouped[key(row['partyLabel']), key(cell['candidateLabel'])]
            aggregate_midpoint = row['totalPartyVotes']*cell['reportedPercent']/100
            require(abs(midpoint-aggregate_midpoint) <= bound+row['totalPartyVotes']*.00005+1e-8, 'Local/aggregate split cell: ' + row['partyLabel'] + '/' + cell['candidateLabel'])

    raw, sid = source('elect-splitvote-summary.csv')
    rows, _ = read_csv(raw)
    summary = []
    overall = {key(r['partyLabel']): r for r in aggregates['national']['rows']}
    for r in rows[1:]:
        n, same, split = count(r[1]), count(r[2]), count(r[4])
        require(same+split == n, 'Exact split summary count sum')
        require(abs(same/n*100-float(r[3])) <= .00501 and abs(split/n*100-float(r[5])) <= .00501, 'Exact split summary percentages')
        is_total = r[0] == 'Total Party Votes'
        is_informal = r[0] == 'Informal Party Votes'
        pk = 'partyinformals' if is_informal else key(r[0])
        if not is_total:
            row = overall[pk]
            require(row['totalPartyVotes'] == n, 'Summary/aggregate row total')
            # The source's informal non-split value corresponds to Party Vote Only,
            # not Candidate Informals. Preserve and expose this source convention.
            column = 'Party Vote Only' if is_informal else r[0]
            percent = next(c['reportedPercent'] for c in row['cells'] if key(c['candidateLabel']) == key(column))
            require(abs(same/n*100-percent) <= .00501, 'Exact summary/aggregate share')
        summary.append({'partyLabel':r[0], 'totalPartyVotes':n, 'nonSplitCandidateVotes':same,
                        'reportedNonSplitPercent':float(r[3]), 'splitCandidateVotes':split,
                        'reportedSplitPercent':float(r[5]), 'isTotal':is_total})
    for field in ('totalPartyVotes','nonSplitCandidateVotes','splitCandidateVotes'):
        require(sum(r[field] for r in summary[:-1]) == summary[-1][field], 'Summary national sum: ' + field)
    require(summary[-1]['totalPartyVotes'] == aggregates['national']['rows'][-1]['totalPartyVotes'], 'Summary national denominator')
    return {'aggregateMatrices':aggregates, 'officialSplitSummary':{'sourceIds':[sid], 'rows':summary,
            'limitations':[f'Informal Party Votes non-split count is {next(r["nonSplitCandidateVotes"] for r in summary if r["partyLabel"] == "Informal Party Votes")} and matches the Party Vote Only column, not Candidate Informals. Retained as published; exclude this category from party-behaviour estimates. Exact aggregate summary counts do not provide exact electorate joint cells.']}}
