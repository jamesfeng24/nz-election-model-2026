"""Stage 24 fixed-input and no-outcome construction checks."""
import copy
import unittest
from unittest.mock import patch

from scripts.checkpoints import stage24_common as common
from scripts.checkpoints import stage24_construction as construction
from scripts.checkpoints import stage24_inventory as inventory


class Stage24ConstructionTests(unittest.TestCase):
    def test_pinned_inventory_and_sample(self):
        common.verify_contract()
        saved = common.read(common.PREFIX + 'input-inventory.json')
        rebuilt, _ = inventory.build()
        self.assertEqual(saved, rebuilt)
        self.assertEqual([(r['targetYear'], r['contests'], r['candidates'])
                          for r in saved['summary']], [(2017, 64, 431), (2023, 64, 459)])

    def test_saved_observed_predictions_exact_and_deterministic(self):
        output, manifest = construction.outputs()
        self.assertEqual(output, common.read(common.PREFIX + 'predictions.json'))
        self.assertEqual(manifest, common.read(common.PREFIX + 'construction-manifest.json'))
        self.assertEqual(len(output['observedReproduction']), 6)
        self.assertEqual(max(max(r['maxAbsoluteShareDifferenceA'],
                                 r['maxAbsoluteShareDifferenceB'])
                             for r in output['observedReproduction']), 0)
        for fold in output['folds']:
            self.assertEqual(set(fold['scenarios']), set(construction.SCENARIOS))
            for scenario in fold['scenarios'].values():
                self.assertEqual(set(scenario), set(construction.METHODS))
                for records in scenario.values():
                    self.assertEqual(len(records), 64)
                    for record in records:
                        self.assertAlmostEqual(sum(record['candidateShares'].values()), 1)

    def test_substitution_changes_only_party_support(self):
        candidate = {'candidateOccurrenceId': 'mapped', 'observedTargetPartySupport': .6,
                     'predictedTargetPartySupport': .3, 's0Reported': None,
                     'coupledSamePartyPercent': None}
        no_group = {'candidateOccurrenceId': 'independent', 'observedTargetPartySupport': 0,
                    'predictedTargetPartySupport': 0, 's0Reported': None,
                    'coupledSamePartyPercent': None}
        contests = [{'targetElectorateId': 'synthetic', 'candidates': [candidate, no_group]}]
        observed = construction.adapter_rows(contests, 'observed')
        predicted = construction.adapter_rows(contests, 'predicted')
        for old, new in zip(observed[0]['candidates'], predicted[0]['candidates']):
            self.assertEqual({k: v for k, v in old.items() if k != 'targetPartySupport'},
                             {k: v for k, v in new.items() if k != 'targetPartySupport'})
        params = {'status': 'fitted', 'kappa': .01, 'theta': []}
        means = {'S': .5, 'V': 0}
        a = construction.model_predictions(observed, means, 'printed', 'baseline', params)[0]['candidateShares']
        c = construction.model_predictions(predicted, means, 'printed', 'baseline', params)[0]['candidateShares']
        self.assertAlmostEqual(a['independent'], .01 / .62)
        self.assertAlmostEqual(c['independent'], .01 / .32)
        self.assertGreater(c['independent'], a['independent'])

    def test_missing_mapping_and_duplicate_destination_rejected(self):
        feature = {'targetOccurrenceId': 'c1', 'targetPartyKey': 'shared',
                   'mappingStatus': 'mapped_shared_group_single_local_destination',
                   'originalAffiliation': 'constituent', 'targetPartySupport': .2,
                   's0Reported': None, 'coupledSamePartyPercent': None,
                   'sEvidenceTier': 'unavailable', 'fallbackReasons': [], 'sourcePartyRowMass': None}
        mapping = {'candidateOccurrenceId': 'c1', 'partyKey': 'shared',
                   'mappingStatus': feature['mappingStatus'], 'sourceAffiliation': 'constituent'}
        self.assertEqual(inventory.candidate_inputs(feature, mapping, {'shared': .3})
                         ['predictedTargetPartySupport'], .3)
        with self.assertRaisesRegex(ValueError, 'Missing target ballot group'):
            inventory.candidate_inputs(feature, mapping, {})
        changed = copy.deepcopy(mapping)
        changed['partyKey'] = 'another'
        with self.assertRaisesRegex(ValueError, 'mapping changed'):
            inventory.candidate_inputs(feature, changed, {'shared': .3})
        no_group = copy.deepcopy(feature)
        no_group.update(targetPartyKey=None, targetPartySupport=0,
                        mappingStatus='verified_no_party_group_independent')
        no_map = {'candidateOccurrenceId': 'c1', 'partyKey': None,
                  'mappingStatus': no_group['mappingStatus'], 'sourceAffiliation': 'constituent'}
        self.assertEqual(inventory.candidate_inputs(no_group, no_map, {})
                         ['predictedTargetPartySupport'], 0)

    def test_target_actuals_not_read_by_construction(self):
        real_read = construction.read
        calls = []

        def guarded(path):
            calls.append(path)
            if path.endswith('actuals.json') or path.endswith('scores.json'):
                raise AssertionError('Evaluation-only data entered construction')
            return real_read(path)

        with patch.object(construction, 'read', side_effect=guarded):
            construction.outputs()
        self.assertNotIn(common.STAGE22 + 'actuals.json', calls)

    def test_observed_party_reference_cannot_change_predicted_branch(self):
        contests = [{'targetElectorateId': 'synthetic', 'candidates': [
            {'candidateOccurrenceId': 'major', 'observedTargetPartySupport': .5,
             'predictedTargetPartySupport': .3, 's0Reported': .6,
             'coupledSamePartyPercent': None},
            {'candidateOccurrenceId': 'no_group', 'observedTargetPartySupport': 0,
             'predictedTargetPartySupport': 0, 's0Reported': None,
             'coupledSamePartyPercent': None}]}]
        changed = copy.deepcopy(contests)
        changed[0]['candidates'][0]['observedTargetPartySupport'] = .8
        means = {'S': .4, 'V': 0}
        baseline = {'status': 'fitted', 'kappa': .01, 'theta': []}
        old_predicted = construction.model_predictions(
            construction.adapter_rows(contests, 'predicted'), means,
            'printed', 'baseline', baseline)
        new_predicted = construction.model_predictions(
            construction.adapter_rows(changed, 'predicted'), means,
            'printed', 'baseline', baseline)
        self.assertEqual(old_predicted, new_predicted)
        old_reference = construction.model_predictions(
            construction.adapter_rows(contests, 'observed'), means,
            'printed', 'baseline', baseline)
        new_reference = construction.model_predictions(
            construction.adapter_rows(changed, 'observed'), means,
            'printed', 'baseline', baseline)
        self.assertNotEqual(old_reference, new_reference)

    def test_changed_required_dependency_rejected(self):
        real_digest = common.digest

        def tampered(path):
            return '0' * 64 if path == common.STAGE23 + 'construction.json' else real_digest(path)

        with patch.object(common, 'digest', side_effect=tampered):
            with self.assertRaisesRegex(ValueError, 'Changed Stage24 required input'):
                common.verify_contract()


if __name__ == '__main__':
    unittest.main()
