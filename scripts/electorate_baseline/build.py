"""Stage64: audit of the 2026 electorate set and its notional 2023 party-vote baselines, joined by stable ids.

python -m scripts.electorate_baseline.build [--check]

Data and audit only. Reads existing artifacts (Stage4 crosswalk and bounds, Stage40 target frame, Stage41 coherent
scenario) and one preserved third-party cross-check; fits nothing and changes no model scale or frozen output.
Māori electorates are inventoried with party-vote baselines only; no candidate-layer quantity is computed for them.
"""
import csv
import math
import unicodedata
from collections import Counter, defaultdict

from .common import (ARTICLE, BOUNDS, CROSSWALK, ELECTION_2023, FRAME, OVERALL_SUMMARY, PARTY_BY_ELECTORATE, PREFIX, REGISTRY,
                     ROOT, SCENARIO, SCHEDULE_B, SCHEDULE_C, SHEET, CODE, arguments, digest, pin, read, save, verify)

QUOTA = {'N': (69875, 3494), 'S': (70037, 3502), 'M': (74367, 3718)}  # Schedule C printed quotas and +/-5% tolerances
THIRD_PARTY_KEYS = {'National Party': 'nationalparty', 'Labour Party': 'labourparty', 'Green Party': 'greenparty',
                    'Te Pāti Māori': 'tepatimaori', 'ACT New Zealand': 'actnewzealand',
                    'The Opportunities Party (TOP)': 'theopportunitiespartytop', 'New Zealand First Party': 'newzealandfirstparty'}
OVERALL_ALIASES = {'leighton baker': 'leighton baker party', 'nz loyal': 'new zealand loyal'}
CONSISTENT, LARGE = 0.01, 0.10  # |difference in ln(party A / party B)|: rounding level, then large
HEADLINE_SEATS = {'National Party': 45, 'Labour Party': 16, 'Te Pāti Māori': 6, 'Green Party': 2, 'ACT New Zealand': 2}


def nfc(text):
    return unicodedata.normalize('NFC', text)


def fraction(value):
    return value['numerator'] / value['denominator']


def target_id(scope, code):
    return f'nz-{scope}-2026-boundary-{code}'


def schedule():
    """Official Schedule C roster (preserved PDF, transcribed controls) checked against its own quota arithmetic."""
    rows = read(SCHEDULE_C)['electorates']
    result = []
    for row in rows:
        island = row['scheduleCode'][0]
        quota, tolerance = QUOTA[island]
        deviation = row['electoralPopulation'] - quota
        result.append({'scope': row['electorateType'], 'code': row['sourceCode'], 'displayCode': row['scheduleCode'],
                       'name': row['name'], 'population': row['electoralPopulation'], 'island': island,
                       'quota': quota, 'deviationFromQuota': deviation,
                       'deviationFraction': deviation / quota, 'withinTolerance': abs(deviation) <= tolerance})
    return result


def third_party():
    rows = list(csv.reader((ROOT / SHEET).read_text(encoding='utf-8').splitlines()))
    table = {}
    for row in rows[2:]:
        if row[1] == 'Abolished':
            abolished = nfc(row[0])
            continue
        table[nfc(row[1])] = {
            'oldSeat': nfc(row[0]),
            'candidateFirst': [row[2], row[3]], 'candidateSecond': [row[4], row[5]],
            'partyFirst': [row[6], float(row[7].rstrip('%')) / 100], 'partySecond': [row[8], float(row[9].rstrip('%')) / 100],
            'candidateFirstShare': float(row[3].rstrip('%')) / 100, 'candidateSecondShare': float(row[5].rstrip('%')) / 100}
    return table, abolished


def party_totals():
    """Official 2023 party-vote totals from the raw Electoral Commission CSV (rows and its own totals rows)."""
    rows = list(csv.reader((ROOT / PARTY_BY_ELECTORATE).read_text(encoding='utf-8-sig').splitlines()))
    header = rows[1]
    parties = header[1:header.index('Total Valid Party Votes')]
    electorates, totals = [], {}
    for row in rows[2:]:
        values = [int(v) for v in row[1:len(header)]]
        if row[0].endswith('Totals'):
            totals[row[0]] = dict(zip(header[1:], values))
        else:
            electorates.append((row[0], dict(zip(header[1:], values))))
    return parties, electorates, totals


