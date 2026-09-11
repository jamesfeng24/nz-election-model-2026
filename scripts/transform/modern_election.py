"""Offline modern-election adapter; deliberately separate from the legacy E9 pipeline."""
import argparse
import hashlib
import json
from pathlib import Path

from .historical import count, key, read_csv, require
from .modern_config import CONFIGS, election_config
from .modern_tables import candidate_table, check_percent, overall_table, party_table, percent, turnout_table, winners_table

ROOT = Path(__file__).resolve().parents[2]


class Sources:
    """Read only registered unchanged election bytes and retain consumed provenance."""

    def __init__(self, root, year=2017):
        self.config = election_config(year)
        self.root = root
        records = json.loads((root / 'data/sources.json').read_text())['sources']
        self.records = {}
        for record in records:
            if record['dateOrElection'] == f'{self.config.year} general election':
                name = Path(record['rawPath']).name
                require(name not in self.records, 'Ambiguous source basename')
                self.records[name] = record
        self.used = set()

    def __call__(self, name):
        record = self.records[name]
        data = (self.root / record['rawPath']).read_bytes()
        require(hashlib.sha256(data).hexdigest() == record['sha256'], 'Raw hash mismatch: ' + name)
        self.used.add(record['id'])
        return data, record['id']


def parse(source, name, parser):
    data, sid = source(name + '.csv')
    return parser(data), sid


def validate_party_percentages(data, party_rows):
    rows, _ = read_csv(data)
    labels = rows[1][1::2]
    seen = set()
    for row in rows[3:]:
        name = key(row[0])
        require(name in party_rows and name not in seen, 'Percentage electorate identity')
        seen.add(name)
        record = party_rows[name]
        require(count(row[-1]) == record['validVotes'], 'Percentage denominator')
        named = {p['partyName']: p['votes'] for p in record['parties']}
        explicit = set(labels) - {'Other', ''}
        for index, label in enumerate(labels):
            if not label:
                continue
            expected = sum(v for k, v in named.items() if k not in explicit) if label == 'Other' else named[label]
            require(count(row[1 + index * 2]) == expected, 'Published party count')
            check_percent(expected, record['validVotes'], percent(row[2 + index * 2]), label)
    require(seen == set(party_rows), 'Percentage coverage')


def make_electorate(entry, ballot, candidate_ballot, parties, winner, source, shared_ids, electorate_names):
    number = entry['sourceElectorateNumber']
    config = source.config
    eid = f'{config.election_id}-electorate-{number:02}'
    cancelled = (entry['electorateName'], number) in config.cancelled_contests
    candidates, sid = parse(source, Path(entry['url']).stem, lambda data: candidate_table(data, electorate_names, cancelled))
    require(candidates['sourceElectorateLabel'] == entry['electorateName'] + ' ' + str(number) + ('\n(Poll Cancelled)' if cancelled else ''), 'Official name/number mismatch')
    require(ballot['name'] == entry['electorateName'], 'Plan/turnout name mismatch')
    require(ballot['scope'] == ('general' if entry['role'] == 'general candidate' else 'maori'), 'Electorate classification')
    for field in (('enrolled', 'electoralPopulation') if cancelled else ('votesCast', 'enrolled', 'electoralPopulation', 'ordinaryDisallowed')):
        require(ballot[field] == candidate_ballot[field], 'Ballot shared control: ' + field)
    for field in ('validVotes', 'informalVotes'):
        require(parties[field] == ballot[field], 'Party ballot denominator')
        require(candidates[field] == candidate_ballot[field], 'Candidate ballot denominator')
    if cancelled:
        require(winner is None and candidates['winnerName'] is None and candidates['majority'] is None, 'Cancelled contest has official winner')
        require(candidate_ballot['validVotes'] == candidate_ballot['informalVotes'] == candidate_ballot['ordinaryDisallowed'] == 0, 'Cancelled ballot observations')
        require(candidate_ballot['votesCast'] == candidate_ballot['specialDisallowed'], 'Cancelled ballot disallowed controls')
        elected = []
    else:
        elected = [c for c in candidates['candidates'] if c['name'] == winner['candidateName']]
        require(len(elected) == 1 and elected[0]['party'] == winner['party'] and elected[0]['votes'] == winner['votes'], 'Official winner mismatch')
        require(candidates['winnerName'] == winner['candidateName'] and candidates['majority'] == winner['majority'], 'Official majority mismatch')
        check_percent(winner['votes'], candidates['validVotes'], winner['reportedPercent'], 'Winner valid share')
        check_percent(winner['votes'], candidate_ballot['votesCast'], candidate_ballot['reportedWinnerPercentOfVotesCast'], 'Winner turnout share')
    for index, candidate in enumerate(candidates['candidates'], 1):
        candidate.update(id=f'{eid}-candidate-{index:02}', nameMatchKey=key(candidate['name']), personId=None, partyKey=key(candidate['party']), elected=None if cancelled else candidate['name'] == winner['candidateName'])
    result = {'id': eid, 'electionId': config.election_id, 'year': config.year, 'sourceElectorateNumber': number,
            'name': ballot['name'], 'kind': ballot['scope'], 'boundaryVersionId': config.boundary_version_id,
            'validPartyVotes': ballot['validVotes'], 'validCandidateVotes': candidate_ballot['validVotes'],
            'partyBallot': ballot, 'candidateBallot': candidate_ballot, 'parties': parties['parties'],
            'candidates': candidates['candidates'], 'winnerCandidateId': None if cancelled else elected[0]['id'], 'majority': None if cancelled else winner['majority'],
            'sourceDisclosureNotes': candidates['sourceDisclosureNotes'], 'votingPlaceRowsValidated': candidates['votingPlaceRowsValidated'], 'sourceIds': sorted(shared_ids + [sid])}

    if config.cancelled_contests:
        result['candidateContestStatus'] = 'cancelled' if cancelled else 'held'
        if cancelled:
            result['sourceCandidateElectorateLabel'] = candidates['sourceElectorateLabel']
    return result


