"""Synthetic Stage 15 geometry and outcome-independent construction contracts."""

import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from scripts.models.conditional_candidate_ledger import (
    construct, evaluation_run, feasibility, geometry, pool, run, sources)
from scripts.validate.source_files import verify_source_files


def source_row(mass, a, b):
    return {'mass': mass, 'cells': [
        {'category': 'party:a', 'bounds': [a, a]},
        {'category': 'party:b', 'bounds': [b, b]}]}


class ConditionalCandidateLedgerTests(unittest.TestCase):
    def test_coupled_source_row_is_not_marginal_box(self):
        cells = [{'bounds': [0.2, 0.8]}, {'bounds': [0.2, 0.8]}]
        self.assertAlmostEqual(geometry.row_maximum(cells, [1, 1]), 1)
        self.assertAlmostEqual(geometry.row_maximum(cells, [1, 0]), 0.8)
        self.assertGreater(sum(cell['bounds'][1] for cell in cells), 1)
        with self.assertRaises(geometry.LedgerGeometryError):
            geometry.row_maximum([{'bounds': [0.7, 1]},
                                  {'bounds': [0.7, 1]}], [1, 0])

    def test_rounded_printed_zero_is_not_structural_absence(self):
        self.assertEqual(pool.cell_bounds(0), [0, 0.00005])
        self.assertEqual(pool.cell_bounds(100), [0.99995, 1])
        with self.assertRaises(geometry.LedgerGeometryError):
            pool.cell_bounds(None)

    def test_weighted_pool_and_seat_hull_are_distinct(self):
        source = {'totalMass': 400, 'rows': [source_row(100, 0.8, 0.2),
                                             source_row(300, 0.2, 0.8)]}
        base = {'mass': 100, 'pool': source,
                'sourceCategoryDestinations': {'party:a': 'a', 'party:b': 'b'}}
        coeff = {'a': 1, 'b': 0, 'party_only': 0}
        self.assertAlmostEqual(geometry.route_maximum(base | {'routing': 'primary'},
                                                       coeff), 35)
        self.assertAlmostEqual(geometry.route_maximum(base | {'routing': 'heterogeneity'},
                                                       coeff), 80)
        self.assertAlmostEqual(geometry.contest_minimum(
            [base | {'routing': 'heterogeneity'}], coeff), 20)
        primary_share = geometry.share_bounds([base | {'routing': 'primary'}],
                        'a', ['a', 'b', 'party_only'], ['a', 'b'], [100, 100])
        hull_share = geometry.share_bounds([base | {'routing': 'heterogeneity'}],
                        'a', ['a', 'b', 'party_only'], ['a', 'b'], [100, 100])
        self.assertAlmostEqual(primary_share['bounds'][0], 0.35, places=8)
        self.assertAlmostEqual(primary_share['bounds'][1], 0.35, places=8)
        self.assertAlmostEqual(hull_share['bounds'][0], 0.2, places=8)
        self.assertAlmostEqual(hull_share['bounds'][1], 0.8, places=8)

    def test_absent_category_releases_only_its_coupled_mass(self):
        source = {'totalMass': 1, 'rows': [source_row(1, 0.7, 0.3)]}
        origin = {'mass': 100, 'pool': source, 'routing': 'primary',
                  'sourceCategoryDestinations': {'party:a': 'a'}}
        self.assertEqual(geometry.linear_bounds([origin],
                         {'a': 1, 'new': 0, 'party_only': 0}), [70, 100])
        self.assertEqual(geometry.linear_bounds([origin],
                         {'a': 0, 'new': 1, 'party_only': 0}), [0, 30])
        self.assertEqual(geometry.linear_bounds([origin],
                         {'a': 1, 'new': 1, 'party_only': 1}), [100, 100])

    def test_entrant_independent_and_identity_labels(self):
        source = {'pools': {'g': {'id': '2008:g', 'totalMass': 1,
                                 'rows': [source_row(1, 0.7, 0.3)],
                                 'supportedDestinations': ['party:a', 'party:b']}}}
        continuity = [{'sourceYear': 2008, 'targetYear': 2011, 'status': 'eligible',
                       'source': {'sourceKey': 'g'}, 'target': {'sourceKey': 'g'}},
                      {'sourceYear': 2008, 'targetYear': 2011, 'status': 'eligible',
                       'source': {'sourceKey': 'a'}, 'target': {'sourceKey': 'a'}},
                      {'sourceYear': 2008, 'targetYear': 2011, 'status': 'eligible',
                       'source': {'sourceKey': 'b'}, 'target': {'sourceKey': 'b'}}]
        ballot = {'validVotes': 100, 'informalVotes': 0,
                  'ordinaryDisallowed': 0, 'specialDisallowed': 0, 'votesCast': 100}
        target = {'partyBallot': ballot, 'parties': [{'partyKey': 'g', 'votes': 100}],
                  'candidates': [{'id': 'a', 'partyKey': 'a', 'personId': None,
                                  'votes': 0, 'elected': False},
                                 {'id': 'b', 'partyKey': 'b', 'personId': None,
                                  'votes': 0, 'elected': False}]}
        first = construct.build_origins(construct.target_inputs(target), source,
                                        continuity, 2008, 2011, 'primary')
        changed = copy.deepcopy(target)
        changed['candidates'][0].update(personId='other', votes=100, elected=True)
        second = construct.build_origins(construct.target_inputs(changed), source,
                                         continuity, 2008, 2011, 'primary')
        self.assertEqual(first, second)
        for party in ('new_party', 'independent'):
            entered = copy.deepcopy(target)
            entered['candidates'].append({'id': 'new', 'partyKey': party,
                                          'votes': 0, 'elected': False})
            origins = construct.build_origins(construct.target_inputs(entered), source,
                                              continuity, 2008, 2011, 'primary')
            self.assertEqual(origins[0]['routing'], 'free')
            self.assertEqual(origins[0]['reason'], 'unsupported_or_ambiguous_target_destination')
            self.assertEqual(geometry.linear_bounds(origins,
                             {'a': 0, 'b': 0, 'new': 1,
                              **{d: 0 for d in pool.NONCANDIDATE_DESTINATIONS}}), [0, 100])

    def test_incompatible_population_and_share_extrema(self):
        seat = {'partyBallot': {'validVotes': 70, 'informalVotes': 0,
                                'ordinaryDisallowed': 0, 'specialDisallowed': 30,
                                'votesCast': 100},
                'parties': [{'partyKey': 'a', 'votes': 70}],
                'candidates': [{'id': 'a', 'partyKey': 'a'},
                               {'id': 'b', 'partyKey': 'b'}]}
        inputs = construct.target_inputs(seat)
        self.assertEqual(sum(g['mass'] for g in inputs['groups']), 100)
        broken = copy.deepcopy(seat)
        broken['partyBallot']['votesCast'] = 99
        with self.assertRaises(geometry.LedgerGeometryError):
            construct.target_inputs(broken)
        origins = [{'mass': 70, 'routing': 'diagonal', 'destination': 'a'},
                   {'mass': 30, 'routing': 'free'}]
        denom = geometry.linear_bounds(origins, {'a': 1, 'b': 1, 'other': 0})
        self.assertEqual(denom, [70, 100])
        ratio = geometry.share_bounds(origins, 'a', ['a', 'b', 'other'],
                                      ['a', 'b'], denom)
        self.assertEqual(ratio['status'], 'defined')
        self.assertAlmostEqual(ratio['bounds'][0], 0.7, places=8)
        self.assertAlmostEqual(ratio['bounds'][1], 1, places=8)
        undefined = geometry.share_bounds([{'mass': 100, 'routing': 'free'}],
                                           'a', ['a', 'b', 'other'], ['a', 'b'], [0, 100])
        self.assertEqual(undefined['status'], 'undefined_zero_feasible_denominator')

    def test_joint_vector_feasibility_respects_pool_and_seat_hull(self):
        source = {'id': '2008:g', 'totalMass': 400,
                  'rows': [source_row(100, 0.8, 0.2),
                           source_row(300, 0.2, 0.8)]}
        candidates = [{'candidateOccurrenceId': 'a'},
                      {'candidateOccurrenceId': 'b'}]
        base = {'candidates': candidates,
                'origins': [{'mass': 100, 'sourcePoolId': '2008:g',
                             'mappedSourceCategories': {'party:a': 'a', 'party:b': 'b'},
                             'routing': 'primary'}]}
        pools = {'2008:g': source}
        self.assertEqual(feasibility.joint_feasibility(base, pools, {'a': 35, 'b': 65})
                         ['status'], 'feasible')
        self.assertEqual(feasibility.joint_feasibility(base, pools, {'a': 50, 'b': 50})
                         ['status'], 'infeasible')
        hull = copy.deepcopy(base)
        hull['origins'][0]['routing'] = 'heterogeneity'
        self.assertEqual(feasibility.joint_feasibility(hull, pools, {'a': 50, 'b': 50})
                         ['status'], 'feasible')

    def test_joint_absent_mass_and_solver_failure_are_explicit(self):
        source = {'id': '2008:g', 'totalMass': 1,
                  'rows': [source_row(1, 0.7, 0.3)]}
        record = {'candidates': [{'candidateOccurrenceId': 'a'},
                                 {'candidateOccurrenceId': 'b'}],
                  'origins': [{'mass': 100, 'sourcePoolId': '2008:g',
                               'mappedSourceCategories': {'party:a': 'a'},
                               'routing': 'primary'}]}
        pools = {'2008:g': source}
        self.assertEqual(feasibility.joint_feasibility(record, pools,
                         {'a': 70, 'b': 30})['status'], 'feasible')
        self.assertEqual(feasibility.joint_feasibility(record, pools,
                         {'a': 60, 'b': 40})['status'], 'infeasible')
        def failed_solver(*args, **kwargs):
            return SimpleNamespace(status=4, x=None)
        self.assertEqual(feasibility.joint_feasibility(record, pools,
                         {'a': 70, 'b': 30}, failed_solver)['status'],
                         'numerical_or_solver_failure')
        def false_success(*args, **kwargs):
            return SimpleNamespace(status=0, x=[0] * len(args[0]))
        self.assertEqual(feasibility.joint_feasibility(record, pools,
                         {'a': 70, 'b': 30}, false_success)['status'],
                         'numerical_or_solver_failure')

    def test_solver_residual_reporting_ignores_valid_roundoff(self):
        problem = feasibility.FeasibilityProblem()
        variable = problem.variable()
        problem.equality({variable: 1}, 1, 'ballots')
        def rounded_solver(*args, **kwargs):
            return SimpleNamespace(status=0, x=[1 + 2e-12])
        result = feasibility.solve_problem(problem, rounded_solver)
        self.assertEqual(result['status'], 'feasible')
        self.assertEqual(result['ballotResidual'], 0)
        self.assertEqual(result['boundViolation'], 0)

    def test_complete_source_row_structural_zero_retains_weight(self):
        def seat(number, candidate_parties):
            sid = f'seat-{number}'
            return {'id': sid, 'kind': 'general',
                    'parties': [{'partyKey': 'g', 'votes': 100}],
                    'partyBallot': {'informalVotes': 0},
                    'candidates': [{'id': f'{sid}-{party}', 'partyKey': party}
                                   for party in candidate_parties]}
        def matrix(number, percentages):
            sid = f'seat-{number}'
            cells = [{'category': 'candidate', 'candidateId': f'{sid}-{party}',
                      'reportedPercent': percent} for party, percent in percentages.items()]
            cells.extend([{'category': 'informal', 'candidateId': None,
                           'reportedPercent': 0},
                          {'category': 'party-vote-only', 'candidateId': None,
                           'reportedPercent': 0}])
            return {'id': f'matrix-{number}', 'electorateId': sid, 'year': 2008,
                    'sourceIds': ['synthetic-only'],
                    'rows': [{'partyLabel': 'g', 'totalPartyVotes': 100, 'cells': cells},
                             {'partyLabel': 'Total Party Votes and Percentages',
                              'totalPartyVotes': 100, 'cells': cells}]}
        election = {'electorates': [seat(1, ['a', 'b']), seat(2, ['a'])]}
        split = {'matrices': [matrix(1, {'a': 60, 'b': 40}),
                              matrix(2, {'a': 100})]}
        result = pool.build_source_pools(2008, election, split)
        origin = result['pools']['g']
        self.assertEqual(origin['includedRows'], 2)
        self.assertEqual(origin['totalMass'], 200)
        self.assertIn('party:b', origin['supportedDestinations'])
        self.assertNotIn('party:b', [cell['category'] for cell in origin['rows'][1]['cells']])
        self.assertEqual(next(cell['bounds'] for cell in origin['rows'][0]['cells']
                              if cell['category'] == 'informal_candidate'), [0, 0.00005])
        routed = {'mass': 100, 'routing': 'primary', 'pool': origin,
                  'sourceCategoryDestinations': {
                      'party:a': 'a', 'party:b': 'b',
                      'informal_candidate': 'informal_candidate',
                      'party_vote_only': 'party_vote_only'}}
        result = geometry.linear_bounds([routed], {'a': 0, 'b': 1,
                         'informal_candidate': 0, 'party_vote_only': 0})
        self.assertLess(result[1], 21)
        self.assertGreater(result[0], 19)

    def test_source_snapshot_accepts_additions_rejects_required_changes(self):
        elections = {year: sources.read(f'data/processed/elections/{year}.json')
                     for year in sources.SOURCE_YEARS + sources.TARGET_YEARS}
        splits = {year: sources.read(f'data/processed/split-votes/{year}.json')
                  for year in sources.SOURCE_YEARS}
        registry = sources.read('data/sources.json')
        saved = sources.read(str(sources.SNAPSHOT))
        self.assertEqual(saved, sources.snapshot(registry, elections, splits))
        self.assertEqual(len(saved['sources']), 612)
        unrelated = copy.deepcopy(registry)
        extra = copy.deepcopy(registry['sources'][0])
        extra['id'] = 'unrelated-stage15-future-source'
        unrelated['sources'].append(extra)
        self.assertEqual(saved, sources.snapshot(unrelated, elections, splits))
        unrelated['sources'].append(copy.deepcopy(extra))
        with self.assertRaises(ValueError):
            sources.snapshot(unrelated, elections, splits)
        required = copy.deepcopy(registry)
        record = next(item for item in required['sources']
                      if item['id'] == saved['sources'][0]['id'])
        record['limitations'] = ['changed']
        with self.assertRaises(ValueError):
            sources.verify_snapshot(saved, required, elections, splits)
        sources.verify_snapshot(saved, registry, elections, splits)
        source = saved['sources'][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / source['rawPath']
            path.parent.mkdir(parents=True)
            path.write_bytes((sources.ROOT / source['rawPath']).read_bytes())
            verify_source_files(root, {'schemaVersion': 1, 'sources': [source]})
            path.write_bytes(path.read_bytes() + b'corrupted')
            with self.assertRaises(ValueError):
                verify_source_files(root, {'schemaVersion': 1, 'sources': [source]})

    def test_full_construction_ignores_target_and_later_outcomes(self):
        frame = sources.read('data/processed/checkpoints/complete-candidate-baseline/input-inventory.json')['records']
        elections = {year: sources.read(f'data/processed/elections/{year}.json')
                     for year in sources.SOURCE_YEARS + sources.TARGET_YEARS}
        saved_pools = sources.read('data/processed/models/conditional-candidate-ledger/source-pools.json')
        pools = {year: saved_pools['sourceYears'][str(year)] for year in sources.SOURCE_YEARS}
        continuity = sources.read('data/processed/models/party-vote-transform/party-continuity.json')['records']
        changed = copy.deepcopy(elections)
        for year in sources.TARGET_YEARS:
            for seat in changed[year]['electorates']:
                seat['winnerCandidateId'] = None
                seat['validCandidateVotes'] = -1
                seat['candidateBallot'] = {'votesCast': -1}
                for candidate in seat['candidates']:
                    candidate['votes'] = -1
                    candidate['elected'] = not candidate['elected']
        actual = construct.construct(frame, changed, pools, continuity)
        expected = sources.read('data/processed/models/conditional-candidate-ledger/ledgers.json')
        self.assertEqual(actual, expected)
        for year in sources.TARGET_YEARS:
            self.assertNotIn(f'data/processed/split-votes/{year}.json', run.INPUTS)

    def test_real_pool_counts_and_manifest_reproduction(self):
        saved = sources.read('data/processed/models/conditional-candidate-ledger/source-pools.json')
        self.assertEqual([saved['sourceYears'][str(year)]['summary']['includedRows']
                          for year in sources.SOURCE_YEARS], [1258, 1021, 1169])
        self.assertEqual([saved['sourceYears'][str(year)]['summary']['excludedRowsByReason']
                          for year in sources.SOURCE_YEARS],
                         [{'zero_mass_origin': 2}, {'zero_mass_origin': 3},
                          {'zero_mass_origin': 1}])
        self.assertEqual(run.build()['construction-manifest.json'],
                         sources.read('data/processed/models/conditional-candidate-ledger/construction-manifest.json'))

    def test_evaluation_reproduction_and_common_frame(self):
        built = evaluation_run.build()
        for name, payload in built.items():
            self.assertEqual(evaluation_run.encode(payload),
                             (evaluation_run.DEST / name).read_bytes())
        diagnostics = built['diagnostics.json']
        self.assertEqual(diagnostics['summary']['commonVoteCandidateCount'], 1313)
        self.assertEqual(diagnostics['summary']['commonPointCandidateCount'], 0)
        self.assertEqual([row['fullyFreePrimaryContests'] for row in
                          diagnostics['summary']['byHoldout']], [54, 42, 61])
        ledgers = sources.read('data/processed/models/conditional-candidate-ledger/ledgers.json')
        for row in ledgers['records']:
            if row['status'] != 'constructed':
                continue
            for method in construct.METHODS:
                entry = row['methods'][method]
                self.assertEqual(sum(origin['mass'] for origin in entry['origins']),
                                 row['votesCast'])
                self.assertLessEqual(entry['validCandidateDenominator'][1],
                                     row['votesCast'] + geometry.BALLOT_TOL)


if __name__ == '__main__':
    unittest.main()