def official_party_list():
    result = {}
    for row in csv.reader((ROOT / OVERALL_SUMMARY).read_text(encoding='utf-8-sig').splitlines()):
        if len(row) > 3 and row[2].strip().isdigit():
            result.setdefault(row[0].strip().lower(), int(row[2]))  # first table only: later 'State of the Parties' repeats names
    return result


def reconcile(scenario, bounds, crosswalk):
    """National reconciliation of the notional baseline with the official 2023 totals."""
    parties, electorates, totals = party_totals()
    keys = {p['sourceHeader']: p['partyKey'] for p in read(ELECTION_2023)['electorates'][0]['parties']}
    listvotes = official_party_list()
    scope_sources = {'general': 'General Electorate Totals', 'maori': 'Māori Electorate Totals'}
    names_general = {nfc(s['name']) for s in crosswalk['scopes']['general']['sources']}
    summed = Counter()
    by_scope = {'general': Counter(), 'maori': Counter()}
    for name, votes in electorates:
        scope = 'general' if nfc(name) in names_general else 'maori'
        for header in parties + ['Total Valid Party Votes']:
            by_scope[scope][header] += votes[header]
            summed[header] += votes[header]
    rows = []
    for header in parties:
        key = keys[header]
        listed = listvotes[OVERALL_ALIASES.get(header.lower(), header.lower())]
        general_mass = bounds['scopes']['general']['partyMassConservation']
        maori_mass = bounds['scopes']['maori']['partyMassConservation']
        general_source = next(r['sourceVotes'] for r in general_mass if r['partyKey'] == key)
        maori_source = next(r['sourceVotes'] for r in maori_mass if r['partyKey'] == key)
        scenario_general = sum(next(p['votes'] for p in t['parties'] if p['partyKey'] == key)
                               for t in scenario['scopes']['general']['targetPartyVectors'])
        scenario_maori = sum(next(p['votes'] for p in t['parties'] if p['partyKey'] == key)
                             for t in scenario['scopes']['maori']['targetPartyVectors'])
        lower_general = sum(next(p['votesLower'] for p in t['parties'] if p['partyKey'] == key) for t in bounds['scopes']['general']['targets'])
        upper_general = sum(next(p['votesUpper'] for p in t['parties'] if p['partyKey'] == key) for t in bounds['scopes']['general']['targets'])
        rows.append({
            'partyKey': key, 'officialCombinedTotal': totals['Combined Totals'][header], 'officialPartyListVotes': listed,
            'sumOfElectorateRows': summed[header], 'officialGeneralTotal': by_scope['general'][header],
            'officialMaoriTotal': totals[scope_sources['maori']][header],
            'boundsSourceGeneral': general_source, 'boundsSourceMaori': maori_source,
            'scenarioTargetGeneral': scenario_general, 'scenarioTargetMaori': scenario_maori,
            'boundsGeneralSumLower': lower_general, 'boundsGeneralSumUpper': upper_general,
            'sourceEqualsOfficial': general_source + maori_source == totals['Combined Totals'][header] == listed == summed[header],
            'scenarioConservesGeneral': abs(scenario_general - general_source) < 1e-6,
            'scenarioConservesMaori': abs(scenario_maori - maori_source) < 1e-6,
            'boundsEncloseGeneralTotal': lower_general <= general_source + 1e-6 and upper_general >= general_source - 1e-6})
    return {'validVotes': {'officialCombined': totals['Combined Totals']['Total Valid Party Votes'],
                           'sumOfElectorateRows': summed['Total Valid Party Votes'],
                           'officialGeneral': by_scope['general']['Total Valid Party Votes'],
                           'officialMaori': totals[scope_sources['maori']]['Total Valid Party Votes'],
                           'boundsSourceGeneral': scenario['scopes']['general']['sourceValidPartyVotes'],
                           'boundsSourceMaori': scenario['scopes']['maori']['sourceValidPartyVotes']},
            'electorateRows': {'general': sum(1 for n, _ in electorates if nfc(n) in names_general), 'maori': sum(1 for n, _ in electorates if nfc(n) not in names_general)},
            'parties': rows}


