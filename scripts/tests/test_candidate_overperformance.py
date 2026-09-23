"""Stage7 contracts: synthetic fixtures are not application observations."""
from copy import deepcopy
import hashlib
import json
import unittest

from scripts.models.candidate_overperformance.inputs import build as inventory, counterpart, validate_contest, DEST, ROOT
from scripts.models.candidate_overperformance.normalize import expected, normalize
from scripts.models.candidate_overperformance.run import build, encode, verify_contract


def fixture(i, cv, cd, pv, pd, year=2011, party='testparty'):
    return {'candidateOccurrenceId': f'fixture-{i}', 'year': year, 'boundaryRegime': '2007',
            'inputClass': 'observed', 'electorateId': f'seat-{i}', 'electorateType': 'general',
            'personId': None, 'eligible': True, 'exclusionReason': None, 'candidateContestStatus': 'held',
            'sourcePublishedCandidateVotes': cv, 'validCandidateVotes': cd, 'candidateShare': cv/cd,
            'localPartyVotes': pv, 'validPartyVotes': pd, 'localPartyShare': pv/pd,
            'candidateAffiliationKey': party, 'partyKey': party, 'sourcePartyLabel': 'Test Party',
            'rawPremium': cv/cd-pv/pd}


class CandidateOverperformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.hashes, cls.counts = inventory()
        cls.refs, cls.out = normalize(cls.rows, cls.counts)

    def test_distinct_denominators_and_two_contest_loo(self):
        a, b = fixture(1, 30, 100, 20, 200), fixture(2, 80, 200, 90, 300)
        refs, out = normalize([a, b], {2011: 70})
        ref = refs[0]
        self.assertAlmostEqual(ref['candidateShare'], 110/300)
        self.assertAlmostEqual(ref['partyShare'], 110/500)
        self.assertEqual(ref['electorateIds'], ['seat-1', 'seat-2'])
        self.assertEqual(ref['contestCount'], 2)
        self.assertAlmostEqual(out[0]['rawPremium'], .2)
        self.assertAlmostEqual(out[0]['leaveOneOutReference']['candidateShare'], .4)
        self.assertAlmostEqual(out[0]['leaveOneOutReference']['partyShare'], .3)
        self.assertAlmostEqual(out[0]['normalizedPremium'], .1)
        self.assertAlmostEqual(out[1]['normalizedPremium'], -.1)

    def test_self_never_defines_own_reference(self):
        a, b = fixture(1, 30, 100, 20, 200), fixture(2, 80, 200, 90, 300)
        _, before = normalize([a, b], {2011: 70})
        a.update(sourcePublishedCandidateVotes=90, candidateShare=.9, rawPremium=.8)
        _, after = normalize([a, b], {2011: 70})
        self.assertEqual(before[0]['leaveOneOutReference'], after[0]['leaveOneOutReference'])
        self.assertNotEqual(before[1]['leaveOneOutReference'], after[1]['leaveOneOutReference'])

    def test_singleton_retains_raw_no_fallback(self):
        _, rows = normalize([fixture(1, 30, 100, 20, 200)], {2011: 70})
        r = rows[0]
        self.assertAlmostEqual(r['rawPremium'], .2)
        self.assertIsNone(r['normalizedPremium'])
        self.assertEqual(r['normalizationReason'], 'insufficient_reference_contests')
        self.assertIsNone(r['leaveOneOutReference']['candidateShare'])
        self.assertEqual(r['methods'], {})

    def test_formula_domains_and_explicit_bounds(self):
        self.assertAlmostEqual(expected('additive', .3, .4, .4)['expectedRaw'], .3)
        self.assertAlmostEqual(expected('additive', .3, .5, .4)['expectedRaw'], .4)
        self.assertAlmostEqual(expected('proportional', .3, .6, .4)['expectedRaw'], .45)
        self.assertAlmostEqual(expected('log_odds', .5, .6, .4)['expectedRaw'], 9/13)
        for p in (0, .1, .8, 1):
            self.assertTrue(0 <= expected('log_odds', p, .99, .01)['expectedRaw'] <= 1)
        for method in ('proportional', 'log_odds'):
            self.assertIsNone(expected(method, .3, .5, 0)['expectedRaw'])
        self.assertEqual(expected('proportional', .3, 0, .4)['expectedRaw'], 0)
        self.assertIsNone(expected('log_odds', .3, 0, .4)['expectedRaw'])
        self.assertEqual(expected('additive', .1, 0, 1)['expectedRaw'], -.9)
        self.assertTrue(expected('additive', .1, 0, 1)['outOfRange'])
        self.assertEqual(expected('proportional', 1, .8, .1)['expectedBounded'], 1)
        with self.assertRaises(ValueError):
            expected('additive', float('nan'), .5, .5)

    def test_exact_identity_only(self):
        parties = {'alliance': {'partyKey': 'internetmana'}}
        self.assertIsNone(counterpart({'party': 'Internet Party'}, parties)[0])
        self.assertIsNone(counterpart({'party': 'MANA Movement'}, parties)[0])
        self.assertEqual(counterpart({'party': 'Independent'}, parties)[1], 'independent_no_party_vote_counterpart')
        for affiliation, grouping in [('NZ Public Party', 'advancenz'), ('Vision New Zealand', 'freedomsnz')]:
            self.assertIsNone(counterpart({'party': affiliation}, {'group': {'partyKey': grouping}})[0])
        top = {'partyKey': 'theopportunitiespartytop'}
        self.assertEqual(counterpart({'party': 'The Opportunities Party (TOP)'}, {'top': top})[0], top)
        self.assertIsNone(counterpart({'party': 'Opportunity'}, {'top': top})[0])

    def test_all_six_inventory_and_immutable_general_ids(self):
        self.assertEqual(set(self.counts), {2008, 2011, 2014, 2017, 2020, 2023})
        self.assertEqual(len(self.out), 3007)
        self.assertEqual(sum(r['eligible'] for r in self.out), 2674)
        self.assertEqual(sum(r['normalizedPremium'] is not None for r in self.out), 2673)
        for y in self.counts:
            original = json.loads((ROOT/f'data/processed/elections/{y}.json').read_bytes())
            mapping = {c['id']: c for e in original['electorates'] for c in e['candidates']}
            rows = [r for r in self.out if r['year'] == y and r['electorateType'] == 'general']
            self.assertEqual(set(mapping), {r['candidateOccurrenceId'] for r in rows})
            for r in rows:
                self.assertEqual(r['sourceCandidateName'], mapping[r['candidateOccurrenceId']]['name'])
                self.assertEqual(r['sourceAffiliation'], mapping[r['candidateOccurrenceId']]['party'])
                self.assertIsNone(r['personId'])

    def test_cancelled_port_waikato_unavailable(self):
        rs = [r for r in self.out if r['year'] == 2023 and r['electorateName'] == 'Port Waikato']
        self.assertEqual(len(rs), 9)
        for r in rs:
            self.assertEqual(r['exclusionReason'], 'cancelled_candidate_contest')
            self.assertEqual(r['sourcePublishedCandidateVotes'], 0)
            self.assertIsNone(r['candidateShare'])
            self.assertIsNone(r['normalizedPremium'])
        e = {'name': 'Other seat', 'candidateContestStatus': 'cancelled', 'validCandidateVotes': 0, 'candidates': []}
        with self.assertRaises(ValueError):
            validate_contest(e, 2023)

    def test_matched_universe_reconciles_and_excludes_noncontested(self):
        for ref in self.refs:
            rs = [r for r in self.out if r['referenceId'] == ref['id']]
            self.assertEqual(len(rs), ref['contestCount'])
            self.assertEqual(sorted(r['electorateId'] for r in rs), ref['electorateIds'])
            for field in ('sourcePublishedCandidateVotes', 'validCandidateVotes', 'localPartyVotes', 'validPartyVotes'):
                self.assertEqual(ref[field], sum(r[field] for r in rs))
                for r in rs:
                    self.assertEqual(r['leaveOneOutReference'][field], ref[field]-r[field])
            self.assertTrue(all(r['eligible'] and r['candidateContestStatus'] == 'held' for r in rs))
        self.assertTrue(any(r['contestCount'] < r['electionElectorateCount'] for r in self.refs))

    def test_mutated_inputs_fail(self):
        base = [fixture(1, 30, 100, 20, 200), fixture(2, 80, 200, 90, 300)]
        changes = [('year', 2026), ('inputClass', 'synthetic'), ('boundaryRegime', '2020'),
                   ('personId', 'guessed'), ('incumbent', True), ('candidateShare', 0),
                   ('validCandidateVotes', 999), ('partyKey', 'freedomsnz'), ('candidateContestStatus', 'cancelled')]
        for field, value in changes:
            with self.subTest(field=field):
                mutated = deepcopy(base)
                mutated[0][field] = value
                with self.assertRaises(ValueError):
                    normalize(mutated, {2011: 70})
        with self.assertRaises(ValueError):
            normalize([base[0], base[0]], {2011: 70})

    def test_reference_never_uses_another_election(self):
        a, b = fixture(1, 30, 100, 20, 200), fixture(2, 80, 200, 90, 300)
        other = fixture(3, 99, 100, 1, 100, year=2008)
        _, baseline = normalize([a, b], {2011: 70})
        _, after = normalize([a, b, other], {2011: 70, 2008: 70})
        self.assertEqual(baseline, after[:2])
        self.assertIsNone(after[2]['normalizedPremium'])

    def test_pinned_input_and_forbidden_paths(self):
        verify_contract(self.hashes)
        for path in ('data/polls/2026.json', 'data/processed/boundaries/2011-2014/candidates.json', 'data/models/opportunity.json'):
            with self.assertRaises(ValueError):
                verify_contract({path: '0'*64})
        path = next(iter(self.hashes))
        with self.assertRaises(ValueError):
            verify_contract({path: '0'*64})

    def test_deterministic_output_and_manifest(self):
        first, second = build(), build()
        self.assertEqual(encode(first), encode(second))
        for name, digest in first['manifest.json']['outputHashes'].items():
            self.assertEqual(hashlib.sha256(encode(first[name])).hexdigest(), digest)
        self.assertEqual(first['selection.json']['primaryNormalization'], 'additive_national_centered')


if __name__ == '__main__':
    unittest.main()
