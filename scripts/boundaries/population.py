"""Disclosure-aware population bounds, not fabricated exact populations."""
import re


def population_interval(value):
    """2025 source rule: suppress unrounded counts <6; random round to base 3.

    A released multiple of three may be either adjacent rounding endpoint,
    so the compatible integer interval is +/-2, not nearest-rounding +/-1.
    These are disclosure bounds, not statistical confidence intervals.
    """
    if value == '-999':
        return {'published': -999, 'value': None, 'status': 'suppressed',
                'lower': 0, 'upper': 5}
    if not re.fullmatch(r'\d+', value or ''):
        raise ValueError('Missing or malformed electoral population')
    count = int(value)
    if count < 6 or count % 3:
        raise ValueError('Unexpected released population under source disclosure rule')
    return {'published': count, 'value': count, 'status': 'random_rounded_base_3',
            'lower': max(6, count - 2), 'upper': count + 2}
