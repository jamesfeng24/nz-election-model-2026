"""Use canonical rational geography; the two overlap directions stay separate."""
from fractions import Fraction
from scripts.checkpoints.stage25_geography import fraction, tier
from .common import read, SNAPSHOT


def classification(row):
    if row['certifiedTwoSidedExact']:
        return 'exact'
    if row['dominantPredecessorId'] is None:
        return 'fallback'
    incoming = row.get('dominantTargetInheritanceLower')
    retained = row.get('dominantSourceRetentionLower')
    if incoming is None or retained is None:
        return 'fallback'
    label = tier(False, fraction(incoming), fraction(retained))
    return {'approximate_two_sided_95':'approximate_95',
            'approximate_two_sided_90_only':'approximate_90',
            'not_two_sided_90':'fallback'}[label]


def admitted(row, threshold):
    if threshold not in (90, 95):
        raise ValueError('Unregistered overlap tier')
    status = classification(row)
    return status == 'exact' or status == 'approximate_95' or threshold == 90 and status == 'approximate_90'


def canonical_2026(frame):
    rows = []
    for seat in frame:
        incoming = seat['dominantPredecessorIncomingBounds']
        dominant = [p for p in seat['predecessors'] if p['sourceBoundaryCode'] == seat['dominantPredecessor']]
        if len(dominant) > 1:
            raise ValueError('Ambiguous dominant predecessor')
        p = dominant[0] if dominant else None
        row = {'geographyId':'2023-2026:'+seat['scope']+':'+seat['targetElectorateId'],
               'targetElectorateId':seat['targetElectorateId'], 'targetElectorateName':seat['officialName'],
               'sourceYear':2023, 'targetYear':2026, 'scope':seat['scope'],
               'certifiedTwoSidedExact':seat['geographyStatus']=='certified_two_sided_exact',
               'dominantPredecessorId':p['sourceElectorateId'] if p else None,
               'dominantTargetInheritanceLower':incoming[0] if p else None,
               'dominantTargetInheritanceUpper':incoming[1] if p else None,
               'dominantSourceRetentionLower':p['sourceRetainedPopulationShareBounds'][0] if p else None,
               'dominantSourceRetentionUpper':p['sourceRetainedPopulationShareBounds'][1] if p else None,
               'predecessors':seat['predecessors'], 'boundaryCode':seat['boundaryCode'],
               'sourceBoundaryVersion':seat['sourceBoundaryVersionId'],
               'targetBoundaryVersion':seat['boundaryVersionId'],
               'units':seat['overlapUnits'], 'evidencePaths':seat['evidencePaths']}
        row['transportTier'] = classification(row)
        rows.append(row)
    return rows


def all_rows():
    historical = read('data/processed/checkpoints/stage25-historical-geography/geography.json')['records']
    return [dict(r, transportTier=classification(r)) for r in historical] + canonical_2026(read(SNAPSHOT+'target-frame.json')['records'])