def build():
    crosswalk, bounds, frame = read(CROSSWALK), read(BOUNDS), {r['targetElectorateId']: r for r in read(FRAME)['records']}
    scenario = read(SCENARIO)['transitions']['2023-2026']
    official = {(r['scope'], r['code']): r for r in schedule()}
    changes = read(SCHEDULE_B)
    sheet, abolished = third_party()
    records, edges, collisions = [], [], []
    plurality_by_target = {}
    fate = defaultdict(list)
    source_names, source_ids = {}, {}
    for scope in ('general', 'maori'):
        data = crosswalk['scopes'][scope]
        sources = {s['code']: s for s in data['sources']}
        source_names[scope] = {c: s['name'] for c, s in sources.items()}
        bound_targets = {t['targetCode']: t for t in bounds['scopes'][scope]['targets']}
        vectors = {t['targetCode']: t for t in scenario['scopes'][scope]['targetPartyVectors']}
        controls = scenario['scopes'][scope]['targetPopulationControls']
        for target in data['targets']:
            code, name = target['code'], target['name']
            tid = target_id(scope, code)
            roster, fr = official[(scope, code)], frame[tid]
            members = []
            for member in target['composition']:
                edge = next(e for e in data['edges'] if e['source'] == member['source'] and e['target'] == code)
                lower, upper = fraction(member['shareLower']), fraction(member['shareUpper'])
                source_ids[(scope, member['source'])] = next(p['sourceElectorateId'] for p in fr['predecessors'] if p['sourceBoundaryCode'] == member['source'])
                members.append({'sourceCode': member['source'], 'sourceName': sources[member['source']]['name'],
                                'sourceElectorateId': source_ids[(scope, member['source'])],
                                'incomingShareLower': lower, 'incomingShareUpper': upper,
                                'jointPopulationLower': edge['lower'], 'jointPopulationUpper': edge['upper'],
                                'sourceRetainedWeightLower': fraction(edge['weightLower']), 'sourceRetainedWeightUpper': fraction(edge['weightUpper'])})
                edges.append({'scope': scope, 'targetElectorateId': tid, 'targetCode': code, 'targetName': name,
                              'sourceElectorateId': source_ids[(scope, member['source'])], 'sourceCode': member['source'],
                              'sourceName': sources[member['source']]['name'], 'jointPopulationLower': edge['lower'],
                              'jointPopulationUpper': edge['upper'], 'suppressedMeshblocks': edge['suppressedCount'],
                              'incomingShareLower': lower, 'incomingShareUpper': upper})
            members.sort(key=lambda m: (-(m['incomingShareLower'] + m['incomingShareUpper']), m['sourceCode']))
            top = members[0]
            identified = all(top['incomingShareLower'] > m['incomingShareUpper'] for m in members[1:])
            plurality_by_target[tid] = (top['sourceName'], identified)
            fate[(scope, top['sourceCode'])].append(tid)
            vector = {p['partyKey']: p for p in vectors[code]['parties']}
            interval = {p['partyKey']: p for p in bound_targets[code]['parties']}
            ranked = sorted(vector, key=lambda k: (-vector[k]['share'], k))
            lead, second = ranked[0], ranked[1]
            record = {
                'targetElectorateId': tid, 'scope': scope, 'boundaryCode': code, 'officialDisplayCode': roster['displayCode'],
                'name': name, 'electoralPopulation': roster['population'], 'island': roster['island'],
                'deviationFromQuotaFraction': roster['deviationFraction'],
                'officialChangeStatus': target['officialChangeStatus'], 'officialRenameFrom': changes['unchangedRename'].get(name),
                'geographyStatus': fr['geographyStatus'], 'exactSourceElectorateId': fr['exactSourceElectorateId'],
                'predecessors': members,
                'pluralityPredecessor': {'name': top['sourceName'], 'sourceElectorateId': top['sourceElectorateId'], 'identifiedByBounds': identified},
                'partyBaseline': {
                    'basis': 'population-weighted source party vote transport (within-source uniform), chosen coherent scenario with bounds',
                    'scenarioValidPartyVotes': vectors[code]['validPartyVotes'],
                    'partyShares': {k: {'scenario': vector[k]['share'], 'lower': interval[k]['shareLower'], 'upper': interval[k]['shareUpper']} for k in sorted(vector)},
                    'leadParty': lead, 'secondParty': second, 'leadMarginPoints': 100 * (vector[lead]['share'] - vector[second]['share']),
                    'leadCertainAcrossBounds': interval[lead]['shareLower'] > interval[second]['shareUpper'],
                    'boundsMeaning': 'population-allocation uncertainty only; not within-source heterogeneity'},
                'candidateLayer': ('not computed: Māori electorates are modelled separately' if scope == 'maori'
                                   else 'no official or repo notional candidate votes; exact seats use source local results, changed seats neutral fallback (Stage39/40)'),
                'populationControlMatchesScheduleC': controls[code] == roster['population']}
            comparator = sheet.get(nfc(name))
            if comparator:
                a, b = THIRD_PARTY_KEYS[comparator['partyFirst'][0]], THIRD_PARTY_KEYS[comparator['partySecond'][0]]
                difference = (math.log(comparator['partyFirst'][1] / comparator['partySecond'][1])
                              - math.log(vector[a]['share'] / vector[b]['share']))
                record['thirdPartyCrossCheck'] = {
                    'source': 'stage64-tallyroom-nz-notional-2023-on-2025-boundaries-sheet', 'role': 'comparison_only_not_model_input',
                    'oldSeat': comparator['oldSeat'], 'candidateFirst': comparator['candidateFirst'], 'candidateSecond': comparator['candidateSecond'],
                    'partyFirst': comparator['partyFirst'], 'partySecond': comparator['partySecond'],
                    'topTwoPartiesAgree': (a, b) == (lead, second), 'leadPartyAgrees': a == lead,
                    'logRatioDifference': difference,
                    'class': 'consistent_with_rounding' if abs(difference) <= CONSISTENT else ('large' if abs(difference) > LARGE else 'moderate')}
            records.append(record)
    records.sort(key=lambda r: r['targetElectorateId'])
    edges.sort(key=lambda e: (e['targetElectorateId'], e['sourceCode']))
    # fates of the 2023 source seats
    fates = []
    for scope in ('general', 'maori'):
        for code, name in sorted(source_names[scope].items()):
            successors = sorted(e['targetName'] for e in edges if e['scope'] == scope and e['sourceCode'] == code)
            plurality_of = sorted(next(r['name'] for r in records if r['targetElectorateId'] == t) for t in fate.get((scope, code), []))
            fates.append({'scope': scope, 'sourceCode': code, 'sourceName': name,
                          'sourceElectorateId': source_ids[(scope, code)], 'successors': successors, 'pluralityPredecessorOf': plurality_of,
                          'fate': ('no_target_plurality' if not plurality_of else ('same_name_plurality' if nfc(name) in {nfc(p) for p in plurality_of} else 'renamed_plurality'))})
    # code namespaces are vintage-specific
    for scope in ('general', 'maori'):
        target_names = {t['code']: t['name'] for t in crosswalk['scopes'][scope]['targets']}
        for code, name in source_names[scope].items():
            if code in target_names and nfc(target_names[code]) != nfc(name):
                collisions.append({'scope': scope, 'code': code, 'sourceName': name, 'targetName': target_names[code]})
    same_name_new_code = sum(1 for scope in ('general', 'maori') for t in crosswalk['scopes'][scope]['targets']
                             for c, n in source_names[scope].items() if nfc(n) == nfc(t['name']) and c != t['code'])
    return {'records': records, 'edges': edges, 'fates': fates, 'collisions': collisions, 'sameNameDifferentCode': same_name_new_code,
            'sheet': sheet, 'abolished': abolished, 'reconciliation': reconcile(scenario, bounds, crosswalk), 'plurality': plurality_by_target}


