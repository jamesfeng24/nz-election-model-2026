import type { ForecastSnapshot } from '../types/export';

export function MethodologyView({
  adjustments,
  incumbency,
}: {
  adjustments?: ForecastSnapshot['adjustments'];
  incumbency?: ForecastSnapshot['incumbency'];
}) {
  return (
    <article className="prose">
      <h2>What the forecast says</h2>
      <p>
        It answers one question: if the election were held today, what would happen? It does not predict how opinion
        will move before 7 November 2026 or forecast campaign events. Each forecast carries the date of the poll refresh
        behind it.
      </p>
      <p>
        It is updated after each weekly poll refresh and stops on election day. The last forecast stays up, labelled
        with its date.
      </p>
      <h2>How to read the ranges</h2>
      <p>
        Every number comes from about 65,000 simulated elections. The 80% range holds the middle four-fifths of them.
        Electorate pages also show a 50% range, which holds the middle half. These are not polling margins of error, and
        they do not cover changes in opinion after the forecast date. Probabilities are rounded to the nearest percent;
        simulation error is under one percentage point.
      </p>
      <h2>How it is built</h2>
      <ol>
        <li>
          <b>National support.</b> A statistical model combines the national polls, allowing for each pollster's usual
          lean and for polling error shared across the industry.
        </li>
        <li>
          <b>Each electorate's party vote.</b> The national picture is spread across electorates using the 2023 results
          re-cast onto the 2026 boundaries, with extra uncertainty for local differences.
        </li>
        <li>
          <b>Electorate winners.</b> Candidates' local shares are estimated from their party's local vote and how
          candidates have performed relative to their party at past elections. Seats with unusual local circumstances
          get wider uncertainty.
        </li>
        <li>
          <b>Māori electorates.</b> These are modelled separately from seat-level polls where they exist; seats without
          a poll are estimated from the 2023 result carried forward and are less certain. For the polled seats the
          chance of winning is shown as a range between two estimates: one takes the seat polls at face value, the other
          allows for past Māori seat polls having ended up further from the results than the model's uncertainty
          implied.
        </li>
        <li>
          <b>Seats in Parliament.</b> Each simulated election is run through New Zealand's MMP rules: the 5% party-vote
          threshold or one electorate win, 120 seats shared by the Sainte-Laguë method, and overhang seats added on top.
        </li>
      </ol>
      <p>
        Groups such as National + ACT + NZ First or Labour + Greens + Te Pāti Māori are seat arithmetic, not predictions
        of coalition deals. "No majority" means neither of those two groups gets more than half of Parliament's seats.
      </p>
      <h2>Electorate seats, list seats and overhang</h2>
      <p>
        A party's seats come from two places: electorate seats, won by a candidate in one electorate, and list seats,
        allocated from the party vote so each party's total matches its share. Parliament has 120 seats. If a party wins
        more electorate seats than its party vote entitles it to, it keeps them all and the extra "overhang" seats are
        added on top. The forecast splits each party's seats into electorate and list and gives the chance of overhang.
      </p>
      <h2>Data sources</h2>
      <p>
        Every poll is listed with its pollster, dates, sample and source on the <a href="../polls/">Polls page</a>.
      </p>
      <ul>
        <li>
          Opinion polls: the Wikipedia opinion-polling tables for the 2026 election (national polls, and polls of
          individual electorates including the Māori electorates), read weekly; supporting press releases from pollsters
          where cited. Wikipedia text is licensed CC BY-SA.
        </li>
        <li>
          Past election results, 2008 to 2023: New Zealand Electoral Commission official results, including the
          split-vote tables.
        </li>
        <li>
          2026 electorate boundaries and populations: Stats NZ and the Representation Commission. The map on the
          electorates page redraws the Stats NZ outlines in simplified form, for illustration only.
        </li>
        <li>2026 candidates: Electoral Commission nominations and party announcements.</li>
        {incumbency && (
          <li>
            Incumbents: a candidate is marked as the incumbent when they are the sitting electorate MP, as shown on{' '}
            <a href={incumbency.url}>{incumbency.label}</a> ({incumbency.asOf}), and are standing in that seat or the
            2026 seat that took over most of it. List MPs are not marked. The marker is shown so you can see who the
            sitting MP is; it does not change the forecast.
          </li>
        )}
        <li>MMP rules: Electoral Act 1993.</li>
      </ul>
      {adjustments && (
        <>
          <h2>Manual adjustments</h2>
          <p>
            The current forecast includes manual adjustments by {adjustments.by}. Only the adjusted numbers are shown,
            so this section says what was changed and why.
          </p>
          <ul>
            {adjustments.items.map((a) => (
              <li key={a.what}>
                <b>{a.what}.</b> {a.why}
              </li>
            ))}
          </ul>
        </>
      )}
    </article>
  );
}
