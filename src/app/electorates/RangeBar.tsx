import { useLayoutEffect, useRef, useState } from 'react';
import type { IntervalSet } from '../../types/domain';
import { pct } from '../format';
import { intervalAt, mainRange } from '../intervals';
import { medianColour } from '../partyColours';

/** The spacing of the bars' faint gridlines, as a share of the vote. */
const gridStep = (axisMax: number) => (axisMax <= 0.25 ? 0.05 : 0.1);
/** Label spacings tried on the share axis (always a whole number of gridlines) and the least room a label needs. */
const LABEL_STEPS = [0.05, 0.1, 0.2, 0.5, 1];
const LABEL_ROOM_PX = 42;

interface Range {
  lower: number;
  upper: number;
}

/**
 * A candidate's share of the vote on the seat's shared axis: the 80% range in a light shade,
 * the 50% range solid and the median as a line. Hovering either range shows its bounds and the median.
 */
export function RangeBar({
  set,
  axisMax,
  label,
  colour,
}: {
  set: IntervalSet;
  axisMax: number;
  label: string;
  colour: string;
}) {
  const [tip, setTip] = useState<{ text: string; x: number } | null>(null);
  const range80 = mainRange(set);
  const range50 = intervalAt(set, 0.5);
  const position = (value: number) => `${(value / axisMax) * 100}%`;
  const extent = (range: Range) => ({
    background: colour,
    left: position(range.lower),
    width: `calc(${position(range.upper)} - ${position(range.lower)})`,
  });
  const showTip = (name: string, range: Range) => (event: React.MouseEvent) => {
    const bar = (event.currentTarget.parentElement as HTMLElement).getBoundingClientRect();
    const text = `${name} range ${pct(range.lower)} – ${pct(range.upper)} · median ${pct(range50.median)}`;
    setTip({ text, x: event.clientX - bar.left });
  };
  return (
    <div
      className="rangebar"
      role="img"
      aria-label={label}
      style={{ '--step': `${(gridStep(axisMax) / axisMax) * 100}%` } as React.CSSProperties}
      onMouseLeave={() => setTip(null)}
    >
      <span
        className="r80"
        style={extent(range80)}
        onMouseMove={showTip('80%', range80)}
        onMouseEnter={showTip('80%', range80)}
      />
      <span
        className="r50"
        style={extent(range50)}
        onMouseMove={showTip('50%', range50)}
        onMouseEnter={showTip('50%', range50)}
      />
      <span className="median" style={{ left: position(range50.median), background: medianColour(colour) }} />
      {tip && (
        <span className="rangetip" style={{ left: tip.x }}>
          {tip.text}
        </span>
      )}
    </div>
  );
}

/**
 * The percentage scale shared by every bar in the table. Labels thin out on a narrow screen: the smallest tick
 * spacing that leaves each label its room is used.
 */
export function ShareAxis({ axisMax }: { axisMax: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const measure = () => setWidth(element.getBoundingClientRect().width);
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Without a measured width (before layout) the gridline spacing is used.
  const step =
    LABEL_STEPS.find(
      (candidate) => candidate >= gridStep(axisMax) && (width <= 0 || (candidate / axisMax) * width >= LABEL_ROOM_PX),
    ) ?? 1;
  const ticks = Array.from({ length: Math.floor(axisMax / step + 1e-9) + 1 }, (_, i) => i * step);
  return (
    <div className="shareaxis" aria-hidden="true" ref={ref}>
      {ticks.map((tick) => {
        const atEnd = Math.abs(tick - axisMax) < 1e-9;
        return (
          <span
            key={tick}
            className={tick === 0 ? 'start' : atEnd ? 'end' : undefined}
            style={{ left: `${(tick / axisMax) * 100}%` }}
          >
            {Math.round(tick * 100)}%
          </span>
        );
      })}
    </div>
  );
}
