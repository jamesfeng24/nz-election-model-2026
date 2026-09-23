"""Stage 10 event, outcome-independence and provenance regressions."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.models.replacement_candidate.analysis import score, select
from scripts.models.replacement_candidate.analysis_run import build as build_analysis_output
from scripts.models.replacement_candidate.inventory import build_inventory
from scripts.models.replacement_candidate.run import build as build_inventory_output, encode
from scripts.validate.source_files import verify_source_files


ROOT = Path(__file__).resolve().parents[2]


def occurrence(candidate_id, year, name, seat='Example', party='nationalparty'):
    return {'candidateOccurrenceId': candidate_id, 'year': year,
            'electorateType': 'general', 'electorateName': seat,
            'partyKey': party, 'candidateAffiliationKey': party,
            'sourceCandidateName': name, 'boundaryRegime': '2014',
            'candidateContestStatus': 'held', 'eligible': True,
            'normalizedPremium': 0.02, 'methods': {
                'proportional': {'residual': 0.01},
                'log_odds': {'residual': 0.01}}}


def link(candidate_id, person, anchor_id=None, anchor_date=None):
    anchors = ([{'candidateOccurrenceId': anchor_id, 'electionDate': anchor_date}]
               if anchor_id else [])
    return {'candidateOccurrenceId': candidate_id, 'personId': person,
            'status': 'confirmed' if candidate_id == anchor_id else 'probable',
            'personExistenceStatus': 'official_profile_corroborated',
            'method': 'test', 'evidence': {'anchorOccurrences': anchors}}


CONTINUITY = [{'sourceYear': 2014, 'targetYear': 2017,
               'canonicalPartyId': 'nationalparty', 'status': 'eligible',
               'source': {'sourceKey': 'nationalparty'},
               'target': {'sourceKey': 'nationalparty'}}]


class ReplacementInventoryTests(unittest.TestCase):
    def build(self, target_name='TARGET, T', target_person='target',
              target_anchor_date='26 November 2011', target_party='nationalparty',
              target_status='held', target_residual=0.01):
        source = occurrence('source', 2014, 'SOURCE, S')
        target = occurrence('target', 2017, target_name, party=target_party)
        target['candidateContestStatus'] = target_status
        target['normalizedPremium'] = target_residual
        prior = occurrence('prior', 2011, 'TARGET, T', seat='Other')
        links = [link('source', 'source-person', 'source', '20 September 2014'),
                 link('target', target_person, 'prior', target_anchor_date)]
        return build_inventory([source, target, prior], links, CONTINUITY,
                               {'source', 'prior'}, [])['records']

    def test_distinct_pre_target_official_people_support_replacement(self):
        row = next(r for r in self.build() if r['sourceYear'] == 2014)
        self.assertEqual(row['identityClass'], 'supported_replacement')
        self.assertTrue(row['primaryEligible'])
        self.assertEqual(row['incomingCareerHistory']['status'], 'unknown')
        self.assertEqual(row['departureReason'], 'unknown')

    def test_target_winner_anchor_is_retrospective_only(self):
        source = occurrence('source', 2014, 'SOURCE, S')
        target = occurrence('target', 2017, 'TARGET, T')
        links = [link('source', 'source-person', 'source', '20 September 2014'),
                 link('target', 'target-person', 'target', '23 September 2017')]
        before = build_inventory([source, target], links, CONTINUITY, {'source'}, [])['records'][0]
        after = build_inventory([source, target], links, CONTINUITY,
                                {'source', 'target'}, [])['records'][0]
        self.assertEqual(before['identityClass'], 'retrospective_distinct_people')
        self.assertFalse(before['primaryEligible'])
        self.assertEqual(before['identityClass'], after['identityClass'])
        self.assertEqual(before['exclusionReasons'], after['exclusionReasons'])

    def test_name_variant_does_not_become_replacement(self):
        source = occurrence('source', 2014, 'SAME, Full Name')
        target = occurrence('target', 2017, 'SAME, F')
        links = [link('source', 'one', 'source', '20 September 2014'),
                 link('target', 'one', 'source', '20 September 2014')]
        row = build_inventory([source, target], links, CONTINUITY, {'source'}, [])['records'][0]
        self.assertEqual(row['identityClass'], 'retrospective_or_ambiguous_continuation')
        self.assertFalse(row['primaryEligible'])

    def test_unlinked_different_name_is_unresolved(self):
        source = occurrence('source', 2014, 'SOURCE, S')
        target = occurrence('target', 2017, 'OTHER, O')
        row = build_inventory([source, target], [], CONTINUITY, {'source'}, [])['records'][0]
        self.assertEqual(row['identityClass'], 'unresolved_identity')
        self.assertFalse(row['primaryEligible'])
        target['sourceCandidateName'] = source['sourceCandidateName']
        same_name = build_inventory([source, target], [], CONTINUITY,
                                    {'source'}, [])['records'][0]
        self.assertEqual(same_name['identityClass'], 'unresolved_identity')

    def test_challenger_party_switch_cancelled_and_boundary_exclusions(self):
        row = next(r for r in self.build() if r['sourceYear'] == 2014)
        self.assertTrue(row['primaryEligible'])
        source = occurrence('source', 2014, 'SOURCE, S')
        target = occurrence('target', 2017, 'TARGET, T')
        prior = occurrence('prior', 2011, 'TARGET, T', seat='Other')
        links = [link('source', 'source-person', 'source', '20 September 2014'),
                 link('target', 'target-person', 'prior', '26 November 2011')]
        for change, reason in (({'boundaryRegime': '2017'}, 'different_boundary_regime'),
                               ({'candidateContestStatus': 'cancelled'}, 'cancelled_contest'),
                               ({'normalizedPremium': None}, 'missing_normalized_premium')):
            changed = {**target, **change}
            result = build_inventory([source, changed, prior], links, CONTINUITY,
                                     {'source', 'prior'}, [])['records']
            self.assertIn(reason, result[0]['exclusionReasons'])
        switched = {**target, 'partyKey': 'labourparty',
                    'candidateAffiliationKey': 'labourparty'}
        self.assertFalse(build_inventory([source, switched, prior], links,
                                         CONTINUITY, {'source', 'prior'}, [])['records'])
        result = build_inventory([source, target, prior], links, CONTINUITY,
                                 {'prior'}, [])['records']
        self.assertIn('outgoing_challenger_separate_diagnostic',
                      result[0]['exclusionReasons'])

    def test_maori_winner_status_stays_unknown(self):
        source = occurrence('source', 2014, 'SOURCE, S')
        target = occurrence('target', 2017, 'TARGET, T')
        source['electorateType'] = target['electorateType'] = 'maori'
        row = build_inventory([source, target], [], CONTINUITY, set(), [])['records'][0]
        self.assertIsNone(row['sourceWasElected'])
        self.assertEqual(row['outgoingStatus'], 'source_winner_unknown')
        self.assertIn('maori_winner_status_unavailable', row['exclusionReasons'])


class ReplacementAnalysisTests(unittest.TestCase):
    def test_benchmark_arithmetic_and_null_selection(self):
        rows = [{'priorResidual': .02, 'targetResidual': .01},
                {'priorResidual': -.01, 'targetResidual': .03}]
        zero = score(rows, lambda row: 0)
        carry = score(rows, lambda row: row['priorResidual'])
        self.assertAlmostEqual(zero['maePP'], 2)
        self.assertAlmostEqual(carry['maePP'], 2.5)
        self.assertAlmostEqual(carry['rmsePP'], (8.5) ** .5)
        analysis = {'primaryTransitionCounts': [{'treatment': 0, 'comparator': 3}],
                    'chronologicalUnavailableReason': 'no treated events'}
        self.assertIsNone(select(analysis)['selectedOperationalReplacementEffectPP'])

    def test_pinned_inventory_and_source_bytes(self):
        generated = build_inventory_output()
        for name, value in generated.items():
            self.assertEqual((ROOT / 'data/processed/models/replacement-candidate' / name).read_bytes(),
                             encode(value))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / 'data/raw/example.txt'
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b'first')
            import hashlib
            source = {'id': 'required', 'rawPath': 'data/raw/example.txt',
                      'sha256': hashlib.sha256(b'first').hexdigest()}
            registry = {'schemaVersion': 1, 'sources': [source]}
            verify_source_files(root, registry)
            raw.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                verify_source_files(root, registry)
            raw.unlink()
            with self.assertRaisesRegex(ValueError, 'Missing raw file'):
                verify_source_files(root, registry)

    def test_full_identity_rebuild_and_analysis_are_reproducible(self):
        generated = build_analysis_output()
        destination = ROOT / 'data/processed/models/replacement-candidate'
        for name, value in generated.items():
            self.assertEqual((destination / name).read_bytes(), encode(value))
        audit = generated['cohort-audit.json']
        self.assertEqual(audit['counts']['unstablePrimary'], 0)
        self.assertGreater(audit['counts']['unstable'], 0)
        self.assertEqual(generated['analysis.json']['primaryTreatmentCount'], 0)
        self.assertIsNone(generated['selection.json']['selectedOperationalReplacementEffectPP'])


if __name__ == '__main__':
    unittest.main()
