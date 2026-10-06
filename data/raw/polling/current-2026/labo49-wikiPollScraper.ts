import * as cheerio from "cheerio";
import { PARTIES } from "./parties";
import type { Poll } from "./types";

// Header text -> party code, matched case-insensitively against each table's
// own column headers rather than assumed by position, so column reordering
// (or a different minor-party lineup, e.g. the 2023 page's "NCP" column)
// doesn't silently corrupt the data.
const HEADER_TO_CODE: Record<string, string> = Object.fromEntries(
  PARTIES.filter((p) => p.code !== "OTH").map((p) => [p.code, p.code])
);
HEADER_TO_CODE["OTHERS"] = "OTH";
// The Opportunities Party's column header changed from "TOP" to "OPP" on the
// live page at some point after this scraper was written -- every row's TOP
// value silently vanished as of that day's refresh (the column just stopped
// matching), corrupting the *historical* data too, since every run re-scrapes
// the full table rather than only new rows.
HEADER_TO_CODE["OPP"] = "TOP";

export function stripFootnotes(text: string): string {
  return text.replace(/\[[a-z0-9]+\]/gi, "").trim();
}

/** Collapses plain hyphens to en-dashes in a pollster name, e.g. "1
 * News-Verian" -> "1 News–Verian", and inserts a missing space between a
 * leading number and the name that follows it, e.g. "1News" -> "1 News".
 * Wikipedia's own tables aren't internally consistent about either -- the
 * same house appears with different spacing/punctuation across different
 * rows, sometimes even within the same table -- which would otherwise
 * silently split one pollster into two entries in every pollster-filter UI
 * on the site. */
export function normalizePollsterName(name: string): string {
  return name.replace(/-/g, "–").replace(/^(\d+)(?=[A-Za-z])/, "$1 ");
}