def audit(model):
    records, edges, fates = model['records'], model['edges'], model['fates']
    roster = schedule()
    sheet, rec = model['sheet'], model['reconciliation']
    by_scope = Counter(r['scope'] for r in records)
    exact = [r for r in records if r['exactSourceElectorateId']]
    comparator = [r for r in records if 'thirdPartyCrossCheck' in r]
    classes = Counter(r['thirdPartyCrossCheck']['class'] for r in comparator)
    exact_diffs = [abs(r['thirdPartyCrossCheck']['logRatioDifference']) for r in comparator if r['exactSourceElectorateId']]
    changed_diffs = [abs(r['thirdPartyCrossCheck']['logRatioDifference']) for r in comparator if not r['exactSourceElectorateId']]
    general_changed = [r for r in comparator if not r['exactSourceElectorateId']]
    sheet_old = {nfc(v['oldSeat']): n for n, v in sheet.items()}
    renames = {}
    for r in comparator:
        old = r['thirdPartyCrossCheck']['oldSeat']
        renames[r['name']] = {'thirdPartyOldSeat': old, 'pluralityPredecessor': r['pluralityPredecessor']['name'],
                              'pluralityIdentifiedByBounds': r['pluralityPredecessor']['identifiedByBounds'],
                              'agrees': nfc(old) == nfc(r['pluralityPredecessor']['name'])}
    mapping_disagreements = sorted(n for n, v in renames.items() if not v['agrees'])
    checks = {
        'rosterCounts': {'general': by_scope['general'], 'maori': by_scope['maori'], 'total': len(records),
                         'scheduleCGeneral': sum(1 for r in roster if r['scope'] == 'general'), 'scheduleCMaori': sum(1 for r in roster if r['scope'] == 'maori'),
                         'islands': dict(sorted(Counter(r['island'] for r in roster).items())), 'impliedListSeats': 120 - len(records)},
        'allTargetsWithinFivePercentOfQuota': all(r['withinTolerance'] for r in roster),
        'namesAndCodesMatchScheduleC': all(r['populationControlMatchesScheduleC'] for r in records) and {(r['scope'], r['boundaryCode'], nfc(r['name'])) for r in records} == {(r['scope'], r['code'], nfc(r['name'])) for r in roster},
        'idsUniqueAndWellFormed': len({r['targetElectorateId'] for r in records}) == 71 and all(r['targetElectorateId'].startswith(('nz-general-2026-boundary-', 'nz-maori-2026-boundary-')) for r in records),
        'everyTargetHasCompletePartyBaseline': all(len(r['partyBaseline']['partyShares']) == 17 and all(
            0 <= v['lower'] <= v['scenario'] + 1e-9 and v['scenario'] <= v['upper'] + 1e-9 <= 1 + 2e-9 for v in r['partyBaseline']['partyShares'].values()) for r in records),
        'scenarioSharesSumToOne': max(abs(sum(v['scenario'] for v in r['partyBaseline']['partyShares'].values()) - 1) for r in records),
        'everyTargetHasPredecessors': all(r['predecessors'] for r in records),
        'edgeCounts': {'general': sum(1 for e in edges if e['scope'] == 'general'), 'maori': sum(1 for e in edges if e['scope'] == 'maori')},
        'everySourceSeatAccountedFor': {'general': sum(1 for f in fates if f['scope'] == 'general'), 'maori': sum(1 for f in fates if f['scope'] == 'maori')},
        'sourceSeatsWithNoTargetPlurality': sorted(f['sourceName'] for f in fates if f['fate'] == 'no_target_plurality'),
        'renamedPluralitySourceSeats': sorted([f['sourceName'], f['pluralityPredecessorOf'][0]] for f in fates if f['fate'] == 'renamed_plurality'),
        'certifiedExactTargets': {'general': sum(1 for r in exact if r['scope'] == 'general'), 'maori': sum(1 for r in exact if r['scope'] == 'maori')},
        'codeNamespaces': {'collidingSameCodeDifferentName': len(model['collisions']), 'sameNameDifferentCode': model['sameNameDifferentCode'],
                           'rule': 'Boundary codes are vintage-specific (alphabetical per vintage); join across vintages by election-local source id or by official name only inside one vintage, never by code.'},
        'nationalReconciliation': {
            'everyPartySourceEqualsOfficialTotal': all(r['sourceEqualsOfficial'] for r in rec['parties']),
            'everyPartyScenarioConservesGeneral': all(r['scenarioConservesGeneral'] for r in rec['parties']),
            'everyPartyScenarioConservesMaori': all(r['scenarioConservesMaori'] for r in rec['parties']),
            'everyPartyBoundsEncloseGeneralTotal': all(r['boundsEncloseGeneralTotal'] for r in rec['parties']),
            'validVotesOfficialCombined': rec['validVotes']['officialCombined'],
            'validVotesSourceGeneralPlusMaori': rec['validVotes']['boundsSourceGeneral'] + rec['validVotes']['boundsSourceMaori'],
            'electorateRows': rec['electorateRows']}}
    cross = {
        'source': 'stage64-tallyroom-nz-notional-2023-on-2025-boundaries-sheet (third party, comparison only)',
        'sheetRows': len(sheet) + 1, 'newSeatsMatched': len(comparator), 'abolishedOldSeat': model['abolished'],
        'sheetHeadlineCandidateWinners': dict(sorted(Counter(v['candidateFirst'][0] for v in sheet.values()).items())),
        'headlineMatchesArticle': dict(sorted(Counter(v['candidateFirst'][0] for v in sheet.values()).items())) == dict(sorted(HEADLINE_SEATS.items())),
        'topTwoPartyAgreement': {'agree': sum(1 for r in comparator if r['thirdPartyCrossCheck']['topTwoPartiesAgree']), 'of': len(comparator),
                                 'disagree': sorted(r['name'] for r in comparator if not r['thirdPartyCrossCheck']['topTwoPartiesAgree'])},
        'logRatioDifferenceClasses': dict(sorted(classes.items())),
        'exactSeats': {'n': len(exact_diffs), 'maxAbs': max(exact_diffs), 'meaning': 'denominator and geography identical, so only rounding and ordinary-vote effects remain'},
        'changedSeats': {'n': len(changed_diffs), 'maxAbs': max(changed_diffs), 'meanAbs': sum(changed_diffs) / len(changed_diffs),
                         'rmse': math.sqrt(sum(d * d for d in changed_diffs) / len(changed_diffs)),
                         'largest': [{'name': r['name'], 'logRatioDifference': r['thirdPartyCrossCheck']['logRatioDifference']}
                                     for r in sorted(general_changed, key=lambda r: -abs(r['thirdPartyCrossCheck']['logRatioDifference']))[:8]]},
        'pluralityPredecessorVersusThirdPartyOldSeat': {'disagreements': mapping_disagreements, 'compared': len(renames),
                                                        'renamesOrAbolished': {n: v for n, v in renames.items() if nfc(v['thirdPartyOldSeat']) != nfc(n)}},
        'leadMarginsNotCertainAcrossBounds': sorted(r['name'] for r in records if not r['partyBaseline']['leadCertainAcrossBounds']),
        'interpretation': 'Population-weighted transport assumes uniform party voting within each source seat; the bounds cover population allocation only. '
                          'Where a source seat is split between unlike areas the cross-check differs by more than rounding. Whether historical residuals already absorb this is not assessed here.'}
    return {'checks': checks, 'thirdPartyCrossCheck': cross}


