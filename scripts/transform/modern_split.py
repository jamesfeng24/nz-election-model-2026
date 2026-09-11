"""Modern split evidence: rounded local matrices and exact national summaries."""
from collections import defaultdict

from .historical import count, key, read_csv, require, split_rows
from .modern_config import election_config
from .modern_tables import percent


ROUNDING = .00501
OTHER = 'Independents & parties with no list candidates'


def checked_table(raw, sid, cancelled=False, unallocated=None):
    table = split_rows(raw)
    table['sourceIds'] = [sid]
    table['precision'] = {'representation': 'rounded-percentage', 'decimalPlaces': 2,
                          'percentageUnit': 'percent', 'exactJointCountsAvailable': False}
    rows = table['rows']
    require(rows and rows[-1]['partyLabel'] == 'Total Party Votes and Percentages', 'Missing split total row')
    require(len({key(r['partyLabel']) for r in rows}) == len(rows), 'Duplicate split row')
    labels = [c['candidateLabel'] for c in rows[0]['cells']]
    require(len(set(labels)) == len(labels), 'Duplicate split column')
    require(sum(r['totalPartyVotes'] for r in rows[:-1]) == rows[-1]['totalPartyVotes'], 'Split row sum')
    for row in rows:
        values = [c['reportedPercent'] for c in row['cells']]
        if row['totalPartyVotes']:
            require(all(v is not None for v in values), 'Missing nonzero split percentage')
            missing = (unallocated or {}).get(key(row['partyLabel']), 0)
            require(0 <= missing <= row['totalPartyVotes'], 'Cancelled split allocation bound')
            expected = 0 if cancelled else 100 * (1 - missing / row['totalPartyVotes'])
            require(row['reportedTotalPercent'] == (0 if cancelled else 100), 'Split reported row total')
            require(abs(sum(values)-expected) <= len(values)*.005+1e-8, 'Split row rounding')
        if cancelled:
            require(row['reportedTotalPercent'] == 0 and all(v == 0 for v in values), 'Cancelled split publication must contain zero percentages')
    return table


def check_column(table, index, observed):
    require(observed >= 0, 'Negative split column control')
    total = table['rows'][-1]['totalPartyVotes']
    reported = table['rows'][-1]['cells'][index]['reportedPercent']
    require(reported is not None and abs(observed/total*100-reported) <= ROUNDING, 'Split overall column share')
    midpoint = sum(r['totalPartyVotes']*(r['cells'][index]['reportedPercent'] or 0)/100 for r in table['rows'][:-1])
    require(abs(midpoint-observed) <= total*.00005+1e-8, 'Split weighted column rounding')


