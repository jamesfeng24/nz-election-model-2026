import type { ForecastSnapshot } from '../types/export';
import { hemicycle, hemicycleDot, largestRemainder } from './hemicycle';
import { mainRange } from './intervals';
import { COLOURS, FALLBACK, headlineRank } from './partyColours';
import { partyLabel } from './partyNames';

const OTHERS_COLOUR = '#a9b4b0';
const WIDTH = 640;
const EDGE_PADDING = 6;
const NORMAL_PARLIAMENT = 120;

interface Slice {
  key: string;
  label: string;
  mean: number;
  /** Absent for "Others", which has no range of its own. */
  range: { median: number; lower: number; upper: number } | null;
  colour: string;
}

/** One slice per party in headline order, plus "Others" for seats the listed parties do not account for. */
function slicesOf(snapshot: ForecastSnapshot): { slices: Slice[]; total: number } {
  const layer = snapshot.seatLayer.status === 'available' ? snapshot.seatLayer.summary : null;
  const parties = layer
    ? layer.parties.map((p) => ({ id: p.partyId, mean: p.meanSeats, seats: p.seats }))
    : snapshot.simulation.partySeatSummaries.map((p) => ({ id: p.partyId, mean: p.seats[0].median, seats: p.seats }));
  const slices: Slice[] = [...parties]
    .sort((a, b) => headlineRank(a.id) - headlineRank(b.id))
    .map((party, i) => {
      const { lower, upper } = mainRange(party.seats);
      return {
        key: party.id,
        label: partyLabel(snapshot, party.id),
        mean: party.mean,
        range: { median: party.seats[0].median, lower, upper },
        colour: COLOURS[party.id] ?? FALLBACK[i % FALLBACK.length],
      };
    });
  const listed = slices.reduce((sum, slice) => sum + slice.mean, 0);
  const size = layer ? layer.parliament.meanSize : listed;
  if (size - listed >= 0.5) {
    slices.push({ key: 'others', label: 'Others', mean: size - listed, range: null, colour: OTHERS_COLOUR });
  }
  return { slices, total: Math.round(size) };
}

/** Expected seats per party as a parliament chart, one dot per seat. */
export function SeatChart({ snapshot }: { snapshot: ForecastSnapshot }) {
  const { slices, total } = slicesOf(snapshot);
  const counts = largestRemainder(
    slices.map((slice) => slice.mean),
    total,
  );
  const owners = counts.flatMap((count, i) => Array<number>(count).fill(i));
  const seats = hemicycle(total);

  // The margin is the dot radius plus a few units, so no dot is clipped.
  const dotRatio = hemicycleDot(total);
  const padding = ((dotRatio * WIDTH) / 2 + EDGE_PADDING) / (1 + dotRatio);
  const scale = (WIDTH - 2 * padding) / 2;
  const dotRadius = dotRatio * scale;
  const height = 2 * padding + scale;

  const summary = slices.map((slice, i) => `${slice.label} ${counts[i]}`).join(', ');
  const overhang = total - NORMAL_PARLIAMENT;
  return (
    <figure className="seatchart">
      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
        role="img"
        aria-label={`Expected seats, left to right: ${summary}. Parliament of ${total}.`}
      >
        {seats.map((seat, i) => (
          <circle
            key={i}
            cx={padding + seat.x * scale}
            cy={padding + seat.y * scale}
            r={dotRadius}
            fill={slices[owners[i]]?.colour ?? OTHERS_COLOUR}
          />
        ))}
        <text x={WIDTH / 2} y={height - 70} textAnchor="middle" className="seatchart-total">
          {total}
        </text>
        <text x={WIDTH / 2} y={height - 46} textAnchor="middle" className="seatchart-sub">
          expected seats
        </text>
      </svg>
      <ul className="seatchart-key">
        {slices.map((slice, i) => (
          <li key={slice.key}>
            <span style={{ background: slice.colour }} aria-hidden="true" />
            <b>{slice.label}</b> {counts[i]}
            {slice.range && (
              <small>
                {' '}
                ({slice.range.lower}–{slice.range.upper})
              </small>
            )}
          </li>
        ))}
      </ul>
      <figcaption>
        Average seats per party, rounded to a Parliament of {total}.{' '}
        {overhang > 0
          ? `That is ${NORMAL_PARLIAMENT} seats plus ${overhang} expected overhang seat${overhang === 1 ? '' : 's'}. `
          : ''}
        Brackets show the 80% range. One typical outcome, not the only one.
      </figcaption>
    </figure>
  );
}
