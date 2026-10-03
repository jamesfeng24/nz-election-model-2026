"""Direct accepted source occurrence joins; no target residual or winner admission."""
from collections import defaultdict
from math import isfinite
from scripts.evidence.practical_candidate_linkage.names import strict_member
from .common import keyed


def link_index(edges, accepted):
    indexed = keyed(edges, 'edgeId')
    broad, strict = set(accepted['broadEdgeIds']), set(accepted['strictEdgeIds'])
    if len(broad) != len(accepted['broadEdgeIds']) or len(strict) != len(accepted['strictEdgeIds']) or not strict <= broad:
        raise ValueError('Invalid accepted linkage views')
    if not broad <= indexed.keys():
        raise ValueError('Dangling accepted link')
    result = {v:defaultdict(list) for v in ('broad','strict','proposals')}
    for edge in edges:
        result['proposals'][edge['targetOccurrenceId']].append(edge)
    for eid in sorted(broad):
        edge = indexed[eid]
        if edge['label'] not in ('documentary_same_person','accepted_algorithmic_same_person') or bool(edge['competingOccurrenceIds']):
            raise ValueError('Accepted relation contradicts frozen safeguards')
        if (eid in strict) != strict_member(edge):
            raise ValueError('Strict rule mismatch')
        result['broad'][edge['targetOccurrenceId']].append(edge)
        if eid in strict:
            result['strict'][edge['targetOccurrenceId']].append(edge)
    return result


def missing(reason, proposals=()):
    return {'status':'neutral_fallback','reason':reason,'valueFraction':None,
            'sourceOccurrenceId':None,'edgeId':None,'candidateStrengthKnown':False,
            'proposedAcceptedEdgeIds':[e['edgeId'] for e in proposals]}


def resolve(target_id, row, view, index, occurrences, residuals):
    candidates = [e for e in index[view].get(target_id,[]) if e['sourceYear']==row['sourceYear'] and e['targetYear']==row['targetYear']]
    if not candidates:
        out = missing('not_in_strict_view' if view=='strict' and index['broad'].get(target_id) else 'no_accepted_adjacent_relation_not_proof_of_replacement')
        leads = [e for e in index['proposals'].get(target_id,[]) if (e['sourceYear'],e['targetYear'])==(row['sourceYear'],row['targetYear'])]
        out['unresolvedProposalIds'] = sorted(e['edgeId'] for e in leads if e['label']=='unresolved_ambiguous')
        out['documentaryDistinctProposalIds'] = sorted(e['edgeId'] for e in leads if e['label']=='documentary_distinct_people')
        return out
    if len(candidates) != 1:
        return missing('conflicting_multiple_direct_sources',candidates)
    e = candidates[0]; sid = e['sourceOccurrenceId']
    if (e['primaryGeographyId'],e['sourceElectorateId'],e['targetElectorateId']) != (row['geographyId'],row['sourceElectorateId'],row['targetElectorateId']) or not e['primaryExactHeld']:
        return missing('seat_change_or_nonexact_relation',candidates)
    source, target = occurrences.get(sid), occurrences.get(target_id)
    if source is None or target is None:
        raise ValueError('Dangling occurrence link')
    if (source['year'],target['year'],source['electorateId'],target['electorateId']) != (row['sourceYear'],row['targetYear'],row['sourceElectorateId'],row['targetElectorateId']):
        raise ValueError('Occurrence-local ID mismatch')
    if source['candidateContestStatus'] != 'held' or target['candidateContestStatus'] != 'held':
        return missing('unheld_occurrence',candidates)
    if e['contextAssessment'] not in ('documented_party_continuity_same_original_affiliation', 'documented_single_party_label_continuity', 'independent_no_party_context'):
        return missing('party_change_outside_frozen_transport_context',candidates)
    r = residuals.get(sid)
    value = r.get('normalizedPremium') if r else None
    if r is not None and (r['year'],r['electorateId']) != (row['sourceYear'],row['sourceElectorateId']):
        raise ValueError('Source residual ID mismatch')
    if value is None or not isfinite(value):
        out = missing('source_residual_unavailable',candidates)
        out.update(sourceOccurrenceId=sid,edgeId=e['edgeId'],normalizationReason=r.get('normalizationReason') if r else 'missing_source_record')
        return out
    return {'status':'supported','reason':None,'valueFraction':value,'displayPP':100*value,
            'sourceOccurrenceId':sid,'sourceReferenceId':r['referenceId'],'edgeId':e['edgeId'],
            'evidenceTier':e['label'],'ruleFlags':e['ruleFlags'],'officialSourceIds':e['officialSourceIds'],
            'historicalFactYears':e['historicalFactYears'],'publicationByForecastCutoff':e['publicationByForecastCutoff'],
            'adjudicationTiming':e['adjudicationTiming'],'careerHistoryRequired':False,
            'sourceNormalization':'frozen_whole_contest_source_election_LOO; no_target_reference_consumed'}