def local_matrix(source, electorate):
    number = electorate['sourceElectorateNumber']
    raw, sid = source(f'split-votes-electorate-{number}.csv')
    cancelled = electorate.get('candidateContestStatus', 'held') == 'cancelled'
    expected_cancelled = (electorate['name'], number) in election_config(electorate['year']).cancelled_contests
    require(cancelled == expected_cancelled, 'Unexpected split cancellation status')
    table = checked_table(raw, sid, cancelled=cancelled)
    label = f"{number:02d} {electorate['name']}" + ('\n(Poll Cancelled)' if cancelled else '')
    require(table['sourceElectorateLabel'] == label, 'Split electorate identity')
    parties = {p['partyKey']: p['votes'] for p in electorate['parties']}
    parties['informalpartyvotes'] = electorate['partyBallot']['informalVotes']
    require({key(r['partyLabel']) for r in table['rows'][:-1]} == set(parties), 'Split party coverage')
    def label_key(label):
        return ' '.join(label.split()).replace(' )', ')')
    candidates = {label_key(f"{c['name']} ({c['party']})"): c for c in electorate['candidates']}
    require(len(candidates) == len(electorate['candidates']), 'Ambiguous candidate split mapping')
    total = sum(parties.values())
    require(table['rows'][-1]['totalPartyVotes'] == total, 'Local split denominator')
    controls = {'Informal Candidate Votes': electorate['candidateBallot']['informalVotes'],
                'Party Vote Only': total-electorate['validCandidateVotes']-electorate['candidateBallot']['informalVotes']}
    source_labels = [c['candidateLabel'] for c in table['rows'][0]['cells']]
    labels = {label_key(label) for label in source_labels}
    require(len(labels) == len(source_labels), 'Ambiguous whitespace-normalized split label')
    require(labels == set(candidates) | set(controls), 'Candidate/source mapping missing or ambiguous: '+electorate['name'])
    for row in table['rows']:
        if row is not table['rows'][-1]:
            require(row['totalPartyVotes'] == parties[key(row['partyLabel'])], 'Local split party count')
        for cell in row['cells']:
            candidate = candidates.get(label_key(cell['candidateLabel']))
            cell['candidateId'] = candidate['id'] if candidate else None
            cell['category'] = 'candidate' if candidate else ('informal' if cell['candidateLabel'] == 'Informal Candidate Votes' else 'party-vote-only')
    for index, cell in enumerate(table['rows'][-1]['cells']):
        label = label_key(cell['candidateLabel'])
        check_column(table, index, 0 if cancelled else (candidates[label]['votes'] if label in candidates else controls[label]))
    mappings = [{'sourceLabel': label, 'candidateId': candidates[label_key(label)]['id'],
                 'basis': 'Whitespace-only within-election source-label reconciliation'}
                for label in source_labels if label_key(label) in candidates and label != label_key(label)]
    if mappings:
        table['sourceLabelMappings'] = mappings
    if cancelled:
        require(electorate['validCandidateVotes'] == 0 and all(c['votes'] == 0 for c in electorate['candidates']), 'Cancelled candidate source counts')
        table.update(candidateContestStatus='cancelled', behaviouralEvidence=False,
                     unallocatedPartyVotes=total,
                     limitation='Published zero destination percentages describe a cancelled poll, not observed candidate or party-vote-only behaviour.')
    return {'schemaVersion': 1, 'id': electorate['id']+'-split', 'electorateId': electorate['id'], 'year': electorate['year'], **table}


def aggregate_matrix(source, electorates, scope, config=None):
    config = config or election_config(2017)
    affiliation = {key(a): key(b) for a, b in config.aggregate_affiliations}
    raw, sid = source('split-votes-'+('all' if scope == 'national' else scope)+'.csv')
    selected = [e for e in electorates if scope == 'national' or e['kind'] == scope]
    unallocated = defaultdict(int)
    for electorate in selected:
        if electorate.get('candidateContestStatus', 'held') == 'cancelled':
            for party_row in electorate['parties']:
                unallocated[party_row['partyKey']] += party_row['votes']
            unallocated['informalpartyvotes'] += electorate['partyBallot']['informalVotes']
    excluded = sum(unallocated.values())
    unallocated[key('Total Party Votes and Percentages')] = excluded
    table = checked_table(raw, sid, unallocated=unallocated)
    if excluded:
        table['cancelledContestAllocation'] = {
            'partyVotesIncludedInPublishedDenominator': excluded,
            'candidateDestinationAllocationAvailable': False,
            'bySourcePartyKey': dict(unallocated),
            'limitation': 'Published denominators include the cancelled contest, but destination percentages allocate no votes from that contest. This is not ordinary split behaviour.'}
    party, candidate = defaultdict(int), defaultdict(int)
    for electorate in selected:
        for p in electorate['parties']:
            party[p['partyKey']] += p['votes']
        for c in electorate['candidates']:
            candidate[affiliation.get(c['partyKey'], c['partyKey'])] += c['votes']
    informal = sum(e['partyBallot']['informalVotes'] for e in selected)
    total = sum(party.values())+informal
    require(table['rows'][-1]['totalPartyVotes'] == total, 'Aggregate split denominator '+scope)
    require({key(r['partyLabel']) for r in table['rows'][:-1]} == set(party)|{'informalpartyvotes'}, 'Aggregate party coverage')
    for row in table['rows'][:-1]:
        require(row['totalPartyVotes'] == (informal if key(row['partyLabel']) == 'informalpartyvotes' else party[key(row['partyLabel'])]), 'Aggregate party count')
    controls = dict(candidate)
    controls[key(OTHER)] = sum(v for k, v in candidate.items() if k not in party)
    controls['candidateinformals'] = sum(e['candidateBallot']['informalVotes'] for e in selected)
    controls['partyvoteonly'] = total-sum(candidate.values())-controls['candidateinformals']-excluded
    require({key(c['candidateLabel']) for c in table['rows'][-1]['cells']} == set(party)|{key(OTHER),'candidateinformals','partyvoteonly'}, 'Aggregate candidate coverage')
    for index, cell in enumerate(table['rows'][-1]['cells']):
        check_column(table, index, controls.get(key(cell['candidateLabel']), 0))
    return table


