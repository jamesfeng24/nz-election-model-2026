"""Design guards only: no anchor estimation, response fit or historical prediction."""
from fractions import Fraction
from math import isfinite

import numpy as np
from scripts.checkpoints.complete_share_feature_rank import rank_details


def initial_direction(source, target, anchor):
    """Use initial direction; crossing/ending distance cannot change the regime."""
    source, target, anchor = map(Fraction, (source, target, anchor))
    if not all(0 <= value <= 1 for value in (source, target, anchor)):
        raise ValueError('Share outside [0,1]')
    movement = target - source
    if movement == 0:
        return {'regime': 'neutral', 'T': None, 'crossesAnchor': False}
    direction = movement * (anchor - source)
    return {'regime': 'toward' if direction > 0 else 'away',
            'T': int(direction > 0), 'startsAtAnchor': source == anchor,
            'crossesAnchor': (source-anchor)*(target-anchor) < 0}


def national_regime(row, anchor_values):
    """Explicit input whitelist: local/candidate outcomes do not classify regimes."""
    if not anchor_values:
        return {'status': 'abstain', 'reason': 'missing_anchor'}
    classifications = [initial_direction(row['nationalSource'], row['nationalTarget'], v)
                       for v in anchor_values]
    if any(r['T'] is None for r in classifications):
        return {'status': 'abstain', 'reason': 'zero_national_movement'}
    if len({r['T'] for r in classifications}) != 1:
        return {'status': 'abstain', 'reason': 'anchor_stability_disagreement'}
    movement = Fraction(row['nationalTarget'])-Fraction(row['nationalSource'])
    local = Fraction(row['partyTarget'])-Fraction(row['partySource'])
    return {'status': 'available', 'T': classifications[0]['T'],
            'regime': classifications[0]['regime'], 'localMovement': str(local),
            'nationalLocalOppose': movement*local < 0,
            'anchorClassifications': classifications}


def source_state_classifier(source_candidate_share, local_movement, baseline):
    """Deferred candidate/seat interpretation exposes its shared C0 dependency."""
    gap = Fraction(baseline)-Fraction(source_candidate_share)
    movement = Fraction(local_movement)
    return {'T': int(gap*movement > 0) if movement else None,
            'sharedOutcomeAndClassifierInput': 'C0',
            'reason': 'deltaC=C1-C0; initial_direction_uses_B-C0; mechanical_dependence_not_removed'}


def anchor_guard(snapshots, estimates):
    """Validate later supplied full/delete-one estimates; never estimate them here."""
    unavailable = lambda reason: {'status': 'abstain', 'reason': reason}
    years = [r['year'] for r in snapshots]
    if len(years) != len(set(years)):
        raise ValueError('Duplicate election snapshot')
    if len(snapshots) < 4:
        return unavailable('fewer_than_four_completed_elections')
    support = [Fraction(r['nationalSupport']) for r in snapshots]
    premiums = [Fraction(r['generalPremium']) for r in snapshots]
    if min(support) == max(support):
        return unavailable('no_national_support_variation')
    if not min(premiums) < 0 < max(premiums):
        return unavailable('no_observed_premium_sign_bracket')
    expected = {None, *years}
    if {r['omittedYear'] for r in estimates} != expected or len(estimates) != len(expected):
        return unavailable('missing_full_or_delete_one_estimates')
    signs, anchors = set(), []
    for estimate in estimates:
        slope, anchor = estimate['slope'], estimate['anchor']
        if (not isfinite(slope) or not isfinite(anchor) or abs(slope) <= 1e-12
                or estimate['rank'] != 2 or not isfinite(estimate['scaledCondition'])
                or estimate['scaledCondition'] > 1e6):
            return unavailable('weak_or_nonfinite_anchor_design_or_zero_slope')
        retained = [r for r in snapshots if r['year'] != estimate['omittedYear']]
        low = min(float(Fraction(r['nationalSupport'])) for r in retained)
        high = max(float(Fraction(r['nationalSupport'])) for r in retained)
        if not 0 <= anchor <= 1 or not low <= anchor <= high:
            return unavailable('extrapolated_crossing')
        signs.add(slope > 0)
        anchors.append(anchor)
    if len(signs) != 1:
        return unavailable('slope_sign_unstable')
    return {'status': 'available', 'stabilityAnchors': anchors,
            'interpretation': 'finite_delete_one_stability_set_not_calibrated_uncertainty'}


def regime_rank_guard(rows):
    """Count distinct party-transition environments, not replicated seats."""
    unavailable = lambda reason: {'status': 'abstain', 'reason': reason}
    if len(rows) < 15:
        return unavailable('fewer_than_five_rows_per_free_coefficient')
    environments = {}
    for row in rows:
        if row['T'] not in (0, 1) or not isfinite(row['x']):
            return unavailable('missing_regime_or_movement')
        environment = row['environmentId']
        if environment in environments and environments[environment] != row['T']:
            raise ValueError('National regime differs within party-transition environment')
        environments[environment] = row['T']
    if min(sum(value == t for value in environments.values()) for t in (0, 1)) < 2:
        return unavailable('fewer_than_two_transition_environments_per_regime')
    if min(sum(row['T'] == t and row['x'] != 0 for row in rows) for t in (0, 1)) < 5:
        return unavailable('fewer_than_five_nonzero_local_rows_per_regime')
    matrix = np.array([[1.0, row['x'], row['x']*row['T']] for row in rows])
    details = rank_details(matrix, [0, 1, 2])
    if details['rank'] != 3 or details['weakCondition']:
        return unavailable('rank_deficient_or_weak_condition')
    return {'status': 'available', 'environmentCounts': {
        str(t): sum(value == t for value in environments.values()) for t in (0, 1)}}
