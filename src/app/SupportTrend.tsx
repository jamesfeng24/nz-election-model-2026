import { useState, type PointerEvent } from 'react';
import type { ForecastSnapshot } from '../types/export';
import { ChartTip, chartPointer, type TipPlace } from './chartHover';
import { longDate } from './format';
import { COLOURS, FALLBACK } from './partyColours';
import { partyLabel } from './partyNames';

const WIDTH = 720;
const HEIGHT = 360;
const MARGIN = { left: 40, right: 104, top: 14, bottom: 34 };
/** End labels closer than this are nudged apart. */
const MIN_LABEL_GAP = 12;
/** A pointer this close (in screen units) to a band still picks that band. */
const BAND_REACH = 8;
/** The chart opens at the start of the election year; a tick box shows the whole run since the 2023 election. */
const DEFAULT_START = '2026-01-01';
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_MS = 31 * 24 * 3600 * 1000;

const fieldworkMidpoint = (start: string | null, end: string) =>
  start ? (Date.parse(start) + Date.parse(end)) / 2 : Date.parse(end);

/** The national model's weekly estimate of support since the 2023 election, with each poll it used as a faint dot. */
export function SupportTrend({ snapshot }: { snapshot: ForecastSnapshot }) {
  const fullTrend = snapshot.evidence?.trend;
  const [sinceElection, setSinceElection] = useState(false);
  const [hover, setHover] = useState<{ party: number; week: number; place: TipPlace } | null>(null);
  if (!fullTrend) return null;
  const defaultStart = fullTrend.weeks.findIndex((week) => week >= DEFAULT_START);
  // A series that starts after the default (or has under two weeks left in it) is shown whole, without the tick box.
  const canWiden = defaultStart > 0 && fullTrend.weeks.length - defaultStart >= 2;
  const start = canWiden && !sinceElection ? defaultStart : 0;
  const trend = {
    ...fullTrend,
    weeks: fullTrend.weeks.slice(start),
    parties: fullTrend.parties.map((p) => ({
      ...p,
      mean: p.mean.slice(start),
      lower90: p.lower90.slice(start),
      upper90: p.upper90.slice(start),
    })),
  };
  const colour = (id: string, index: number) => COLOURS[id] ?? FALLBACK[index % FALLBACK.length];

  const firstWeek = Date.parse(trend.weeks[0]);
  const lastWeek = Date.parse(trend.weeks[trend.weeks.length - 1]);
  const polls = snapshot
    .evidence!.nationalPolls.filter((poll) => poll.usedInModel)
    .filter((poll) => fieldworkMidpoint(poll.fieldworkStart, poll.fieldworkEnd) >= firstWeek);
  const yMax = Math.ceil((Math.max(...trend.parties.flatMap((p) => p.upper90)) + 1) / 10) * 10;
  const x = (time: number) =>
    MARGIN.left + ((time - firstWeek) / (lastWeek - firstWeek)) * (WIDTH - MARGIN.left - MARGIN.right);
  const y = (value: number) => MARGIN.top + (1 - value / yMax) * (HEIGHT - MARGIN.top - MARGIN.bottom);
  const pointAt = (week: string, value: number) => `${x(Date.parse(week))},${y(value)}`;
  const line = (values: number[]) => trend.weeks.map((week, k) => pointAt(week, values[k])).join(' ');
  const band = (party: (typeof trend.parties)[number]) =>
    [
      line(party.upper90),
      [...trend.weeks]
        .reverse()
        .map((week, k) => pointAt(week, party.lower90[trend.weeks.length - 1 - k]))
        .join(' '),
    ].join(' ');

  const gridValues = Array.from({ length: yMax / 10 + 1 }, (_, k) => k * 10);
  // Year starts over a long run, month starts over a short one.
  const ticks: { time: number; label: string }[] = [];
  const longRun = lastWeek - firstWeek > 18 * MONTH_MS;
  const nextTick = (after: number) => {
    const date = new Date(after);
    return longRun
      ? Date.UTC(date.getUTCFullYear() + 1, 0, 1)
      : Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1);
  };
  for (let time = nextTick(firstWeek); time < lastWeek; time = nextTick(time)) {
    const date = new Date(time);
    const month = date.getUTCMonth();
    ticks.push({
      time,
      label: longRun ? String(date.getUTCFullYear()) : month === 0 ? `Jan ${date.getUTCFullYear()}` : MONTHS[month],
    });
  }

  const endLabels = trend.parties
    .map((party, index) => ({ party, index, at: y(party.mean[party.mean.length - 1]) }))
    .sort((a, b) => a.at - b.at);
  endLabels.forEach((label, k) => {
    if (k > 0 && label.at - endLabels[k - 1].at < MIN_LABEL_GAP) label.at = endLabels[k - 1].at + MIN_LABEL_GAP;
  });

  const summary = trend.parties
    .map((p) => `${partyLabel(snapshot, p.partyId)} ${p.mean[p.mean.length - 1].toFixed(1)}%`)
    .join(', ');
  const plotRight = WIDTH - MARGIN.right;
  const axisBottom = HEIGHT - MARGIN.bottom;

  // The week nearest the pointer, then the band the pointer is in; where bands overlap, the party whose estimate is
  // closest to the pointer.
  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    const at = chartPointer(e, WIDTH, HEIGHT);
    if (at.x < MARGIN.left || at.x > plotRight || at.y < MARGIN.top || at.y > axisBottom) return setHover(null);
    const time = firstWeek + ((at.x - MARGIN.left) / (plotRight - MARGIN.left)) * (lastWeek - firstWeek);
    const week = trend.weeks.reduce(
      (best, w, k) => (Math.abs(Date.parse(w) - time) < Math.abs(Date.parse(trend.weeks[best]) - time) ? k : best),
      0,
    );
    const value = (1 - (at.y - MARGIN.top) / (axisBottom - MARGIN.top)) * yMax;
    const reach = (BAND_REACH / (axisBottom - MARGIN.top)) * yMax;
    let party = -1;
    let bestScore = Infinity;
    trend.parties.forEach((p, index) => {
      const outside = Math.max(p.lower90[week] - value, value - p.upper90[week], 0);
      if (outside > reach) return;
      const score = (outside > 0 ? 1000 + outside : 0) + Math.abs(p.mean[week] - value);
      if (score < bestScore) {
        bestScore = score;
        party = index;
      }
    });
    setHover(party < 0 ? null : { party, week, place: at });
  };
  const hovered = hover && { ...hover, series: trend.parties[hover.party] };

  return (
    <figure className="trend">
      <svg
        onPointerMove={onMove}
        onPointerDown={onMove}
        onPointerLeave={() => setHover(null)}
        onPointerCancel={() => setHover(null)}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Weekly support since the 2023 election, ${longDate(trend.weeks[0])} to ${longDate(trend.weeks[trend.weeks.length - 1])}: ${summary}`}
      >
        {gridValues.map((value) => (
          <g key={value}>
            <line x1={MARGIN.left} x2={plotRight} y1={y(value)} y2={y(value)} className="grid" />
            <text x={MARGIN.left - 6} y={y(value) + 4} textAnchor="end" className="tick">
              {value}%
            </text>
          </g>
        ))}
        {ticks.map(({ time, label }) => (
          <g key={time}>
            <line x1={x(time)} x2={x(time)} y1={MARGIN.top} y2={axisBottom} className="grid" />
            <text x={x(time)} y={HEIGHT - 12} textAnchor="middle" className="tick">
              {label}
            </text>
          </g>
        ))}
        {trend.parties.map((party, index) =>
          polls.map((poll) => {
            const share = poll.shares.find((s) => s.partyId === party.partyId)?.percent;
            if (share == null) return null;
            return (
              <circle
                key={`${party.partyId}-${poll.id}`}
                cx={x(fieldworkMidpoint(poll.fieldworkStart, poll.fieldworkEnd))}
                cy={y(share)}
                r="1.8"
                fill={colour(party.partyId, index)}
                opacity="0.35"
              />
            );
          }),
        )}
        {trend.parties.map((party, index) => (
          <g key={party.partyId}>
            <polygon points={band(party)} fill={colour(party.partyId, index)} opacity="0.12" />
            <polyline fill="none" stroke={colour(party.partyId, index)} strokeWidth="2" points={line(party.mean)} />
          </g>
        ))}
        {hovered && (
          <circle
            cx={x(Date.parse(trend.weeks[hovered.week]))}
            cy={y(hovered.series.mean[hovered.week])}
            r="4.5"
            fill="#fff"
            stroke={colour(hovered.series.partyId, hover.party)}
            strokeWidth="2.5"
          />
        )}
        {endLabels.map(({ party, index, at }) => (
          <text
            key={party.partyId}
            x={plotRight + 6}
            y={at + 4}
            fill={colour(party.partyId, index)}
            className="endlabel"
          >
            {partyLabel(snapshot, party.partyId)}
          </text>
        ))}
      </svg>
      {hovered && (
        <ChartTip place={hovered.place}>
          <strong style={{ color: colour(hovered.series.partyId, hovered.party) }}>
            {partyLabel(snapshot, hovered.series.partyId)}
          </strong>{' '}
          {longDate(trend.weeks[hovered.week])}
          <br />
          {hovered.series.mean[hovered.week].toFixed(1)}%{' '}
          <span className="charttip-range">
            (90% range {hovered.series.lower90[hovered.week].toFixed(1)}–
            {hovered.series.upper90[hovered.week].toFixed(1)}%)
          </span>
        </ChartTip>
      )}
      {canWiden && (
        <label className="trend-toggle">
          <input type="checkbox" checked={sinceElection} onChange={(e) => setSinceElection(e.target.checked)} /> Since
          the 2023 election
        </label>
      )}
      <figcaption>
        {trend.basis} Dots are individual polls the model used. <a href="../polls/">Every poll, with sources</a>.
      </figcaption>
    </figure>
  );
}
