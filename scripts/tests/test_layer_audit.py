"""Stage61 layer calibration audit: frozen design, Māori exclusion, arithmetic checks and determinism."""
import unittest

import numpy as np
from scipy.special import expit, roots_hermitenorm

from scripts.layer_audit import analysis, run
from scripts.layer_audit.common import PREFIX, design, digest, equivalent, read


def summary():
    return read(PREFIX + '/summary.json')


class FrozenDesign(unittest.TestCase):
    def test_contract_pins_the_registered_rules(self):
        contract = design()
        self.assertEqual(contract['status'], 'frozen_before_scoring')
        self.assertEqual(contract['statistics']['bootstrap']['draws'], 2000)
        self.assertEqual(contract['statistics']['bootstrap']['seed'], 61)
        self.assertEqual(contract['scope']['estimatedFoldYears'], {'local_party': [2014, 2017, 2020, 2023], 'candidate': [2017, 2020, 2023]})
        self.assertEqual(contract['scope']['priorOnlyFoldYears'], {'local_party': [2011], 'candidate': [2014]})
        for key in ('adopt', 'refit', 'nationalMcmc', 'newSourcesOrAcquisition', 'frozenStage45To48OutputsTouched', 'dataSourcesJsonTouched'):
            self.assertFalse(contract['constraints'][key])

    def test_nothing_is_adopted_refit_or_simulated(self):
        s = summary()
        self.assertFalse(s['adopted'] or s['refit'] or s['nationalMcmc'])

    def test_verdict_thresholds(self):
        rules = design()['verdictRules']
        self.assertEqual(analysis.verdict_scale(0.80, [0.7, 0.9], rules), 'conservative')
        self.assertEqual(analysis.verdict_scale(0.97, [0.9, 0.99], rules), 'calibrated')  # below 1 but within 5 percent
        self.assertEqual(analysis.verdict_scale(0.80, [0.7, 1.05], rules), 'calibrated')  # interval spans one
        self.assertEqual(analysis.verdict_scale(1.12, [1.05, 1.2], rules), 'too_tight')
        self.assertEqual(analysis.verdict_scale(1.03, [1.01, 1.06], rules), 'calibrated')


class MaoriAndFrame(unittest.TestCase):
    def test_general_electorates_only_and_maori_rows_counted(self):
        frame = summary()['frame']
        self.assertEqual(frame['generalFrameRowsScored'], {'party': 321, 'candidate': 257})
        self.assertEqual(frame['maoriFrameRowsNotScored'], 35)
        self.assertEqual(frame['filter'], 'electorate type (scope), never party')
        inventory = read(analysis.INVENTORY)
        self.assertTrue(all(r['scope'] == 'general' for r in inventory['partyRecords'] + inventory['candidateRecords']))

    def test_a_non_general_record_is_rejected(self):
        real = analysis.read

        def poisoned(path):
            data = real(path)
            if path == analysis.INVENTORY:
                data = dict(data)
                data['partyRecords'] = [dict(data['partyRecords'][0], scope='maori')] + data['partyRecords'][1:]
            return data
        analysis.read = poisoned
        try:
            with self.assertRaises(ValueError):
                analysis.scalar_frame('local_party')
        finally:
            analysis.read = real

    def test_every_general_record_is_scored_for_balance_and_mass(self):
        for layer in ('local_party', 'candidate'):
            frame, skipped = analysis.scalar_frame(layer)
            self.assertEqual(skipped, {})
            self.assertEqual(sum(len(f['ids']['balance']) for f in frame.values()), 321 if layer == 'local_party' else 257)