def validate_aggregates(electorates, party_controls, overall):
    all_parties = {p['partyKey']: p for p in overall['parties']}
    require(len(all_parties) == len(overall['parties']), 'Duplicate national affiliation')
    for scope, control in party_controls.items():
        selected = electorates if scope == 'national' else [e for e in electorates if e['kind'] == scope]
        for party in control['parties']:
            total = sum(p['votes'] for e in selected for p in e['parties'] if p['partyKey'] == party['partyKey'])
            require(total == party['votes'], 'Party geographic aggregate: ' + scope)
    for party_key, party in all_parties.items():
        party_records = [p for e in electorates for p in e['parties'] if p['partyKey'] == party_key]
        if party['partyVotes'] is None:
            require(not party_records, 'Unreported national party affiliation appears on ballot')
        else:
            require(sum(p['votes'] for p in party_records) == party['partyVotes'], 'National party total: ' + party['name'])
        candidates = [c for e in electorates for c in e['candidates'] if c['partyKey'] == party_key]
        require(sum(c['votes'] for c in candidates) == party['candidateVotes'], 'National candidate-party total: ' + party['name'])
        require(len(candidates) == party['candidateNominations'], 'National candidate nominations: ' + party['name'])
    require({c['partyKey'] for e in electorates for c in e['candidates']} <= set(all_parties), 'Unknown candidate affiliation')


