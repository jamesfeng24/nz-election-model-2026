"""Stage55 replacement-effect test: frozen design, sample rules, chronology, scoring arithmetic and determinism."""
import json
import unittest
from collections import Counter

import numpy as np

from scripts.balance_scale.data import environments
from scripts.replacement_effect import analysis, run, sample
from scripts.replacement_effect.common import DESIGN, FOLD_YEARS, PREFIX, ROOT, design, digest, equivalent, read


def load(name):
    return read(PREFIX + '/' + name)


def fake_rows(deltas, years=None, base=1.0):
    years = years or [2017] * len(deltas)
    return [{'year': y, 'arms': {'C': {'crps': base, 'sqError': 1.0, 'nlpd': 0.0},
                                  'X': {'crps': base + d, 'sqError': 1.0 + d, 'nlpd': 0.0}}}
            for d, y in zip(deltas, years)]


class FrozenDesign(unittest.TestCase):
    def test_contract_pins_the_registered_rule(self):
        contract = design()
        self.assertEqual(contract['arms'].keys(), {'C', 'K', 'P', 'T'})
        rule = contract['decisionRule']
        self.assertEqual((rule['relativeCrpsThreshold'], rule['minimumAffectedSeats']), (0.003, 20))
        self.assertEqual(rule['bootstrap'], {'draws': 2000, 'seed': 55, 'level': 0.9,
                                             'scheme': 'seats resampled with replacement within election, pooled equal-seat mean'})
        self.assertEqual(contract['sample']['primary']['transitionTypes'], ['retirement'])
        self.assertIsNone(contract['constraints']['selectedOperationalReplacementEffectPP'])
        self.assertFalse(contract['constraints']['composedScoring'])
        self.assertEqual(contract['folds'], {'2017': [2011, 2014], '2020': [2011, 2014, 2017], '2023': [2011, 2014, 2017, 2020]})

    def test_nothing_is_adopted_and_stage10_shift_stays_undeployed(self):
        summary = load('summary.json')
        self.assertIsNone(summary['selectedOperationalReplacementEffectPP'])
        self.assertFalse(summary['stage10ShiftMinus6p64ppDeployed'])
        self.assertFalse(summary['adopted'])
        manifest = load('manifest.json')
        self.assertFalse(manifest['dataSourcesJsonTouched'])
        self.assertFalse(manifest['newNationalInference'])
        self.assertFalse(load('input-contract.json')['dataSourcesJsonTouched'])


class SampleRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = sample.rows()

    def test_counts_follow_the_stage51_ledger(self):
        self.assertEqual(len(self.table), 333)
        self.assertEqual(Counter(r['relation'] for r in self.table), {'continuation': 258, 'candidate_change': 75})
        summary = sample.summarise(self.table)
        self.assertEqual((summary['primary'], summary['extended'], summary['primaryNoListOnly']), (47, 59, 39))
        self.assertEqual(summary['changesExcludedFromPrimaryByReason']['maori_scope'], 3)

    def test_primary_rows_obey_the_registered_rule(self):
        spec = design()['sample']['primary']
        for r in sample.select(self.table, 'primary'):
            self.assertEqual((r['scope'], r['relation'], r['transitionType']), ('general', 'candidate_change', 'retirement'))
            self.assertFalse(set(r['tags']) & set(spec['excludedTags']))
            self.assertTrue(np.isfinite(r['RoldFraction']) and np.isfinite(r['RnewFraction']))
            self.assertTrue(r['sourceOccurrenceId'] and r['targetOccurrenceId'])

    def test_by_election_party_change_and_maori_rows_never_enter_any_arm_sample(self):
        for name in sample.SAMPLES:
            for r in sample.select(self.table, name):
                self.assertEqual(r['scope'], 'general')
                self.assertNotIn(r['transitionType'], ('by_election_succession', 'by_election_party_change', 'party_change',
                                                       'boundary_complication'))

    def test_join_is_by_occurrence_id_and_matches_stage7(self):
        occ = sample.occurrence_index()
        for r in self.table[:50]:
            self.assertEqual(r['RoldFraction'], occ[r['sourceOccurrenceId']]['normalizedPremium'])


class Chronology(unittest.TestCase):
    def test_fits_use_only_earlier_target_years(self):
        table = sample.rows()
        folds = analysis.fit_folds(table, 'primary')
        for year in FOLD_YEARS:
            self.assertTrue(all(y < year for y in folds[year]['trainingTargetYears']))
            train = sample.select(table, 'primary', below=year)
            self.assertEqual(folds[year]['trainingSeats'], len(train))
            self.assertAlmostEqual(folds[year]['K']['a'], np.mean([r['RnewFraction'] for r in train]), places=12)
            self.assertTrue(0 <= folds[year]['P']['rho'] <= 1)

    def test_rho_is_constrained_and_a_is_resolved_at_the_bound(self):
        rows = [{'RoldFraction': x, 'RnewFraction': y, 'targetYear': 2011, 'primary': True}
                for x, y in [(0.0, 0.05), (0.1, -0.05), (0.2, -0.15)]]
        fold = analysis.fit_folds(rows, 'primary')[2017]
        self.assertEqual(fold['P']['rho'], 0.0)
        self.assertTrue(fold['P']['atBound'])
        self.assertAlmostEqual(fold['P']['a'], np.mean([0.05, -0.05, -0.15]), places=12)


