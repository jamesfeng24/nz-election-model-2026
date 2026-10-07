"""Stage69 tests: voting-place parsing, locations, allocation arithmetic, reconciliation and the saved notional artifacts.

Fixtures marked synthetic exist only in these tests and never feed an application result.
"""
import json
import unittest

import numpy as np

from scripts.voting_place_notionals import allocate as al
from scripts.voting_place_notionals import nztm
from scripts.voting_place_notionals import parse
from scripts.voting_place_notionals import places
from scripts.voting_place_notionals.common import PREFIX, ROOT, digest, equivalent, read

# pyproj reference values (EPSG:4326 -> EPSG:2193), computed once offline: (lat, lon, easting, northing)
NZTM_REFERENCE = [(-41.2865, 174.7762, 1748735.5530602792, 5427916.478887198)]


def load(name):
    return read(PREFIX + '/' + name)


class Projection(unittest.TestCase):
    def test_matches_reference_to_a_millimetre(self):
        for lat, lon, e, n in NZTM_REFERENCE:
            x, y = nztm.forward(lat, lon)
            self.assertAlmostEqual(x, e, places=3)
            self.assertAlmostEqual(y, n, places=3)

    def test_central_meridian(self):
        x, _ = nztm.forward(-41.0, 173.0)
        self.assertAlmostEqual(x, 1600000.0, places=3)


class Parsing(unittest.TestCase):
    def test_every_candidate_and_party_file_reconciles_exactly(self):
        for n in range(1, 73):
            for path in (parse.candidate_path(n), 'data/raw/elections/2023/statistics/csv/party-votes-by-voting-place-%d.csv' % n):
                ok, _ = parse.reconcile(parse.parse_file(path))
                self.assertTrue(ok, path)

    def test_cancelled_port_waikato_candidate_table_is_empty_not_zero_filled(self):
        table = parse.parse_file(parse.candidate_path(39))
        self.assertEqual(table['name'], 'Port Waikato')
        self.assertEqual(sum(table['total']), 0)
        party = parse.parse_file('data/raw/elections/2023/statistics/csv/party-votes-by-voting-place-39.csv')
        self.assertGreater(sum(party['total']), 40000)

    def test_party_files_match_electorate_party_controls(self):
        import csv, io
        rows = list(csv.reader(io.StringIO((ROOT / 'data/raw/elections/2023/statistics/csv/votes-for-registered-parties-by-electorate.csv').read_text(encoding='utf-8-sig'))))
        control = {parse.nfc(r[0]): [int(v) for v in r[1:19]] for r in rows[2:] if r[0] and not r[0].endswith('Totals')}
        for n in range(1, 66):
            table = parse.parse_file('data/raw/elections/2023/statistics/csv/party-votes-by-voting-place-%d.csv' % n)
            self.assertEqual(table['total'][:18], control[table['name']], table['name'])


class VenueText(unittest.TestCase):
    def test_street_part(self):
        self.assertEqual(places.street_part('Albany Community Hub, 575 Albany Highway'), '575 Albany Highway')
        self.assertEqual(places.street_part('Church Unlimited, Auditorium 2, 3 Te Atatū Road'), '3 Te Atatū Road')
        self.assertEqual(places.street_part('Panmure Library, 7-13 Pilkington Road'), '7 Pilkington Road')
        self.assertIsNone(places.street_part('Naenae Library, Hillary Court'))

    def test_roving_rows(self):
        self.assertTrue(places.is_roving({'locality': 'Taken in Napier', 'venue': 'Care Homes, Team 1'}))
        self.assertTrue(places.is_roving({'locality': 'x', 'venue': 'Pop-up Voting Services, Various Locations'}))
        self.assertFalse(places.is_roving({'locality': 'Dunedin', 'venue': 'Dunedin Hospital, 1st Floor, 201 Great King Street'}))


def synthetic_seat():
    """SYNTHETIC: one old seat of four meshblocks on a line, two going to target B (east), two to target A (west)."""
    rows = [{'source': 'S', 'target': t, 'population': p, 'suppressed': 0, 'x': x, 'y': 0.0}
            for t, p, x in (('A', 100, 0.0), ('A', 100, 1.0), ('B', 100, 9.0), ('B', 300, 10.0))]
    return al.seat_frames(rows)['S']


class Allocation(unittest.TestCase):
    def test_population_flow(self):
        a = al.population_flow(synthetic_seat())
        self.assertTrue(np.allclose(a, [1 / 3, 2 / 3]))

    def test_nearest_flows_and_conservation(self):
        seat = synthetic_seat()
        xy = np.array([[0.0, 0.0], [10.0, 0.0]])
        flows, empty = al.nearest_flows(seat, xy)
        self.assertTrue(np.allclose(flows, [[1, 0], [0, 1]]))
        votes = np.array([[30, 10], [20, 40]])
        nonplace = np.array([5, 5])
        for lam in (0.0, 0.5, 1.0):
            out = al.allocate(votes, nonplace, flows, empty, al.population_flow(seat), lam)
            self.assertAlmostEqual(out.sum(), votes.sum() + nonplace.sum())
            self.assertTrue(np.allclose(out.sum(axis=0), votes.sum(axis=0) + nonplace))

    def test_single_target_reproduces_the_old_seat(self):
        rows = [{'source': 'S', 'target': 'T', 'population': 50, 'suppressed': 0, 'x': float(i), 'y': 0.0} for i in range(5)]
        seat = al.seat_frames(rows)['S']
        flows, empty = al.nearest_flows(seat, np.array([[0.0, 0.0], [4.0, 0.0]]))
        votes = np.array([[7, 3], [2, 8]])
        out = al.allocate(votes, np.array([1, 1]), flows, empty, al.population_flow(seat), 0.3)
        self.assertTrue(np.allclose(out[0], [10, 12]))

    def test_empty_catchment_votes_join_the_non_place_pool(self):
        rows = [{'source': 'S', 'target': 'T', 'population': 10, 'suppressed': 0, 'x': 0.0, 'y': 0.0}]
        seat = al.seat_frames(rows)['S']
        flows, empty = al.nearest_flows(seat, np.array([[0.0, 0.0], [100.0, 0.0]]))
        self.assertEqual(list(empty), [False, True])
        out = al.allocate(np.array([[5, 5], [3, 1]]), np.array([0, 0]), flows, empty, np.array([1.0]), 0.0)
        self.assertTrue(np.allclose(out, [[8, 6]]))


class MeshblockFrame(unittest.TestCase):
    def test_frame_inventory(self):
        from scripts.voting_place_notionals.frame import read_rows
        rows = read_rows()
        self.assertEqual(len(rows), 57553)
        self.assertEqual(len({r['meshblock'] for r in rows}), 57553)
        self.assertEqual(len({r['source'] for r in rows}), 65)
        self.assertEqual(len({r['target'] for r in rows}), 64)
        self.assertTrue(all(r['population'] >= 0 for r in rows))
