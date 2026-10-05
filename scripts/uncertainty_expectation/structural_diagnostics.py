"""Complete-denominator descriptive associations; no new structural labels."""
from collections import Counter
import numpy as np
from .common import PREFIX, INVENTORY, arguments, read, save, verify
from .audits import association


def build():
    value = read(PREFIX+'/structure.json')
    outcomes = {r['id']: r for r in value['retrospectiveDiagnostics']}
    groups, diagnostics = [], []
    for year in (2014, 2017, 2020, 2023):
        records = [r for r in value['structuralRecords'] if r['year'] == year]
        group = {'year': year, 'seats': len(records),
            'sourceStates': dict(Counter(c['status'] for r in records for c in r['sourceContenders'])),
            'targetStates': dict(Counter(c['structuralStatus'] for r in records for c in r['targets'])),
            'unknownRosterAvailabilitySeats': sum(r['historicalAvailability'] != 'verified' for r in records),
            'sourceProxyDefinition': 'source nonmajor candidate share times incoming population scenario; not a reconstructed target vote',
            'SWithoutAcceptedPersonLinkCandidates': sum(c['S']['SDespiteNoAcceptedPersonLink'] for r in records for c in r['targets']),
            'associations': {}}
        for coordinate, field in (('balance', 'balanceRawLogError'), ('mass', 'majorMassRawLogError')):
            selected = [r for r in records if outcomes[r['id']][field] is not None]
            support = np.array([r['sourceNonmajorSupportProxy'] for r in selected])
            errors = np.array([outcomes[r['id']][field] for r in selected])
            centered = errors-errors.mean()
            sd = float(np.sqrt(np.mean(centered**2)))
            group['associations'][coordinate] = {'records': len(selected), 'unknown': len(records)-len(selected),
                'sourceSupportVsSignedError': association(support, errors),
                'sourceSupportVsSquaredWithinElectionError': association(support, centered**2),
                'descriptiveElectionErrorMean': float(errors.mean()), 'descriptiveElectionErrorSD': sd}
            diagnostics.extend({'id': r['id'], 'coordinate': coordinate,
                'sourceSupportProxy': r['sourceNonmajorSupportProxy'], 'rawLogError': float(e),
                'descriptivelyCenteredError': float(v), 'descriptivelyStandardizedError': float(v/sd) if sd else None,
                'notForecastStandardized': True} for r, e, v in zip(selected, errors, centered))
        groups.append(group)
    traces = []
    for row in read(INVENTORY)['candidateRecords']:
        theta = row['parameters']['coefficients']
        traces.append({'id': row['targetElectorateId'], 'savedFitId': row['savedFitId'],
            'trainingOnlyMeans': row['trainingOnlyMeans'], 'kappa': row['parameters']['kappa'],
            'coefficients': theta, 'trainingIds': row['trainingIds'],
            'candidates': [{'id': f['id'], 'centeredS': f['centered'][0], 'centeredR': f['centered'][1],
                'SLogIntensityContribution': theta['S']*f['centered'][0],
                'RLogIntensityContribution': theta['R']*f['centered'][1],
                'totalFeatureLogIntensity': theta['S']*f['centered'][0]+theta['R']*f['centered'][1],
                'supportedMass': f['supportedMass']} for f in row['features']],
            'noNewPredictionOrFit': True})
    return {'stage': 47, 'seats': len(value['structuralRecords']), 'byElection': groups, 'records': diagnostics,
        'fixedFeatureContributions': traces,
        'datedPredictorFeasibility': 'Unknown rosters/strength timing prevents a fully forecast-available structural variance rule; no nonmatch is promoted to departure.',
        'allValidObservationsRetained': True, 'withinElectionCenteringIsDescriptiveOnly': True,
        'significanceTestsOrFits': None, 'labelsChosenFromErrors': False}


def main():
    args = arguments()
    verify()
    save('structural-diagnostics.json', build(), args.check)


if __name__ == '__main__':
    main()
