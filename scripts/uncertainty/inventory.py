"""Conditional means and separate outcome references; no uncertainty fitting."""
from fractions import Fraction
import numpy as np
from scripts.transport.geography import all_rows
from scripts.models.complete_party_vector.construction import construct_vector
from scripts.checkpoints.joint_candidate_share.kernel import centered
from .common import PREFIX, METHOD, YEARS, read, save, verify, arguments

PARTY = 'data/processed/models/expanded-party-substitution/'
CANDIDATE = 'data/processed/models/joint-candidate-share/construction.json'
DESIGN = 'data/processed/checkpoints/joint-candidate-share-design/inventory.json'
CONTINUOUS = 'data/processed/continuous-transport/'


def group(key, layer):
    if key == 'nationalparty':
        return 'national'
    if key == 'labourparty':
        return 'labour'
    return 'no_group' if key is None and layer == 'candidate' else 'other'


def simplex(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all() or (x < 0).any() or abs(x.sum() - 1) > 1e-12:
        raise ValueError('Missing/nonconserving complete simplex')
    return x


def party_mean(g, cats, exact, flows):
    cid = g['targetElectorateId']
    if g['targetYear'] not in (2014, 2020):
        old = exact[cid]
        return old['localPartyShares'], old['sourceAffinityStatus'], old['targetPartyGroupKeys']
    scenario = flows['transitions'][f"{g['sourceYear']}-{g['targetYear']}"]['scopes']['general']
    code = str(int(cid.split('-')[-1])).zfill(3)
    source = next(s for s in scenario['targetPartyVectors'] if s['targetCode'] == code)
    source_shares = {p['partyKey']: float(Fraction(p['shareExact']['numerator'], p['shareExact']['denominator'])) for p in source['parties']}
    local = {}
    for c in cats:
        if c['relationship'] == 'exit':
            continue
        value = None if c['relationship'] == 'entrant' else source_shares[c['sourcePartyKey']]
        local[c['categoryId']] = {'sourceLocalShare': value, 'sourceLocalStatus': 'entrant_no_source_category' if value is None else 'observed_positive' if value > 0 else 'observed_zero'}
    shares, status = construct_vector(cats, local, {c['categoryId']: c['suppliedTargetNationalShare'] for c in cats if c['relationship'] != 'exit'})
    keys = {c['categoryId']: c['targetPartyKey'] for c in cats if c['relationship'] != 'exit'}
    if cid in exact:
        old = exact[cid]
        if keys != old['targetPartyGroupKeys'] or max(abs(shares[k]-old['localPartyShares'][k]) for k in shares) > 1e-12:
            raise ValueError('Exact party-vector reproduction failed')
    return shares, status, keys


def candidate_record(g, target, fold, row, prediction, continuous):
    cs = row['candidates']
    ids = [c['targetOccurrenceId'] for c in cs]
    values = prediction['candidateShares']
    if set(ids) != set(values):
        raise ValueError('Complete conditional candidate slate mismatch')
    params = fold['fits'][METHOD]['parameters']
    features = []
    for c in cs:
        if continuous:
            f = c['continuous']
            z = [f['S']['contribution'], f['R']['contribution']]
            mass = {k: f[k]['supportedWeight'] for k in ('S', 'R')}
            evidence = [x['evidence'] for x in f['R']['components'] if x.get('evidence')]
        else:
            z = [centered(c, k, fold['trainingOnlyMeans'], 'broad', 'printed') for k in ('S', 'R')]
            mass = {'S': float(c['s0Reported'] is not None), 'R': float(c['R']['broad']['status'] == 'supported')}
            evidence = [c['R']['broad']]
        features.append({'id': c['targetOccurrenceId'], 'group': c['partyBallotGroupKey'], 'centered': z,
            'supportedMass': mass, 'residualEvidence': evidence})
    outcome = {c['id']: c['votes']/target['validCandidateVotes'] for c in target['candidates']}
    if set(outcome) != set(ids):
        raise ValueError('Candidate outcome roster mismatch')
    return {'layer': 'candidate', 'targetYear': g['targetYear'], 'sourceYear': g['sourceYear'],
        'targetElectorateId': g['targetElectorateId'], 'name': target['name'], 'scope': 'general',
        'geography': g['transportTier'], 'geographyId': g['geographyId'], 'ids': ids,
        'groups': [group(c['partyBallotGroupKey'], 'candidate') for c in cs],
        'mean': simplex([values[i] for i in ids]).tolist(), 'actual': simplex([outcome[i] for i in ids]).tolist(),
        'denominator': target['validCandidateVotes'], 'winnerId': target['winnerCandidateId'],
        'features': features, 'parameters': params, 'trainingIds': fold['trainingIds'],
        'trainingOnlyMeans': fold['trainingOnlyMeans'], 'savedFitId': fold['fits'][METHOD]['fitId'],
        'predictionStatus': 'earlier_fit_fixed_to_observed_local_party; reused_development',
        'predictionReference': 'Stage43 continuous joint' if continuous else 'Stage33 primary_fixed_to_observed joint',
        'outcomeReference': f"data/processed/elections/{g['targetYear']}.json#{g['targetElectorateId']}/candidateBallot"}


def build(elections=None):
    elections = {y: read(f'data/processed/elections/{y}.json') for y in YEARS} if elections is None else elections
    seats = {y: {s['id']: s for s in e['electorates']} for y, e in elections.items()}
    geography = [g for g in all_rows() if g['targetYear'] in YEARS]
    exact = {r['targetElectorateId']: r for r in read(PARTY + 'party-vectors.json')['records']}
    cat = {r['targetYear']: r['categories'] for r in read(PARTY + 'input-inventory.json')['categoryRelationships']}
    flow = read('data/processed/forecast-transport/party-construction.json')
    design = {r['targetElectorateId']: r for r in read(DESIGN)['contestRecords']}
    continuous = {r['targetElectorateId']: r for r in read(CONTINUOUS + 'inventory.json')['records']}
    joint = read(CANDIDATE)['folds']
    extended = read('data/processed/continuous-candidate-comparison/construction.json')['folds']
    parties, candidates, frame = [], [], []
    for g in geography:
        cid, year = g['targetElectorateId'], g['targetYear']
        if g['scope'] != 'general':
            frame.append({'id': cid, 'year': year, 'scope': g['scope'], 'geography': g['transportTier'],
                'partyStatus': 'coverage_only_separate_maori_layer', 'candidateStatus': 'coverage_only_separate_maori_layer'})
            continue
        target = seats[year].get(cid)
        if target is None:
            frame.append({'id': cid, 'year': year, 'scope': g['scope'], 'geography': g['transportTier'],
                'partyStatus': 'missing_preserved_election_record', 'candidateStatus': 'missing_preserved_election_record'})
            continue
        frame.append({'id': cid, 'year': year, 'scope': g['scope'], 'geography': g['transportTier'],
            'partyStatus': 'available' if g['scope'] == 'general' else 'coverage_only_separate_maori_layer',
            'candidateStatus': 'no_earlier_fit' if year == 2011 else 'cancelled' if target['validCandidateVotes'] <= 0 else 'available' if g['scope'] == 'general' else 'coverage_only_separate_maori_layer'})
        if g['scope'] != 'general':
            continue
        shares, status, keys = party_mean(g, cat[year], exact, flow)
        ids = sorted(shares)
        actual = {p['partyKey']: p['votes']/target['validPartyVotes'] for p in target['parties']}
        if set(actual) != set(keys.values()) or len(set(keys.values())) != len(keys):
            raise ValueError('Complete party roster/group accounting failed')
        parties.append({'layer': 'local_party', 'targetYear': year, 'sourceYear': g['sourceYear'],
            'targetElectorateId': cid, 'name': target['name'], 'scope': 'general', 'geography': g['transportTier'],
            'geographyId': g['geographyId'], 'ids': ids, 'ballotGroupKeys': [keys[i] for i in ids],
            'groups': [group(keys[i], 'local_party') for i in ids],
            'mean': simplex([shares[i] for i in ids]).tolist(), 'actual': simplex([actual[keys[i]] for i in ids]).tolist(),
            'affinities': [status[i]['affinity'] for i in ids], 'denominator': target['validPartyVotes'],
            'predictionStatus': 'parameter_free_source_affinity_conditional_national_truth; reused_development',
            'predictionReference': 'Stage31 exact / Stage41 feasible source geography plus frozen Stage23 rule',
            'sourceReference': PARTY + 'input-inventory.json' if year not in (2014, 2020) else 'data/processed/forecast-transport/party-construction.json',
            'outcomeReference': f'data/processed/elections/{year}.json#{cid}/partyBallot',
            'suppliedNationalScenario': {c['categoryId']: c['suppliedTargetNationalShare'] for c in cat[year] if c['relationship'] != 'exit'}})
        if year == 2011 or target['validCandidateVotes'] <= 0:
            continue
        fold = next(f for f in joint if f['branch'] == 'primary' and f['targetYear'] == year)
        if year in (2014, 2020):
            saved = next(f for f in extended if f['targetYear'] == year)
            pred = next(p for p in saved['predictions']['joint'] if p['targetElectorateId'] == cid)
            row = continuous[cid]
        else:
            saved = next(f for f in joint if f['branch'] == 'primary_fixed_to_observed' and f['targetYear'] == year)
            pred = next(p for p in saved['predictions'][METHOD] if p['targetElectorateId'] == cid)
            row = design[cid]
        candidates.append(candidate_record(g, target, fold, row, pred, year in (2014, 2020)))
    return {'stage': 44, 'partyRecords': parties, 'candidateRecords': candidates, 'fullFrame': frame,
        'priorUse': 'all elections repeatedly used in development; no untouched validation', 'operationalSelection': None}


def main():
    args = arguments()
    verify()
    value = build()
    save('inventory.json', value, args.check)
    print('Stage44 evidence', len(value['partyRecords']), len(value['candidateRecords']))


if __name__ == '__main__':
    main()
