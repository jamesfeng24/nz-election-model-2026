"""Stage 10 event, outcome-independence and provenance regressions."""

from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import json
import shutil
import unittest

from scripts.models.replacement_candidate.analysis import chronological, fit, score, select
from scripts.models.replacement_candidate.analysis_run import build as build_analysis_output
from scripts.models.replacement_candidate.identity_evidence import (
    build_person_links, validate_adjudications, verify_identity_snapshot)
from scripts.models.replacement_candidate.inventory import build_inventory
from scripts.models.replacement_candidate.maori_winners import build_overlay, verify_snapshot
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

    def test_maori_winner_overlay_is_separate_from_general_primary(self):
        source = occurrence('source', 2014, 'SOURCE, S')
        target = occurrence('target', 2017, 'TARGET, T')
        source['electorateType'] = target['electorateType'] = 'maori'
        row = build_inventory([source, target], [], CONTINUITY, set(), [],
                              maori_winner_ids={'source'})['records'][0]
        self.assertTrue(row['sourceWasElected'])
        self.assertEqual(row['outgoingStatus'], 'source_winner')
        self.assertIn('maori_scope_separate_diagnostic', row['exclusionReasons'])
        self.assertFalse(row['primaryEligible'])


class ReplacementAnalysisTests(unittest.TestCase):
    def test_benchmark_arithmetic_and_null_selection(self):
        rows = [{'priorResidual': .02, 'targetResidual': .01},
                {'priorResidual': -.01, 'targetResidual': .03}]
        zero = score(rows, lambda row: 0)
        carry = score(rows, lambda row: row['priorResidual'])
        self.assertAlmostEqual(zero['maePP'], 2)
        self.assertAlmostEqual(carry['maePP'], 2.5)
        self.assertAlmostEqual(carry['rmsePP'], (8.5) ** .5)
        analysis = build_analysis_output()['analysis.json']
        decision = select(analysis, acquisition_independent=False)
        self.assertIsNone(decision['selectedOperationalReplacementEffectPP'])
        self.assertIn('acquisition_independent_of_target_later_outcomes', decision['failedGates'])

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
        self.assertEqual(generated['analysis.json']['primaryTreatmentCount'], 5)
        self.assertEqual(generated['analysis.json']['primaryComparatorCount'], 39)
        self.assertIsNone(generated['selection.json']['selectedOperationalReplacementEffectPP'])

    def test_pretarget_newcomer_and_list_mp_without_prior_win(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / 'data/raw/nomination.html'
            raw.parent.mkdir(parents=True)
            raw.write_text('<p>Candidate New selected for Example in 2017.</p>')
            source = occurrence('source', 2014, 'SOURCE, S')
            target = occurrence('target', 2017, 'NEW, Candidate')
            links = [link('source', 'parliament:source', 'source', '20 September 2014')]
            evidence = {'eventId': 'source->target', 'sourceYear': 2014, 'targetYear': 2017,
                        'electorateName': 'Example', 'sourceEvidenceId': 'parliament:source',
                        'targetEvidenceId': 'nomination', 'sourceFactDate': '2014-09-20',
                        'targetFactDate': '2017-05-01', 'sourceNameProof': 'Source S',
                        'targetNameProof': 'Candidate New', 'sourceRetrievalAt': None,
                        'targetRetrievalAt': '2026-09-24', 'sourcePublicationDate': None,
                        'targetPublicationDate': '2017-05-01',
                        'sourceRoute': 'source_winner_anchor',
                        'targetRoute': 'pre_result_party_selection', 'role': 'primary',
                        'targetOutcomeDependent': False, 'sourceOccurrenceConfidence': 'confirmed',
                        'targetOccurrenceConfidence': 'confirmed'}
            plan = {'records': [{'eventId': 'source->target', 'externalPriority': True}]}
            sources = [{'id': 'nomination', 'rawPath': 'data/raw/nomination.html',
                        'retrievedAt': '2026-09-24', 'publishedDate': '2017-05-01'}]
            accepted = validate_adjudications(root, plan, {'records': [evidence]},
                                               [source, target], sources, [], [], links)
            before = build_inventory([source, target], links, CONTINUITY, {'source'}, [],
                                     accepted)['records'][0]
            after = build_inventory([source, target], links, CONTINUITY,
                                    {'source', 'target'}, [], accepted)['records'][0]
            self.assertEqual(before['identityClass'], 'supported_replacement')
            self.assertTrue(before['primaryEligible'])
            self.assertEqual(before['primaryEligible'], after['primaryEligible'])
            changed = {**evidence, 'targetFactDate': '2017-09-24'}
            with self.assertRaisesRegex(ValueError, 'target/later historical fact'):
                validate_adjudications(root, plan, {'records': [changed]},
                                       [source, target], sources, [], [], links)

    def test_dated_profiles_alias_and_incoming_loser_are_explicit(self):
        outputs = build_inventory_output()
        records = outputs['inventory.json']['records']
        links = outputs['person-links.json']['links']
        self.assertEqual(len(links), 20)
        self.assertEqual(len({link['candidateOccurrenceId'] for link in links}), 20)
        self.assertTrue(all(link['careerHistoryStatus'] ==
                            'separate_dated_tenure_overlay_or_unknown' for link in links))
        by_seat = {(r['sourceYear'], r['electorateName']): r for r in records
                   if r['stage10IdentityEvidence']}
        wall = by_seat[2008, 'Manurewa']
        self.assertTrue(wall['primaryEligible'])
        self.assertTrue(wall['incomingCareerHistory']['priorList'])
        self.assertFalse(wall['incomingCareerHistory']['priorElectorate'])
        for year, seat in ((2008, 'Botany'), (2008, 'Mana'),
                           (2014, 'Mt Albert'), (2020, 'Tauranga')):
            record = by_seat[year, seat]
            self.assertEqual(record['identityClass'], 'supported_by_election_successor')
            self.assertFalse(record['primaryEligible'])
        self.assertEqual(by_seat[2014, 'Hutt South']['identityClass'],
                         'retrospective_alias_replacement')
        self.assertFalse(by_seat[2014, 'Hutt South']['primaryEligible'])
        rongotai = by_seat[2020, 'Rongotai']
        self.assertTrue(rongotai['primaryEligible'])
        elected = {c['id'] for e in json.loads((ROOT / 'data/processed/elections/2023.json').read_text())['electorates']
                   for c in e['candidates'] if c['elected']}
        self.assertNotIn(rongotai['targetOccurrenceId'], elected)

    def test_new_occurrence_link_conflicts_and_dangling_ids_fail(self):
        evidence = {'sourceOccurrenceConfidence': 'confirmed',
                    'targetOccurrenceConfidence': 'confirmed',
                    'sourceRoute': 'source_winner_anchor',
                    'targetRoute': 'pre_result_party_selection',
                    'sourceEvidenceId': 'source-evidence',
                    'targetEvidenceId': 'target-evidence',
                    'sourceFactDate': '2014-09-20', 'targetFactDate': '2017-05-01',
                    'sourcePublicationDate': None, 'targetPublicationDate': '2017-05-01',
                    'sourceRetrievalAt': None, 'targetRetrievalAt': '2026-09-24',
                    'role': 'primary'}
        occurrences = [occurrence('source', 2014, 'SOURCE, S'),
                       occurrence('target', 2017, 'TARGET, T'),
                       occurrence('other', 2017, 'OTHER, O')]
        links = build_person_links({'source->target': evidence}, [], occurrences)['links']
        self.assertEqual(len(links), 2)
        self.assertTrue(links[0]['personId'].startswith('person:stage10:occurrence:'))
        with self.assertRaisesRegex(ValueError, 'Dangling'):
            build_person_links({'source->missing': evidence}, [], occurrences)
        conflicting = {**evidence, 'sourceEvidenceId': 'other-evidence'}
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            build_person_links({'source->target': evidence, 'source->other': conflicting},
                               [], occurrences)

    def test_chronological_fit_never_reads_holdout_target_to_train(self):
        rows = [{'eventId': str(i), 'targetYear': year, 'priorPP': x,
                 'targetPP': y, 'replacement': replacement}
                for i, (year, x, y, replacement) in enumerate([
                    (2011, 0, 1, 0), (2011, 2, 3, 0), (2011, 1, -2, 1),
                    (2011, 3, -1, 1), (2017, 0, 2, 0), (2017, 2, -3, 1),
                    (2023, 1, 4, 0), (2023, 3, -5, 1)])]
        before = chronological(rows)
        changed = deepcopy(rows)
        changed[-1]['targetPP'] = 1000
        after = chronological(changed)
        self.assertEqual(before[0]['fittedReplacement'], after[0]['fittedReplacement'])
        self.assertEqual(before[1]['fittedReplacement'], after[1]['fittedReplacement'])
        self.assertNotEqual(before[1]['replacementScore'], after[1]['replacementScore'])
        self.assertNotEqual(fit(rows[:4], 'replacement'), fit(rows[:4], 'no_replacement'))

    def test_maori_official_winners_and_stage_specific_registry_contract(self):
        occurrences = json.loads((ROOT / 'data/processed/models/candidate-overperformance/occurrences.json').read_text())['records']
        snapshot = json.loads((ROOT / 'data/source-plans/stage10-maori-winner-sources.json').read_text())
        registry = json.loads((ROOT / 'data/sources.json').read_text())
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for source in snapshot['sources']:
                destination = root / source['rawPath']
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / source['rawPath'], destination)
            required = verify_snapshot(root, occurrences, registry, snapshot)
            overlay = build_overlay(root, occurrences, required)
            self.assertEqual(len(overlay['records']), 21)
            self.assertEqual(len({r['winnerOccurrenceId'] for r in overlay['records']}), 21)
            extended = deepcopy(registry)
            extended['sources'].append({'id': 'unrelated', 'rawPath': 'data/raw/unrelated.txt'})
            verify_snapshot(root, occurrences, extended, snapshot)
            changed = deepcopy(registry)
            next(r for r in changed['sources'] if r['id'] == required[0]['id'])['resource'] = 'altered'
            with self.assertRaisesRegex(ValueError, 'Changed or deleted'):
                verify_snapshot(root, occurrences, changed, snapshot)
            deleted = deepcopy(registry)
            deleted['sources'] = [r for r in deleted['sources'] if r['id'] != required[0]['id']]
            with self.assertRaisesRegex(ValueError, 'Missing required'):
                verify_snapshot(root, occurrences, deleted, snapshot)
            duplicate = deepcopy(registry)
            duplicate['sources'].append({**required[0], 'rawPath': 'data/raw/unrelated.txt'})
            with self.assertRaisesRegex(ValueError, 'Ambiguous source ID'):
                verify_snapshot(root, occurrences, duplicate, snapshot)
            corrupt_occurrences = deepcopy(occurrences)
            next(r for r in corrupt_occurrences if r['candidateOccurrenceId'] ==
                 overlay['records'][0]['winnerOccurrenceId'])['sourcePublishedCandidateVotes'] += 1
            with self.assertRaisesRegex(ValueError, 'winner name, votes or majority'):
                build_overlay(root, corrupt_occurrences, required)
            raw = root / required[0]['rawPath']
            raw.write_bytes(raw.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'raw bytes'):
                verify_snapshot(root, occurrences, registry, snapshot)

    def test_identity_source_snapshot_accepts_additions_but_rejects_changes(self):
        snapshot = json.loads((ROOT / 'data/source-plans/stage10-identity-sources.json').read_text())
        registry = json.loads((ROOT / 'data/sources.json').read_text())
        verify_identity_snapshot(registry, snapshot)
        extra = deepcopy(registry)
        extra['sources'].append({'id': 'unrelated', 'rawPath': 'data/raw/unrelated'})
        verify_identity_snapshot(extra, snapshot)
        changed = deepcopy(registry)
        required_id = snapshot['sources'][0]['id']
        next(r for r in changed['sources'] if r['id'] == required_id)['resource'] = 'altered'
        with self.assertRaisesRegex(ValueError, 'Changed or deleted'):
            verify_identity_snapshot(changed, snapshot)
        deleted = deepcopy(registry)
        deleted['sources'] = [r for r in deleted['sources'] if r['id'] != required_id]
        with self.assertRaisesRegex(ValueError, 'Changed or deleted'):
            verify_identity_snapshot(deleted, snapshot)


if __name__ == '__main__':
    unittest.main()
