"""Stage60 stronger balance-scale test: frozen design, chronology, exclusion, decision rule and sealed outputs."""
import copy
import unittest
import numpy as np
from scripts.balance_scale.common import equivalent
from scripts.balance_shrink import decision as D, evaluation as E, fit as F, report, summary as S, verification as V
from scripts.balance_shrink.common import PREFIX, DESIGN_DOC, design, digest, read, ROOT, YEARS, arms


def load(name):
    return read(PREFIX + '/' + name)


def lean(year, ident, crps, multiplier=1.0, covered=True, width=10.0, score=5.0, energy=6.0):
    return {'id': ident, 'year': year, 'crpsPP': [crps, crps], 'energyPP': energy, 'multiplier': multiplier, 'majorCRPSPrefix': crps,
            'intervals': {str(l): {'covered': [covered, covered], 'widths': [width, width], 'scores': [score, score]} for l in (50, 80, 90)}}


class FrozenDesign(unittest.TestCase):
    def test_contract_pins_the_registered_rule(self):
        spec = design()
        self.assertEqual(spec['armOrder'], ['control', 'grid95', 'grid90', 'grid85', 'grid80', 'free', 'penalised'])
        self.assertEqual(spec['candidateArms'], ['grid95', 'grid90', 'grid85', 'grid80', 'free'])
        self.assertEqual([spec['arms'][a]['multiplier'] for a in ('control', 'grid95', 'grid90', 'grid85', 'grid80')], [1.0, 0.95, 0.9, 0.85, 0.8])
        self.assertEqual(spec['arms']['penalised']['role'], 'reference')
        self.assertEqual(spec['folds'], {'2014': [], '2017': [2014], '2020': [2014, 2017], '2023': [2014, 2017, 2020]})
        rule = spec['decision']
        self.assertEqual(rule['improves']['crpsMaterialityPP'], 0.01)
        self.assertEqual(rule['improves']['minimumFoldsNegative'], 2)
        self.assertEqual((rule['coverageFloor']['nominalMargin'], rule['coverageFloor']['alreadyUndercoveringMargin']), (0.10, 0.05))
        self.assertEqual(rule['coverageFloor']['elections'], [2014, 2017, 2020, 2023])
        self.assertEqual(rule['selection']['bootstrap']['seed'], 60)
        self.assertIsNone(rule['operationalAdoption'])
        self.assertEqual(spec['layer']['excludedByElectorateType'], 'maori')
        self.assertFalse(spec['composedWidthImplication']['newBank'])

    def test_consumed_inputs_and_design_are_pinned(self):
        pinned = load('input-contract.json')
        self.assertFalse(pinned['dataSourcesJsonTouched'])
        self.assertIn(DESIGN_DOC, pinned['inputHashes'])
        for path, expected in pinned['inputHashes'].items():
            self.assertEqual(digest(path), expected, path)

    def test_nothing_is_adopted(self):
        decision, manifest = load('decision.json'), load('manifest.json')
        self.assertIsNone(decision['operationalAdoption'])
        self.assertFalse(manifest['dataSourcesJsonTouched'])
        self.assertFalse(manifest['newNationalInference'])
        self.assertFalse(manifest['newComposedBank'])
        self.assertIsNone(manifest['operationalAdoption'])


