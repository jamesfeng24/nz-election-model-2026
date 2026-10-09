import type { ReleasePoint } from '../data/loader';
import { longDate, prob } from './format';

/** The chart switches on once this many releases exist; before that nothing is drawn. */
export const MIN_RELEASES = 3;
const LINES = [
  { kind: 'bloc', id: 'nat-act-nzf', colour: '#00529f', short: null },
  { kind: 'bloc', id: 'lab-grn-tpm', colour: '#d82a20', short: null },
  { kind: 'scenario', id: 'hung', colour: '#6b6b6b', short: 'Hung parliament' },
] as const;

export function TrendChart({ history }: { history: ReleasePoint[] }) {
  if (history.length < MIN_RELEASES) return null;
  const W = 640, H = 300, left = 44, right = 150, top = 16, bottom = 40;
  const t = (p: ReleasePoint) => Date.parse(p.dataCutoff);
  const t0 = t(history[0]), t1 = t(history[history.length - 1]);
  const x = (p: ReleasePoint) => left + ((t1 === t0 ? 0 : (t(p) - t0) / (t1 - t0))) * (W - left - right);
  const y = (v: number) => top + (1 - v) * (H - top - bottom);
  const series = LINES.flatMap(line => {
    const pts = history.flatMap(p => { const v = (line.kind === 'bloc' ? p.blocMajority : p.scenarios)[line.id]; return v ? [{ p, v: v.p, label: v.label }] : []; });
    return pts.length === history.length ? [{ line, pts }] : [];
  });
  if (series.length === 0) return null;
  return <figure className="trend">
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Chance over ${history.length} releases: ${series.map(s => `${s.pts[0].label} from ${prob(s.pts[0].v)} to ${prob(s.pts[s.pts.length - 1].v)}`).join('; ')}`}>
      {[0, 0.25, 0.5, 0.75, 1].map(v => <g key={v}><line x1={left} x2={W - right} y1={y(v)} y2={y(v)} className="grid" /><text x={left - 6} y={y(v) + 4} textAnchor="end" className="tick">{Math.round(v * 100)}%</text></g>)}
      {series.map(({ line, pts }) => <g key={line.id}>
        <polyline fill="none" stroke={line.colour} strokeWidth="2.5" points={pts.map(q => `${x(q.p)},${y(q.v)}`).join(' ')} />
        {pts.map(q => <circle key={q.p.snapshotId} cx={x(q.p)} cy={y(q.v)} r="3.5" fill={line.colour} />)}
        <text x={W - right + 8} y={y(pts[pts.length - 1].v) + 4} fill={line.colour} className="endlabel">{line.short ?? pts[pts.length - 1].label} {prob(pts[pts.length - 1].v)}</text>
      </g>)}
      <text x={left} y={H - 12} className="tick">{longDate(history[0].dataCutoff)}</text>
      <text x={W - right} y={H - 12} textAnchor="end" className="tick">{longDate(history[history.length - 1].dataCutoff)}</text>
    </svg>
    <figcaption>Chance of a majority, and of a hung parliament, at each weekly release. Each point is a separate forecast of the same kind; the lines show how the picture has changed, not a prediction.</figcaption>
  </figure>;
}
