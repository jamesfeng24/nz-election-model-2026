"""Stage 16 chronology, evidence separation, nesting and interval contracts."""
import copy
import json
import unittest
from unittest.mock import patch

import numpy as np

from scripts.models.conditional_nat_lab_response import analysis, common, inventory, model, run
from scripts.models.conditional_nat_lab_response.common import DEST, YEARS, read, validate_inputs


def synthetic_rows():
    rows = []
    for i in range(20):
        x, w = (i % 10 - 4) / 100, i // 10
        y = .02 + .6*x - .03*w
        rows.append({'id': f'synthetic-{i}', 'party': 'synthetic-only',
            'sourceYear': 2008, 'targetYear': 2011, 'x': x, 'y': y,
            'sourceWon': w, 'c0': .4, 'c1': .4+y, 'p0': .4,
            'partyInputs': {mode: [.4+x, .4+x] for mode in model.MODES}})
    return rows


class ConditionalResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((DEST/'specification.json').read_bytes())
        cls.base = read('data/processed/models/party-vote-transform/backtest-records.json')['records']
        cls.stage6 = read('data/processed/models/nat-lab-elasticity/records.json')
        cls.elections = {y: read(f'data/processed/elections/{y}.json') for y in YEARS}
        cls.evidence = inventory.evidence_bundle()
        cls.inventory = inventory.build_inventory(cls.base, cls.stage6, cls.elections, cls.evidence)
        cls.rows = analysis.assemble(cls.inventory, cls.elections, cls.base)

    def test_inventory_full_frame_unknown_is_not_continuation(self):
        self.assertEqual(len(self.inventory['records']), 384)
        self.assertEqual(sum(r['eligible'] for r in self.inventory['records']), 382)
        self.assertTrue(all(r['primaryCrossElectionRelation'] == 'unresolved' for r in self.inventory['records']))
        self.assertEqual(sum(r['inheritedStage13Relation'] is not None for r in self.inventory['records']), 48)
        self.assertTrue(all(r['targetCandidateIncumbency'] == 'unknown' for r in self.inventory['records']))

    def test_complete_inventory_ignores_target_results(self):
        changed = copy.deepcopy(self.elections)
        base = copy.deepcopy(self.base)
        evidence = copy.deepcopy(self.evidence)
        for y in (2011, 2017, 2023):
            for seat in changed[y]['electorates']:
                seat['winnerCandidateId'] = None
                seat['validCandidateVotes'] = -1
                for c in seat['candidates']:
                    c['elected'] = not c['elected']
                    c['votes'] = -1
        for r in base:
            r['actualTargetShare'] = -1
        for r in evidence['occurrences']:
            if r['year'] in (2011, 2017, 2023):
                r['sourcePublishedCandidateVotes'] = -1
                r['candidateShare'] = -1
                r['normalizedPremium'] = -1
        self.assertEqual(inventory.build_inventory(base, self.stage6, changed, evidence), self.inventory)

    def test_exact_ols_and_nuisance_matched_restrictions(self):
        rows = synthetic_rows()
        fitted = model.fit(rows, self.spec['models']['source_victory'])
        for key, expected in [('alpha', .02), ('beta', .6), ('gamma', -.03)]:
            self.assertAlmostEqual(fitted[key], expected, places=12)
        for name in ('source_victory_beta0', 'source_victory_beta1'):
            restricted = model.fit(rows, self.spec['models'][name])
            beta = self.spec['models'][name]['fixedBeta']
            for w in (0, 1):
                rs = [r for r in rows if r['sourceWon'] == w]
                offset = sum(r['y']-beta*r['x'] for r in rs)/len(rs)
                self.assertAlmostEqual(restricted['alpha']+w*restricted['gamma'], offset)
            self.assertNotEqual(restricted['alpha'], fitted['alpha'])

    def test_missing_status_rank_and_earliest_training_abstain(self):
        definition = self.spec['models']['source_victory']
        self.assertEqual(model.fit([], definition)['reason'], 'no_earlier_training_transition')
        missing = synthetic_rows();missing[0]['sourceWon'] = None
        self.assertEqual(model.fit(missing, definition)['reason'], 'unknown_source_victory')
        singular = synthetic_rows()
        for r in singular:r['x'] = r['sourceWon']
        self.assertEqual(model.fit(singular, definition)['reason'], 'rank_deficient_or_near_singular')
        self.assertEqual(model.fit([], self.spec['models']['beta1'])['beta'], 1)

    def test_signed_interval_propagation_no_midpoint_or_clipping(self):
        row = synthetic_rows()[0];row['partyInputs']['additive'] = [.2, .6]
        fitted = {'status': 'available', 'alpha': .1, 'beta': -2., 'gamma': 0.}
        p = model.predict(row, fitted, 'additive')
        self.assertAlmostEqual(p['bounds'][0], .1)
        self.assertAlmostEqual(p['bounds'][1], .9)
        self.assertIsNone(p['point'])
        row['partyInputs']['additive'] = [0, 1]
        p = model.predict(row, fitted, 'additive')
        self.assertTrue(p['outOfRangePossible'])
        self.assertLess(p['bounds'][0], 0)
        self.assertGreater(p['bounds'][1], 1)

    def test_fixed_transforms_and_benchmark_arithmetic(self):
        row = synthetic_rows()[0]
        for name in ('beta0','beta1'):
            fitted = model.fit([], self.spec['models'][name])
            pred = model.predict(row,fitted,'actual_observed_local_party')
            expected = row['c0'] + fitted['beta']*row['x']
            self.assertAlmostEqual(pred['point'],expected)
            metrics = model.score([pred],[row])
            self.assertAlmostEqual(metrics['maePP'][0],100*abs(expected-row['c1']))
            self.assertAlmostEqual(metrics['biasPP'][0],100*(expected-row['c1']))

    def test_heldout_outcomes_only_score_not_fit_or_predict(self):
        for party in ('nationalparty','labourparty'):
            own = [r for r in self.rows if r['party']==party]
            for year in (2017,2023):
                test = [r for r in own if r['targetYear']==year]
                changed = copy.deepcopy(own)
                for r in changed:
                    if r['targetYear']==year:r['c1']=0;r['y']=-r['c0']
                train = model.training_rows(own,test)
                altered_train = model.training_rows(changed,test)
                self.assertEqual(train,altered_train)
                self.assertLess(max(r['targetYear'] for r in train),test[0]['sourceYear'])
                fitted = model.fit(train,self.spec['models']['source_victory'])
                p = [model.predict(r,fitted,'actual_observed_local_party') for r in test]
                altered_test = [r for r in changed if r['targetYear']==year]
                self.assertEqual(p,[model.predict(r,fitted,'actual_observed_local_party') for r in altered_test])
                self.assertNotEqual(model.score(p,test),model.score(p,altered_test))

    def test_full_adapter_and_fold_pipeline_target_mutation(self):
        baseline = analysis.analyses(self.rows, self.spec)
        for year in (2011, 2017, 2023):
            changed = copy.deepcopy(self.elections)
            for seat in changed[year]['electorates']:
                seat['winnerCandidateId'] = None
                seat['validCandidateVotes'] = max(1, len(seat['candidates']))
                for candidate in seat['candidates']:
                    candidate['votes'] = 1
                    candidate['elected'] = not candidate['elected']
            updated_inventory = inventory.build_inventory(self.base, self.stage6, changed, self.evidence)
            self.assertEqual(updated_inventory, self.inventory)
            updated_rows = analysis.assemble(updated_inventory, changed, self.base)
            updated = analysis.analyses(updated_rows, self.spec)
            before = [r for r in baseline['folds'] if r['targetYear'] == year]
            after = [r for r in updated['folds'] if r['targetYear'] == year]
            for original, altered in zip(before, after):
                self.assertEqual(original['fit'], altered['fit'])
                self.assertEqual(original['predictions'], altered['predictions'])
                self.assertEqual(original['eligibleCount'], altered['eligibleCount'])

    def test_original_stage6_chronological_results_agree(self):
        old = read('data/processed/models/nat-lab-elasticity/backtests.json')['records']
        for record in old:
            if record['mode']!='chronological' or record['model']!='fitted':continue
            own = [r for r in self.rows if r['party']==record['party']]
            test = [r for r in own if r['sourceYear']==record['holdoutSourceYear']]
            fitted = model.fit(model.training_rows(own,test),self.spec['models']['stage6_zero_intercept'])
            self.assertAlmostEqual(fitted['beta'],record['beta'],places=12)
            scores = model.score([model.predict(r,fitted,record['baseline']) for r in test],test)
            for metric in ('maePP','rmsePP','biasPP'):
                self.assertAlmostEqual(scores[metric][0],record['metrics'][metric],places=10)

    def test_independent_numpy_coefficients(self):
        for party in ('nationalparty','labourparty'):
            rows=[r for r in self.rows if r['party']==party]
            fit=model.fit(rows,self.spec['models']['source_victory'])
            x=np.array([[1,r['x'],r['sourceWon']] for r in rows]);y=np.array([r['y'] for r in rows])
            expected,_,rank,_=np.linalg.lstsq(x,y,rcond=None)
            self.assertEqual(rank,3)
            np.testing.assert_allclose([fit['alpha'],fit['beta'],fit['gamma']],expected,atol=1e-12,rtol=0)

    def test_independent_chronological_source_victory_errors(self):
        for party in ('nationalparty', 'labourparty'):
            for year in (2017, 2023):
                own = [r for r in self.rows if r['party'] == party]
                test = [r for r in own if r['targetYear'] == year]
                train = model.training_rows(own, test)
                x = np.array([[1, r['x'], r['sourceWon']] for r in train])
                y = np.array([r['y'] for r in train])
                coefficient = np.linalg.lstsq(x, y, rcond=None)[0]
                fitted = model.fit(train, self.spec['models']['source_victory'])
                for mode in model.MODES:
                    design = np.array([[1, r['partyInputs'][mode][0]-r['p0'], r['sourceWon']] for r in test])
                    error = np.array([r['c0']-r['c1'] for r in test]) + design @ coefficient
                    expected = [np.mean(np.abs(error))*100, np.sqrt(np.mean(error**2))*100, np.mean(error)*100]
                    actual = model.score([model.predict(r, fitted, mode) for r in test], test)
                    np.testing.assert_allclose([actual[k][0] for k in ('maePP','rmsePP','biasPP')], expected, atol=1e-10, rtol=0)

    def test_dependency_and_source_contract_rejections(self):
        with patch.object(common, 'digest', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'Changed Stage 16 input'):
                validate_inputs()
        registry = read('data/sources.json')
        for operation in ('modify', 'delete', 'duplicate', 'append'):
            changed = copy.deepcopy(registry)
            required = read('data/source-plans/stage15-conditional-ledger-sources.json')['sources'][0]['id']
            index = next(i for i, r in enumerate(changed['sources']) if r['id'] == required)
            if operation == 'modify':
                changed['sources'][index]['url'] = 'https://invalid.example/changed'
            elif operation == 'delete':
                del changed['sources'][index]
            elif operation == 'duplicate':
                changed['sources'].append(copy.deepcopy(changed['sources'][index]))
            else:
                changed['sources'].append({'id': 'unrelated-test-only'})
            def substituted(path):
                return changed if path == 'data/sources.json' else read(path)
            with patch.object(common, 'read', side_effect=substituted):
                if operation == 'append':
                    self.assertGreater(validate_inputs(), 612)
                else:
                    with self.assertRaises(ValueError):
                        validate_inputs()

    def test_input_integrity_and_reproduction(self):
        self.assertGreater(validate_inputs(),612)
        outputs=run.build()
        for name,value in outputs.items():
            self.assertEqual((DEST/name).read_bytes(),run.encode(value))


if __name__=='__main__':unittest.main()