def check_local_aggregate(matrices, general, aggregate, config=None):
    affiliation = {key(a): key(b) for a, b in config.aggregate_affiliations} if config else {}
    candidates = {c['id']: c for e in general for c in e['candidates']}
    listed = {p['partyKey'] for p in general[0]['parties']}
    intervals = defaultdict(lambda: [0.0, 0.0])
    for matrix in matrices:
        if matrix.get('behaviouralEvidence') is False:
            continue
        for row in matrix['rows'][:-1]:
            party = 'informalpartyvotes' if row['partyLabel'] == 'Informal Party Votes' else key(row['partyLabel'])
            for cell in row['cells']:
                if cell['category'] == 'candidate':
                    destination = candidates[cell['candidateId']]['partyKey']
                    destination = affiliation.get(destination, destination)
                    if destination not in listed:
                        destination = key(OTHER)
                else:
                    destination = 'candidateinformals' if cell['category'] == 'informal' else 'partyvoteonly'
                intervals[party, destination][0] += row['totalPartyVotes']*(cell['reportedPercent'] or 0)/100
                intervals[party, destination][1] += row['totalPartyVotes']*.00005
    for row in aggregate['rows'][:-1]:
        for cell in row['cells']:
            midpoint, bound = intervals[key(row['partyLabel']), key(cell['candidateLabel'])]
            require(abs(midpoint-row['totalPartyVotes']*cell['reportedPercent']/100) <= bound+row['totalPartyVotes']*.00005+1e-8, 'Local/aggregate split interval')


def check_aggregate_scopes(aggregates):
    """General and Māori rounded cells must sum to the national interval."""
    scopes = {scope: {r['partyLabel']: r for r in table['rows']} for scope, table in aggregates.items()}
    for label, national in scopes['national'].items():
        components = [scopes[scope][label] for scope in ('general', 'maori')]
        require(sum(r['totalPartyVotes'] for r in components) == national['totalPartyVotes'], 'Aggregate scope row count')
        for index, cell in enumerate(national['cells']):
            midpoint = sum(r['totalPartyVotes'] * (r['cells'][index]['reportedPercent'] or 0) / 100 for r in components)
            target = national['totalPartyVotes'] * (cell['reportedPercent'] or 0) / 100
            require(abs(midpoint - target) <= national['totalPartyVotes'] * .0001 + 1e-8, 'Aggregate scope interval')


def split_summary(source, aggregate):
    raw, sid = source('split-votes-summary.csv')
    rows, _ = read_csv(raw)
    require(rows[1][:3] == ['Party', 'Total Party Votes', 'Non Split Candidate Votes'], 'Split summary header')
    controls = {key(r['partyLabel']): r for r in aggregate['rows']}
    result = []
    for row in rows[3:]:
        n, same, split = count(row[1]), count(row[2]), count(row[4])
        a, b = percent(row[3]), percent(row[5])
        require(same+split == n and n > 0, 'Exact split summary count sum')
        require(abs(same/n*100-a) <= ROUNDING and abs(split/n*100-b) <= ROUNDING, 'Exact split summary percentage')
        is_total = row[0] == 'Total Party Votes and Percentages'
        if not is_total:
            informal = row[0] == 'Informal Party Votes'
            control = controls['informalpartyvotes' if informal else key(row[0])]
            require(control['totalPartyVotes'] == n, 'Split summary row control')
            label = 'Party Vote Only' if informal else row[0]
            cells = [c for c in control['cells'] if key(c['candidateLabel']) == key(label)]
            require(len(cells) == 1 and abs(same/n*100-cells[0]['reportedPercent']) <= ROUNDING, 'Exact summary/aggregate split agreement')
        result.append({'partyLabel': row[0], 'totalPartyVotes': n, 'nonSplitCandidateVotes': same,
                       'reportedNonSplitPercent': a, 'splitCandidateVotes': split, 'reportedSplitPercent': b, 'isTotal': is_total})
    require(result[-1]['isTotal'] and sum(r['isTotal'] for r in result) == 1, 'Summary total row')
    for field in ('totalPartyVotes', 'nonSplitCandidateVotes', 'splitCandidateVotes'):
        require(sum(r[field] for r in result[:-1]) == result[-1][field], 'Summary national sum')
    require(result[-1]['totalPartyVotes'] == aggregate['rows'][-1]['totalPartyVotes'], 'Summary national denominator')
    return {'sourceIds': [sid], 'rows': result, 'limitations': ['Informal Party Votes non-split count matches Party Vote Only, not Candidate Informals; preserve the published convention and exclude it from party-behaviour estimates. Exact national summary counts do not supply exact local joint cells.']}


