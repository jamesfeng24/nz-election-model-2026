"""Diagnostic-only joins, paired arithmetic, provenance and outcome isolation."""

from copy import deepcopy
import unittest

from scripts.checkpoints import model_failure_diagnostics as diagnostics
from scripts.checkpoints import model_failure_inventory as inventory


class ModelFailureDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pinned = inventory.read(
            'data/processed/checkpoints/model-failure-diagnostics/diagnostic-inventory.json')

    def test_paired_arithmetic_sign_and_denominator(self):
        row = diagnostics.paired_row('synthetic', .4, .42, .5, contestId='seat')
        self.assertAlmostEqual(row['modelErrorPP'], 2)
        self.assertAlmostEqual(row['controlErrorPP'], 10)
        self.assertAlmostEqual(row['deltaAbsolutePP'], -8)
        self.assertAlmostEqual(row['deltaSquaredPP2'], -96)
        metric = diagnostics.metrics([row])
        self.assertAlmostEqual(metric['contestEqualMeanDeltaAbsolutePP'], -8)
        self.assertAlmostEqual(metric['contestEqualModelRmsePP'], 2)

    def test_contest_equal_differs_from_candidate_equal_when_slate_sizes_differ(self):
        one = diagnostics.paired_row('a', .5, .6, .5, contestId='one')
        two = [diagnostics.paired_row(str(i), .5, .5, .6, contestId='two')
               for i in range(3)]
        metric = diagnostics.metrics([one, *two])
        self.assertAlmostEqual(metric['meanDeltaAbsolutePP'], -5)
        self.assertAlmostEqual(metric['contestEqualMeanDeltaAbsolutePP'], 0)

    def test_stage18_exact_sample_and_outcome_only_mutation(self):
        construction = inventory.read(inventory.PATHS['stage18Construction'])
        actuals = inventory.read(inventory.PATHS['stage18Actuals'])
        before = diagnostics.stage18_rows(self.pinned, construction, actuals)
        changed = deepcopy(actuals)
        first = changed['records'][0]['candidateShares']
        keys = list(first)
        first[keys[0]] += .0001
        first[keys[1]] -= .0001
        after = diagnostics.stage18_rows(self.pinned, construction, changed)
        self.assertNotEqual(before[0]['modelErrorPP'], after[0]['modelErrorPP'])
        self.assertEqual(construction, inventory.read(inventory.PATHS['stage18Construction']))
        changed['records'][0]['candidateShares'].pop(keys[0])
        with self.assertRaisesRegex(ValueError, 'denominator or ID mismatch'):
            diagnostics.stage18_rows(self.pinned, construction, changed)

    def test_stage16_pair_alignment_and_covariate_join(self):
        analysis = inventory.read(inventory.PATHS['stage16Analysis'])
        inputs = inventory.read(inventory.PATHS['stage16Inputs'])
        rows = diagnostics.stage16_rows(self.pinned, analysis, inputs)
        self.assertEqual(len(rows), 2048)
        changed = deepcopy(analysis)
        fold = next(f for f in changed['folds'] if f['targetYear'] == 2017
                    and f['party'] == 'nationalparty'
                    and f['mode'] == 'actual_observed_local_party'
                    and f['model'] == 'source_victory')
        fold['predictions'][0]['id'] = 'different-id'
        with self.assertRaisesRegex(ValueError, 'paired sample'):
            diagnostics.stage16_rows(self.pinned, changed, inputs)
        duplicate = deepcopy(inputs)
        duplicate['records'].append(duplicate['records'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            diagnostics.stage16_rows(self.pinned, analysis, duplicate)

    def test_stage16_target_outcome_changes_errors_not_saved_predictions(self):
        analysis = inventory.read(inventory.PATHS['stage16Analysis'])
        inputs = inventory.read(inventory.PATHS['stage16Inputs'])
        original = diagnostics.stage16_rows(self.pinned, analysis, inputs)
        changed = deepcopy(inputs)
        next(r for r in changed['records'] if r['id'] == original[0]['id'])['c1'] += .001
        updated = diagnostics.stage16_rows(self.pinned, analysis, changed)
        self.assertEqual([(r['id'], r['modelShare'], r['controlShare']) for r in original],
                         [(r['id'], r['modelShare'], r['controlShare']) for r in updated])
        self.assertNotEqual(original[0]['modelErrorPP'], updated[0]['modelErrorPP'])

    def test_stage6_target_outcome_changes_errors_not_saved_predictions(self):
        backtests = inventory.read(inventory.PATHS['stage6Backtests'])
        records = inventory.read(inventory.PATHS['stage6Records'])
        original = diagnostics.stage6_rows(self.pinned, backtests, records)
        changed_backtests = deepcopy(backtests)
        changed_records = deepcopy(records)
        target = original[0]['id']
        next(r for r in changed_records['records'] if r['id'] == target)[
            'targetCandidateShare'] += .001
        for group in changed_backtests['records']:
            for point in group['predictions']:
                if point['recordId'] == target:
                    point['actual'] += .001
        updated = diagnostics.stage6_rows(self.pinned, changed_backtests, changed_records)
        self.assertEqual([(r['id'], r['modelShare'], r['controlShare']) for r in original],
                         [(r['id'], r['modelShare'], r['controlShare']) for r in updated])
        self.assertNotEqual(original[0]['modelErrorPP'], updated[0]['modelErrorPP'])

    def test_stage6_and_stage11_units_remain_distinct(self):
        stage6 = diagnostics.stage6_rows(
            self.pinned, inventory.read(inventory.PATHS['stage6Backtests']),
            inventory.read(inventory.PATHS['stage6Records']))
        self.assertEqual(len(stage6), 256)
        self.assertTrue(all(row['denominator'] == 'valid_candidate_votes' for row in stage6))
        self.assertEqual(self.pinned['comparisons']['stage11']['unit'],
                         'matched_candidate_component_pp_of_all_target_party_ballots')

    def test_sparse_bins_and_raw_out_of_range_visible(self):
        self.assertEqual(diagnostics.bin_label(-.1, (0, .5, 1)), 'below_0')
        self.assertEqual(diagnostics.bin_label(1.1, (0, .5, 1)), 'above_1')
        self.assertEqual(diagnostics.bin_label(.5, (0, .5, 1)), '[0.5,1]')

    def test_pinned_input_hash_rejects_changed_artifact(self):
        changed = deepcopy(self.pinned)
        changed['inputs']['stage18Construction']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed frozen model artifact'):
            diagnostics.build(changed)


if __name__ == '__main__':
    unittest.main()
