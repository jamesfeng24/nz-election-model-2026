"""Compatibility entry point for the original 2011 control API."""
from .historical_split_controls import validate_split_controls


def validate_2011(source, electorates, matrices):
    return validate_split_controls(source, electorates, matrices, year=2011)
