"""WGS84 latitude/longitude to NZTM2000 (EPSG:2193) eastings/northings, pure Python.

Kruger n-series for the transverse Mercator (millimetre accuracy over New Zealand). NZGD2000 and WGS84 differ by
well under a metre, far below the geocoding error this stage carries, so no datum shift is applied.
Tested against pyproj reference values in scripts/tests/test_stage69_voting_place_notionals.py.
"""
import math

A, F = 6378137.0, 1 / 298.257222101
K0, LON0, FE, FN = 0.9996, math.radians(173.0), 1600000.0, 10000000.0
N = F / (2 - F)
RECT = A / (1 + N) * (1 + N ** 2 / 4 + N ** 4 / 64)
ALPHA = (N / 2 - 2 * N ** 2 / 3 + 5 * N ** 3 / 16 + 41 * N ** 4 / 180,
         13 * N ** 2 / 48 - 3 * N ** 3 / 5 + 557 * N ** 4 / 1440,
         61 * N ** 3 / 240 - 103 * N ** 4 / 140,
         49561 * N ** 4 / 161280)


def forward(lat, lon):
    phi, lam = math.radians(lat), math.radians(lon) - LON0
    c = 2 * math.sqrt(N) / (1 + N)
    t = math.sinh(math.atanh(math.sin(phi)) - c * math.atanh(c * math.sin(phi)))
    xi0 = math.atan2(t, math.cos(lam))
    eta0 = math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    xi = xi0 + sum(a * math.sin(2 * (j + 1) * xi0) * math.cosh(2 * (j + 1) * eta0) for j, a in enumerate(ALPHA))
    eta = eta0 + sum(a * math.cos(2 * (j + 1) * xi0) * math.sinh(2 * (j + 1) * eta0) for j, a in enumerate(ALPHA))
    return FE + K0 * RECT * eta, FN + K0 * RECT * xi
