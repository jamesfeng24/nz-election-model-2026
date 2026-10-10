import type { ForecastSnapshot } from '../types/export';
import { prob } from './format';
import { mainRange } from './intervals';
import { COLOURS, FALLBACK, headlineRank } from './partyColours';
import { partyLabel } from './partyNames';

/** Seats by party, one row each: a bar at the median in the party's colour, then the numbers. */
export function SeatBars({ snapshot }: { snapshot: ForecastSnapshot }) {
  if (snapshot.seatLayer.status !== 'available') return null;
  const rows = [...snapshot.seatLayer.summary.parties]
    .sort((a, b) => headlineRank(a.partyId) - headlineRank(b.partyId))
    .map((party, i) => ({
      party,
      name: partyLabel(snapshot, party.partyId),
      range: mainRange(party.seats),
      colour: COLOURS[party.partyId] ?? FALLBACK[i % FALLBACK.length],
    }));
  const axisMax = Math.max(10, Math.ceil(Math.max(...rows.map((r) => r.range.upper)) / 10) * 10);

  return (
    <div className="seatbars">
      <table>
        <caption>
          Seats by party across simulated elections: median with 80% range, and the average split into electorate seats
          and list seats.
        </caption>
        <thead>
          <tr>
            <th scope="col">Party</th>
            <th scope="col">
              <span className="sr-only">Bar</span>
            </th>
            <th scope="col">Median</th>
            <th scope="col">80% range</th>
            <th scope="col">Electorate</th>
            <th scope="col">List</th>
            <th scope="col">Overhang</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ party, name, range, colour }) => {
            const median = party.seats[0].median;
            return (
              <tr key={party.partyId}>
                <th scope="row">{name}</th>
                <td className="barcell">
                  <div className="seatbar" role="img" aria-label={`${name}: median ${median} seats`}>
                    <span style={{ background: colour, width: `${(median / axisMax) * 100}%` }} />
                  </div>
                </td>
                <td className="num">
                  <strong>{median}</strong>
                </td>
                <td className="num">
                  {range.lower} – {range.upper}
                </td>
                <td className="num">{party.meanElectorateSeats.toFixed(1)}</td>
                <td className="num">{party.meanListSeats.toFixed(1)}</td>
                <td className="num">{prob(party.probOverhang.p)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="legend">
        Bars show median seats. Electorate seats are won in an electorate; list seats come from the party vote; both are
        averages. Overhang: the chance the party wins more electorate seats than its party vote entitles it to.
      </p>
    </div>
  );
}

/** How likely overhang is and how big Parliament would be. */
export function OverhangNote({ snapshot }: { snapshot: ForecastSnapshot }) {
  if (snapshot.seatLayer.status !== 'available') return null;
  const { parliament } = snapshot.seatLayer.summary;
  const distribution = Object.entries(parliament.overhangDistribution).map(([n, p]) => [Number(n), p] as const);
  const chanceOf = (extraSeats: number) => distribution.find(([n]) => n === extraSeats)?.[1] ?? 0;
  const threeOrMore = distribution.filter(([n]) => n >= 3).reduce((sum, [, p]) => sum + p, 0);
  const size = mainRange(parliament.size);
  const mean = parliament.meanOverhang.toFixed(1);
  return (
    <div className="overhang">
      <h3>Overhang</h3>
      <p>
        Parliament has 120 seats, plus any "overhang" seats: extra electorate seats a party wins beyond its party-vote
        share. Chance of at least one overhang seat: <strong>{prob(parliament.probAnyOverhang.p)}</strong>; average{' '}
        {mean} seat{mean === '1.0' ? '' : 's'}. Chance of none {prob(chanceOf(0))}, one seat {prob(chanceOf(1))}, two
        seats {prob(chanceOf(2))}, three or more {prob(threeOrMore)}. Parliament would have a median of{' '}
        {parliament.size[0].median} seats ({size.lower} – {size.upper}, 80% range).
      </p>
    </div>
  );
}
