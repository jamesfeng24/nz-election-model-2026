"""Deterministic historical parsing. No regression or forecast code."""
from __future__ import annotations
import csv
import io
from decimal import Decimal
import re
import unicodedata


def text(value: str) -> str:
    return unicodedata.normalize('NFC', value.strip())


def read_csv(data: bytes) -> tuple[list[list[str]], str]:
    try:
        decoded = data.decode('utf-8-sig')
        encoding = 'utf-8-sig'
    except UnicodeDecodeError:
        decoded = data.decode('cp1252')
        encoding = 'cp1252'
    return [[text(cell) for cell in row] for row in csv.reader(io.StringIO(decoded)) if any(cell.strip() for cell in row)], encoding


def count(value: str) -> int:
    cleaned = value.strip().replace(',', '')
    if not re.fullmatch(r'\d+', cleaned):
        raise ValueError('Missing or invalid count: ' + repr(value))
    return int(cleaned)


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def split_rows(data: bytes) -> dict:
    rows, encoding = read_csv(data)
    header = rows[0]
    if header[1] != 'Total Party Votes' or header[-1] != 'Total %':
        raise ValueError('Unrecognized split-vote header')
    parsed = []
    for row in rows[1:]:
        if len(row) != len(header):
            raise ValueError('Ragged split-vote row')
        cells = []
        for category, value in zip(header[2:-1], row[2:-1]):
            percent = None if not value else Decimal(value)
            if percent is not None and not 0 <= percent <= 100:
                raise ValueError('Invalid split percentage')
            cells.append({'candidateLabel': category, 'count': None, 'reportedPercent': None if percent is None else float(percent)})
        parsed.append({'partyLabel': row[0], 'totalPartyVotes': count(row[1]), 'cells': cells,
                       'reportedTotalPercent': None if not row[-1] else float(Decimal(row[-1]))})
    return {'sourceElectorateLabel': header[0], 'sourceEncoding': encoding, 'rows': parsed,
            'countAvailability': 'unavailable: source publishes rounded percentages, not joint counts'}

# Source-label keys are for joins only. Original Unicode labels are always retained.
def key(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in unicodedata.normalize('NFKD', value).casefold() if not unicodedata.combining(c)))


def split_party_key(party_key: str, year: int) -> str:
    """Official 2014 split reports group these candidatures under Internet MANA.

    Candidate records and national candidate totals retain the actual affiliations.
    This is a publication grouping, not cross-election party continuity.
    """
    if year == 2014 and party_key in ('internetparty', 'manamovement'):
        return 'internetmana'
    return party_key


def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def candidate_table(data: bytes) -> dict:
    rows, encoding = read_csv(data)
    start = next(i for i, r in enumerate(rows) if r[0] == 'Electorate Candidate Valid Votes')
    summary = rows[start]
    winner_text = next(cell for cell in summary if ' - majority ' in cell)
    winner, majority = winner_text.rsplit(' - majority ', 1)
    candidates = []
    for r in rows[start + 1:]:
        require(len(r) >= 4, 'Candidate summary row missing fields')
        candidates.append({'name': r[0], 'party': r[1], 'votes': count(r[2]),
                           'sourceShare': None if not r[3] else float(Decimal(r[3]))})
    total = sum(c['votes'] for c in candidates)
    # Independent control: polling-place table's explicit final totals row.
    totals = next(r for r in rows[:start] if len(r) > 4 and r[1].endswith(' Total'))
    require(count(totals[-2]) == total, 'Candidate footer does not reconcile with polling-place total')
    for c in candidates:
        c['share'] = ratio(c['votes'], total)
    return {'sourceElectorateLabel': rows[1][0], 'candidates': candidates, 'validVotes': total,
            'informalVotes': count(totals[-1]), 'winnerName': winner, 'majority': count(majority), 'sourceEncoding': encoding}


