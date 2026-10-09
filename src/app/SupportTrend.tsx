import type { ForecastSnapshot } from '../types/export';
import { COLOURS, FALLBACK } from './SeatChart';
import { longDate } from './format';

const midpoint = (start: string | null, end: string) => (start ? (Date.parse(start) + Date.parse(end)) / 2 : Date.parse(end));

/** The national model's weekly estimate of support since the 2023 election, with each listed poll as a faint dot. */
export function SupportTrend({ snapshot }: { snapshot: ForecastSnapshot }) {
  const trend = snapshot.evidence?.trend;
  if (!trend) return null;
  const polls = snapshot.evidence!.nationalPolls.filter(p => p.usedInModel);
  const abbreviation = (id: string) => snapshot.directory.parties.find(p => p.partyId === id)?.abbreviation ?? id;
  const W = 720, H = 360, left = 40, right = 56, top = 14, bottom = 34;
  const t0 = Date.parse(trend.weeks[0]), t1 = Date.parse(trend.weeks[trend.weeks.length - 1]);
  const topValue = Math.max(...trend.parties.flatMap(p => p.upper90));
  const yMax = Math.ceil((topValue + 1) / 10) * 10;
  const x = (t: number) => left + ((t - t0) / (t1 - t0)) * (W - left - right);
  const y = (v: number) => top + (1 - v / yMax) * (H - top - bottom);
  const colour = (id: string, i: number) => COLOURS[id] ?? FALLBACK[i % FALLBACK.length];
  const years = [2024, 2025, 2026].map(yr => Date.UTC(yr, 0, 1)).filter(t => t > t0 && t < t1);
  // End labels, nudged apart so they stay readable.
  const ends = trend.parties.map((p, i) => ({ p, i, at: y(p.mean[p.mean.length - 1]) })).sort((a, b) => a.at - b.at);
  ends.forEach((e, k) => { if (k > 0 && e.at - ends[k - 1].at < 12) e.at = ends[k - 1].at + 12; });
  const line = (values: number[]) => trend.weeks.map((w, k) => `${x(Date.parse(w))},${y(values[k])}`).join(' ');
  return <figure className="trend">
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Weekly support since the 2023 election, ${longDate(trend.weeks[0])} to ${longDate(trend.weeks[trend.weeks.length - 1])}: ${trend.parties.map(p => `${abbreviation(p.partyId)} ${p.mean[p.mean.length - 1].toFixed(1)}%`).join(', ')}`}>
      {Array.from({ length: yMax / 10 + 1 }, (_, k) => k * 10).map(v => <g key={v}><line x1={left} x2={W - right} y1={y(v)} y2={y(v)} className="grid" /><text x={left - 6} y={y(v) + 4} textAnchor="end" className="tick">{v}%</text></g>)}
      {years.map(t => <g key={t}><line x1={x(t)} x2={x(t)} y1={top} y2={H - bottom} className="grid" /><text x={x(t)} y={H - 12} textAnchor="middle" className="tick">{new Date(t).getUTCFullYear()}</text></g>)}
      {trend.parties.map((p, i) => polls.map(poll => { const share = poll.shares.find(s => s.partyId === p.partyId)?.percent; return share == null ? null : <circle key={`${p.partyId}-${poll.id}`} cx={x(midpoint(poll.fieldworkStart, poll.fieldworkEnd))} cy={y(share)} r="1.8" fill={colour(p.partyId, i)} opacity="0.35" />; }))}
      {trend.parties.map((p, i) => <g key={p.partyId}>
        <polygon points={`${line(p.upper90)} ${[...trend.weeks].reverse().map((w, k) => `${x(Date.parse(w))},${y(p.lower90[trend.weeks.length - 1 - k])}`).join(' ')}`} fill={colour(p.partyId, i)} opacity="0.12" />
        <polyline fill="none" stroke={colour(p.partyId, i)} strokeWidth="2" points={line(p.mean)} />
      </g>)}
      {ends.map(({ p, i, at }) => <text key={p.partyId} x={W - right + 6} y={at + 4} fill={colour(p.partyId, i)} className="endlabel">{abbreviation(p.partyId)}</text>)}
    </svg>
    <figcaption>{trend.basis} Dots are individual polls the model used.{' '}
      <a href="../polls/">Every poll, with sources</a>.</figcaption>
  </figure>;
}
