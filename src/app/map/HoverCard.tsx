import { prob } from '../format';
import type { MapForecast } from './types';

/** The favourite, then every candidate with chance of winning, median vote share and incumbent tag. */
export function HoverCard({ seat }: { seat: MapForecast }) {
  if (!seat.available) {
    return (
      <>
        <h3>{seat.name}</h3>
        <p>No forecast available.</p>
      </>
    );
  }
  const noSittingMp = seat.incumbentStatus !== 'unknown' && !seat.incumbent;
  return (
    <>
      <h3>{seat.name}</h3>
      <p className="winner">
        Most likely winner: <strong>{seat.leaderName}</strong> ({seat.leaderPartyName}), {prob(seat.leaderP)}
        {noSittingMp ? '. No sitting MP is standing here' : ''}
      </p>
      <table>
        <thead>
          <tr>
            <th>Candidate</th>
            <th>Chance of winning</th>
            <th>Share of electorate vote</th>
          </tr>
        </thead>
        <tbody>
          {seat.candidates.map((candidate, i) => (
            <tr key={candidate.id} className={i === 0 ? 'lead' : undefined}>
              <td>
                <span className="dot" style={{ background: candidate.colour }} aria-hidden="true" />
                {candidate.name} <small>{candidate.partyName}</small>
                {candidate.incumbent && (
                  <>
                    {' '}
                    <span className="incumbent">Incumbent</span>
                  </>
                )}
              </td>
              <td className="num">{prob(candidate.winP)}</td>
              <td className="num">{candidate.share === null ? '–' : `${(candidate.share * 100).toFixed(1)}%`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
