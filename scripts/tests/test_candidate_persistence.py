"""Stage 8 geography, leakage, benchmark and reproducibility checks."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.models.candidate_persistence.model import analyze, fit, score, select
from scripts.models.candidate_persistence.official import parse_members, project_members
from scripts.models.candidate_persistence.pairs import build_pairs
from scripts.models.candidate_persistence.run import DEST, ROOT, build, encode, verify_inputs


def occurrence(candidate_id, year, seat='Example', regime='2007', residual=0.01,
               eligible=True, status='held'):
    return {'candidateOccurrenceId': candidate_id, 'year': year,
            'electorateName': seat, 'electorateType': 'general',
            'sourceCandidateName': 'LEE, Alex Morgan', 'candidateAffiliationKey': 'example',
            'boundaryRegime': regime, 'candidateContestStatus': status,
            'eligible': eligible, 'normalizedPremium': residual,
            'partyKey': 'example', 'methods': {'proportional': {'residual': residual},
                                             'log_odds': {'residual': residual}}}


def link(candidate_id, status='confirmed'):
    return {'candidateOccurrenceId': candidate_id, 'personId': 'person:1', 'status': status,
            'method': 'fixture', 'evidence': {'directOccurrenceEvidence': status == 'confirmed',
                                             'winnerOccurrenceIds': [candidate_id] if status == 'confirmed' else [],
                                             'evidenceRetrievedAt': None, 'evidencePublishedAt': None}}


class CandidatePersistenceTests(unittest.TestCase):
    def test_same_name_does_not_override_boundary_regime(self):
        rows = [occurrence('a', 2011), occurrence('b', 2014, regime='2014')]
        pair = build_pairs(rows, [link('a'), link('b')])['pairs'][0]
        self.assertFalse(pair['retrospectiveConfirmedEligible'])
        self.assertIn('changed_boundary_transition', pair['exclusionReasons'])
        self.assertIn('different_boundary_regime', pair['exclusionReasons'])

    def test_same_boundary_and_confirmed_links_required(self):
        rows = [occurrence('a', 2008), occurrence('b', 2011)]
        self.assertTrue(build_pairs(rows, [link('a'), link('b')])['pairs'][0]['retrospectiveConfirmedEligible'])
        pair = build_pairs(rows, [link('a'), link('b', 'probable')])['pairs'][0]
        self.assertFalse(pair['retrospectiveConfirmedEligible'])
        self.assertTrue(pair['probableSensitivityEligible'])

    def test_missing_and_excluded_premiums_remain_excluded(self):
        rows = [occurrence('a', 2020, regime='2020', residual=None),
                occurrence('b', 2023, regime='2020', eligible=False, status='cancelled')]
        pair = build_pairs(rows, [link('a'), link('b')])['pairs'][0]
        self.assertFalse(pair['retrospectiveConfirmedEligible'])
        self.assertIn('missing_normalized_premium', pair['exclusionReasons'])
        self.assertIn('missing_exact_party_counterpart', pair['exclusionReasons'])
        self.assertIn('cancelled_contest', pair['exclusionReasons'])

    def test_referential_integrity(self):
        rows = [occurrence('a', 2008)]
        with self.assertRaisesRegex(ValueError, 'Dangling identity link'):
            build_pairs(rows, [link('missing')])
        with self.assertRaisesRegex(ValueError, 'Duplicate occurrence ID'):
            build_pairs(rows + rows, [link('a')])

    def test_chronological_training_does_not_use_target_or_future(self):
        pairs = []
        for year, x, y in [(2011, 0.01, 0.02), (2011, 0.02, 0.03),
                           (2017, 0.01, 0.95), (2023, 0.03, 0.01)]:
            pairs.append({'pairId': f'{year}:{len(pairs)}', 'targetYear': year,
                          'electorateType': 'general', 'retrospectiveConfirmedEligible': True,
                          'validationEligible': True,
                          'probableSensitivityEligible': True,
                          'priorResidual': x, 'targetResidual': y,
                          'sourcePartyKey': 'x', 'targetPartyKey': 'x'})
        before = analyze(pairs)
        changed = deepcopy(pairs)
        changed[2]['targetResidual'] = -0.95
        after = analyze(changed)
        self.assertEqual(before['chronological'][1]['trainingFit'],
                         after['chronological'][1]['trainingFit'])
        self.assertEqual(before['chronological'][1]['trainingTargetYears'], [2011])
        self.assertEqual(before['chronological'][2]['trainingTargetYears'], [2011, 2017])
        self.assertNotEqual(before['chronological'][2]['trainingFit'],
                            after['chronological'][2]['trainingFit'])

    def test_intercept_and_benchmark_scoring(self):
        rows = [{'x': 0.0, 'y': 0.01}, {'x': 0.01, 'y': 0.03}]
        fitted = fit(rows)
        self.assertAlmostEqual(fitted['intercept'], 0.01)
        self.assertAlmostEqual(fitted['slope'], 2.0)
        self.assertAlmostEqual(score(rows, [0.0, 0.0])['maePP'], 2.0)
        self.assertAlmostEqual(score(rows, [row['x'] for row in rows])['rmsePP'],
                               (2.5) ** 0.5)

    def test_insufficient_validation_does_not_select_coefficient(self):
        empty = analyze([], cohort='validation')
        decision = select(empty, [empty, empty], {'confirmedCount': 0})
        self.assertIsNone(decision['selectedOperationalCoefficient'])
        self.assertFalse(decision['performanceGatePassed'])
        self.assertFalse(decision['identityBreadthGatePassed'])

    def test_official_projection_needs_winner_and_unique_profile(self):
        former = (ROOT / 'data/raw/identity-parliament-former.html').read_bytes()
        self.assertGreaterEqual(len(parse_members(former)), 100)
        rows = [{'candidateOccurrenceId': 'a', 'year': 2008,
                 'sourceCandidateName': 'ADAMS, Amy', 'candidateAffiliationKey': 'national',
                 'electorateName': 'Example', 'electorateType': 'general'}]
        members = [{'name': 'Adams, Amy', 'sourceUrl': 'https://www3.parliament.nz/en/mps-and-electorates/former-members-of-parliament/adams-amy/',
                    'serviceText': 'National Party, 8 November 2008 - 17 October 2020'}]
        self.assertEqual(project_members(rows, members, set()), [])
        projected = project_members(rows, members, {'a'})
        self.assertEqual(projected[0]['personId'], 'parliament:adams-amy')
        self.assertTrue(projected[0]['directOccurrenceEvidence'])
        self.assertIn('aliasEvidence', projected[0])

    def test_target_win_and_later_anchor_do_not_create_validation_eligibility(self):
        from scripts.models.candidate_persistence.identity import build_identity
        rows = [occurrence('a', 2020, regime='2020'), occurrence('b', 2023, regime='2020')]
        for row in rows:
            row.update({'sourceAffiliation': 'example', 'personId': None,
                        'provenance': {'sourceIds': []}})
        member_record = {'name': 'LEE, Alex Morgan',
                         'sourceUrl': 'https://www3.parliament.nz/en/mps-and-electorates/former-members-of-parliament/lee-alex/',
                         'serviceText': 'Example, 17 October 2020 - 14 October 2023'}
        def pair_with_winners(winners):
            projected = project_members(rows, [member_record], winners)
            identity = build_identity(rows, projected)
            return build_pairs(rows, identity['links'])['pairs'][0], identity
        target_only, target_identity = pair_with_winners({'b'})
        self.assertFalse(target_only['validationEligible'])
        self.assertEqual([link['status'] for link in target_identity['links']], ['probable', 'confirmed'])
        self.assertIn('source_occurrence_not_directly_corroborated', target_only['validationExclusionReasons'])
        both, _ = pair_with_winners({'a', 'b'})
        source_only, _ = pair_with_winners({'a'})
        self.assertTrue(both['validationEligible'])
        self.assertTrue(source_only['validationEligible'])
        self.assertFalse(source_only['retrospectiveConfirmedEligible'])
        self.assertEqual(both['outcomeDependencies']['validation']['targetElection'], False)

    def test_later_winner_can_adjudicate_identity_without_earlier_validation(self):
        from scripts.models.candidate_persistence.identity import build_identity
        rows = [occurrence('a', 2014, regime='2014'), occurrence('b', 2017, regime='2014'),
                occurrence('c', 2020, regime='2020')]
        for row in rows:
            row.update({'sourceAffiliation': 'example', 'personId': None,
                        'provenance': {'sourceIds': []}})
        member_record = {'name': 'LEE, Alex Morgan',
                         'sourceUrl': 'https://www3.parliament.nz/en/mps-and-electorates/former-members-of-parliament/lee-alex/',
                         'serviceText': 'Example, 17 October 2020 - 14 October 2023'}
        projected = project_members(rows, [member_record], {'c'})
        identity = build_identity(rows, projected)
        pair = next(pair for pair in build_pairs(rows, identity['links'])['pairs']
                    if pair['targetYear'] == 2017)
        self.assertEqual([link['status'] for link in identity['links']], ['probable', 'probable', 'confirmed'])
        self.assertFalse(pair['validationEligible'])
        self.assertEqual(pair['anchorOutcomeRoles'][0]['role'], 'later')
        self.assertIsNone(identity['links'][0]['evidence']['evidencePublishedAt'])

    def test_pinned_inputs_and_deterministic_outputs(self):
        contract = json.loads((DEST / 'input-contract.json').read_text())
        verify_inputs(contract)
        repeated = build()
        for name, value in repeated.items():
            self.assertEqual((DEST / name).read_bytes(), encode(value))
        coverage = repeated['person-links.json']['coverage']
        self.assertEqual((coverage['confirmedCount'], coverage['probableCount'],
                          coverage['unresolvedCount']), (169, 793, 2045))
        for person_link in repeated['person-links.json']['links']:
            if person_link['status'] == 'confirmed':
                self.assertTrue(person_link['evidence']['directOccurrenceEvidence'])
        self.assertEqual(repeated['pairs.json']['diagnostics']['outcomeIndependentValidationPairs'], 39)
        for pair in repeated['pairs.json']['pairs']:
            if pair['validationEligible']:
                self.assertFalse(pair['outcomeDependencies']['validation']['targetElection'])
                self.assertFalse(pair['outcomeDependencies']['validation']['laterElection'])
        modified = dict(contract)
        modified['data/processed/elections/2008.json'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed pinned Stage8 input'):
            verify_inputs(modified)


if __name__ == '__main__':
    unittest.main()