def outputs():
    model = build()
    return {'register.json': {'schemaVersion': 1, 'stage': 64, 'targets': model['records'],
                              'dataClass': 'synthetic_notional_party_vote_reconstruction_not_observed_votes'},
            'mapping.json': {'schemaVersion': 1, 'stage': 64, 'edges': model['edges'], 'sourceSeatFates': model['fates'],
                             'codeNamespaceCollisions': model['collisions']},
            'reconciliation.json': {'schemaVersion': 1, 'stage': 64, **model['reconciliation']},
            'audit.json': {'schemaVersion': 1, 'stage': 64, **audit(model)}}


def main():
    args = arguments()
    if args.check:
        verify()
    results = outputs()
    if not args.check:
        save('input-contract.json', {'inputHashes': pin(), 'newResources': 2, 'dataSourcesJsonTouched': False,
                                     'registry': REGISTRY})
    for name, value in results.items():
        save(name, value, args.check)
    manifest = {'stage': 64, 'consumedInputs': read(PREFIX + '/input-contract.json')['inputHashes'],
                'derivedArtifacts': {f'{PREFIX}/{n}': digest(f'{PREFIX}/{n}') for n in results},
                'code': {p: digest(p) for p in CODE}, 'dataSourcesJsonTouched': False, 'modelOrScaleChanged': False,
                'newNationalInference': False, 'hashesAreNotProofOfLinuxReproduction': True}
    save('manifest.json', manifest, args.check)


if __name__ == '__main__':
    main()
