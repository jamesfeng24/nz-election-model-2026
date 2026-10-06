# NZ Poll of Polls

A rolling poll-of-polls average for the 2026 New Zealand general election, built
with Next.js. Party support data is scraped from Wikipedia's [Opinion polling
for the 2026 New Zealand general
election](https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_New_Zealand_general_election)
page.

## What it does

- **Poll of polls**: for every date a new poll is published, averages the most
  recent result from each pollster active in the trailing 60 days (see
  `lib/pollOfPolls.ts`), so no single house is overweighted just for polling
  more often.
- **Trend chart**: the poll-of-polls average over time, per party.
- **All-polls table**: every individual survey since the 2023 election, linked
  back to its source.

## Getting started

```bash
npm install
npm run fetch-polls   # scrape the latest polls into data/polls.json
npm run dev           # http://localhost:3000
```

## Refreshing the data

```bash
npm run fetch-polls
```

This re-scrapes the Wikipedia polls table and overwrites `data/polls.json` and
`data/meta.json`. A GitHub Actions workflow
(`.github/workflows/refresh-polls.yml`) runs this daily and opens a PR when the
data has changed.

## Project structure

- `scripts/fetch-polls.ts` — scraper (Wikipedia REST API + cheerio).
- `lib/parties.ts` — party metadata and chart colors.
- `lib/pollOfPolls.ts` — poll-of-polls aggregation.
- `data/polls.json` — scraped poll data (committed, refreshed by the scraper).
- `components/` — chart, table, and snapshot UI.

## Deploying

Any Next.js host (e.g. [Vercel](https://vercel.com/new)) works out of the box
— `npm run build && npm start`.
