"""Pre-fit tenure, identity and outcome-independence checks for Stage 9."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.models.freshman_incumbency.inventory import build_inventory, classify_tenure
from scripts.models.freshman_incumbency.run import DEST, build, encode
from scripts.models.freshman_incumbency.tenure import parse_profile


def profile(rows, first='2008-11-08'):
    return {'sourceId': 'official:1', 'sourceUrl': 'https://example.test/lee',
            'displayName': 'Lee, Alex', 'publishedDate': None, 'retrievedAt': '2026-09-23',
            'firstParliamentElectedDate': first, 'serviceRows': rows,
            'tenureEvidenceStatus': 'complete_dated_table'}


def service(start, end=None, kind='electorate', seat='Example'):
    return {'serviceKind': kind, 'electorateName': seat if kind == 'electorate' else None,
            'party': 'Example Party', 'startDate': start, 'endDate': end}


def occurrence(candidate_id, year):
    return {'candidateOccurrenceId': candidate_id, 'year': year,
            'sourceCandidateName': 'LEE, Alex Morgan', 'electorateName': 'Example',
            'candidateAffiliationKey': 'exampleparty'}


def pair():
    return {'pairId': 'source->target', 'sourceOccurrenceId': 'source',
            'targetOccurrenceId': 'target', 'personId': 'person:1',
            'sourceYear': 2008, 'targetYear': 2011, 'electorateType': 'general',
            'sourceElectorate': 'Example', 'sourceIdentityStatus': 'confirmed',
            'targetIdentityStatus': 'probable', 'probableSensitivityEligible': True,
            'targetResidual': 0.99, 'priorResidual': 0.01}


class FreshmanInventoryTests(unittest.TestCase):
    def test_first_electorate_win_and_prior_list_are_separate(self):
        source = occurrence('source', 2008)
        rows = [service('2008-11-08'), service('2005-09-17', '2008-11-08', 'list')]
        p = profile(rows, '2005-09-17')
        self.assertEqual(classify_tenure(source, 2011, p)[0], 'first_term')
        record = build_inventory([pair()], [source, occurrence('target', 2011)], [p], {'source'})['records'][0]
        self.assertTrue(record['priorListService'])
        self.assertFalse(record['primaryEligible'])
        self.assertIn('prior_list_service_primary_exclusion', record['exclusionReasons'])

    def test_prior_tenure_seat_switch_and_former_service(self):
        source = occurrence('source', 2008)
        continuing = profile([service('2005-09-17', '2008-11-08', seat='Earlier'),
                              service('2008-11-08')], '2005-09-17')
        self.assertEqual(classify_tenure(source, 2011, continuing)[1], 'continuing_incumbent_seat_switch')
        former = deepcopy(continuing)
        former['serviceRows'][0]['endDate'] = '2007-01-01'
        self.assertEqual(classify_tenure(source, 2011, former)[1], 'returning_former_electorate_mp')
        earlier_return = profile([service('1993-11-06', '1996-10-12', seat='Earlier'),
                                  service('2005-09-17')], '1993-11-06')
        self.assertEqual(classify_tenure(source, 2011, earlier_return)[1],
                         'returning_former_electorate_mp')
        experienced = profile([service('2005-09-17')], '2005-09-17')
        self.assertEqual(classify_tenure(source, 2011, experienced)[0], 'experienced')

    def test_off_cycle_entry_and_interrupted_service(self):
        source = occurrence('source', 2014)
        off_cycle = profile([service('2011-03-05')], '2011-03-05')
        self.assertEqual(classify_tenure(source, 2017, off_cycle)[1], 'off_cycle_electorate_entry')
        interrupted = profile([service('2014-09-20', '2016-01-01')], '2014-09-20')
        self.assertEqual(classify_tenure(source, 2017, interrupted)[1], 'service_interrupted_before_target')

    def test_unknown_career_and_uncertain_occurrence_identity(self):
        source = occurrence('source', 2008)
        p = profile([service('2008-11-08')], first=None)
        self.assertEqual(classify_tenure(source, 2011, p)[0], 'uncertain')
        uncertain_pair = pair()
        uncertain_pair['targetIdentityStatus'] = 'unresolved'
        record = build_inventory([uncertain_pair], [source, occurrence('target', 2011)],
                                 [profile([service('2008-11-08')])], {'source'})['records'][0]
        self.assertIn('unresolved_occurrence_identity', record['exclusionReasons'])

    def test_target_and_later_wins_cannot_change_pre_result_eligibility(self):
        rows = [occurrence('source', 2008), occurrence('target', 2011)]
        p = profile([service('2008-11-08')])
        baseline = build_inventory([pair()], rows, [p], {'source'})['records'][0]
        target_wins = build_inventory([pair()], rows, [p], {'source', 'target', 'later'})['records'][0]
        self.assertEqual(baseline, target_wins)
        changed_outcome = pair()
        changed_outcome['targetResidual'] = -0.99
        self.assertEqual(baseline, build_inventory([changed_outcome], rows, [p], {'source'})['records'][0])

    def test_profile_parser_preserves_published_and_historical_dates(self):
        html = b'''<title>Lee, Alex - New Zealand Parliament</title>
        <span class="publish-date"><strong>Published date:</strong> 08 Sep 2026</span>
        Date first elected: 8 November 2008
        <table><tr><th>Member for / List</th><th>Party</th><th>Start</th><th>End</th></tr>
        <tr><td>Example</td><td>Example Party</td><td>08/11/2008</td><td>26/11/2011</td></tr></table>'''
        got = parse_profile(html, {'id': 'source', 'url': 'https://example.test', 'retrievedAt': '2026-09-23'})
        self.assertEqual(got['publishedDate'], '2026-09-08')
        self.assertEqual(got['serviceRows'][0]['startDate'], '2008-11-08')

    def test_pinned_inventory_outputs_reproduce(self):
        outputs = build()
        for name, value in outputs.items():
            self.assertEqual((DEST / name).read_bytes(), encode(value))


if __name__ == '__main__':
    unittest.main()
