import type { ForecastSnapshot } from '../types/export';
import { partyLabel } from './partyNames';
import { PRIMARY_INTERVAL_LEVEL } from '../types/domain';
import { hemicycle, largestRemainder } from './hemicycle';

/** Left-to-right order of the headline chart, set by James (2026-10-09). Parties not in the snapshot are skipped. */
export const HEADLINE_ORDER = ['tepatimaori', 'greenparty', 'labourparty', 'opportunity', 'newzealandfirstparty', 'nationalparty', 'actnewzealand'];
export const COLOURS: Record<string, string> = {
  tepatimaori: '#8c1d40', greenparty: '#1c9a47', labourparty: '#d82a20', opportunity: '#12a4c6',
  newzealandfirstparty: '#222222', nationalparty: '#00529f', actnewzealand: '#e0b800',
};
export const FALLBACK = ['#6b5b95', '#c47f17', '#4d7c8a', '#a05195', '#7a8b3a', '#b5524b', '#5a6b73'];
const OTHER = '#a9b4b0';

interface Slice { key: string; label: string; mean: number; median: number; lower: number; upper: number; colour: string }

function slices(snapshot: ForecastSnapshot): { slices: Slice[]; total: number } {
  const name = (id: string) => partyLabel(snapshot, id, 'short');
  const layer = snapshot.seatLayer.status === 'available' ? snapshot.seatLayer.summary : null;
  const rows = layer
    ? layer.parties.map(p => ({ id: p.partyId, mean: p.meanSeats, set: p.seats }))
    : snapshot.simulation.partySeatSummaries.map(p => ({ id: p.partyId, mean: p.seats[0].median, set: p.seats }));
  const rank = (id: string) => { const i = HEADLINE_ORDER.indexOf(id); return i < 0 ? HEADLINE_ORDER.length : i; };
  const ordered = [...rows].sort((a, b) => rank(a.id) - rank(b.id));
  const out: Slice[] = ordered.map((r, i) => {
    const r80 = r.set.find(v => v.level === PRIMARY_INTERVAL_LEVEL)!;
    return { key: r.id, label: name(r.id), mean: r.mean, median: r.set[0].median, lower: r80.lower, upper: r80.upper, colour: COLOURS[r.id] ?? FALLBACK[i % FALLBACK.length] };
  });
  const listed = out.reduce((a, s) => a + s.mean, 0);
  const size = layer ? layer.parliament.meanSize : listed;
  if (size - listed >= 0.5) out.push({ key: 'others', label: 'Others', mean: size - listed, median: Math.round(size - listed), lower: NaN, upper: NaN, colour: OTHER });
  return { slices: out, total: Math.round(size) };
}

/** Headline graphic: expected seats per party as a parliament chart, one dot per seat, parties in James's order. */
export function SeatChart({ snapshot }: { snapshot: ForecastSnapshot }) {
  const { slices: parts, total } = slices(snapshot);
  const counts = largestRemainder(parts.map(p => p.mean), total);
  const seats = hemicycle(total);
  const owner: number[] = counts.flatMap((n, i) => Array(n).fill(i) as number[]);
  const W = 640, pad = 20, scale = (W - 2 * pad) / 2, H = 2 * pad + scale;
  const row = Math.max(1, Math.round(Math.sqrt(total / 2.2)));
  const dot = Math.min(11, (scale * 0.6) / (row - 1 || 1) * 0.42);
  const summary = parts.map((p, i) => `${p.label} ${counts[i]}`).join(', ');
  return <figure className="seatchart">
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Expected seats, left to right: ${summary}. Parliament of ${total}.`}>
      {seats.map((s, i) => <circle key={i} cx={pad + s.x * scale} cy={pad + s.y * scale} r={dot} fill={parts[owner[i]]?.colour ?? OTHER} />)}
      <text x={W / 2} y={H - 70} textAnchor="middle" className="seatchart-total">{total}</text>
      <text x={W / 2} y={H - 46} textAnchor="middle" className="seatchart-sub">expected seats</text>
    </svg>
    <ul className="seatchart-key">{parts.map((p, i) => <li key={p.key}><span style={{ background: p.colour }} aria-hidden="true" /><b>{p.label}</b> {counts[i]}
      {Number.isNaN(p.lower) ? null : <small> ({p.lower}–{p.upper})</small>}</li>)}</ul>
    <figcaption>Average seats per party across simulated elections, rounded so the dots add up to a Parliament of {total}. Brackets give the 80% range. Dots show the single most typical picture, not the only one.</figcaption>
  </figure>;
}
