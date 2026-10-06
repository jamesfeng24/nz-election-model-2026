"""Candidate-transition evidence ledger: contracts, safeguards and determinism."""
import copy
import json
import unittest
from collections import Counter, defaultdict

from scripts.evidence.candidate_transitions import run as ct
from scripts.evidence.candidate_transitions.universe import (
    ALIASES, CANDIDATE_VOTES, GEOGRAPHY, MAORI_OVERLAY, OCCURRENCES, PAIRS, build_rows, seat_winners, verify_winners)
from scripts.evidence.practical_candidate_linkage.names import alias_pairs, parse_name

OUT = ct.DEST


def load(name):
    return json.loads((OUT / name).read_bytes())


def synthetic_occurrence(cid, year, seat, name, party, votes, status='held'):
    return {'candidateOccurrenceId': cid, 'year': year, 'electorateId': f'{seat}-{year}', 'electorateName': seat,
            'electorateType': 'general', 'sourceCandidateName': name, 'partyKey': party,
            'candidateContestStatus': status, 'sourcePublishedCandidateVotes': votes}


class LedgerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = load('incumbent-seat-ledger.json')['records']
        cls.summary = load('summary.json')

    def test_universe_counts_are_fixed_by_preserved_winners(self):
        self.assertEqual(len(self.ledger), 333)
        self.assertEqual(Counter(r['sourceYear'] for r in self.ledger),
                         {2008: 62, 2011: 64, 2014: 68, 2017: 70, 2020: 69})
        self.assertEqual(len({r['key'] for r in self.ledger}), 333)
        self.assertTrue(all(r['party'] in ('NAT', 'LAB') for r in self.ledger))

    def test_every_row_is_classified_and_changes_are_sourced(self):
        registry = {s['id'] for s in ct.read(ct.REGISTRY)['sources']}
        for row in self.ledger:
            self.assertIn(row['relation'], ('continuation', 'candidate_change'))
            if row['relation'] == 'candidate_change':
                transition = row['transition']
                self.assertIn(transition['transitionType'], ct.CHANGE_TYPES)
                self.assertIn(transition['confidence'], ('high', 'medium'))
                self.assertTrue(transition['reasoning'])
                self.assertTrue(transition['evidence'])
                for item in transition['evidence']:
                    self.assertIn(item['source'], registry)
            else:
                self.assertIn(row['continuationBasis'], ('automatic_name_match_same_party_successor_seat',
                                                        'curated_identity_judgement'))

    def test_by_election_successors_are_the_target_candidate(self):
        aliases = alias_pairs(ct.read(ALIASES))
        from scripts.evidence.practical_candidate_linkage.names import name_match
        successions = [r for r in self.ledger if r['relation'] == 'candidate_change'
                       and r['transition']['transitionType'] == 'by_election_succession']
        self.assertEqual(len(successions), 9)
        for row in successions:
            effective = row['transition']['effectiveIncumbentAtTarget']
            self.assertTrue(row['transition']['effectiveIncumbentRecontests'])
            self.assertTrue(name_match(parse_name(effective['name']),
                                       parse_name(row['primaryTargetCandidate']['name']), aliases)['compatible'])

    def test_known_resolutions(self):
        by_key = {r['key']: r for r in self.ledger}
        self.assertEqual(by_key['2011-2014|NAT|Kaikōura']['transition']['transitionType'], 'deselection')
        self.assertEqual(by_key['2014-2017|NAT|Northland']['transition']['transitionType'], 'by_election_party_change')
        self.assertEqual(by_key['2020-2023|LAB|Hamilton West']['transition']['transitionType'], 'by_election_party_change')
        self.assertEqual(by_key['2011-2014|NAT|Waitakere']['transition']['transitionType'], 'boundary_complication')
        # Name variants resolved as the same person, not as replacements.
        for key in ('2008-2011|NAT|Maungakiekie', '2011-2014|NAT|Nelson', '2014-2017|LAB|Ikaroa-Rāwhiti',
                    '2020-2023|LAB|Takanini', '2011-2014|LAB|Māngere'):
            self.assertEqual(by_key[key]['relation'], 'continuation', key)
            self.assertEqual(by_key[key]['continuationBasis'], 'curated_identity_judgement')
        # A postponed contest is a continuation, never a replacement.
        self.assertEqual(by_key['2020-2023|NAT|Port Waikato']['relation'], 'continuation')
        self.assertEqual(by_key['2020-2023|NAT|Port Waikato']['primaryTargetCandidate']['contestStatus'], 'cancelled')

    def test_summary_reconciles(self):
        s = self.summary
        self.assertEqual(s['continuations'] + s['candidateChanges'], s['incumbentSeats'])
        self.assertEqual(sum(s['changesByType'].values()), s['candidateChanges'])
        self.assertEqual(sum(p['candidateChanges'] for p in s['byPair'].values()), s['candidateChanges'])
        self.assertEqual(s['stage10Reconciliation']['stage10Total'], 61)
        # Every exact-name difference is either a same-person variant or a documented change.
        for pair in s['exactNameDifferencesByPair'].values():
            self.assertEqual(pair['exactStringDifferences'], pair['resolvedSamePersonAutomatic']
                             + pair['resolvedSamePersonCurated'] + pair['candidateChanges'])

    def test_dates_are_well_formed_and_registry_hashes_hold(self):
        ct.verify_registry(ct.read(ct.REGISTRY))
        for row in self.ledger:
            if row['relation'] == 'candidate_change':
                for item in row['transition']['evidence']:
                    if item['date'] is not None:
                        self.assertRegex(item['date'], ct.DATE)

    def test_outputs_are_deterministic_and_inputs_unchanged(self):
        outputs = ct.construct()
        for name, value in outputs.items():
            expected = value if isinstance(value, bytes) else ct.encode({'schemaVersion': 1, **value})
            self.assertEqual((OUT / name).read_bytes(), expected, name)
        manifest = load('manifest.json')
        for path, expected in manifest['inputSha256'].items():
            self.assertEqual(ct.digest(path), expected, path)

    def test_no_numerical_estimate_fields(self):
        text = (OUT / 'incumbent-seat-ledger.json').read_text(encoding='utf-8')
        for forbidden in ('rawPremium', 'normalizedPremium', 'priorResidual', 'targetResidual', 'coefficient'):
            self.assertNotIn(forbidden, text)


