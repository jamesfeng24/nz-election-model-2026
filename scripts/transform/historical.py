"""Deterministic historical parsing. No regression or forecast code."""
from __future__ import annotations
import csv
import io
from decimal import Decimal
import re
import unicodedata


def text(value: str) -> str:
    return unicodedata.normalize('NFC', value.strip())


def read_csv(data: bytes) -> tuple[list[list[str]], str]:
    try:
        decoded = data.decode('utf-8-sig')
        encoding = 'utf-8-sig'
    except UnicodeDecodeError:
        decoded = data.decode('cp1252')
        encoding = 'cp1252'
    return [[text(cell) for cell in row] for row in csv.reader(io.StringIO(decoded)) if any(cell.strip() for cell in row)], encoding


def count(value: str) -> int:
    cleaned = value.strip().replace(',', '')
    if not re.fullmatch(r'\d+', cleaned):
        raise ValueError('Missing or invalid count: ' + repr(value))
    return int(cleaned)


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def split_rows(data: bytes) -> dict:
    rows, encoding = read_csv(data)
    header = rows[0]
    if header[1] != 'Total Party Votes' or header[-1] != 'Total %':
        raise ValueError('Unrecognized split-vote header')
    parsed = []
    for row in rows[1:]:
        if len(row) != len(header):
            raise ValueError('Ragged split-vote row')
        cells = []
        for category, value in zip(header[2:-1], row[2:-1]):
            percent = None if not value else Decimal(value)
            if percent is not None and not 0 <= percent <= 100:
                raise ValueError('Invalid split percentage')
            cells.append({'candidateLabel': category, 'count': None, 'reportedPercent': None if percent is None else float(percent)})
        parsed.append({'partyLabel': row[0], 'totalPartyVotes': count(row[1]), 'cells': cells,
                       'reportedTotalPercent': None if not row[-1] else float(Decimal(row[-1]))})
    return {'sourceElectorateLabel': header[0], 'sourceEncoding': encoding, 'rows': parsed,
            'countAvailability': 'unavailable: source publishes rounded percentages, not joint counts'}
