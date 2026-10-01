"""Focused contracts for fixed-cohort evidence, timing and outcome separation."""

import copy
import unittest
from unittest.mock import patch

from scripts.checkpoints import adjudicate_identity as stage
from scripts.checkpoints.acquired_sources import validate_sources
from scripts.checkpoints.identity_evidence_pass import verify_snapshot


class Stage13AdjudicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = stage.read(stage.PRESERVED)['records']
        cls.claims = stage.read(stage.CLAIMS)['claims']
        cls.sources = stage.read(stage.NEW_SOURCES)['sources'] + [
            source for path in stage.OLDER_PLANS
            for source in stage.read(path)['sources']]

    def test_primary_party_claim_is_occurrence_specific(self):
        source_index = stage.validate_claims(self.claims, self.audit, self.sources)
        records, people, _ = stage.build_records(
            self.audit, stage.read(stage.SUPPLEMENT)['records'],
            stage.read(stage.ACTIVE), self.claims, source_index, stage.read(stage.PREFLIGHT))
        self.assertEqual(records[9]['primaryOccurrenceConfidence'], 'confirmed')
        self.assertIsNone(records[9]['personId'])
        self.assertFalse(people[0]['crossElectionIdentityEstablished'])
        self.assertEqual(records[30]['primaryOccurrenceConfidence'], 'unresolved')
        self.assertEqual(records[30]['adjudicatedEvidence'][0]['decision'], 'ancillary_only')
        self.assertEqual(records[19]['primaryOccurrenceConfidence'], 'unresolved')
        self.assertEqual(records[130]['primaryOccurrenceConfidence'], 'probable')
        self.assertIsNone(records[9]['adjudicatedEvidence'][0]['historicalFactDate'])
        self.assertTrue(records[9]['adjudicatedEvidence'][0]['publicationDate'])
        self.assertTrue(records[9]['adjudicatedEvidence'][0]['retrievalDate'])
        self.assertEqual(records[9]['strictPreTargetCutoffAvailability'], 'unknown')

    def test_ancillary_cannot_be_promoted_and_duplicates_fail(self):
        changed = copy.deepcopy(self.claims)
        next(item for item in changed if item['sourceTier'] == 'candidate_submitted')['decision'] = 'confirmed'
        with self.assertRaises(ValueError):
            stage.validate_claims(changed, self.audit, self.sources)
        with self.assertRaises(ValueError):
            stage.validate_claims(self.claims + [self.claims[0]], self.audit, self.sources)

    def test_source_evidence_must_be_present(self):
        changed = copy.deepcopy(self.claims)
        changed[0]['evidenceNeedle'] = 'this phrase does not occur in the pinned source'
        with self.assertRaises(ValueError):
            stage.validate_claims(changed, self.audit, self.sources)

    def test_outcome_flags_change_coverage_only(self):
        original = stage.build()
        with patch.object(stage, 'observed_outcomes', return_value={
                row['candidateOccurrenceId']: False for row in self.audit}):
            counterfactual = stage.build()
        for name in ('occurrence-evidence.json', 'person-evidence.json',
                     'relations.json', 'unresolved-conflicts.json'):
            self.assertEqual(original[name], counterfactual[name])
        self.assertNotEqual(original['coverage.json']['groups'], counterfactual['coverage.json']['groups'])

    def test_relation_endpoints_are_sampled_and_not_inferred_from_names(self):
        built = stage.build()
        occurrence_ids = {row['candidateOccurrenceId'] for row in
                          built['occurrence-evidence.json']['records']}
        relations = built['relations.json']['records']
        self.assertEqual(len(relations), 128)
        self.assertTrue(any(row['inheritedSamePersonHypothesisIds'] for row in relations))
        self.assertEqual(sum(row['retrospectiveInheritedRelation'] ==
                             'same_profile_two_direct_winner_anchors' for row in relations), 4)
        for row in relations:
            self.assertIn(row['sourceOccurrenceId'], occurrence_ids)
            self.assertIn(row['targetOccurrenceId'], occurrence_ids)
            self.assertEqual(row['verifiedRelation'], 'unresolved')

    def test_search_and_preflight_accounting(self):
        ledger = stage.read(stage.ACTIVE)
        searches = stage.validate_ledger(self.audit, ledger, stage.read(stage.PREFLIGHT),
                                         stage.read(stage.NEW_SOURCES)['sources'])
        self.assertEqual(searches, 766)
        changed = copy.deepcopy(ledger)
        changed['records'][0]['searchAttempts'].append(changed['records'][0]['searchAttempts'][0])
        with self.assertRaises(ValueError):
            stage.validate_ledger(self.audit, changed, stage.read(stage.PREFLIGHT),
                                  stage.read(stage.NEW_SOURCES)['sources'])

    def test_required_records_and_raw_bytes_remain_pinned(self):
        plan = stage.read(stage.NEW_SOURCES)
        older = [stage.read(path) for path in stage.OLDER_PLANS]
        count = validate_sources(plan, older, lambda path: (stage.ROOT / path).read_bytes())
        self.assertEqual(count, 18)
        with self.assertRaises(ValueError):
            validate_sources(plan, older, lambda path: b'changed raw source')
        snapshot = stage.read(stage.SNAPSHOT)
        registry = stage.read(stage.REGISTRY)
        verify_snapshot(snapshot, registry)
        changed = copy.deepcopy(registry)
        pinned_id = snapshot['requiredSourceRecords'][0]['id']
        changed['sources'] = [row for row in changed['sources'] if row['id'] != pinned_id]
        with self.assertRaises(ValueError):
            verify_snapshot(snapshot, changed)

    def test_deterministic_saved_outputs(self):
        built = stage.build()
        for name, payload in built.items():
            self.assertEqual((stage.ROOT / stage.OUT / name).read_bytes(), stage.encode(payload))

    def test_unrelated_source_registration_does_not_change_stage13(self):
        original = stage.build()
        self.assertNotIn('data/sources.json', original['manifest.json']['inputSha256'])
        unchanged_read = stage.read

        def registry_with_unrelated_addition(path):
            value = unchanged_read(path)
            if path == stage.REGISTRY:
                value = copy.deepcopy(value)
                value['sources'].append({'id': 'unrelated-future-stage-source'})
            return value

        with patch.object(stage, 'read', side_effect=registry_with_unrelated_addition):
            self.assertEqual(stage.build(), original)


if __name__ == '__main__':
    unittest.main()
