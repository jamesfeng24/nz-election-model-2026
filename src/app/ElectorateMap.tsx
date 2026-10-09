import { useEffect, useMemo, useState } from 'react';
import type { ForecastSnapshot } from '../types/export';
import { COLOURS } from './SeatChart';
import { partyLabel } from './partyNames';
import { prob } from './format';

interface MapSeat { id: string; name: string; kind: 'general' | 'maori'; path: string; box: [number, number, number, number] }
interface MapData { width: number; height: number; insets: { name: string; box: [number, number, number, number] }[]; seats: MapSeat[]; source: string }

/** One forecast seat as the map needs it. */
export interface MapForecast { id: string; name: string; kind: 'general' | 'maori'; leaderParty: string | null; leaderPartyName: string; leaderName: string; leaderP: number; available: boolean }

const INDEPENDENT = '#8b8f94';
const NO_FORECAST = '#d9dedb';
/** Names compared without case, macrons, hyphens or spaces, so "Tāmaki Makaurau" matches however the export spells it. */
const key = (name: string) => name.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');

/** Darker for seats the model is surer of: toss-ups are pale, safe seats solid. */
export const opacityFor = (p: number) => 0.2 + 0.8 * Math.max(0, Math.min(1, (p - 0.4) / 0.6));

function fillFor(seat: MapForecast | undefined) {
  if (!seat || !seat.available) return { fill: NO_FORECAST, opacity: 1 };
  return { fill: seat.leaderParty ? COLOURS[seat.leaderParty] ?? INDEPENDENT : INDEPENDENT, opacity: opacityFor(seat.leaderP) };
}

function Shapes({ seats, forecasts, onSelect, hrefBase, hover, setHover }: {
  seats: MapSeat[]; forecasts: Map<string, MapForecast>; onSelect?: (id: string) => void; hrefBase: string;
  hover: string | null; setHover: (id: string | null) => void;
}) {
  return <>{seats.map(shape => {
    const f = forecasts.get(`${shape.kind}:${key(shape.name)}`);
    const { fill, opacity } = fillFor(f);
    const body = <path d={shape.path} fill={fill} fillOpacity={opacity} className={hover === f?.id && f ? 'hot' : undefined} vectorEffect="non-scaling-stroke" />;
    if (!f) return <g key={shape.id}>{body}<title>{shape.name}</title></g>;
    return <a key={shape.id} href={`${hrefBase}#seat=${f.id}`} onClick={onSelect ? e => { e.preventDefault(); onSelect(f.id); } : undefined}
      onMouseEnter={() => setHover(f.id)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(f.id)} onBlur={() => setHover(null)}
      aria-label={`${shape.name}: ${f.available ? `${f.leaderName} ${prob(f.leaderP)} to win` : 'no forecast'}`}>
      {body}<title>{shape.name}{f.available ? `: ${f.leaderName} (${f.leaderPartyName}) ${prob(f.leaderP)}` : ': no forecast'}</title></a>;
  })}</>;
}

const intersects = (a: [number, number, number, number], [x, y, w, h]: [number, number, number, number]) =>
  !(a[2] < x || a[0] > x + w || a[3] < y || a[1] > y + h);

/** Clickable map of the 2026 electorates, shaded by the most likely winner's party and how sure the model is. */
export function ElectorateMap({ snapshot, forecasts, onSelect, hrefBase = '' }: { snapshot: ForecastSnapshot; forecasts: MapForecast[]; onSelect?: (id: string) => void; hrefBase?: string }) {
  const [data, setData] = useState<MapData | 'failed' | null>(null);
  const [kind, setKind] = useState<'general' | 'maori'>('general');
  const [hover, setHover] = useState<string | null>(null);
  useEffect(() => { let live = true; import('../../data/processed/site-map/2026/map.json').then(m => live && setData(m.default as unknown as MapData), () => live && setData('failed')); return () => { live = false; }; }, []);
  const byName = useMemo(() => new Map(forecasts.map(f => [`${f.kind}:${key(f.name)}`, f])), [forecasts]);
  const parties = useMemo(() => [...new Set(forecasts.filter(f => f.available).map(f => f.leaderParty))], [forecasts]);
  if (data === null) return <p role="status">Loading map…</p>;
  if (data === 'failed') return null;
  const shown = data.seats.filter(s => s.kind === kind);
  const hot = hover ? forecasts.find(f => f.id === hover) : undefined;
  const shared = { forecasts: byName, onSelect, hrefBase, hover, setHover };
  const legendOf = (id: string | null) => ({ id: id ?? 'independent', name: id ? partyLabel(snapshot, id) : 'Independent', colour: id ? COLOURS[id] ?? INDEPENDENT : INDEPENDENT });
  return <section className="map" aria-labelledby="map-heading">
    <h2 id="map-heading">Map of electorates</h2>
    <div className="maptoggle" role="group" aria-label="Which electorates to show">
      <button type="button" aria-pressed={kind === 'general'} onClick={() => setKind('general')}>General (64)</button>
      <button type="button" aria-pressed={kind === 'maori'} onClick={() => setKind('maori')}>Māori (7)</button>
    </div>
    <p className="maphint" aria-live="polite">{hot ? (hot.available ? `${hot.name}: ${hot.leaderName}, ${hot.leaderPartyName}, ${prob(hot.leaderP)} to win` : `${hot.name}: no forecast available`) : 'Select a seat to see its forecast.'}</p>
    <div className="mapgrid">
      <svg viewBox={`0 0 ${data.width} ${data.height}`} className="mapmain" role="group" aria-label={`Map of the ${kind === 'general' ? 'general' : 'Māori'} electorates, coloured by the most likely winner's party`}>
        <Shapes seats={shown} {...shared} />
      </svg>
      {kind === 'general' && <div className="mapinsets">{data.insets.map(inset => <figure key={inset.name}>
        <svg viewBox={inset.box.join(' ')} role="group" aria-label={`${inset.name}, enlarged`}><Shapes seats={shown.filter(s => intersects(s.box, inset.box))} {...shared} /></svg>
        <figcaption>{inset.name}</figcaption></figure>)}</div>}
    </div>
    <ul className="maplegend" aria-label="Colour key">{parties.map(legendOf).map(l => <li key={l.id}><span style={{ background: l.colour }} aria-hidden="true" />{l.name}</li>)}</ul>
    <p className="maplegend2"><span className="fade" aria-hidden="true" /> Paler seats are closer contests; solid seats are safer. Colour shows the party of the candidate most likely to win, not a poll of that seat. Outlines are simplified for drawing and the Chatham Islands are not shown.</p>
  </section>;
}