def turnout_table(data: bytes) -> tuple[list[dict], dict]:
    rows, _ = read_csv(data)
    start = next(i for i, row in enumerate(rows) if row[0] == 'Electoral District') + 2
    result = []
    totals = {}
    scope = 'general'
    for r in rows[start:]:
        if len(r) < 13:
            continue
        record = {'name': r[0], 'scope': scope, 'ordinaryValid': count(r[1]), 'specialValid': count(r[2]),
                  'validVotes': count(r[3]), 'ordinaryInformal': count(r[4]), 'specialInformal': count(r[5]),
                  'informalVotes': count(r[6]), 'ordinaryDisallowed': count(r[7]), 'specialDisallowed': count(r[8]),
                  'votesCast': count(r[9]), 'enrolled': count(r[10]), 'electoralPopulation': count(r[11]),
                  'reportedTurnoutPercent': float(Decimal(r[12]))}
        require(record['ordinaryValid'] + record['specialValid'] == record['validVotes'], 'Valid vote components: ' + r[0])
        require(record['ordinaryInformal'] + record['specialInformal'] == record['informalVotes'], 'Informal components: ' + r[0])
        require(sum(record[k] for k in ('validVotes', 'informalVotes', 'ordinaryDisallowed', 'specialDisallowed')) == record['votesCast'], 'Votes cast components: ' + r[0])
        require(abs(record['votesCast'] / record['enrolled'] * 100 - record['reportedTurnoutPercent']) < 0.00001, 'Turnout percentage: ' + r[0])
        if 'Totals' in r[0]:
            totals[scope if r[0] != 'Combined Totals' else 'national'] = record
            scope = 'maori'
        else:
            result.append(record)
    return result, totals