def build_split(source, all_electorates, national_parties, config=None):
    """Build complete evidence from checksum-verified source callbacks."""
    config = config or election_config(2017)
    require(all(e['year'] == config.year for e in all_electorates), 'Mixed election split inputs')
    general = [e for e in all_electorates if e['kind'] == 'general']
    require(len(general) == config.general_electorates and len(all_electorates) == config.total_electorates, f'{config.year} split electorate coverage')
    matrices = [local_matrix(source, e) for e in general]
    aggregates = {scope: aggregate_matrix(source, all_electorates, scope, config) for scope in ('general', 'maori', 'national')}
    check_local_aggregate(matrices, general, aggregates['general'], config)
    check_aggregate_scopes(aggregates)
    summary = split_summary(source, aggregates['national'])
    if config.cancelled_contests:
        summary['cancelledContestConvention'] = {
            'partyVotesIncludedInPublishedDenominator': aggregates['national']['cancelledContestAllocation']['partyVotesIncludedInPublishedDenominator'],
            'limitation': 'The exact published split residual includes party votes from the cancelled candidate contest. Preserve these official counts; they are not wholly behavioural split counts and do not identify local joint cells.'}
        summary['limitations'].append(summary['cancelledContestConvention']['limitation'])
    supporting = [local_matrix(source, e) for e in all_electorates if e['sourceElectorateNumber'] in config.supporting_split_numbers]
    require(len(supporting) == len(config.supporting_split_numbers), 'Supporting split coverage')
    extra = {}
    if supporting:
        extra['supportingMatrices'] = supporting
    if config.aggregate_affiliations:
        extra['aggregateAffiliationMappings'] = [
            {'sourceAffiliation': a, 'aggregateSplitColumn': b,
             'scope': 'aggregate split controls only',
             'basis': 'Inferred reporting grouping: official candidate and local split labels remain unchanged; aggregate column controls reconcile only with this grouping.',
             'sourceIds': sorted({sid for m in supporting + list(aggregates.values()) for sid in m['sourceIds']})}
            for a, b in config.aggregate_affiliations]

    return ({'schemaVersion': 1, 'year': config.year, 'matrices': matrices, 'aggregateMatrices': aggregates, 'officialSplitSummary': summary, **extra},
            {'checks': ['Local split rows, columns and rounded intervals', 'General/Māori/national split controls', 'Local/general aggregate interval agreement', 'Exact national split summary'],
             'labelMappings': [], 'limitations': ['Local and aggregate matrix percentages are rounded to two decimal places; exact joint cell counts remain null.', *summary['limitations'], *(['Aggregate splits group NZ Public Party under Advance NZ, inferred from reconciled column controls; candidate affiliations and supporting Te Tai Tokerau local labels remain NZ Public Party. This is not party continuity evidence.'] if config.supporting_split_numbers else ['Aggregate candidate-affiliation grouping is recorded explicitly; published candidate and local split labels remain unchanged. This is not party continuity evidence.'] if config.aggregate_affiliations else [])]})