class Chronology(unittest.TestCase):
    def test_free_arm_uses_only_earlier_elections(self):
        fits = load('fit.json')
        for year, fold in fits['folds'].items():
            self.assertTrue(all(y < int(year) for y in fold['trainingYears']))
        self.assertEqual(fits['folds']['2014']['multipliers']['free'], 1.0)
        self.assertEqual(fits['folds']['2014']['multipliers']['penalised'], 1.0)
        self.assertEqual(fits['descriptive2026Refit']['trainingYears'], [2014, 2017, 2020, 2023])
        self.assertFalse(fits['descriptive2026Refit']['scored'])

    def test_free_arm_reproduces_the_stage48_unpenalised_constant_and_ridge_is_off(self):
        fits = load('fit.json')
        old = read('data/processed/balance-scale/fit.json')['folds']
        self.assertEqual(fits['ridge'], 0.0)
        for year in ('2017', '2020', '2023'):
            self.assertAlmostEqual(fits['folds'][year]['free']['a'], old[year]['unpenalisedConstant']['a'], places=6)
            self.assertAlmostEqual(fits['folds'][year]['multipliers']['penalised'], float(np.exp(old[year]['constant']['theta'][0])), places=12)
            self.assertFalse(fits['folds'][year]['free']['boundContact'])
        multipliers = [fits['folds'][y]['multipliers']['free'] for y in ('2017', '2020', '2023')]
        self.assertTrue(all(0.7 < m < 0.9 for m in multipliers))

    def test_fit_is_deterministic(self):
        self.assertTrue(equivalent(load('fit.json'), F.build(), 1e-6))


class Exclusion(unittest.TestCase):
    def test_every_scored_record_is_a_general_electorate(self):
        records = read('data/processed/uncertainty/inventory.json')['candidateRecords']
        self.assertEqual({r['scope'] for r in records}, {'general'})
        self.assertEqual(load('evaluation.json')['seatsByElection'], {'2014': 64, '2017': 64, '2020': 65, '2023': 64})
        self.assertTrue(load('verification.json')['exclusion']['passed'])

    def test_a_non_general_record_is_refused_by_electorate_type_not_party(self):
        records = copy.deepcopy(read('data/processed/uncertainty/inventory.json'))
        records['candidateRecords'][0]['scope'] = 'maori'
        original = E.read
        E.read = lambda path: records if path == E.INVENTORY else original(path)
        try:
            with self.assertRaises(ValueError):
                E.candidate_rows(records['candidateRecords'][0]['targetYear'])
        finally:
            E.read = original