def build_year(root, year: int) -> dict:
    import hashlib
    import json
    from pathlib import Path
    sources = json.loads((root / 'data/sources.json').read_text())['sources']
    by_path = {Path(s['rawPath']).relative_to(root_relative).as_posix(): s
               for s in sources if (root_relative := Path('data/raw/elections') / str(year)) in Path(s['rawPath']).parents}
    used = set()

    def source(name):
        record = by_path[name]
        data = (root / record['rawPath']).read_bytes()
        require(hashlib.sha256(data).hexdigest() == record['sha256'], 'Raw hash mismatch: ' + name)
        used.add(record['id'])
        return data, record['id']

    def rows(name):
        data, sid = source('e9/csv/' + name)
        return read_csv(data)[0], sid

    pv, party_sid = source('e9/csv/e9_part9_1.csv')
    cv, candidate_sid = source('e9/csv/e9_part9_2.csv')
    turnout, turnout_totals = turnout_table(pv)
    cand_turnout, cand_totals = turnout_table(cv)
    controls_by_name = {key(r['name']): r for r in cand_turnout}
    overall, overall_sid = rows('e9_part1.csv')
    national_rows = [r for r in overall if len(r) >= 9 and r[1].isdigit() and r[6].isdigit()]
    national_parties = {key(r[0]): {'name': r[0], 'partyVotes': count(r[2]) if r[2] else None,
                                  'candidateVotes': count(r[6]), 'sourceId': overall_sid} for r in national_rows}
    party_rows, party_detail_sid = rows('e9_part4.csv')
    party_header = party_rows[1]
    valid_index = next(i for i, name in enumerate(party_header) if name == 'Total Valid Party Votes')
    party_cols = []
    mappings = []
    for i, label in enumerate(party_header[1:valid_index], 1):
        matched = [p for k, p in national_parties.items() if k == key(label)]
        if not matched:
            matched = [p for k, p in national_parties.items() if k.startswith(key(label))]
        require(len(matched) == 1, 'Ambiguous party header: ' + label)
        party_cols.append((i, matched[0]['name']))
        if key(label) != key(matched[0]['name']):
            mappings.append({'sourceLabel': label, 'matchedLabel': matched[0]['name'], 'reason': 'unique truncated-header prefix in official national summary'})
    party_by_name = {key(r[0]): r for r in party_rows[3:] if len(r) > valid_index}
    winners, winner_sid = rows('e9_part6.csv')
    winners_by_name = {key(r[0]): r for r in winners[2:] if len(r) >= 6}
    percentage_rows, percentage_sid = rows('e9_part5.csv')
    percentage_by_name = {key(r[0]): r for r in percentage_rows[3:] if len(r) > 4}
    percentage_header = percentage_rows[1]
    all_electorates = []
    matrices = []
    discrepancies = []
    candidate_aggregates = {}
    party_aggregates = {}
    for number, turnout_record in enumerate(turnout, 1):
        name = turnout_record['name']
        name_key = key(name)
        other = controls_by_name[name_key]
        require(other['votesCast'] == turnout_record['votesCast'], 'Party/candidate votes cast differ: ' + name)
        raw_candidates, cand_source = source(f'e9/csv/e9_part8_cand_{number}.csv')
        candidate = candidate_table(raw_candidates)
        require(key(re.sub(r'\s+\d+$', '', candidate['sourceElectorateLabel'])) == name_key, 'Electorate number/name mismatch')
        require(candidate['validVotes'] == other['validVotes'] and candidate['informalVotes'] == other['informalVotes'], 'Candidate electorate totals: ' + name)
        winner = winners_by_name[name_key]
        highest = max(c['votes'] for c in candidate['candidates'])
        official = next(c for c in candidate['candidates'] if key(c['name']) == key(winner[1]))
        require(highest == count(winner[3]) == official['votes'], 'Official winner: ' + name)
        require(key(candidate['winnerName']) == key(winner[1]), 'Conflicting official winner names: ' + name)
        ordered = sorted((c['votes'] for c in candidate['candidates']), reverse=True)
        require(ordered[0] - ordered[1] == count(winner[4]) == candidate['majority'], 'Winner majority: ' + name)
        require(abs(highest / candidate['validVotes'] * 100 - float(winner[5].rstrip('%'))) <= .00501, 'Winner share: ' + name)
        election_id = f'nz-general-{year}'
        electorate_id = f'{election_id}-electorate-{number:02d}'
        for index, c in enumerate(candidate['candidates'], 1):
            c['id'] = f'{electorate_id}-candidate-{index:02d}'
            c['nameMatchKey'] = key(c['name'])
            c['personId'] = None  # Linking is deferred; full-name keys are not identity proof.
            c['partyKey'] = key(c['party'])
            c['elected'] = c is official
            if c['sourceShare'] is not None:
                require(abs(c['share'] - c['sourceShare']) <= 1.1e-9, 'Candidate reported share: ' + c['name'])
            candidate_aggregates[c['partyKey']] = candidate_aggregates.get(c['partyKey'], 0) + c['votes']
        party_row = party_by_name[name_key]
        valid_party = turnout_record['validVotes']
        require(count(party_row[valid_index]) == valid_party and count(party_row[valid_index + 1]) == turnout_record['informalVotes'], 'Party electorate totals: ' + name)
        parties = []
        for col, party_name in party_cols:
            votes = count(party_row[col])
            pk = key(party_name)
            parties.append({'partyKey': pk, 'partyName': party_name, 'sourceHeader': party_header[col], 'votes': votes, 'share': ratio(votes, valid_party)})
            party_aggregates[pk] = party_aggregates.get(pk, 0) + votes
        require(sum(p['votes'] for p in parties) == valid_party, 'Party sum: ' + name)
        require(abs(sum(p['share'] for p in parties) - 1) < 1e-12, 'Party normalization: ' + name)
        require(abs(sum(c['share'] for c in candidate['candidates']) - 1) < 1e-12, 'Candidate normalization: ' + name)
        pr = percentage_by_name[name_key]
        require(count(pr[-1]) == valid_party, 'Published percentage table total: ' + name)
        for i in range(1, len(pr) - 1, 2):
            require(abs(count(pr[i]) / valid_party * 100 - float(pr[i+1])) <= .00501, 'Published party percentage: ' + name)
        record = {'id': electorate_id, 'electionId': election_id, 'year': year, 'sourceElectorateNumber': number,
                  'name': name, 'kind': turnout_record['scope'], 'boundaryVersionId': f'historical-election-{year}-as-published',
                  'validPartyVotes': valid_party, 'validCandidateVotes': candidate['validVotes'],
                  'partyBallot': turnout_record, 'candidateBallot': other, 'parties': parties, 'candidates': candidate['candidates'],
                  'winnerCandidateId': official['id'], 'majority': candidate['majority'],
                  'sourceIds': [party_sid, candidate_sid, party_detail_sid, cand_source, winner_sid, percentage_sid, overall_sid]}
        all_electorates.append(record)
        if record['kind'] != 'general':
            continue
        split_data, split_sid = source(f'elect-splitvote-{number}.csv')
        split = split_rows(split_data)
        matrix = {'schemaVersion': 1, 'id': electorate_id + '-split', 'electorateId': electorate_id,
                  'year': year, 'sourceIds': [split_sid], **split}
        # Match split candidate display names by surname + party within this electorate only.
        # Nicknames differ from full legal names; never carry this rule across elections.
        for row in matrix['rows']:
            is_total = row['partyLabel'] == 'Total Party Votes and Percentages'
            pk = key(row['partyLabel'])
            if not is_total:
                target = turnout_record['informalVotes'] if pk == 'informalpartyvotes' else next(p['votes'] for p in parties if p['partyKey'] == pk)
                require(target == row['totalPartyVotes'], 'Split party row total: ' + name + ' / ' + row['partyLabel'])
            for cell in row['cells']:
                label = cell['candidateLabel']
                if label in ('Informal Candidate Votes', 'Party Vote Only'):
                    cell['candidateId'] = None
                    cell['category'] = 'informal' if label.startswith('Informal') else 'party-vote-only'
                else:
                    match = re.fullmatch(r'(.*) \((.*)\)', label)
                    require(match is not None, 'Unrecognized candidate label: ' + label)
                    short_name, party = match.groups()
                    matches = [c for c in candidate['candidates'] if key(c['name'].split(',')[0]) == key(short_name.split(',')[0]) and split_party_key(c['partyKey'], year) == key(party)]
                    aliases = {
                        (2011, 'Bay of Plenty', 'STEVENS, Sharon (Mana)'): 'TIPENE, Tangi Sharon',
                        (2011, 'Dunedin North', 'TUREI, Metiria (Green Party)'): 'STANTON TUREI, Metiria Leanne Agnes',
                        (2011, 'Hamilton East', 'ORGAD, Sehai (Labour Party)'): 'SCHOENBERGER-ORGAD, Sehai',
                        (2011, 'Manukau East', 'TAYLOR, Asenati (New Zealand First Party)'): 'LOLE-TAYLOR, Asenati',
                        (2011, 'Maungakiekie', 'HO, Jerry (New Zealand First Party)'): 'HE, Xiao Peng',
                        (2011, 'New Lynn', 'DAVIDSON, Sean (Aotearoa Legalise Cannabis Party)'): 'DAVIDSON-NORRIS, Sean Benjamin',
                        (2011, 'Pakuranga', 'MULFORD, Helen Jane (New Zealand First Party)'): 'MULFORD-TYLER, Helen Jane',
                        (2011, 'Wellington Central', 'KARENA, Puhi (Independent)'): 'FUIMAONO-KARENA, Geoffrey Wayne Puhi',
                        (2008, 'Dunedin North', 'TUREI, Metiria (Green Party)'): 'STANTON TUREI, Metiria Leanne Agnes',
                        (2008, 'Hunua', 'KENWORTHY (SHAW), Fiona (Green Party)'): 'KENWORTHY, Fiona Marie',
                        (2008, 'Hunua', 'MULFORD, Helen (New Zealand First Party)'): 'MULFORD - TYLER, Helen Jane',
                        (2008, 'Maungakiekie', 'PARATENE, Rawiri (Green Party)'): 'BROUGHTON, David Peter',
                        (2008, 'Ohariu', 'STRYPE, Danyl (Aotearoa Legalise Cannabis Party)'): 'BRUCE, Daniel Antonio',
                        (2008, 'Selwyn', 'NORMAN, Victoria (United Future)'): 'ROGERS, Victoria Jane',
                        (2008, 'Waitakere', 'MISA TUPOU, Fia (New Zealand Pacific Party)'): 'TURNER-TUPOU, Fia Taemanu',
                    }
                    alias = aliases.get((year, name, label))
                    if not matches and alias:
                        matches = [c for c in candidate['candidates'] if c['name'] == alias and split_party_key(c['partyKey'], year) == key(party)]
                        mapping = {'electorate': name, 'sourceLabel': label, 'matchedLabel': alias, 'reason': 'same-electorate source name variant; unique party candidate and overall vote share reconcile; not a cross-election person identity'}
                        if mapping not in mappings:
                            mappings.append(mapping)
                    require(len(matches) == 1, 'Ambiguous local candidate match: ' + name + '/' + label)
                    cell['candidateId'] = matches[0]['id']
                    cell['category'] = 'candidate'
            values = [c['reportedPercent'] for c in row['cells']]
            if row['totalPartyVotes'] > 0:
                require(all(v is not None for v in values), 'Missing percentage on nonzero split row')
                require(abs(sum(values) - 100) <= len(values)*.005 + 1e-8, 'Split percentages do not reconcile within rounding: ' + name)
            # Source overall column shares are rounded; use bounded comparison, never inferred counts.
        totals_row = matrix['rows'][-1]
        denominator = valid_party + turnout_record['informalVotes']
        require(totals_row['totalPartyVotes'] == denominator, 'Split total denominator: ' + name)
        require(sum(r['totalPartyVotes'] for r in matrix['rows'][:-1]) == denominator, 'Split row count sum: ' + name)
        for j, cell in enumerate(totals_row['cells']):
            if cell['category'] == 'candidate':
                observed = next(c['votes'] for c in candidate['candidates'] if c['id'] == cell['candidateId'])
            elif cell['category'] == 'informal':
                observed = candidate['informalVotes']
            else:
                observed = denominator - candidate['validVotes'] - candidate['informalVotes']
            midpoint = sum(r['totalPartyVotes'] * (r['cells'][j]['reportedPercent'] or 0) / 100 for r in matrix['rows'][:-1])
            tolerance = sum(r['totalPartyVotes'] * .00005 for r in matrix['rows'][:-1]) + 1e-8
            if abs(midpoint - observed) > tolerance:
                discrepancies.append({'code': 'split-column-outside-rounding', 'electorate': name, 'column': cell['candidateLabel'], 'officialCount': observed, 'percentageImpliedMidpoint': midpoint, 'roundingBound': tolerance})
            require(abs(observed / denominator * 100 - cell['reportedPercent']) <= .00501, 'Split overall column share: ' + name)
        matrices.append(matrix)
    for field in ('validVotes', 'informalVotes', 'votesCast', 'enrolled'):
        require(sum(r['partyBallot'][field] for r in all_electorates) == turnout_totals['national'][field], 'National party control: ' + field)
        require(sum(r['candidateBallot'][field] for r in all_electorates) == cand_totals['national'][field], 'National candidate control: ' + field)
        for scope in ('general', 'maori'):
            require(sum(r['partyBallot'][field] for r in all_electorates if r['kind'] == scope) == turnout_totals[scope][field], scope + ' party control: ' + field)
            require(sum(r['candidateBallot'][field] for r in all_electorates if r['kind'] == scope) == cand_totals[scope][field], scope + ' candidate control: ' + field)
    for pk, total in party_aggregates.items():
        require(total == national_parties[pk]['partyVotes'], 'National party aggregate: ' + pk)
    for pk, p in national_parties.items():
        require(candidate_aggregates.get(pk, 0) == p['candidateVotes'], 'National candidate-party aggregate: ' + pk)
    require(not (set(candidate_aggregates) - set(national_parties)), 'Unknown national candidate party')
    general = [r for r in all_electorates if r['kind'] == 'general']
    report = {'schemaVersion': 1, 'year': year, 'generalElectorates': len(general), 'supportingMaoriElectorates': len(all_electorates)-len(general),
              'candidateRecords': sum(len(r['candidates']) for r in general), 'partyVoteRecords': sum(len(r['parties']) for r in general),
              'splitMatrices': len(matrices), 'nationalPartyValidVotes': turnout_totals['national']['validVotes'],
              'nationalCandidateValidVotes': cand_totals['national']['validVotes'], 'nationalVotesCast': turnout_totals['national']['votesCast'],
              'labelMappings': mappings, 'discrepancies': discrepancies,
              'checks': ['nonnegative integer counts', 'vote/share normalization', 'official winners and majorities', 'turnout components and rates', 'electorate/general/Maori/national totals', 'national party and candidate-party aggregates', 'split row counts and rounding-bounded percentages/columns'],
              'limitations': ['Split cells publish rounded percentages only; exact counts remain null.', 'Candidate person IDs are not asserted; full names, parties and comparison keys support later reviewed linking.', 'Electorate names retain CSV spelling; missing macrons in a source are not invented.', 'Māori candidate files are supporting inputs for national reconciliation; primary outputs cover general electorates.']}
    extra_split = {}
    if year == 2011:
        from .historical_2011 import validate_2011
        extra_split = validate_2011(source, all_electorates, matrices)
        report['checks'].extend(['2011 unique electorate/candidate IDs and complete split coverage', '2011 aggregate split matrices and exact summary controls', '2011 local-to-general aggregate split intervals'])
        report['sourcePeculiarities'] = extra_split['officialSplitSummary']['limitations']
    return {'elections': {'schemaVersion': 1, 'year': year, 'electorates': general, 'nationalControls': {'party': turnout_totals, 'candidate': cand_totals, 'parties': list(national_parties.values())}, 'sourceIds': sorted(used)},
            'split': {'schemaVersion': 1, 'year': year, 'matrices': matrices, **extra_split}, 'validation': report}


def main():
    import argparse
    import hashlib
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, choices=(2008, 2011, 2014), required=True)
    parser.add_argument('--check', action='store_true', help='Compare regenerated outputs with committed bytes')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    outputs = build_year(root, args.year)
    paths = {'elections': f'data/processed/elections/{args.year}.json', 'split': f'data/processed/split-votes/{args.year}.json', 'validation': f'data/processed/elections/{args.year}-validation.json'}
    for kind, relative in paths.items():
        data = (json.dumps(outputs[kind], ensure_ascii=False, indent=2) + '\n').encode()
        path = root / relative
        if args.check:
            require(path.read_bytes() == data, 'Stale processed output: ' + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print(relative, hashlib.sha256(data).hexdigest())
    print(json.dumps(outputs['validation'], ensure_ascii=False))


if __name__ == '__main__':
    main()
