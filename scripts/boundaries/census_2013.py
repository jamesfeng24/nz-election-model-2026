"""Disclosure-compatible 2013 descent bounds; never impute an electoral value."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = '2013_Census_Maori_descent_for_the_census_usually_resident_population_count(1)_'
UR = '2013_Census_census_usually_resident_population_count(1)'
FIELDS = ['Maori_Descent', 'No_Maori_Descent', "Don't_Know",
          'Not_Elsewhere_Included(14)', 'Total_people_stated', 'Total_people']


def registered_bytes(path, hashes):
    raw = (ROOT / path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    records = [s for s in json.loads((ROOT / 'data/sources.json').read_bytes())['sources']
               if s['rawPath'] == path]
    if len(records) != 1 or records[0]['sha256'] != digest:
        raise ValueError('Unregistered or altered input: ' + path)
    hashes[path] = digest
    return raw


def count_bounds(value, ceiling=None):
    """Random base-three rounding, not nearest rounding; suppression has no 0–5 rule."""
    if value == '..C':
        if ceiling is None:
            raise ValueError('Confidential total needs an authoritative upper bound')
        return 0, ceiling
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError('Missing/malformed Census count: ' + repr(value))
    n = int(value)
    if n % 3:
        raise ValueError('Expected base-three published count')
    return max(0, n - 2), min(n + 2, ceiling) if ceiling is not None else n + 2


def descent_bounds(row):
    """Project feasible Yes/No/unknown partitions; unknown imputation stays unknown.

    U=Y+N+K+R, S=Y+N+K, and electoral descent D=Y+q,
    0<=q<=K+R. Independent published rounding applies to every count.
    No nominal D or local roll ratio is inferred.
    """
    ulo, uhi = count_bounds(row[UR])
    values = [row[PREFIX + f] for f in FIELDS]
    y, n, k, r, stated, total = [count_bounds(v, uhi) for v in values]
    ulo, uhi = max(ulo, total[0]), min(uhi, total[1])
    candidates = []
    for u in range(ulo, uhi + 1):
        for s in range(max(stated[0], u - r[1]), min(stated[1], u - r[0]) + 1):
            ymin = max(y[0], s - n[1] - k[1])
            ymax = min(y[1], s - n[0] - k[0])
            if ymin <= ymax:
                nmin = max(n[0], s - y[1] - k[1])
                candidates.append((u, ymin, u - nmin, nmin))
    if not candidates:
        raise ValueError('Inconsistent rounded Census descent partition')
    return {'residentLower': min(x[0] for x in candidates),
            'residentUpper': max(x[0] for x in candidates),
            'electoralDescentLower': min(x[1] for x in candidates),
            'electoralDescentUpper': max(x[2] for x in candidates),
            'nonMaoriDescentLower': min(x[3] for x in candidates),
            'publishedResident': int(row[UR]),
            'sourceCategories': dict(zip(FIELDS, values)),
            'confidentialCategoryCount': values.count('..C')}


def load_census(hashes):
    path = 'data/raw/boundaries/2007-2014/census-meshblock-dataset.zip'
    raw = registered_bytes(path, hashes)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        rows = csv.DictReader(io.TextIOWrapper(archive.open(
            '2013-mb-dataset-Total-New-Zealand-Individual-Part-1.csv'), encoding='cp1252'))
        result = {}
        for row in rows:
            label = row['Area_Code_and_Description']
            if not label.startswith('MB '):
                continue
            code = label[3:]
            if len(code) != 7 or not code.isdigit() or code in result:
                raise ValueError('Invalid/duplicate Census meshblock')
            try:
                result[code] = descent_bounds(row)
            except ValueError as error:
                raise ValueError(code + ': ' + str(error)) from error
    return result