class Arithmetic(unittest.TestCase):
    def test_location_preserves_the_conditional_mean(self):
        p = np.array([0.05, 0.3, 0.5, 0.77, 0.97])
        sd = np.array([0.2, 0.4, 0.6, 0.5, 0.9])
        loc = analysis.location(p, sd)
        nodes, weights = roots_hermitenorm(121)
        weights = weights / np.sqrt(2 * np.pi)
        expected = expit(loc[:, None] + sd[:, None] * nodes[None, :]) @ weights
        self.assertLess(np.max(np.abs(expected - p)), 1e-10)

    def test_raw_moments_equal_the_saved_stage45_descriptive_moments(self):
        for layer in ('local_party', 'candidate'):
            frame, _ = analysis.scalar_frame(layer)
            self.assertLess(max(analysis.moment_crosscheck(layer, frame).values()), 1e-9)

    def test_within_seat_moments_match_the_stage45_descriptive_moments(self):
        s = summary()
        for layer in ('local_party', 'candidate'):
            block = s['seatScale'][layer]['components']['within']
            for year, ratio in block['perElectionRatio'].items():
                self.assertAlmostEqual(ratio, block['stage45DescriptiveSeatMomentRatio'][year], places=9)

    def test_a_calibrated_synthetic_frame_scores_one(self):
        rng = np.random.default_rng(1)
        seat, shared = 0.3, 0.1
        e = rng.normal(0, np.hypot(seat, shared), 200000)
        e = e - e.mean() + rng.normal(0, shared)
        ratio = analysis.seat_ratio(e) / (seat ** 2 + shared ** 2)
        self.assertAlmostEqual(ratio, 1.0, delta=0.02)

    def test_width_arithmetic_endpoints(self):
        self.assertAlmostEqual(analysis.width_at(30., 20., 1.), 30.)
        self.assertAlmostEqual(analysis.width_at(30., 20., 0.), 20.)
        self.assertAlmostEqual(analysis.width_at(29.89, 20.84, 0.85), 27.68, delta=0.05)  # the plan's own check

    def test_ablation_widths_reproduce_the_stage47_table(self):
        widths = analysis.ablation_widths()
        self.assertAlmostEqual(widths['full'], 29.89, places=2)
        self.assertAlmostEqual(widths['no_candidate_balance'], 20.84, places=2)
        self.assertAlmostEqual(widths['national_at_mean'], 25.41, places=2)
        self.assertAlmostEqual(widths['no_candidate_within'], widths['full'], places=6)

    def test_bootstrap_streams_are_deterministic_and_label_separated(self):
        a = analysis.rng_for('x', 1).integers(0, 100, 5)
        self.assertEqual(a.tolist(), analysis.rng_for('x', 1).integers(0, 100, 5).tolist())
        self.assertNotEqual(a.tolist(), analysis.rng_for('x', 2).integers(0, 100, 5).tolist())


class StoredIntervals(unittest.TestCase):
    def test_pit_bins_agree_with_stored_coverage_flags(self):
        for key, block in summary()['storedIntervalCoverage'].items():
            for name, pool in block['pooled'].items():
                n = sum(pool['pitBins'])
                self.assertAlmostEqual(pool['pitBins'][3] / n, np.mean([block['perElection'][str(y)]['coverage']['0.5'] * block['perElection'][str(y)]['options']
                                                                       for y in pool['years']]) * len(pool['years']) / n, places=9)
                self.assertAlmostEqual(sum(pool['pitBins'][2:5]) / n, sum(block['perElection'][str(y)]['coverage']['0.8'] * block['perElection'][str(y)]['options']
                                                                           for y in pool['years']) / n, places=9)

    def test_group_labels_cover_national_labour_and_other(self):
        self.assertEqual({k.split('.')[1] for k in summary()['storedIntervalCoverage']}, {'national', 'labour', 'other'})

    def test_narrowing_never_ranks_a_shared_part(self):
        n = summary()['narrowing']
        self.assertFalse(n['rows']['candidate.shared']['rankable'])
        self.assertFalse(n['rows']['local_party.shared']['rankable'])
        self.assertNotIn('candidate.shared', n['rankingAll'])


class Determinism(unittest.TestCase):
    def test_saved_summary_regenerates(self):
        self.assertTrue(equivalent(summary(), run.build()))

    def test_manifest_hashes_match_the_saved_inputs(self):
        for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
            self.assertEqual(digest(path), expected, path)


if __name__ == '__main__':
    unittest.main()
