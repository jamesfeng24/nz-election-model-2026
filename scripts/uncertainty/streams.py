"""Stable separate random banks; one shared election effect across seats."""
import hashlib
import numpy as np
from .common import SEED


def normal(key, draws):
    if type(draws) is not int or draws <= 0 or draws % 2:
        raise ValueError('Even positive draw count required')
    seed = int.from_bytes(hashlib.sha256(f'{SEED}:{key}'.encode()).digest()[:16], 'big')
    values = np.random.Generator(np.random.PCG64(seed)).standard_normal(draws//2)
    return np.column_stack((values,-values)).reshape(-1)


def noise(row, scales, draws, stress=False):
    layer, year, seat = row['layer'],row['targetYear'],row['targetElectorateId']
    shared = np.column_stack([normal(f'{layer}:{year}:shared:{g}',draws) for g in row['groups']])
    specific = np.column_stack([normal(f'{layer}:{year}:seat:{seat}:{cid}',draws) for cid in row['ids']])
    multiplier = np.sqrt(1.5) if stress and layer=='candidate' and row['geography']!='exact' else 1.
    eta = scales['shared']*shared + scales['seat']*multiplier*specific
    return eta-eta.mean(axis=1,keepdims=True)


def national_indices(chain_shape, draws):
    chains, per_chain = chain_shape[:2]
    if draws>chains*per_chain or draws%chains:
        raise ValueError('Invalid balanced national subset')
    order=np.random.Generator(np.random.PCG64(SEED)).permutation(per_chain)
    return np.array([chain*per_chain+i for i in order[:draws//chains] for chain in range(chains)],dtype=int)
