"""Stage 9 numerical, leakage, cohort audit and provenance regression tests."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.models.freshman_incumbency.analysis_run import build, validate_tenure_source_plan
from scripts.models.freshman_incumbency.model import analyze, fit, prepare_rows, score, select
from scripts.models.freshman_incumbency.outcome_audit import audit
from scripts.models.freshman_incumbency.run import DEST, ROOT, encode
from scripts.validate.source_files import verify_source_files


def row(pair_id, target_year, x, y, treatment):
    return {'pairId': pair_id, 'personId': pair_id, 'targetYear': target_year,
            'treatment': treatment, 'xPP': x, 'yPP': y}


class FreshmanAnalysisTests(unittest.TestCase):
    def test_joint_effect_and_benchmarks_use_identical_units(self):
        rows = [row(f'{group}:{x}', 2017, x, 1 + 2*x + 3*group, group)
                for group in (0, 1) for x in (0, 1, 2)]
        fitted = fit(rows)
        self.assertAlmostEqual(fitted['interceptPP'], 1)
        self.assertAlmostEqual(fitted['priorSlope'], 2)
        self.assertAlmostEqual(fitted['freshmanEffectPP'], 3)
        self.assertEqual(score(rows, [1 + 2*r['xPP'] + 3*r['treatment'] for r in rows])['maePP'], 0)
        self.assertEqual(score(rows, [0]*len(rows))['n'], len(rows))
        self.assertEqual(score(rows, [r['xPP'] for r in rows])['n'], len(rows))

    def test_holdout_training_never_reads_its_target_outcomes(self):
        rows = [row(f'{year}:{group}:{x}', year, x, 1 + x + group, group)
                for year in (2011, 2017, 2023) for group in (0, 1) for x in (0, 1)]
        first = analyze(rows)
        changed = deepcopy(rows)
        changed[4]['yPP'] += 100
        second = analyze(changed)
        self.assertEqual(first['chronological'][1]['trainingFit'],
                         second['chronological'][1]['trainingFit'])
        self.assertNotEqual(first['chronological'][2]['trainingFit'],
                            second['chronological'][2]['trainingFit'])
        self.assertEqual(first['chronological'][1]['trainingTargetYears'], [2011])
        self.assertEqual(first['chronological'][2]['trainingTargetYears'], [2011, 2017])

    def test_allowed_pair_set_removes_outcome_dependent_link(self):
        inventory = [{'pairId': 'keep', 'primaryEligible': True, 'exclusionReasons': [],
                      'electorateType': 'general', 'tenureCategory': 'first_term',
                      'personId': 'p1', 'sourceYear': 2008, 'targetYear': 2011,
                      'sourceIdentityStatus': 'probable', 'targetIdentityStatus': 'probable'},
                     {'pairId': 'drop', 'primaryEligible': True, 'exclusionReasons': [],
                      'electorateType': 'general', 'tenureCategory': 'experienced',
                      'personId': 'p2', 'sourceYear': 2008, 'targetYear': 2011,
                      'sourceIdentityStatus': 'confirmed', 'targetIdentityStatus': 'confirmed'}]
        pairs = [{'pairId': pair_id, 'priorResidual': 0.01, 'targetResidual': 0.02}
                 for pair_id in ('keep', 'drop')]
        self.assertEqual([r['pairId'] for r in prepare_rows(inventory, pairs, allowed_pair_ids={'keep'})],
                         ['keep'])

    def test_insufficient_evidence_selects_null(self):
        empty = analyze([])
        decision = select(empty, [empty, empty, empty], 0,
                          [{'targetYear': 2017, 'confirmedTargetLosers': 0, 'targetWinners': 1},
                           {'targetYear': 2023, 'confirmedTargetLosers': 0, 'targetWinners': 1}])
        self.assertIsNone(decision['selectedOperationalFreshmanEffectPP'])
        self.assertFalse(decision['gates']['twoChronologicalHoldoutsIdentified'])

    def test_real_counterfactual_removes_only_documented_three_links(self):
        inventory = json.loads((DEST / 'inventory.json').read_bytes())['records']
        profiles = json.loads((DEST / 'tenure-evidence.json').read_bytes())['profiles']
        result, kept, evaluated = audit(ROOT, inventory, profiles)
        amendment = json.loads((DEST / 'postfit-audit-amendment.json').read_bytes())
        self.assertEqual(result['counts']['lostPrimaryPairIds'], amendment['excludedPairIds'])
        self.assertEqual(len(evaluated), 90)
        self.assertEqual(len(kept), 122)
        self.assertEqual(result['counts']['counterfactualNewComparablePairIds'], [])
        self.assertTrue(all(row['classificationStable'] for row in result['records']
                            if row['pairId'] in evaluated))

    def test_stage_specific_raw_contract_rejects_changed_missing_duplicate_sources(self):
        real = json.loads((ROOT / 'data/source-plans/freshman-incumbency-tenure-sources.json').read_bytes())
        self.assertEqual(len(real['sources']), 108)
        validate_tenure_source_plan(real)
        verify_source_files(ROOT, real)
        altered = deepcopy(real)
        del altered['sources'][0]['licence']
        with self.assertRaisesRegex(ValueError, 'Incomplete Stage 9 source provenance'):
            validate_tenure_source_plan(altered)
        altered = deepcopy(real)
        altered['sources'][1]['url'] = altered['sources'][0]['url']
        with self.assertRaisesRegex(ValueError, 'Duplicate Stage 9 source URL'):
            validate_tenure_source_plan(altered)
        altered = deepcopy(real)
        altered['sources'].pop()
        with self.assertRaisesRegex(ValueError, 'Unexpected Stage 9 tenure source inventory'):
            validate_tenure_source_plan(altered)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / 'data/raw/profile.html'
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b'official profile fixture')
            source = {'id': 'profile', 'rawPath': 'data/raw/profile.html',
                      'sha256': hashlib.sha256(raw.read_bytes()).hexdigest()}
            plan = {'schemaVersion': 1, 'sources': [source]}
            verify_source_files(root, plan)
            with self.assertRaisesRegex(ValueError, 'Duplicate source id'):
                verify_source_files(root, {'schemaVersion': 1, 'sources': [source, source]})
            raw.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                verify_source_files(root, plan)
            raw.unlink()
            with self.assertRaisesRegex(ValueError, 'Missing raw file'):
                verify_source_files(root, plan)

    def test_analysis_outputs_reproduce_from_pinned_inputs(self):
        for name, value in build().items():
            self.assertEqual((DEST / name).read_bytes(), encode(value))


if __name__ == '__main__':
    unittest.main()
