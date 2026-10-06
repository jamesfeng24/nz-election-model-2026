/**
 * Scrapes the "Table of polls" from Wikipedia's opinion-polling page for the
 * next New Zealand general election and writes the result to data/polls.json.
 *
 * Run with: npm run fetch-polls
 */
import { readFile, writeFile } from "node:fs/promises";
import { installDevProxyIfPresent, scrapeWikiPollTable } from "../lib/wikiPollScraper";
import type { Poll } from "../lib/types";

const WIKI_PAGE = "Opinion_polling_for_the_2026_New_Zealand_general_election";
const SOURCE_URL = `https://en.wikipedia.org/api/rest_v1/page/html/${WIKI_PAGE}`;
const OUTPUT_PATH = new URL("../data/polls.json", import.meta.url);
const META_PATH = new URL("../data/meta.json", import.meta.url);
const NEW_POLLS_PATH = new URL("../data/newPolls.json", import.meta.url);

/** Identifies the same poll row across runs -- pollster + the raw date-range
 * label (rather than the parsed ISO date) since that's exactly what's in the
 * source table and won't drift if date parsing ever changes. */
function pollKey(p: Pick<Poll, "pollster" | "dateLabel">): string {
  return `${p.pollster}|${p.dateLabel}`;
}

async function loadPreviousFirstSeen(): Promise<Map<string, string>> {
  try {
    const raw = await readFile(OUTPUT_PATH, "utf-8");
    const previous = JSON.parse(raw) as Poll[];
    // Pre-migration data has no firstSeenAt at all; fall back to the poll's
    // own survey date so the migration run doesn't flag ~100 pre-existing
    // polls as newly added just because the field is new.
    return new Map(previous.map((p) => [pollKey(p), p.firstSeenAt ?? p.date]));
  } catch {
    return new Map();
  }
}

async function main() {
  await installDevProxyIfPresent();

  const res = await fetch(SOURCE_URL, {
    headers: { "User-Agent": "nzpolls-scraper (https://github.com/labo49/nzpolls)" },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ${SOURCE_URL}: ${res.status} ${res.statusText}`);
  }
  const html = await res.text();
  const { polls: scraped, skipped } = scrapeWikiPollTable(html, "Table_of_polls");

  const runTimestamp = new Date().toISOString();
  const previousFirstSeen = await loadPreviousFirstSeen();

  const polls: Poll[] = scraped.map((p) => ({
    ...p,
    // A poll not seen in the previous run's data is new as of this run; a
    // poll already on record keeps whichever timestamp it first got, so it
    // doesn't re-appear as "new" every day it's still in the table.
    firstSeenAt: previousFirstSeen.get(pollKey(p)) ?? runTimestamp,
  }));

  const newPolls = polls.filter((p) => p.firstSeenAt === runTimestamp && !previousFirstSeen.has(pollKey(p)));

  await writeFile(OUTPUT_PATH, JSON.stringify(polls, null, 2) + "\n", "utf-8");
  await writeFile(
    META_PATH,
    JSON.stringify({ fetchedAt: runTimestamp, source: `https://en.wikipedia.org/wiki/${WIKI_PAGE}` }, null, 2) + "\n",
    "utf-8"
  );
  await writeFile(NEW_POLLS_PATH, JSON.stringify(newPolls, null, 2) + "\n", "utf-8");
  console.log(
    `Wrote ${polls.length} rows to data/polls.json (${newPolls.length} new, skipped ${skipped} non-poll rows).`
  );
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
