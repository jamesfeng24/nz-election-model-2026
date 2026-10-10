import { useEffect, useMemo, useRef, useState } from 'react';
import type { ForecastSnapshot } from '../types/export';
import { chance } from './format';
import { HoverCard } from './map/HoverCard';
import { MapShapes } from './map/MapShapes';
import { incumbentNote, seatKey, type Box, type MapData, type MapForecast } from './map/types';
import { partyColour } from './partyColours';
import { partyLabel } from './partyNames';

const intersects = (a: Box, [x, y, w, h]: Box) => !(a[2] < x || a[0] > x + w || a[3] < y || a[1] > y + h);

/** Space the hover bubble needs: it flips left or up near the right and bottom edges. */
const BUBBLE_WIDTH = 420;
const BUBBLE_HEIGHT = 260;

/** Clickable map of the 2026 electorates, shaded by the most likely winner's party and how sure the model is. */
export function ElectorateMap({
  snapshot,
  forecasts,
  onSelect,
  hrefBase = '',
  highlight = null,
}: {
  snapshot: ForecastSnapshot;
  forecasts: MapForecast[];
  onSelect?: (id: string) => void;
  hrefBase?: string;
  /** Seats to keep coloured; the rest are greyed out. */
  highlight?: Set<string> | null;
}) {
  const [data, setData] = useState<MapData | 'failed' | null>(null);
  const [kind, setKind] = useState<'general' | 'maori'>('general');
  const [hover, setHover] = useState<string | null>(null);
  const [pointer, setPointer] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const grid = useRef<HTMLDivElement>(null);

  // Positions the bubble inside the map area, so nothing on the page moves while hovering.
  const track = (clientX: number, clientY: number) => {
    const box = grid.current?.getBoundingClientRect();
    if (box) setPointer({ x: clientX - box.left, y: clientY - box.top, w: box.width, h: box.height });
  };

  useEffect(() => {
    let live = true;
    import('../../data/processed/site-map/2026/map.json').then(
      (module) => live && setData(module.default as unknown as MapData),
      () => live && setData('failed'),
    );
    return () => {
      live = false;
    };
  }, []);

  const bySeat = useMemo(() => new Map(forecasts.map((f) => [`${f.kind}:${seatKey(f.name)}`, f])), [forecasts]);
  const parties = useMemo(
    () => [...new Set(forecasts.filter((f) => f.available).map((f) => f.leaderParty))],
    [forecasts],
  );

  if (data === null) return <p role="status">Loading map…</p>;
  if (data === 'failed') return null;

  const shown = data.seats.filter((seat) => seat.kind === kind);
  const hasIncumbency = forecasts.some((f) => f.incumbentStatus !== 'unknown');
  const hovered = hover ? forecasts.find((f) => f.id === hover) : undefined;
  const shared = { forecasts: bySeat, onSelect, hrefBase, hover, setHover, highlight };
  const legend = parties.map((id) => ({
    id: id ?? 'independent',
    name: id ? partyLabel(snapshot, id) : 'Independent',
    colour: partyColour(id),
  }));
  const spoken = hovered
    ? (hovered.available
        ? `${hovered.name}: ${hovered.leaderName}, ${hovered.leaderPartyName}, ${chance(hovered.leaderP, hovered.leaderRange)} to win`
        : `${hovered.name}: no forecast available`) + incumbentNote(hovered)
    : '';
  const kindName = kind === 'general' ? 'general' : 'Māori';

  return (
    <section className="map" aria-labelledby="map-heading">
      <h2 id="map-heading">Map</h2>
      <div className="maptoggle" role="group" aria-label="Which electorates to show">
        <button type="button" aria-pressed={kind === 'general'} onClick={() => setKind('general')}>
          General (64)
        </button>
        <button type="button" aria-pressed={kind === 'maori'} onClick={() => setKind('maori')}>
          Māori (7)
        </button>
      </div>
      <p className="maphint">
        Hover over a seat for its candidates. Click it for full details.
        {highlight && ' Seats outside the filters are greyed out.'}
      </p>
      <p className="sr-only" aria-live="polite">
        {spoken}
      </p>
      <div
        className="mapgrid"
        ref={grid}
        onMouseMove={(event) => track(event.clientX, event.clientY)}
        onFocusCapture={(event) => {
          const box = (event.target as Element).getBoundingClientRect();
          track(box.left + box.width / 2, box.top + box.height / 2);
        }}
      >
        {hovered && pointer && (
          <div
            className={`mapbubble${pointer.x > pointer.w - BUBBLE_WIDTH ? ' left' : ''}${pointer.y > pointer.h - BUBBLE_HEIGHT ? ' up' : ''}`}
            style={{ left: pointer.x, top: pointer.y }}
            aria-hidden="true"
          >
            <HoverCard seat={hovered} />
          </div>
        )}
        <svg
          viewBox={`0 0 ${data.width} ${data.height}`}
          className="mapmain"
          role="group"
          aria-label={`Map of the ${kindName} electorates, coloured by the most likely winner's party`}
        >
          <MapShapes seats={shown} {...shared} stripe={data.width / 110} />
        </svg>
        {kind === 'general' && (
          <div className="mapinsets">
            {data.insets.map((inset) => (
              <figure key={inset.name}>
                <svg viewBox={inset.box.join(' ')} role="group" aria-label={`${inset.name}, enlarged`}>
                  <MapShapes
                    seats={shown.filter((seat) => intersects(seat.box, inset.box))}
                    {...shared}
                    stripe={inset.box[2] / 38}
                  />
                </svg>
                <figcaption>{inset.name}</figcaption>
              </figure>
            ))}
          </div>
        )}
      </div>
      <ul className="maplegend" aria-label="Colour key">
        {legend.map((item) => (
          <li key={item.id}>
            <span style={{ background: item.colour }} aria-hidden="true" />
            {item.name}
          </li>
        ))}
      </ul>
      <p className="maplegend2">
        <span className="fade" aria-hidden="true" /> Paler seats are closer contests; solid seats are safer. Colour
        shows the party of the candidate most likely to win, not a poll of that seat.
        {hasIncumbency && (
          <>
            {' '}
            <span className="flipkey" aria-hidden="true" /> Diagonal stripes mark a projected flip, a seat where the
            sitting MP is standing but the most likely winner is from another party. Hover or select any seat to see its
            incumbent.
          </>
        )}{' '}
        Outlines are simplified for drawing and the Chatham Islands are not shown.
      </p>
    </section>
  );
}