class DecisionRule(unittest.TestCase):
    rule = design()['decision']

    def comparison(self, **changes):
        base = {'deltaMajorCRPSPP': -0.05, 'deltaMajorIntervalScorePP': -0.5, 'deltaEnergyPP': -0.05,
                'coverageGuard': {'50': {'passed': True}, '80': {'passed': True}, '90': {'passed': True}}, 'foldsNegative': 3,
                'resolution': {'passed': True}}
        base.update(changes)
        return base

    def test_classes_follow_the_stage48_rule(self):
        rule = self.rule['improves']
        self.assertEqual(D.classify(self.comparison(), rule, True), 'IMPROVES')
        self.assertEqual(D.classify(self.comparison(deltaMajorCRPSPP=-0.005), rule, True), 'NEGLIGIBLE')
        self.assertEqual(D.classify(self.comparison(deltaMajorCRPSPP=0.02), rule, True), 'WORSE')
        self.assertEqual(D.classify(self.comparison(foldsNegative=1), rule, True), 'MIXED')
        self.assertEqual(D.classify(self.comparison(deltaMajorIntervalScorePP=0.1), rule, True), 'MIXED')
        self.assertEqual(D.classify(self.comparison(deltaEnergyPP=0.03), rule, True), 'MIXED')
        self.assertEqual(D.classify(self.comparison(resolution={'passed': False}), rule, True), 'MIXED')
        self.assertEqual(D.classify(self.comparison(), rule, False), 'MIXED')

    def summary(self, control, arm):
        cell = lambda c50, c80: {'majorIntervals': {'50': {'coverage': c50}, '80': {'coverage': c80}}}
        return {str(y): {'control': cell(*control[y]), 'arm': cell(*arm[y])} for y in (2014, 2017, 2020, 2023)}

    def test_coverage_floor_and_the_already_undercovering_term(self):
        floor = self.rule['coverageFloor']
        control = {2014: (0.367, 0.812), 2017: (0.68, 0.906), 2020: (0.508, 0.892), 2023: (0.68, 0.945)}
        ok = {2014: (0.352, 0.76), 2017: (0.60, 0.875), 2020: (0.41, 0.85), 2023: (0.63, 0.91)}
        self.assertTrue(D.coverage_floor(self.summary(control, ok), 'arm', floor)['passed'])
        # 2014 may lose at most 0.05 against its own control; elsewhere the floor is nominal - 0.10
        low_2014 = {**ok, 2014: (0.30, 0.76)}
        result = D.coverage_floor(self.summary(control, low_2014), 'arm', floor)
        self.assertFalse(result['passed'])
        self.assertAlmostEqual(result['rows']['2014:50']['threshold'], 0.317, places=12)
        low_2020 = {**ok, 2020: (0.39, 0.85)}
        result = D.coverage_floor(self.summary(control, low_2020), 'arm', floor)
        self.assertFalse(result['rows']['2020:50']['passed'])
        self.assertAlmostEqual(result['rows']['2020:50']['threshold'], 0.40, places=12)
        bad_80 = {**ok, 2014: (0.352, 0.688)}
        self.assertFalse(D.coverage_floor(self.summary(control, bad_80), 'arm', floor)['rows']['2014:80']['passed'])

    def test_selection_picks_the_least_aggressive_arm_within_noise_of_the_best(self):
        order = arms()
        summary = {'grid95': {'majorCRPSPP': 3.40, 'meanMultiplier': 0.95}, 'grid90': {'majorCRPSPP': 3.38, 'meanMultiplier': 0.90},
                   'grid85': {'majorCRPSPP': 3.365, 'meanMultiplier': 0.85}, 'free': {'majorCRPSPP': 3.36, 'meanMultiplier': 0.82}}
        intervals = {'grid95': [0.03, 0.05], 'grid90': [-0.001, 0.04], 'grid85': [-0.002, 0.02]}
        chosen = D.choose(['grid95', 'grid90', 'grid85', 'free'], summary, self.rule, order, lambda a, b: intervals[a])
        self.assertEqual((chosen['best'], chosen['recommended']), ('free', 'grid90'))
        self.assertEqual(chosen['descriptiveAlternative'], 'grid85')
        self.assertTrue(chosen['withinNoise']['free']['withinNoise'])
        self.assertFalse(chosen['withinNoise']['grid95']['withinNoise'])
        self.assertEqual(D.choose([], summary, self.rule, order, None)['recommended'], None)

    def test_bootstrap_is_seeded_and_resamples_within_election(self):
        records = {'control': [lean(y, f'{y}-{i}', 3.0) for y in (2014, 2017, 2020, 2023) for i in range(5)]}
        spec = self.rule['selection']['bootstrap']
        a, sizes = D.bootstrap_indices(records, spec)
        b, _ = D.bootstrap_indices(records, spec)
        self.assertEqual(sizes, [5, 5, 5])
        self.assertTrue(all(np.array_equal(x, y) for x, y in zip(a, b)))
        delta = np.full(15, -0.1)
        self.assertEqual(D.bootstrap_interval(delta, a, sizes, spec), D.bootstrap_interval(delta, b, sizes, spec))
        low, high = D.bootstrap_interval(delta, a, sizes, spec)
        self.assertAlmostEqual(low, -0.1, places=12)
        self.assertAlmostEqual(high, -0.1, places=12)

    def test_summary_equal_seat_arithmetic(self):
        records = [lean(2017, 'a', 2.0, covered=True, width=8.0), lean(2017, 'b', 4.0, covered=False, width=12.0)]
        s = S.summarize(records)
        self.assertEqual(s['majorCRPSPP'], 3.0)
        self.assertEqual((s['majorIntervals']['50']['covered'], s['majorIntervals']['50']['total']), (2, 4))
        self.assertEqual(s['majorIntervals']['90']['widthPP'], 10.0)

    def test_composed_arithmetic_is_exact_at_the_endpoints(self):
        entry = {'national': {'full': 30.0, 'no_candidate_balance': 20.0}}
        self.assertAlmostEqual(D.width_at(entry, 'national', 1.0, 0.7), 30.0, places=12)
        self.assertAlmostEqual(D.width_at(entry, 'national', 0.0, 1.0), 20.0, places=12)
        self.assertLess(D.width_at(entry, 'national', 0.8, 0.7), 30.0)
        self.assertLess(D.width_at(entry, 'national', 0.8, 1.0), D.width_at(entry, 'national', 0.8, 0.7))


class SealedOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evaluation, cls.fits, cls.decision = load('evaluation.json'), load('fit.json'), load('decision.json')

    def test_arms_are_paired_on_identical_seats(self):
        ids = [r['id'] for r in self.evaluation['records']['control']]
        self.assertEqual(len(ids), 257)
        for a in arms():
            self.assertEqual([r['id'] for r in self.evaluation['records'][a]], ids)

    def test_control_and_reference_equal_stage48_exactly(self):
        verification = load('verification.json')
        self.assertTrue(verification['passed'])
        for arm in verification['equalsStage48'].values():
            self.assertEqual(set(arm['maximumAbsoluteDifference'].values()), {0, 0.0})

    def test_2014_free_and_reference_are_control_and_grid_differs(self):
        identity = load('verification.json')['identity2014']
        self.assertTrue(identity['freeIdenticalToControl'] and identity['penalisedIdenticalToControl'] and identity['gridArmsDifferFromControl'])

    def test_decision_is_reproduced_and_internally_consistent(self):
        self.assertTrue(equivalent(self.decision, D.build()))
        finding, selection = self.decision['finding'], self.decision['selection']
        if selection['recommended']:
            self.assertEqual(finding, f'recommend_{selection["recommended"]}_for_james_signoff')
            self.assertIn(selection['recommended'], selection['qualifying'])
        for arm in selection['qualifying']:
            self.assertEqual(self.decision['classification'][arm], 'IMPROVES')
            self.assertTrue(self.decision['coverageFloor'][arm]['passed'])
        self.assertNotIn('penalised', selection['qualifying'])

    def test_manifest_is_reproduced(self):
        from scripts.balance_shrink import manifest
        self.assertEqual(load('manifest.json'), manifest.build())

    def test_verification_is_reproduced(self):
        self.assertTrue(equivalent(load('verification.json'), V.build()))

    def test_findings_document_is_reproduced(self):
        self.assertEqual((ROOT / 'docs/stage60-balance-shrink-findings.md').read_text(), report.build())

    def test_two_seats_regenerate_to_the_saved_scores(self):
        from scripts.balance_scale.simulate import scaled
        from scripts.uncertainty.construction import scale_for
        from scripts.uncertainty.metrics import crps
        from scripts.uncertainty_expectation.simulation import component
        rows = E.candidate_rows(2023)
        fit = scale_for(read('data/processed/uncertainty-revision/scales.json'), 'candidate', 2023)['scales']
        for row in (rows[0], rows[-1]):
            for arm in ('grid85', 'free'):
                q, _ = component(row, scaled(fit, self.fits['folds']['2023']['multipliers'][arm]), design()['components']['draws'])
                major = [k for k, g in enumerate(row['groups']) if g in ('national', 'labour')]
                value = float(np.mean(crps(100 * q[:, major], 100 * np.asarray(row['actual'])[major])))
                saved = next(r for r in self.evaluation['records'][arm] if r['id'] == row['targetElectorateId'])
                self.assertAlmostEqual(value, float(np.mean(saved['crpsPP'])), places=9)

    def test_one_whole_election_is_reproduced(self):
        """2017 replays every seat and arm (about 30 seconds); the four-election replay is `evaluation --check` (about 90 seconds)."""
        records, gaps, _ = E.year_task(2017)
        for arm in arms():
            saved = [r for r in self.evaluation['records'][arm] if r['year'] == 2017]
            self.assertTrue(equivalent(saved, records[arm], 1e-10), arm)
        self.assertEqual(len(gaps), self.evaluation['seatsByElection']['2017'])

if __name__ == '__main__':
    unittest.main()
