import type { ForecastSnapshot } from '../types/export';
import { PRIMARY_INTERVAL_LEVEL } from '../types/domain';
import { partyLabel } from './partyNames';
import { COLOURS, FALLBACK, HEADLINE_ORDER } from './SeatChart';
import { prob } from './format';

const rank = (id: string) => { const i = HEADLINE_ORDER.indexOf(id); return i < 0 ? HEADLINE_ORDER.length : i; };

/**
 * Seats by party as one row each, in the headline order: a plain bar in the party's colour drawn at the median, then the
 * numbers (median, 80% range, electorate and list seats, chance of overhang), so the extra seats are never hidden in a footnote.
 */
export function SeatBars({ snapshot }: { snapshot: ForecastSnapshot }) {
  if (snapshot.seatLayer.status !== 'available') return null;
  const { parties } = snapshot.seatLayer.summary;
  const rows = [...parties].sort((a, b) => rank(a.partyId) - rank(b.partyId)).map((p, i) => {
    const r80 = p.seats.find(v => v.level === PRIMARY_INTERVAL_LEVEL)!;
    return { p, lower: r80.lower, upper: r80.upper, colour: COLOURS[p.partyId] ?? FALLBACK[i % FALLBACK.length] };
  });
  const axisMax = Math.max(10, Math.ceil(Math.max(...rows.map(r => r.upper)) / 10) * 10);
  const x = (v: number) => `${(v / axisMax) * 100}%`;
  return <div className="seatbars">
    <table>
      <caption>Seats by party across simulated elections: median with 80% range, and the average split into electorate seats and list seats.</caption>
      <thead><tr><th scope="col">Party</th><th scope="col"><span className="sr-only">Bar</span></th><th scope="col">Median</th><th scope="col">80% range</th><th scope="col">Electorate</th><th scope="col">List</th><th scope="col">Overhang</th></tr></thead>
      <tbody>{rows.map(({ p, lower, upper, colour }) => <tr key={p.partyId}>
        <th scope="row">{partyLabel(snapshot, p.partyId)}</th>
        <td className="barcell"><div className="seatbar" role="img" aria-label={`${partyLabel(snapshot, p.partyId)}: median ${p.seats[0].median} seats`}>
          <span style={{ background: colour, width: x(p.seats[0].median) }} />
        </div></td>
        <td className="num"><strong>{p.seats[0].median}</strong></td><td className="num">{lower} – {upper}</td>
        <td className="num">{p.meanElectorateSeats.toFixed(1)}</td><td className="num">{p.meanListSeats.toFixed(1)}</td>
        <td className="num">{prob(p.probOverhang.p)}</td></tr>)}</tbody>
    </table>
    <p className="legend">Bars show median seats. Electorate seats are won in an electorate; list seats come from the party vote; both are averages. Overhang: the chance the party wins more electorate seats than its party vote entitles it to.</p>
  </div>;
}

/** One paragraph on overhang: how likely it is and how big Parliament would be. */
export function OverhangNote({ snapshot }: { snapshot: ForecastSnapshot }) {
  if (snapshot.seatLayer.status !== 'available') return null;
  const { parliament } = snapshot.seatLayer.summary;
  const dist = Object.entries(parliament.overhangDistribution).map(([n, p]) => [Number(n), p] as const);
  const at = (k: number) => dist.find(([n]) => n === k)?.[1] ?? 0;
  const threeUp = dist.filter(([n]) => n >= 3).reduce((s, [, p]) => s + p, 0);
  const r80 = parliament.size.find(v => v.level === PRIMARY_INTERVAL_LEVEL)!;
  return <div className="overhang">
    <h3>Overhang</h3>
    <p>Parliament has 120 seats, plus any "overhang" seats: extra electorate seats a party wins beyond its party-vote share. Chance of at least one overhang seat: <strong>{prob(parliament.probAnyOverhang.p)}</strong>; average {parliament.meanOverhang.toFixed(1)} seat{parliament.meanOverhang.toFixed(1) === '1.0' ? '' : 's'}. Chance of none {prob(at(0))}, one seat {prob(at(1))}, two seats {prob(at(2))}, three or more {prob(threeUp)}. Parliament would have a median of {parliament.size[0].median} seats ({r80.lower} – {r80.upper}, 80% range).</p>
  </div>;
}
