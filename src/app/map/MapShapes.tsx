import { useId } from 'react';
import { chance } from '../format';
import { partyColour } from '../partyColours';
import { incumbentNote, opacityFor, seatKey, type MapForecast, type MapSeat } from './types';

const NO_FORECAST_COLOUR = '#d9dedb';

function fillFor(seat: MapForecast | undefined, highlight: Set<string> | null) {
  if (!seat || !seat.available || (highlight && !highlight.has(seat.id))) {
    return { fill: NO_FORECAST_COLOUR, opacity: 1 };
  }
  return { fill: partyColour(seat.leaderParty), opacity: opacityFor(seat.leaderP) };
}

/**
 * The seats as links to their seat page. `stripe` is the stripe period in drawing units,
 * set per drawing so the stripes look the same size on screen.
 */
export function MapShapes({
  seats,
  forecasts,
  onSelect,
  hrefBase,
  hover,
  setHover,
  stripe,
  highlight,
}: {
  seats: MapSeat[];
  forecasts: Map<string, MapForecast>;
  onSelect?: (id: string) => void;
  hrefBase: string;
  hover: string | null;
  setHover: (id: string | null) => void;
  stripe: number;
  highlight: Set<string> | null;
}) {
  const stripePattern = useId().replace(/:/g, '');
  return (
    <>
      <defs>
        <pattern
          id={stripePattern}
          width={stripe}
          height={stripe}
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width={stripe / 2} height={stripe} fill="#fff" fillOpacity=".7" />
        </pattern>
      </defs>
      {seats.map((shape) => {
        const forecast = forecasts.get(`${shape.kind}:${seatKey(shape.name)}`);
        const { fill, opacity } = fillFor(forecast, highlight);
        const body = (
          <>
            <path
              d={shape.path}
              fill={fill}
              fillOpacity={opacity}
              className={forecast && hover === forecast.id ? 'hot' : undefined}
              vectorEffect="non-scaling-stroke"
            />
            {forecast?.partyFlip && (!highlight || highlight.has(forecast.id)) && (
              <path d={shape.path} fill={`url(#${stripePattern})`} className="flip" pointerEvents="none" />
            )}
          </>
        );
        if (!forecast) {
          return (
            <g key={shape.id}>
              {body}
              <title>{shape.name}</title>
            </g>
          );
        }
        const summary = forecast.available
          ? `${forecast.leaderName} ${chance(forecast.leaderP, forecast.leaderRange)} to win`
          : 'no forecast';
        return (
          <a
            key={shape.id}
            href={`${hrefBase}#seat=${forecast.id}`}
            onClick={
              onSelect
                ? (event) => {
                    event.preventDefault();
                    onSelect(forecast.id);
                  }
                : undefined
            }
            onMouseEnter={() => setHover(forecast.id)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(forecast.id)}
            onBlur={() => setHover(null)}
            aria-label={`${shape.name}: ${summary}${incumbentNote(forecast)}`}
          >
            {body}
            <title>
              {shape.name}
              {forecast.available
                ? `: ${forecast.leaderName} (${forecast.leaderPartyName}) ${chance(forecast.leaderP, forecast.leaderRange)}`
                : ': no forecast'}
              {incumbentNote(forecast)}
            </title>
          </a>
        );
      })}
    </>
  );
}
