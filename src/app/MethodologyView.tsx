import type { ForecastSnapshot } from '../types/export';

/** Plain-language method note for the public. Facts here come from docs/nowcast-specification.md and config/nowcast-2026.json. */
export function MethodologyView({ adjustments }: { adjustments?: ForecastSnapshot['adjustments'] }) {
  return <article className="prose">
    <h2>What this forecast says</h2>
    <p>It answers one question: if the New Zealand general election were held under current political conditions, what would happen? It is not a prediction of how opinion will move between now and 7 November 2026, and it does not try to forecast campaign events. Each forecast carries the date of the poll refresh behind it.</p>
    <p>It is updated once after each weekly poll refresh and stops updating on election day, when the last forecast stays up, labelled with its date.</p>
    <h2>How to read the ranges</h2>
    <p>Every number comes from about 65,000 simulated elections. The 80% range is the central range of those simulations: in four of five simulated elections the result falls inside it. The 50% and 90% ranges sit alongside. These are not polling margins of error, and they do not cover movement in opinion after the forecast date. Probabilities are rounded to the nearest percent and their simulation error is under one percentage point.</p>
    <h2>How it is built</h2>
    <ol>
      <li><b>National support.</b> A statistical model combines the published national polls, allowing for each pollster's habitual lean and for polling error shared by the whole industry.</li>
      <li><b>Each electorate's party vote.</b> The national picture is spread across electorates using the 2023 results re-cast onto the 2026 boundaries, with extra uncertainty for local differences.</li>
      <li><b>Electorate winners.</b> Candidates' local shares are estimated from their party's local vote and how candidates have performed relative to their party at past elections. Seats with unusual local circumstances get wider uncertainty.</li>
      <li><b>Māori electorates.</b> These are modelled separately from seat-level polls where they exist; seats without a poll are estimated from the 2023 result carried forward and are less certain.</li>
      <li><b>Seats in Parliament.</b> Each simulated election is run through New Zealand's MMP rules (Electoral Act 1993 as at 1 January 2026): the 5% party-vote threshold or one electorate win, 120 seats shared by the Sainte-Laguë method, and overhang seats added on top.</li>
    </ol>
    <p>Groups such as NAT+ACT+NZF or LAB+GRN+TPM are seat arithmetic. They are not predictions of coalition agreements.</p>
    <h2>Data sources</h2>
    <p>Every poll used, and every seat poll found, is listed with its pollster, dates, sample and source on the <a href="../polls/">Polls page</a>.</p>
    <ul>
      <li>Opinion polls: the Wikipedia opinion-polling tables for the 2026 election (national polls, and polls of individual electorates including the Māori electorates), read weekly; supporting press releases from pollsters where cited. Wikipedia text is licensed CC BY-SA.</li>
      <li>Past election results, 2008 to 2023: New Zealand Electoral Commission official results, including the split-vote tables.</li>
      <li>2026 electorate boundaries and populations: Stats NZ and the Representation Commission.</li>
      <li>2026 candidates: Electoral Commission nominations and party announcements.</li>
      <li>MMP rules: Electoral Act 1993.</li>
    </ul>
    {adjustments && <>
      <h2>Manual adjustments</h2>
      <p>The current forecast includes manual adjustments by {adjustments.by}. Only the adjusted numbers are shown, so this section says what was changed and why.</p>
      <ul>{adjustments.items.map(a => <li key={a.what}><b>{a.what}.</b> {a.why}</li>)}</ul>
    </>}
    <h2>What it cannot do</h2>
    <p>It cannot see anything polls have not yet measured. Polls can be wrong in ways that move together, electorate polls are rare and small, and candidates' circumstances can change after the forecast date. The limitations listed with each forecast say what was missing or assumed at that date.</p>
    <p>This is an independent research project, not an official election service.</p>
  </article>;
}
