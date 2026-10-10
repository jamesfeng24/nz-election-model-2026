import type { PointerEvent, ReactNode } from 'react';

/** Where the pointer is, in the chart's own coordinates (its viewBox) and relative to its figure. */
export function chartPointer(e: PointerEvent<SVGSVGElement>, width: number, height: number) {
  const svg = e.currentTarget;
  const box = svg.getBoundingClientRect();
  const figure = (svg.closest('figure') ?? svg).getBoundingClientRect();
  return {
    x: (e.clientX - box.left) * (box.width ? width / box.width : 1),
    y: (e.clientY - box.top) * (box.height ? height / box.height : 1),
    left: e.clientX - figure.left,
    top: e.clientY - figure.top,
    figureWidth: figure.width,
  };
}

export type TipPlace = { left: number; top: number; figureWidth: number };

/** A small card beside the pointer; it flips to the left of the pointer on the right side of the chart. */
export function ChartTip({ place, children }: { place: TipPlace; children: ReactNode }) {
  const flip = place.figureWidth > 0 && place.left > place.figureWidth * 0.6;
  return (
    <div
      className="charttip"
      aria-hidden="true"
      style={{
        left: place.left,
        top: place.top,
        transform: flip ? 'translate(calc(-100% - 14px), 14px)' : 'translate(14px, 14px)',
      }}
    >
      {children}
    </div>
  );
}
