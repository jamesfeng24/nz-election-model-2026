"""Synthetic Stage 15 geometry and outcome-independent construction contracts."""

import copy
from pathlib import Path
import tempfile
import unittest

from scripts.models.conditional_candidate_ledger import construct, geometry, pool, sources
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


if __name__ == '__main__':
    unittest.main()
