"""Synthetic GeoPackage headers and real immutable export reconciliation."""
import struct
import unittest
from shapely.geometry import Polygon
from scripts.boundaries.geopackage import decode_geometry


class GeoPackageTests(unittest.TestCase):
    def test_endianness_and_crs(self):
        shape=Polygon([(0,0),(1,0),(1,1),(0,0)])
        for flag,endian in [(0,'>'),(1,'<')]:
            blob=b'GP\0'+bytes([flag])+struct.pack(endian+'i',2193)+shape.wkb
            self.assertTrue(decode_geometry(blob,2193).equals(shape))
            with self.assertRaises(ValueError):decode_geometry(blob,4326)

    def test_null_is_unavailable_and_malformed_headers_fail(self):
        self.assertIsNone(decode_geometry(None,2193))
        for blob in [b'',b'not a geopackage',b'GP\0\x0b'+b'\0'*50,b'GP\0\x21'+b'\0'*50]:
            with self.subTest(blob=blob),self.assertRaises(ValueError):decode_geometry(blob,2193)

    def test_false_empty_flag_fails(self):
        shape=Polygon([(0,0),(1,0),(1,1),(0,0)])
        with self.assertRaises(ValueError):
            decode_geometry(b'GP\0\x11'+struct.pack('<i',2193)+shape.wkb,2193)
