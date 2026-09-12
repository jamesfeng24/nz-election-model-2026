"""Exact rational rounding envelopes and narrowly registered source discrepancies."""
from fractions import Fraction
from .historical import require


def envelope(total, reported):
    """Closed enclosure of a two-decimal rounding interval, clipped to 0–100%.

    Including tie endpoints is conservative across rounding conventions. These
    are feasibility bounds, never reconstructed joint-count observations.
    """
    require(total >= 0 and reported is not None, 'Missing split interval input')
    p = Fraction(str(reported))
    require(0 <= p <= 100, 'Invalid split interval percentage')
    return (total * max(Fraction(0), p-Fraction(1,200))/100,
            total * min(Fraction(100), p+Fraction(1,200))/100)


def add_intervals(values):
    values = list(values)
    return tuple(sum((v[i] for v in values), Fraction(0)) for i in (0,1))


class SourceDiscrepancies:
    """Fail closed unless a disjoint interval has the reviewed exact fingerprint."""
    def __init__(self, expected):
        self.expected = expected
        self.records = []

    def compare(self, identifier, left, right, source_ids):
        if max(left[0], right[0]) <= min(left[1], right[1]):
            return
        record = {'id': identifier, 'leftInterval': [str(x) for x in left],
                  'rightInterval': [str(x) for x in right],
                  'minimumGapVotes': str(max(left[0]-right[1], right[0]-left[1])),
                  'sourceIds': sorted(set(source_ids)),
                  'status': 'unresolved-official-source-discrepancy'}
        require(record in self.expected, 'Unreviewed split discrepancy: '+str(record))
        self.records.append(record)

    def finish(self):
        require(sorted(self.records, key=lambda r:r['id']) == sorted(self.expected, key=lambda r:r['id']),
                'Reviewed split discrepancy inventory changed')