class Arithmetic(unittest.TestCase):
    def test_gaussian_crps_matches_the_closed_form(self):
        self.assertAlmostEqual(float(analysis.crps(0.3, 0.3, 2.0)), 2.0 * (2 / np.sqrt(2 * np.pi) - 1 / np.sqrt(np.pi)), places=12)
        grid = np.linspace(-12, 12, 480001)
        numeric = np.trapezoid((analysis.norm.cdf(grid, 0.4, 1.3) - (grid >= 1.1)) ** 2, grid)
        self.assertAlmostEqual(float(analysis.crps(1.1, 0.4, 1.3)), float(numeric), places=4)

    def test_control_arm_reproduces_the_stage48_balance_means_and_scales(self):
        env = environments()
        for row in load('seat-scores.json')['primary']:
            e = env[row['year']]
            k = e['ids'].index(row['seat'])
            self.assertAlmostEqual(row['arms']['C']['p'], float(e['p'][k]), places=12)
            self.assertEqual(row['arms']['C']['maxAbsLogWeightShift'], 0.0)
            self.assertAlmostEqual(row['totalSd'], float(np.hypot(e['seat'], e['shared'])), places=12)
            self.assertAlmostEqual(row['v'], float(e['v'][k]), places=12)

    def test_arms_move_only_the_replaced_candidate_and_renormalise(self):
        records = {r['targetElectorateId']: r for r in read('data/processed/uncertainty/inventory.json')['candidateRecords']}
        row = load('seat-scores.json')['primary'][0]
        rec = records[row['seat']]
        self.assertAlmostEqual(sum(rec['mean']), 1.0, places=9)
        self.assertEqual(row['arms']['T']['rHatPP'].keys(), set(map(str, [i for i in range(len(rec['ids']))
                                                                         if rec['ids'][i] in {
                                                                             r['targetOccurrenceId'] for r in sample.rows()
                                                                             if r['key'] in row['replacedKeys']}])))

    def test_decision_labels_follow_the_registered_rule(self):
        rule = design()['decisionRule']
        better = analysis.compare(fake_rows([-0.02] * 24, [2017] * 8 + [2020] * 8 + [2023] * 8), 'X', 'C', rule)
        self.assertEqual(better['label'], 'IMPROVES')
        worse = analysis.compare(fake_rows([0.02] * 24, [2017] * 8 + [2020] * 8 + [2023] * 8), 'X', 'C', rule)
        self.assertEqual(worse['label'], 'WORSE')
        flat = analysis.compare(fake_rows([0.0001] * 24, [2017] * 8 + [2020] * 8 + [2023] * 8), 'X', 'C', rule)
        self.assertEqual(flat['label'], 'NEGLIGIBLE')
        small = analysis.compare(fake_rows([-0.02] * 10), 'X', 'C', rule)
        self.assertEqual(small['label'], 'INSUFFICIENT')
        noisy = analysis.compare(fake_rows([-0.5, 0.45] * 12, [2017] * 8 + [2020] * 8 + [2023] * 8, base=1.0), 'X', 'C', rule)
        self.assertEqual(noisy['label'], 'MIXED' if abs(noisy['relativeDeltaCrps']) >= 0.003 else 'NEGLIGIBLE')

    def test_finding_table(self):
        rule = design()['decisionRule']

        def result(k, pk, pc):
            return {'K vs C': {'label': k}, 'P vs K': {'label': pk}, 'P vs C': {'label': pc}}
        self.assertEqual(analysis.finding(result('IMPROVES', 'IMPROVES', 'IMPROVES'), rule), 'partial_transfer')
        self.assertEqual(analysis.finding(result('IMPROVES', 'NEGLIGIBLE', 'IMPROVES'), rule), 'constant_shift_only')
        self.assertEqual(analysis.finding(result('NEGLIGIBLE', 'WORSE', 'WORSE'), rule), 'neutral_adequate')
        self.assertEqual(analysis.finding(result('MIXED', 'WORSE', 'WORSE'), rule), 'mixed_report_to_james')
        self.assertEqual(analysis.finding(result('NEGLIGIBLE', 'NEGLIGIBLE', 'IMPROVES'), rule), 'mixed_report_to_james')


class Stage10Gap(unittest.TestCase):
    def test_missing_2008_seats_are_macron_name_keys(self):
        gap = load('stage10-gap.json')
        first = gap['pairs'][0]
        self.assertEqual((first['sourceYear'], first['targetYear'], first['generalSeatsInSourceElection'],
                          first['seatsInStage10Inventory']), (2008, 2011, 63, 55))
        self.assertEqual({d['seat'] for d in first['missing']},
                         {'Kaikoura', 'Mangere', 'Ohariu', 'Otaki', 'Rangitikei', 'Tamaki', 'Taupo', 'Te Atatu'})
        self.assertTrue(all(d['cause'] == 'target_name_differs_only_by_macron' for d in first['missing']))
        changes = [h['key'] for h in gap['ledgerRowsInMissingSeats'] if h['key'].startswith('2008-2011')
                   and h['relation'] == 'candidate_change']
        self.assertEqual(sorted(changes), ['2008-2011|LAB|Te Atatu', '2008-2011|NAT|Rangitikei', '2008-2011|NAT|Tamaki'])


class Determinism(unittest.TestCase):
    def test_saved_artifacts_regenerate_and_manifest_hashes_hold(self):
        table, results, scores, summary = run.build()
        self.assertTrue(equivalent(load('summary.json'), json.loads(json.dumps(summary))))
        self.assertTrue(equivalent(load('scores.json'), json.loads(json.dumps(scores))))
        self.assertTrue(equivalent(load('sample.json')['rows'], json.loads(json.dumps(table))))
        for path, expected in load('input-contract.json')['inputHashes'].items():
            self.assertEqual(digest(path), expected, path)
        for path, expected in load('manifest.json')['derivedArtifacts'].items():
            self.assertEqual(digest(path), expected, path)
        self.assertTrue((ROOT / DESIGN).exists())


if __name__ == '__main__':
    unittest.main()
