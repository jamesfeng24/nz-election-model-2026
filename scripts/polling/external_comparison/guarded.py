"""Guarded one-case execution; no new sampler/model specification."""
import argparse
from .runtime import validate_runtime


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,choices=[2017,2020,2023],required=True);p.add_argument('--attempt',type=int,choices=[1,2],default=1);a=p.parse_args()
    validate_runtime()
    from .inference import run_case
    run_case(a.year,a.attempt)
