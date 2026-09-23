"""Identity and history evidence tests for candidate persistence."""

from copy import deepcopy
import unittest

from scripts.models.candidate_persistence.identity import build_identity


def occurrence(candidate_id, year, name='LEE, Alex Morgan', party='nationalparty',
               seat='Example', scope='general'):
    return {'candidateOccurrenceId': candidate_id, 'year': year,
            'sourceCandidateName': name, 'sourceAffiliation': party,
            'candidateAffiliationKey': party, 'electorateName': seat,
            'electorateType': scope, 'personId': None,
            'provenance': {'sourceIds': [f'official-{year}']}}


def member(candidate_id, person_id='parliament:123', **fields):
    return {'candidateOccurrenceId': candidate_id, 'personId': person_id,
            'sourceUrl': 'https://www.parliament.nz/member/123', **fields}


class CandidateIdentityTests(unittest.TestCase):
    def test_probable_chain_is_separate_from_official_confirmation(self):
        rows = [occurrence('a', 2008), occurrence('b', 2011), occurrence('c', 2014, seat='Elsewhere')]
        result = build_identity(rows, [member('a')])
        self.assertEqual([(r['candidateOccurrenceId'], r['status']) for r in result['links']],
                         [('a', 'confirmed'), ('b', 'probable')])
        self.assertEqual(result['links'][1]['personId'], 'parliament:123')
        self.assertEqual(result['links'][1]['evidence']['corroboratingOccurrenceIds'], ['a'])
        self.assertEqual(result['unresolved'][0]['candidateOccurrenceId'], 'c')
        self.assertEqual(result['coverage']['occurrenceCount'], 3)
        self.assertEqual(result['coverage']['unresolvedCount'], 1)

    def test_name_alone_or_alias_does_not_link(self):
        rows = [occurrence('a', 2008),
                occurrence('b', 2011, seat='Elsewhere'),
                occurrence('c', 2014, name='Lee, Alex Morgan'),
                occurrence('d', 2017, party='labourparty')]
        result = build_identity(rows)
        self.assertEqual(result['links'], [])
        self.assertEqual(len(result['unresolved']), 4)
        self.assertEqual(result['persons'], [])

    def test_same_election_name_collision_abstains(self):
        rows = [occurrence('a', 2008), occurrence('b', 2008, seat='Elsewhere'),
                occurrence('c', 2011)]
        result = build_identity(rows)
        self.assertEqual(result['links'], [])
        self.assertEqual({r['reason'] for r in result['unresolved']},
                         {'same_election_name_collision'})

    def test_conflicting_official_identity_in_chain_rejected(self):
        rows = [occurrence('a', 2008), occurrence('b', 2011)]
        with self.assertRaisesRegex(ValueError, 'Conflicting official people'):
            build_identity(rows, [member('a', 'person:one'), member('b', 'person:two')])

    def test_simultaneous_occurrences_for_official_person_rejected(self):
        rows = [occurrence('a', 2011), occurrence('b', 2011, seat='Elsewhere')]
        with self.assertRaisesRegex(ValueError, 'simultaneous occurrences'):
            build_identity(rows, [member('a'), member('b')])

    def test_history_retains_unknown_and_left_censored_prior_tenure(self):
        rows = [occurrence('a', 2008), occurrence('b', 2011)]
        result = build_identity(rows)
        history = {r['candidateOccurrenceId']: r for r in result['historyStatus']}
        self.assertEqual(history['b']['priorLinkedOccurrenceIds'], ['a'])
        self.assertEqual(history['b']['status'], 'unknown')
        self.assertEqual(history['b']['priorParliamentaryTenure'], 'unknown')
        self.assertTrue(history['a']['leftCensored'])
        self.assertTrue(history['b']['leftCensored'])
        self.assertIsNone(history['b']['leadership'])

    def test_career_start_status_needs_explicit_evidence(self):
        rows = [occurrence('a', 2011)]
        with self.assertRaisesRegex(ValueError, 'prior-service evidence'):
            build_identity(rows, [member('a', status='first_term_incumbent')])
        result = build_identity(rows, [member('a', status='first_term_incumbent',
                                              priorServiceEvidence='official career record',
                                              leadership=False)])
        self.assertEqual(result['historyStatus'][0]['status'], 'first_term_incumbent')
        self.assertFalse(result['historyStatus'][0]['leftCensored'])
        self.assertFalse(result['historyStatus'][0]['leadership'])

    def test_official_name_variant_requires_preserved_alias_evidence(self):
        rows = [occurrence('a', 2011)]
        with self.assertRaisesRegex(ValueError, 'alias evidence'):
            build_identity(rows, [member('a', sourceName='Alex Morgan Lee')])
        result = build_identity(rows, [member('a', sourceName='Alex Morgan Lee',
                                              aliasEvidence='official name correspondence')])
        self.assertEqual(result['links'][0]['evidence']['officialSourceName'], 'Alex Morgan Lee')
        self.assertEqual(result['links'][0]['evidence']['aliasEvidence'], 'official name correspondence')

    def test_deterministic_order_and_immutable_source(self):
        rows = [occurrence('b', 2011), occurrence('a', 2008), occurrence('c', 2023, seat='Elsewhere')]
        before = deepcopy(rows)
        first = build_identity(rows)
        second = build_identity(list(reversed(rows)))
        self.assertEqual(first, second)
        self.assertEqual(rows, before)

    def test_referential_and_identity_input_integrity(self):
        rows = [occurrence('a', 2008)]
        with self.assertRaisesRegex(ValueError, 'Duplicate occurrence ID'):
            build_identity(rows + rows)
        with self.assertRaisesRegex(ValueError, 'Unknown or duplicate official occurrence'):
            build_identity(rows, [member('missing')])
        changed = deepcopy(rows)
        changed[0]['personId'] = 'source-mutation'
        with self.assertRaisesRegex(ValueError, 'Source person ID must remain null'):
            build_identity(changed)


if __name__ == '__main__':
    unittest.main()