class SyntheticSafeguards(unittest.TestCase):
    """Synthetic fixtures only; never read by application results."""

    def setUp(self):
        self.aliases = alias_pairs(ct.read(ALIASES))
        self.occurrences = [
            synthetic_occurrence('s1', 2008, 'SeatA', 'SMITH, Alan Bob', 'nationalparty', 100),
            synthetic_occurrence('s2', 2008, 'SeatA', 'JONES, Carl', 'labourparty', 90),
            synthetic_occurrence('t1', 2011, 'SeatA', 'LEE, Dana', 'nationalparty', 100),
            synthetic_occurrence('t2', 2011, 'SeatA', 'JONES, Carl', 'labourparty', 90)]
        self.geography = [{'targetElectorateId': 'SeatA-2011', 'targetElectorateName': 'SeatA', 'dominantPredecessorId': 'SeatA-2008',
                           'exclusiveTier': 'exact', 'predecessors': [{
                               'sourceElectorateId': 'SeatA-2008',
                               **{k: {'numerator': 1, 'denominator': 1} for k in (
                                   'sourceRetentionLower', 'sourceRetentionUpper', 'targetInheritanceLower', 'targetInheritanceUpper')}}]}]
        self.curation = {'transitions': {}, 'identityJudgements': {}, 'continuationNotes': {}, 'supplementarySeatGains': []}

    def rows(self):
        winners = {k: v for k, v in seat_winners(self.occurrences).items() if v['year'] == 2008}
        return build_rows(self.occurrences, self.geography, {'pairs': []}, winners)

    def classify(self, rows):
        by_year = defaultdict(list)
        for o in self.occurrences:
            by_year[o['year']].append(o)
        return ct.classify(rows, self.curation, {'ct-x'}, by_year, self.aliases)

    def test_unclassified_difference_fails_instead_of_defaulting(self):
        rows = [r for r in self.rows() if r['sourceYear'] == 2008]
        with self.assertRaisesRegex(ValueError, 'Unclassified'):
            self.classify(rows)

    def test_curated_change_on_same_person_row_fails(self):
        self.occurrences[2]['sourceCandidateName'] = 'SMITH, Alan'
        rows = [r for r in self.rows() if r['sourceYear'] == 2008 and r['party'] == 'NAT']
        self.curation['transitions'] = {rows[0]['key']: {}}
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            self.classify(rows)

    def test_unregistered_or_missing_evidence_fails(self):
        for items in ([], [{'source': 'ct-nope', 'claim': 'x', 'date': None, 'dateKind': 'event', 'reading': 'direct'}]):
            with self.assertRaises(ValueError):
                ct.verify_evidence(items, {'ct-x'}, 'synthetic')

    def test_malformed_date_fails(self):
        item = {'source': 'ct-x', 'claim': 'x', 'date': '2011-13', 'dateKind': 'event', 'reading': 'direct'}
        for bad in ('2011-13', '2011-02-32', '11 March 2011'):
            item['date'] = bad
            with self.assertRaises(ValueError):
                ct.verify_evidence([item], {'ct-x'}, 'synthetic')
        for good in ('2011', '2011-03', '2011-03-05'):
            item['date'] = good
            ct.verify_evidence([item], {'ct-x'}, 'synthetic')

    def test_tied_winner_fails(self):
        self.occurrences[1]['sourcePublishedCandidateVotes'] = 100
        self.occurrences[1]['partyKey'] = 'labourparty'
        with self.assertRaisesRegex(ValueError, 'Tied'):
            seat_winners(self.occurrences)

    def test_changed_raw_extract_fails(self):
        registry = copy.deepcopy(ct.read(ct.REGISTRY))
        registry['sources'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed raw'):
            ct.verify_registry(registry)

    def test_preserved_winners_match_published_flags(self):
        occurrences = ct.read(OCCURRENCES)['records']
        verify_winners(seat_winners(occurrences), ct.read(CANDIDATE_VOTES), ct.read(MAORI_OVERLAY))


if __name__ == '__main__':
    unittest.main()