def build_core(root, source=None, year=2017):
    source = source or Sources(root, year)
    config = source.config
    (ballots, party_totals), party_sid = parse(source, 'party-votes-and-turnout-by-electorate', turnout_table)
    (candidate_ballots, candidate_totals), candidate_sid = parse(source, 'candidate-votes-and-turnout-by-electorate', lambda data: turnout_table(data, tuple(name for name, _ in config.cancelled_contests)))
    parties, parties_sid = parse(source, 'votes-for-registered-parties-by-electorate', party_table)
    winners, winner_sid = parse(source, 'winning-electorate-candidates', winners_table)
    overall, overall_sid = parse(source, 'overall-results-summary', overall_table)
    percentage_data, percentage_sid = source('percentage-votes-for-registered-parties.csv')
    percentage_rows = {**parties['records'], **{key(r['name']): r for r in parties['totals'].values()}}
    validate_party_percentages(percentage_data, percentage_rows)
    plan = json.loads((root / config.source_plan).read_text())
    require(plan['year'] == config.year, 'Source plan election mismatch')
    entries = [e for e in plan['resources'] if e['role'] in ('general candidate', 'supporting Maori candidate')]
    require(len(entries) == config.total_electorates and len({e['sourceElectorateNumber'] for e in entries}) == config.total_electorates, 'Candidate plan coverage')
    by_name = {key(b['name']): b for b in ballots}
    candidates_by_name = {key(b['name']): b for b in candidate_ballots}
    require(set(by_name) == set(candidates_by_name) == set(parties['records']) == {key(e['electorateName']) for e in entries}, 'Electorate table coverage')
    require(set(winners) == set(by_name) - {key(name) for name, _ in config.cancelled_contests}, 'Official winner coverage')
    require(all(any(e['electorateName'] == name and e['sourceElectorateNumber'] == number for e in entries) for name, number in config.cancelled_contests), 'Cancellation configuration identity')
    shared_ids = [party_sid, candidate_sid, parties_sid, winner_sid, overall_sid, percentage_sid]
    electorates = [make_electorate(e, by_name[key(e['electorateName'])], candidates_by_name[key(e['electorateName'])], parties['records'][key(e['electorateName'])], winners.get(key(e['electorateName'])), source, shared_ids, [b['name'] for b in ballots]) for e in entries]
    require(sum(e['kind'] == 'general' for e in electorates) == config.general_electorates and sum(e['kind'] == 'maori' for e in electorates) == config.maori_electorates, 'General/Maori coverage')
    ids = [c['id'] for e in electorates for c in e['candidates']]
    require(len(set(ids)) == len(ids), 'Duplicate candidate occurrence')
    validate_aggregates(electorates, parties['totals'], overall)
    for ballot, totals in [('Party', party_totals), ('Candidate', candidate_totals)]:
        for kind, field in [('valid', 'validVotes'), ('informal', 'informalVotes')]:
            require(totals['national'][field] == overall[kind + ballot + 'Votes'], 'Overall ballot control')
    for p in overall['parties']:
        p['sourceId'] = overall_sid
    result = {'schemaVersion': 1, 'year': config.year, 'electorates': [e for e in electorates if e['kind'] == 'general'],
              'nationalControls': {'party': party_totals, 'candidate': candidate_totals, 'parties': overall['parties']},
              'sourceIds': sorted(source.used)}
    return result, electorates


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def build_year(root, year=2017):
    source = Sources(root, year)
    config = source.config
    election, electorates = build_core(root, source)
    from .modern_split import build_split
    split, details = build_split(source, electorates, election['nationalControls']['parties'], config)
    require(len(source.used) == config.source_files, 'Source inventory coverage')
    report = {'schemaVersion': 1, 'year': config.year, 'generalElectorates': config.general_electorates, 'supportingMaoriElectorates': config.maori_electorates,
              'candidateRecords': sum(len(e['candidates']) for e in election['electorates']),
              'partyVoteRecords': sum(len(e['parties']) for e in election['electorates']),
              'splitMatrices': len(split['matrices']), 'splitStatus': 'validated',
              'sourceFilesConsumed': len(source.used), 'discrepancies': [],
              'checks': ['official index name/number identity', 'all candidate voting-place rows and columns', 'party/candidate/turnout/valid/informal controls', 'official winner and majority', 'two-decimal source percentage reconciliation', 'national party and candidate-party totals and nominations', 'general/Maori/national control sums', 'unique election-local candidate IDs', 'consumed source checksums'] + details['checks'],
              'labelMappings': details['labelMappings'], 'limitations': ['Primary records cover general electorates only; Maori candidatures support national controls.', 'personId is null: no cross-election linking.', 'No boundary harmonization or fitted model.'] + details['limitations']}
    return {'elections': election, 'validation': report, 'split': split}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, choices=sorted(CONFIGS), default=2017)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build_year(ROOT, args.year)
    for kind, value in outputs.items():
        relative = f'data/processed/split-votes/{args.year}.json' if kind == 'split' else f'data/processed/elections/{args.year}{"-validation" if kind == "validation" else ""}.json'
        path = ROOT / relative
        if args.check:
            require(path.read_bytes() == encode(value), 'Stale processed output: ' + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encode(value))
    print(json.dumps(outputs['validation'], ensure_ascii=False))


if __name__ == '__main__':
    main()
