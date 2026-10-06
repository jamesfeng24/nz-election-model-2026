"""Shared helpers: canonical JSON, hashing, strict timestamp parsing and the one error type."""
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ELECTION_ID = 'nz-general-2026'
NATIONAL_KEY = 'nationalparty'
LABOUR_KEY = 'labourparty'


class AdjustmentError(ValueError):
    """Every invalid adjustment, label or layer input fails loudly with this error."""


def require(condition, message):
    if not condition:
        raise AdjustmentError(message)


def canonical(value):
    """Sorted keys, fixed indent, one trailing newline: identical bytes for identical content."""
    return json.dumps(value, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + '\n'


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_text(text):
    return sha256_bytes(text.encode('utf-8'))


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def parse_time(value, field):
    """ISO 8601 date-time with an explicit offset (or Z); naive times are refused."""
    require(isinstance(value, str), f'{field} must be an ISO 8601 string')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise AdjustmentError(f'{field} is not an ISO 8601 date-time: {value!r}') from None
    require(parsed.tzinfo is not None, f'{field} needs an explicit UTC offset (for example +13:00 or Z): {value!r}')
    return parsed


def number(value, field, low=None, high=None):
    """A finite real number (booleans are not numbers), optionally bounded."""
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
            f'{field} must be a finite number, got {value!r}')
    require(low is None or value >= low, f'{field} must be >= {low}, got {value}')
    require(high is None or value <= high, f'{field} must be <= {high}, got {value}')
    return float(value)


def one_line(value, field, maximum=300, minimum=1):
    require(isinstance(value, str), f'{field} must be a string')
    require(value == value.strip() and '\n' not in value and '\r' not in value,
            f'{field} must be one line with no leading or trailing space')
    require(minimum <= len(value) <= maximum, f'{field} must be {minimum} to {maximum} characters, got {len(value)}')
    return value


def exact_keys(record, keys, field):
    require(isinstance(record, dict), f'{field} must be an object')
    missing, extra = sorted(set(keys) - set(record)), sorted(set(record) - set(keys))
    require(not missing, f'{field} is missing {missing}')
    require(not extra, f'{field} has unknown fields {extra}')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
