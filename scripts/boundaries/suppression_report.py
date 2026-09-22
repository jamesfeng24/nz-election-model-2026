"""Sharp conditional disclosure bounds for the two unchanged-seat exceptions."""
import argparse
import json
from fractions import Fraction
from pathlib import Path
from scripts.boundaries.current_inputs import load, aggregate, ROOT
from scripts.boundaries.feasible import bounded_sum_component, tighten_destinations, outgoing_weight_bounds, fraction_json

OUTPUT = ROOT / 'data/processed/boundaries/2020-2025/suppression-exceptions.json'
EXCEPTIONS = (('general', '4018221'), ('maori', '4019214'))


def build():
    inputs = load()
    reports = []
    detected = set()
    for kind, key in [('general', 'unchangedGeneral'), ('maori', 'unchangedMaori')]:
        for target_name in inputs['changes'][key]:
            source_name = inputs['changes']['unchangedRename'].get(target_name, target_name)
            for cell in inputs['cells'][kind]:
                old = inputs['sourceNames'][kind][cell['source']] == source_name
                new = inputs['targetNames'][kind][cell['target']] == target_name
                if old != new:
                    detected.add((kind, cell['meshblockId']))
    if detected != set(EXCEPTIONS):
        raise ValueError('Unexpected unchanged-electorate membership exception')
    for kind, meshblock in EXCEPTIONS:
        cells = inputs['cells'][kind]
        cell = next(c for c in cells if c['meshblockId'] == meshblock)
        if cell['population']['status'] != 'suppressed':
            raise ValueError('Expected suppressed source observation')
        peers = [c for c in cells if c['target'] == cell['target'] and c['meshblockId'] != meshblock]
        lower, upper = bounded_sum_component(0, 5, sum(c['population']['lower'] for c in peers),
                                              sum(c['population']['upper'] for c in peers),
                                              inputs['controls'][kind][cell['target']])
        edges = outgoing_weight_bounds(tighten_destinations(aggregate(cells), inputs['controls'][kind]))
        edge = next(e for e in edges if e['source'] == cell['source'] and e['target'] == cell['target'])
        if edge['meshblockCount'] != 1:
            raise ValueError('Exception transfer is no longer a single meshblock')
        reports.append({**cell, 'electorateType': kind,
                        'sourceName': inputs['sourceNames'][kind][cell['source']],
                        'targetName': inputs['targetNames'][kind][cell['target']],
                        'publishedSourcePopulationControl': None,
                        'sourceControlReason': 'No same-vintage source-electorate total is registered; election turnout population is a different vintage and is not imposed.',
                        'targetPopulationControl': inputs['controls'][kind][cell['target']],
                        'conditionalPopulationLower': lower, 'conditionalPopulationUpper': upper,
                        'transfer': edge,
                        'targetCompositionLower': fraction_json(Fraction(lower, inputs['controls'][kind][cell['target']])),
                        'targetCompositionUpper': fraction_json(Fraction(upper, inputs['controls'][kind][cell['target']])),
                        'notionalPartyVoteImpact': {'formula': 'source party votes × transfer weight',
                            'pointEstimate': None, 'lowerMultiplier': edge['weightLower'], 'upperMultiplier': edge['weightUpper'],
                            'conservation': 'Any feasible increase here reduces other destinations from the same source; marginal endpoints must not be summed as a joint allocation.'},
                        'interpretation': 'Zero is feasible but not identified. Preserve suppressed value and full feasible range; do not force an unchanged-seat identity or discard this meshblock.'})
    return {'schemaVersion': 1, 'status': 'resolved_as_partially_identified',
            'transitionId': 'nz-2023-to-2026', 'inputHashes': inputs['inputHashes'],
            'method': 'Integer meshblock disclosure intervals plus exact published target totals; destination partitions are independent, giving sharp edge and outgoing-ratio bounds.',
            'conditionality': 'Bounds assume Schedule C totals describe the same electoral-population universe. No unregistered source-side total or unobserved subgroup count is imposed.',
            'technicalAdjustmentEvidence': 'Preserved layer metadata describes technical changes without population; Schedule B marks affected seats unchanged, but neither identifies these suppressed cells individually as zero.',
            'nominalPopulation': None, 'exceptions': reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = (json.dumps(build(), ensure_ascii=False, indent=2) + '\n').encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != raw:
            raise SystemExit('Stale suppression report')
    else:
        OUTPUT.write_bytes(raw)
    print('Two exceptions resolved as bounds; no nominal population inferred')


if __name__ == '__main__':
    main()
