"""Rebuild/check election-local Stage7 outputs from pinned observed evidence."""
import argparse
import hashlib
import json

from scripts.models.candidate_overperformance.inputs import ROOT, DEST, BASE, build as inventory
from scripts.models.candidate_overperformance.normalize import normalize
from scripts.models.candidate_overperformance.diagnostics import build as diagnostics


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()


def verify_contract(contract):
    for path, digest in contract.items():
        if not path.startswith('data/') or any(x in path for x in ('..', '/2026', '/boundaries/', '/models/', 'poll', 'forecast', 'opportunity')):
            raise ValueError('Forbidden Stage7 input: '+path)
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed pinned input: '+path)


def build():
    contract = json.loads((DEST/'input-contract.json').read_bytes())
    verify_contract(contract)
    rows, hashes, counts = inventory()
    if hashes != contract:
        raise ValueError('Unpinned Stage7 input')
    spec = json.loads((DEST/'specification.json').read_bytes())
    if spec['elections'] != [2008, 2011, 2014, 2017, 2020, 2023] or spec['primaryNormalization'] != 'additive_national_centered':
        raise ValueError('Frozen Stage7 specification changed')
    refs, occurrences = normalize(rows, counts)
    diag, sens = diagnostics(occurrences, refs)
    outputs = {
        'references.json': {'schemaVersion': 1, 'references': refs, 'coverageDenominator': 'All official electorates, including cancelled candidate contests; only eligible held contests enter numerators.'},
        'occurrences.json': {'schemaVersion': 1, 'usage': 'Historical descriptive outcomes. An observed target-election residual or reference offset is not an input to a forecast of that election.', 'records': occurrences},
        'diagnostics.json': diag, 'normalization-sensitivity.json': sens,
    }
    # This is the documented descriptive decision, not an optimized model-selection rule.
    outputs['selection.json'] = {
        'schemaVersion': 1, 'primaryNormalization': 'additive_national_centered',
        'normalizationStatus': 'retained_descriptive_primary', 'alternativeSensitivityMethods': ['proportional', 'log_odds'],
        'unresolvedPathology': 'No broad failure of additive interpretation; material Maori scope differences and individual scale sensitivity remain for later validation.',
        'forecastRestriction': 'Same-election observed residual/reference is descriptive only, never a predictor of that same election.',
        'reason': 'Retain the prespecified interpretable raw percentage-point residual. Range and share-level diagnostics do not justify replacing the estimand; alternative scales remain sensitivity fields, not fitted competitors.',
        'pathologyCounts': {m: {k: v[k] for k in ('definedCount', 'outOfRangeCount', 'undefinedReasons', 'maximumBoundedAdjustmentPP')} for m, v in sens['overall'].items()},
        'limitations': ['Occurrence-level descriptive residual only; not personal quality, persistence or a causal effect.',
                       'Sparse slates can have noisy leave-one-out references; quantitative coverage remains explicit, with no extra cutoff.',
                       'Election-wide general/Maori reference can mask scope differences; scope diagnostics are separate.',
                       'Alternative normalization scales can materially differ; retain sensitivity for later historical validation.',
                       'No candidate residual is transported across people, elections or boundaries. No2026 baseline is constructed.',
                       'Stage6 remains provisional; complete predictive views must not stack overlapping premiums/effects.'],
        'nextStage': 'Candidate persistence only; build reusable person/history/status evidence once at its start when authorized.'}
    dependencies = ['scripts/models/party_vote_transform/inputs.py', 'scripts/transform/historical.py',
                    'scripts/transform/modern_tables.py', 'scripts/transform/modern_config.py', 'scripts/transform/panel_config.py']
    code = sorted(list((ROOT/'scripts/models/candidate_overperformance').glob('*.py')) + [ROOT/p for p in dependencies])
    outputs['manifest.json'] = {
        'schemaVersion': 1, 'branchBase': BASE, 'elections': spec['elections'],
        'counts': {k: diag['overall'][k] for k in ('occurrenceCount', 'eligibleCount', 'normalizedCount')},
        'referenceCount': len(refs), 'inputHashes': contract,
        'specificationSha256': hashlib.sha256((DEST/'specification.json').read_bytes()).hexdigest(),
        'codeHashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in code},
        'outputHashes': {name: hashlib.sha256(encode(value)).hexdigest() for name, value in outputs.items()},
    }
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, value in build().items():
        raw = encode(value)
        path = DEST/name
        if args.check:
            if not path.exists() or path.read_bytes() != raw:
                raise ValueError('Stale Stage7 output: '+name)
        else:
            path.write_bytes(raw)
    print('Stage7 deterministic outputs and pinned inputs verified' if args.check else 'Stage7 outputs generated')


if __name__ == '__main__':
    main()
