"""Reproduce supplemental linkage separately from outcome coverage diagnostics."""
import argparse
from collections import defaultdict
from hashlib import sha256

from scripts.checkpoints.stage25_availability import mapped_contests
from scripts.checkpoints.stage21_identity_final import observed_winners
from .common import (ROOT, DEST, INPUTS, OCCURRENCES, GEOGRAPHY, CONTINUITY, LINKS,
                     MAPPING, TENURE, read, encode, digest, verify_inputs)
from .components import SAME, validate_components, person_groups
from .evidence import preserved_claims, inherited_audit
from .names import alias_pairs, strict_member
from .proposals import adapt_occurrences, generate
from .report import coverage, readiness, table


def ballot_groups(mapping):
    result = {}
    for contest in mapped_contests(mapping).values():
        for candidate in contest['candidates']:
            cid = candidate['candidateOccurrenceId']
            group = candidate['partyKey']
            if cid in result and result[cid] != group:
                raise ValueError('Conflicting ballot group')
            result[cid] = group
    return result


def review_queue(edges, cap=60):
    if not 0 <= cap <= 60:
        raise ValueError('Review cap outside frozen contract')
    exceptions = [e for e in edges if e['label']=='unresolved_ambiguous']
    ordered = sorted(exceptions, key=lambda e:(e['sourceYear'],e['targetYear'],e['ambiguityType'],
                                               e['sourceOccurrenceId'],e['targetOccurrenceId']))
    return [{'edgeId':e['edgeId'],'position':i+1,'sourceYear':e['sourceYear'],
             'targetYear':e['targetYear'],'ambiguityType':e['ambiguityType'],
             'reviewState':'pending_preserved_inspection' if i<cap else 'not_reviewed_budget'}
            for i,e in enumerate(ordered)]


def construct(occurrences=None, links=None, mapping=None, claims=None):
    verify_inputs()
    original = read(OCCURRENCES)['records'] if occurrences is None else occurrences
    links = read(LINKS)['links'] if links is None else links
    mapping = read(MAPPING) if mapping is None else mapping
    rows, duplicates = adapt_occurrences(original, ballot_groups(mapping))
    aliases = alias_pairs(read(str((DEST/'aliases.json').relative_to(ROOT))))
    claims = preserved_claims() if claims is None else claims
    geo = read(GEOGRAPHY)['records']
    edges = generate(rows,geo,read(CONTINUITY)['records'],links,claims,aliases)
    audits = validate_components(edges,rows,aliases)
    groups = {'broad':person_groups(edges,rows), 'strict':person_groups(edges,rows,strict=True)}
    accepted = [e for e in edges if e['label'] in SAME]
    connected_ids = {cid for e in accepted for cid in (e['sourceOccurrenceId'],e['targetOccurrenceId'])}
    for row in rows:
        row['relationshipState'] = 'accepted_same_person_edge' if row['candidateOccurrenceId'] in connected_ids else 'no_accepted_same_person_edge_not_proof_of_replacement'
    return {'occurrences.json':{'records':rows,'deduplicatedRepresentations':duplicates},
            'proposed-links.json':{'records':edges,'componentAudits':audits},
            'accepted-relationships.json':{'broadEdgeIds':[e['edgeId'] for e in accepted],
                 'strictEdgeIds':[e['edgeId'] for e in accepted if strict_member(e)],
                 'distinctEdgeIds':[e['edgeId'] for e in edges if e['label']=='documentary_distinct_people'],
                 'historicalAdjudicationsOverwritten':False},
            'persons.json':groups, 'review-queue.json':{'records':review_queue(edges)},
            'inherited-evidence-audit.json':{'records':inherited_audit(rows)},
            'documentary-claims.json':{'records':claims}, 'review-table.md':table(edges)}


def apply_review(queue, dispositions):
    selected = [r['edgeId'] for r in queue if r['reviewState']=='pending_preserved_inspection']
    records = dispositions['records']
    ids = [r['edgeId'] for r in records]
    if len(ids)!=len(set(ids)) or ids!=selected[:len(ids)] or len(ids)>60:
        raise ValueError('Manual review must be a unique prefix within the cap')
    by_id = {r['edgeId']:r for r in records}
    result=[]
    for row in queue:
        finding=by_id.get(row['edgeId'])
        state = 'reviewed_unresolved' if finding else 'not_reviewed_budget' if row['reviewState']=='not_reviewed_budget' else 'not_reviewed_stopped'
        if finding:
            if finding['disposition']!='unresolved' or not finding['inspectionEvidence'] or not finding['reason']:
                raise ValueError('Promotion needs separate occurrence-specific evidence amendment; no silent review override')
            for evidence in finding['inspectionEvidence']:
                if digest(evidence['artifact'])!=evidence['sha256']:
                    raise ValueError('Changed manual inspection evidence')
        result.append({**row,'reviewState':state,'manualDisposition':finding})
    return result


def reports(outputs):
    original=read(OCCURRENCES)['records']
    edges=outputs['proposed-links.json']['records']
    rows=outputs['occurrences.json']['records']
    review=apply_review(outputs['review-queue.json']['records'],read(str((DEST/'manual-review.json').relative_to(ROOT))))
    return {'review.json':{'records':review,'automaticChecks':'rule_competitor_component_provenance_checks_not_documentary_validation'},
            'coverage.json':coverage(rows,edges,read(GEOGRAPHY)['records'],outputs['persons.json'],review,observed_winners(original)),
            'readiness.json':readiness(edges,original,read(TENURE)['records'])}


def save(name,value,check):
    raw=value if isinstance(value,bytes) else encode({'schemaVersion':1,'stage':26,**value})
    path=DEST/name
    if check:
        if path.read_bytes()!=raw:
            raise ValueError(f'Changed deterministic linkage artifact: {name}')
    else:
        path.write_bytes(raw)
    return sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--construct-only',action='store_true')
    args=parser.parse_args()
    outputs=construct()
    if not args.construct_only:
        outputs.update(reports(outputs))
    hashes={name:save(name,value,args.check) for name,value in outputs.items()}
    if not args.construct_only:
        manual='data/processed/evidence/practical-candidate-linkage/manual-review.json'
        scripts=sorted(Path.relative_to(ROOT).as_posix() for Path in (ROOT/'scripts/evidence/practical_candidate_linkage').glob('*.py'))
        manifest={'inputSha256':{p:digest(p) for p in (*INPUTS,manual,str((DEST/'input-contract.json').relative_to(ROOT)))},
                  'generatorSha256':{p:digest(p) for p in scripts},'outputSha256':hashes}
        save('manifest.json',manifest,args.check)
    print({'occurrences':len(outputs['occurrences.json']['records']),
           'proposedEdges':len(outputs['proposed-links.json']['records']),
           'broadEdges':len(outputs['accepted-relationships.json']['broadEdgeIds']),
           'strictEdges':len(outputs['accepted-relationships.json']['strictEdgeIds'])})


if __name__=='__main__':
    main()
