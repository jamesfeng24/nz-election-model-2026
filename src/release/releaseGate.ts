import type { ForecastSnapshot } from '../types/export';

/**
 * TypeScript side of the publication gate (docs/release-checklist.md), run on a validated v2 snapshot before it is
 * archived. The schema already enforces the universe, nesting and synthetic guards; this adds the release checks.
 * Every failure blocks publication; nothing is filled, clipped or silently dropped.
 */
export interface ReleasePolicy {
  /** Largest Monte Carlo SE allowed on any published probability (release policy proposal: 0.01). */
  probabilityMcseMax: number;
  /** Rehearsals only: permit a synthetic-fixture snapshot into a non-public archive. */
  allowSynthetic: boolean;
}

export interface GateResult { passed: boolean; failures: string[] }

type Estimate = { p: number; mcse: number; ess: number };

function estimates(snapshot: ForecastSnapshot): [string, Estimate][] {
  const out: [string, Estimate][] = [];
  if (snapshot.seatLayer.status === 'available') {
    const s = snapshot.seatLayer.summary;
    for (const p of s.parties)
      for (const key of ['probAnySeat', 'probQualified', 'probQualifiedByPartyVote', 'probQualifiedByLifeboatOnly', 'probOverhang'] as const)
        out.push([`${p.partyId}.${key}`, p[key]]);
    for (const b of s.blocs) out.push([`${b.id}.probMajority`, b.probMajority], [`${b.id}.probExactHalf`, b.probExactHalf]);
    out.push(['parliament.probAnyOverhang', s.parliament.probAnyOverhang]);
    for (const sc of s.scenarios) out.push([`scenario.${sc.id}`, sc.probability]);
  }
  for (const d of snapshot.electorateDetail)
    for (const c of d.candidates) {
      out.push([`${d.electorateId}.${c.candidateId}.winProbability`, c.winProbability]);
      if (c.winProbabilityInflation) out.push([`${d.electorateId}.${c.candidateId}.winProbabilityInflation`, c.winProbabilityInflation]);
    }
  return out;
}

export function releaseGate(snapshot: ForecastSnapshot, policy: ReleasePolicy): GateResult {
  const failures: string[] = [];
  if (snapshot.provenance.kind !== 'model' && !policy.allowSynthetic) failures.push('Only model snapshots may be published');
  if (snapshot.targetType !== 'nowcast') failures.push('The primary release is a nowcast');
  if (snapshot.unavailableElectorates.length) failures.push(`${snapshot.unavailableElectorates.length} electorates have no prediction`);
  if (snapshot.seatLayer.status !== 'available') failures.push(`Seat layer withheld: ${snapshot.seatLayer.reason}`);
  if (snapshot.mmp.status !== 'available') failures.push('MMP allocation withheld');
  if (snapshot.electorateDetail.length !== snapshot.simulation.electoratePredictions.length)
    failures.push('Every predicted electorate needs its detail');
  if (!(policy.probabilityMcseMax > 0 && policy.probabilityMcseMax < 0.5)) failures.push('Invalid probability MCSE threshold');
  const imprecise = estimates(snapshot).filter(([, e]) => !(e.mcse <= policy.probabilityMcseMax));
  if (imprecise.length)
    failures.push(`${imprecise.length} probabilities exceed the Monte Carlo SE threshold ${policy.probabilityMcseMax} (first: ${imprecise.slice(0, 3).map(([k, e]) => `${k} ${e.mcse.toFixed(4)}`).join(', ')})`);
  return { passed: failures.length === 0, failures };
}
