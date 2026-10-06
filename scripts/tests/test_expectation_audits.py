"""Saved-evidence audit arithmetic; no model fits or historical bank rebuilding."""
from copy import deepcopy
import unittest
from scripts.uncertainty_expectation import audits
from scripts.uncertainty_expectation.common import read, INVENTORY


def score_row(year, seat, width, count=1):
    values = {'covered': [True]*count, 'widths': [width]*count, 'scores': [width]*count}
    return {'id': seat, 'year': year, 'groups': ['national']+['other']*(count-1),
            'ids': [str(i) for i in range(count)], 'crpsPP': [width]*count,
            **{'interval'+str(level): values for level in audits.LEVELS}}


class ExpectationAuditTests(unittest.TestCase):
    def test_equal_election_and_contest_weights_are_distinct(self):
        rows = [score_row(2014, 'a', 10), score_row(2020, 'b', 2), score_row(2020, 'c', 2)]
        self.assertAlmostEqual(audits.width_summary(rows, 'national')['intervals']['90']['widthPP'], 14/3)
        self.assertAlmostEqual(audits.width_summary(rows, 'national', True)['intervals']['90']['widthPP'], 6)
        self.assertEqual(audits.width_summary(rows, 'national')['intervals']['90']['total'], 3)

    def test_minor_options_do_not_dilute_major_widths(self):
        rows = [score_row(2014, 'a', 10, 8)]
        result = audits.width_summary(rows, 'national')
        self.assertEqual(result['coordinates'], 1)
        self.assertEqual(result['intervals']['90']['widthPP'], 10)
        self.assertEqual(audits.width_summary(rows, 'other')['coordinates'], 7)
        self.assertEqual(audits.width_summary(rows, 'labour')['status'], 'unavailable')

    def test_target_incoming_fraction_not_source_outgoing(self):
        row = {'targetElectorateId': 'seat-01', 'sourceYear': 2011, 'targetYear': 2014}
        geo = {'seat-01': {'certifiedTwoSidedExact': False}}
        flows = {'transitions': {'2011-2014': {'scopes': {'general': {
            'targetPopulationControls': {'001': 100}, 'aggregatedEdges': [
                {'targetCode': '001', 'population': 75, 'weight': {'numerator': 1, 'denominator': 10}},
                {'targetCode': '001', 'population': 25, 'weight': {'numerator': 1, 'denominator': 2}}]}}}}}
        result = audits.fragmentation(row, geo, flows)
        self.assertEqual(result['incomingPopulationFractions'], [.75, .25])
        self.assertEqual(result['value'], .375)
        flows['transitions']['2011-2014']['scopes']['general']['targetPopulationControls']['001'] = 101
        with self.assertRaisesRegex(ValueError, 'does not conserve'):
            audits.fragmentation(row, geo, flows)

    def test_unknown_and_exact_population_status(self):
        row = {'targetElectorateId': 'seat-01', 'sourceYear': 2011, 'targetYear': 2014}
        self.assertEqual(audits.fragmentation(row, {'seat-01': {'certifiedTwoSidedExact': True}}, {})['value'], 0)
        self.assertIsNone(audits.fragmentation(row, {'seat-01': {'certifiedTwoSidedExact': False}}, {'transitions': {}})['value'])

    def test_characteristics_actual_pipeline_exclude_target_outcomes(self):
        inv = read(INVENTORY)
        row = deepcopy(inv['candidateRecords'][0])
        geography = {r['targetElectorateId']: r for r in read(audits.GEOGRAPHY)['records']}
        flows = read(audits.FLOW)
        original = audits.characteristics(row, geography, flows)
        row['actual'] = list(reversed(row['actual']))
        row['winnerId'] = 'counterfactual-winner'
        self.assertEqual(audits.characteristics(row, geography, flows), original)
        row['features'][0]['supportedMass']['R'] = 0
        self.assertNotEqual(audits.characteristics(row, geography, flows)['supportedR'], original['supportedR'])

    def test_missing_major_and_duplicate_major_are_unknown(self):
        row = {'targetElectorateId': 'seat-01', 'geography': 'exact', 'groups': ['national'],
               'features': [{'supportedMass': {'R': 1}}]}
        geography = {'seat-01': {'certifiedTwoSidedExact': True}}
        self.assertIsNone(audits.characteristics(row, geography, {})['supportedR'])
        row['groups'] = ['national', 'national', 'labour']
        row['features'] = [{'supportedMass': {'R': 1}}]*3
        self.assertIsNone(audits.characteristics(row, geography, {})['supportedR'])

    def test_raw_balance_uses_log_odds_not_clr_category_count(self):
        row = {'groups': ['national', 'labour', 'other'], 'mean': [.5, .4, .1], 'actual': [.4, .5, .1]}
        value = audits.raw_residual(row, 'balance')
        changed = {'groups': ['national', 'labour', 'other', 'other'], 'mean': [.5, .4, .05, .05], 'actual': [.4, .5, .05, .05]}
        self.assertAlmostEqual(value, audits.raw_residual(changed, 'balance'), places=5)

    def test_absent_variation_and_weight_errors(self):
        self.assertEqual(audits.association([1, 1], [2, 3])['status'], 'unavailable')
        with self.assertRaisesRegex(ValueError, 'weights'):
            audits.association([1, 2], [2, 3], [1, -1])
        self.assertAlmostEqual(audits.association([1, 2, 3], [3, 2, 1])['pearson'], -1)

    def test_actual_exact_persistence_join_rejects_changed_boundaries(self):
        result = audits.dependence()
        counts = {transition: sum(p['transition'] == transition for p in result['remainingSeatErrorPersistence']['pairs'])
                  for transition in result['remainingSeatErrorPersistence']['byTransition']}
        self.assertEqual(counts, {'2014-2017': 64, '2017-2020': 34, '2020-2023': 64})
        for pair in result['remainingSeatErrorPersistence']['pairs']:
            self.assertLess(int(pair['transition'].split('-')[0]), int(pair['transition'].split('-')[1]))


if __name__ == '__main__':
    unittest.main()