export function parseNumber(raw: string): number | null {
  const cleaned = stripFootnotes(raw).replace(/,/g, "").trim();
  if (!cleaned || cleaned === "–" || cleaned === "-" || /^n\/a$/i.test(cleaned)) {
    return null;
  }
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Parses the *last* "D MMM YYYY" occurrence out of a date-range label (e.g.
 * "4 Sep – 8 Oct 2023" -> the poll's end date, "8 Oct 2023"). Preferred
 * over each row's `data-sort-value` attribute, which is usually correct but
 * has been observed stale/wrong on at least one live row (an "election
 * result" row template default that wasn't updated) -- the visible label is
 * the ground truth a reader would see, so trust it first.
 */
export function parseDateLabelToISO(label: string): string | null {
  const cleaned = stripFootnotes(label);
  const pattern = /(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})/g;
  const matches = [...cleaned.matchAll(pattern)];
  if (matches.length === 0) return null;
  const [, day, monthAbbr, year] = matches[matches.length - 1];
  const month = MONTHS.indexOf(monthAbbr) + 1;
  if (month === 0) return null;
  return `${year}-${String(month).padStart(2, "0")}-${day.padStart(2, "0")}`;
}

function findPollsTable($: cheerio.CheerioAPI, headingId: string): cheerio.Cheerio<import("domhandler").Element> {
  const heading = $(`#${headingId}`);
  if (heading.length === 0) {
    throw new Error(`Could not find #${headingId} heading on the page`);
  }
  const table = heading.closest("section").find("table.wikitable").first();
  if (table.length === 0) {
    throw new Error(`Could not find the polls table under #${headingId}`);
  }
  return table;
}

function hrefToSourceUrl(href: string | null | undefined): string | null {
  if (!href) return null;
  if (!href.startsWith("./") && !href.startsWith("#")) return href;
  return `https://en.wikipedia.org/wiki/${href.replace(/^\.\//, "")}`;
}

/** A freshly-parsed poll row, before the caller stamps a `firstSeenAt`. */
export type ScrapedPoll = Omit<Poll, "firstSeenAt">;

export interface ScrapeResult {
  polls: ScrapedPoll[];
  skipped: number;
}

/**
 * Parses a Wikipedia "opinion polling" nationwide-polls wikitable (Parsoid
 * HTML, e.g. from the REST /page/html/ endpoint) into Poll rows. `headingId`
 * is the id of the heading immediately above the table (e.g. "Table_of_polls"
 * on the current-election page, "Party_vote" on a past-election page).
 */
export function scrapeWikiPollTable(html: string, headingId: string): ScrapeResult {
  const $ = cheerio.load(html);
  const table = findPollsTable($, headingId);

  const allRows = table.find("tr");
  const headerCells = allRows.first().find("th");
  // NOTE: cheerio's .map() (like jQuery's) drops null/undefined return values
  // instead of keeping them the way Array.prototype.map does, which silently
  // shortens this array -- and misaligns every subsequent column index --
  // whenever a header doesn't match a known code (e.g. a minor party not in
  // PARTIES, such as the 2023 page's "NCP" column). Go via toArray() so a
  // native Array.map is used and unmapped columns stay as `null` in place.
  const columnCodes: (string | null)[] = headerCells.toArray().map((el) => {
    const text = $(el).text().trim().toUpperCase();
    if (text.startsWith("DATE")) return "DATE";
    if (text.startsWith("POLLING")) return "POLLSTER";
    if (text.startsWith("SAMPLE")) return "SAMPLE";
    if (text.startsWith("LEAD")) return "LEAD";
    return HEADER_TO_CODE[text] ?? null;
  });

  const polls: ScrapedPoll[] = [];
  let skipped = 0;

  allRows.slice(1).each((_, rowEl) => {
    const tds = $(rowEl).find("td");
    // Event-annotation rows (e.g. "Budget 2026 is delivered") and stray
    // spacer/header-repeat rows don't have one cell per column -- skip them.
    if (tds.length !== columnCodes.length) {
      skipped++;
      return;
    }

    const dateIdx = columnCodes.indexOf("DATE");
    const dateTd = tds.eq(dateIdx);
    const dateLabel = stripFootnotes(dateTd.text());
    const isoDate = parseDateLabelToISO(dateLabel) ?? dateTd.attr("data-sort-value") ?? null;
    if (!isoDate) {
      skipped++;
      return;
    }

    const pollsterTd = tds.eq(columnCodes.indexOf("POLLSTER"));
    const pollster = normalizePollsterName(stripFootnotes(pollsterTd.text()));
    const sourceUrl = hrefToSourceUrl(pollsterTd.find("a").first().attr("href"));

    const sampleSize = parseNumber(tds.eq(columnCodes.indexOf("SAMPLE")).text());

    const results: Poll["results"] = {};
    columnCodes.forEach((code, i) => {
      if (!code || code === "DATE" || code === "POLLSTER" || code === "SAMPLE" || code === "LEAD") {
        return;
      }
      const value = parseNumber(tds.eq(i).text());
      if (value !== null) {
        (results as Record<string, number>)[code] = value;
      }
    });

    polls.push({
      date: isoDate,
      dateLabel,
      pollster,
      sourceUrl,
      sampleSize,
      results,
    });
  });

  // Chronological, oldest first.
  polls.sort((a, b) => a.date.localeCompare(b.date));

  return { polls, skipped };
}

export interface Milestone {
  date: string;
  label: string;
  sourceUrl: string | null;
}

/**
 * Parses the same wikitable's event-annotation rows (the ones
 * `scrapeWikiPollTable` skips as not having one cell per data column) into
 * timeline milestones -- these render as a 2-cell row: a date cell and a
 * bolded description cell spanning the rest of the columns, e.g. "2 Mar
 * 2026 | The Strait of Hormuz is closed as part of the Iran war...". A
 * handful of other non-poll rows (blank spacers, the repeated header row
 * further down the page) also fail the "one cell per column" test but have
 * 0 or a different td count, so requiring exactly 2 tds is what isolates
 * genuine milestones.
 */
export function scrapeWikiMilestones(html: string, headingId: string): Milestone[] {
  const $ = cheerio.load(html);
  const table = findPollsTable($, headingId);
  const allRows = table.find("tr");

  const milestones: Milestone[] = [];
  allRows.slice(1).each((_, rowEl) => {
    const tds = $(rowEl).find("td");
    if (tds.length !== 2) return;

    const dateTd = tds.eq(0);
    const dateLabel = stripFootnotes(dateTd.text());
    const isoDate = parseDateLabelToISO(dateLabel) ?? dateTd.attr("data-sort-value") ?? null;
    if (!isoDate) return;

    const descTd = tds.eq(1);
    const label = stripFootnotes(descTd.text()).replace(/\s+/g, " ").trim();
    if (!label) return;

    milestones.push({ date: isoDate, label, sourceUrl: hrefToSourceUrl(descTd.find("a").first().attr("href")) });
  });

  milestones.sort((a, b) => a.date.localeCompare(b.date));
  return milestones;
}

/** Sandboxed dev environments route outbound HTTPS through a local proxy that
 * Node's fetch (unlike curl) doesn't pick up from HTTPS_PROXY automatically.
 * Harmless/no-op in environments (CI, production) with direct internet access. */
export async function installDevProxyIfPresent(): Promise<void> {
  const proxyUrl = process.env.HTTPS_PROXY || process.env.https_proxy;
  if (!proxyUrl) return;
  const { ProxyAgent, setGlobalDispatcher } = await import("undici");
  setGlobalDispatcher(new ProxyAgent(proxyUrl));
}
